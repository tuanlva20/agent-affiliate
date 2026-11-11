# Adversarial Challenge Handoff Report — Milestone 1 Database Layer

**Agent**: `teamwork_challenger` (`m1_challenger_2`)  
**Verdict**: `REQUEST_CHANGES`  
**Overall Risk Assessment**: `CRITICAL`  
**Date**: 2026-11-10T07:45:30Z  

---

## 1. Observation

Adversarial stress testing was executed against `src/database/models.py` and `src/database/session.py` via the test suite `tests/test_database_stress.py`.

### Test Execution Command
```bash
pytest tests/test_database_stress.py -v
```

### Execution Output & Summary
```
============================= test session starts ==============================
collected 8 items

tests/test_database_stress.py::test_concurrency_50_parallel_coroutines_data_integrity FAILED [ 12%]
tests/test_database_stress.py::test_concurrency_transaction_isolation_and_cross_pollution FAILED [ 25%]
tests/test_database_stress.py::test_json_in_place_mutation_persistence FAILED [ 37%]
tests/test_database_stress.py::test_json_boundaries_deep_nesting_large_payload_and_unicode PASSED [ 50%]
tests/test_database_stress.py::test_cascade_delete_orm_niche_and_product PASSED [ 62%]
tests/test_database_stress.py::test_cascade_delete_database_level_bulk_sql FAILED [ 75%]
tests/test_database_stress.py::test_lifecycle_all_valid_states_progression PASSED [ 87%]
tests/test_database_stress.py::test_lifecycle_invalid_state_rejection_guard FAILED [100%]

========================= 5 failed, 3 passed in 0.81s ==========================
```

### Verbatim Failures and Code Anchors

1. **Failure 1: High-Concurrency Silent Data Loss**
   - **File**: `src/database/session.py:42-48`
   ```python
   if url.startswith("sqlite"):
       engine = create_async_engine(
           url,
           poolclass=StaticPool,
           connect_args={"check_same_thread": False},
           echo=False,
       )
   ```
   - **Verbatim Error**:
   ```
   AssertionError: 50 coroutines had 36 failures: [
     ValueError('Product prod_conc_002 missing! Silent data loss detected.'),
     ValueError('Product prod_conc_003 missing! Silent data loss detected.'),
     ValueError('Product prod_conc_004 missing! Silent data loss detected.')
   ]
   ```

2. **Failure 2: Transaction Isolation Cross-Pollution**
   - **File**: `src/database/session.py:98-115`
   - **Verbatim Error**:
   ```
   AssertionError: Transaction isolation failure: Dirty uncommitted data was persisted by concurrent commit!
   ```

3. **Failure 3: In-Place JSON Mutations Silently Dropped**
   - **File**: `src/database/models.py:30`
   ```python
   JSONType = JSONB().with_variant(JSON(), "sqlite")
   ```
   - **Verbatim Error**:
   ```
   AssertionError: In-place mutation dropped! Expected 9.8, got 6.0. JSONType lacks MutableDict.as_mutable() wrapper.
   assert 6.0 == 9.8
   ```

4. **Failure 4: Database-Level Bulk Delete Cascade Failure**
   - **File**: `src/database/session.py:42-48` (absence of SQLite foreign_keys pragma)
   - **Verbatim Error**:
   ```
   AssertionError: Database-level CASCADE failed! Channel orphaned after Niche bulk delete. SQLite foreign_keys PRAGMA is not enabled on connection.
   assert <src.database.models.Channel object at 0x10ed41f40> is None
   ```

5. **Failure 5: Channel Lifecycle Invalid State Rejection Missing**
   - **File**: `src/database/models.py:82-84`
   ```python
   # Lifecycle states: 'warming', 'ready_to_post', 'cooldown', 'captcha_blocked'
   lifecycle_status: Mapped[str] = mapped_column(
       String(30), default="warming", server_default="warming"
   )
   ```
   - **Verbatim Error**:
   ```
   Failed: DID NOT RAISE any of (ValueError, IntegrityError, DBAPIError)
   ```
   Invalid states `"banned"`, `"active"`, `"UNKNOWN_STATUS"`, and `""` were successfully inserted and persisted without any error.

---

## 2. Logic Chain

1. **From Observation 1 to Finding 1 (Silent Data Loss)**:
   - In `src/database/session.py`, `get_async_engine()` enforces `poolclass=StaticPool` for any URL starting with `sqlite`.
   - `StaticPool` holds a single DBAPI connection and supplies that exact same connection to all `AsyncSession` instances checked out concurrently.
   - When 50 coroutines run `get_db()` in parallel, they interleave their statements on this single connection.
   - When coroutine $A$ exits its `get_db()` block, `session.close()` triggers a connection rollback/reset.
   - Any coroutines $B, C, \dots$ that were mid-transaction with staged inserts have their uncommitted records silently wiped out without raising an exception to the caller.
   - Consequently, 36 out of 50 products were lost during parallel writes.

2. **From Observation 2 to Finding 2 (ACID Isolation Breach)**:
   - Because all sessions share the single physical connection under `StaticPool`, they share the single physical SQLite transaction.
   - When Task 1 flushes uncommitted "dirty" data, and Task 2 subsequently calls `session.commit()`, Task 2's commit statement issues `COMMIT` to SQLite, permanently committing Task 1's dirty data before Task 1 can raise an exception and trigger `session.rollback()`.
   - Conversely, when Task 1 rolls back, it clears Task 2's uncommitted work. This completely breaks transaction isolation.

3. **From Observation 3 to Finding 3 (In-Place JSON Mutation Loss)**:
   - In `src/database/models.py`, `JSONType` is a bare `JSONB().with_variant(JSON(), "sqlite")`.
   - SQLAlchemy's unit-of-work detects modifications by comparing object identity unless the type is wrapped with `sqlalchemy.ext.mutable.MutableDict.as_mutable()`.
   - When mutating a product's evaluation dictionary in-place (`product.evaluation_data['score'] = 9.8`), the object identity of `product.evaluation_data` remains unchanged.
   - SQLAlchemy flags the column as clean and does not emit an `UPDATE` SQL statement upon `session.commit()`. The mutation is silently discarded.

4. **From Observation 4 to Finding 4 (Missing Foreign Key PRAGMA in SQLite)**:
   - SQLite disables foreign key enforcement by default (`PRAGMA foreign_keys = OFF`).
   - `src/database/session.py` initializes the SQLite engine without configuring a connection listener to execute `PRAGMA foreign_keys = ON`.
   - Although ORM deletes (`session.delete(niche)`) trigger SQLAlchemy-level relationship cascades, direct/bulk SQL statements (`delete(Niche)...`) leave orphaned `Channel`, `Product`, and `VideoJob` records in the database.

5. **From Observation 5 to Finding 5 (Unchecked Lifecycle State Transitions)**:
   - The contract in `PROJECT.md` specifies four valid lifecycle states: `warming`, `ready_to_post`, `cooldown`, `captcha_blocked`.
   - `Channel.lifecycle_status` in `src/database/models.py` is defined as an unconstrained `String(30)`.
   - There is neither a `CheckConstraint` nor a `@validates("lifecycle_status")` model validator. Arbitrary invalid states can be persisted, allowing invalid state transitions that break downstream publishing workflows.

---

## 3. Challenges & Detailed Stress Test Results

### Challenge Summary

| Challenge ID | Severity | Dimension | Status |
|---|---|---|---|
| CH-01 | **CRITICAL** | High Concurrency: 50 Coroutines Silent Data Loss | **CONFIRMED DEFECT** |
| CH-02 | **CRITICAL** | High Concurrency: Cross-Task Transaction Pollution | **CONFIRMED DEFECT** |
| CH-03 | **HIGH** | JSON Boundaries: In-Place Mutation Drop | **CONFIRMED DEFECT** |
| CH-04 | **HIGH** | Cascade Deletes: SQLite Bulk SQL Foreign Key Enforcement | **CONFIRMED DEFECT** |
| CH-05 | **MEDIUM** | Lifecycle State Machine: Invalid State Guarding Missing | **CONFIRMED DEFECT** |

### Stress Test Results

| Test Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|
| `test_concurrency_50_parallel_coroutines_data_integrity` | 50 channels, 50 products, 50 jobs saved; 0 exceptions | 36 coroutines failed with missing products; only 14 products saved | **FAIL** |
| `test_concurrency_transaction_isolation_and_cross_pollution` | Dirty data rolled back; valid data committed | Dirty data committed by concurrent task commit | **FAIL** |
| `test_json_in_place_mutation_persistence` | `evaluation_data['score']` updated to 9.8 | Value remained 6.0; update dropped | **FAIL** |
| `test_json_boundaries_deep_nesting_large_payload_and_unicode` | 60 nested levels, 2MB payload, emoji intact | Persisted and reloaded identically | **PASS** |
| `test_cascade_delete_orm_niche_and_product` | Deleting Niche/Product deletes children via ORM | All child entities deleted cleanly | **PASS** |
| `test_cascade_delete_database_level_bulk_sql` | Bulk delete cascades at DB level | Channels & Products orphaned | **FAIL** |
| `test_lifecycle_all_valid_states_progression` | All 4 states saved and queried | Successfully saved all 4 states | **PASS** |
| `test_lifecycle_invalid_state_rejection_guard` | Rejects invalid states with error | Accepted all invalid strings | **FAIL** |

---

## 4. Caveats

- Testing was performed on `aiosqlite` (SQLite async) with both in-memory and file configurations. PostgreSQL was verified via connection parameters and configuration inspection; local Postgres instance required credentials not present in `.env`.
- High concurrency on PostgreSQL will bypass the `StaticPool` issue, but will instead be bound by SQLAlchemy's default `QueuePool` size (`pool_size=5`, `max_overflow=10`). 50 concurrent coroutines will raise `TimeoutError: QueuePool limit reached` unless `pool_size` and `max_overflow` are explicitly configured in `src/database/session.py`.

---

## 5. Conclusion & Verdict

**Verdict**: `REQUEST_CHANGES`

The database layer does NOT satisfy the adversarial stress criteria for Milestone 1. The implementation has two CRITICAL defects (silent data loss and broken transaction isolation under concurrency) and three HIGH/MEDIUM defects (in-place JSON mutations dropped, missing SQLite FK pragma, and lack of lifecycle status validation).

### Required Changes Before Milestone 1 Sign-Off:

1. **Fix In-Place JSON Mutation Tracking (`src/database/models.py`)**:
   Wrap `JSONType` with `MutableDict.as_mutable`:
   ```python
   from sqlalchemy.ext.mutable import MutableDict

   JSONType = MutableDict.as_mutable(JSONB().with_variant(JSON(), "sqlite"))
   ```

2. **Add Channel Lifecycle Status Validation & Constraints (`src/database/models.py`)**:
   Add a `CheckConstraint` and `@validates` on `Channel`:
   ```python
   from sqlalchemy import CheckConstraint
   from sqlalchemy.orm import validates

   class Channel(Base):
       __tablename__ = "channels"
       __table_args__ = (
           CheckConstraint(
               "lifecycle_status IN ('warming', 'ready_to_post', 'cooldown', 'captcha_blocked')",
               name="chk_channel_lifecycle_status",
           ),
       )

       VALID_LIFECYCLE_STATUSES = {"warming", "ready_to_post", "cooldown", "captcha_blocked"}

       @validates("lifecycle_status")
       def validate_lifecycle_status(self, key, value):
           if value not in self.VALID_LIFECYCLE_STATUSES:
               raise ValueError(f"Invalid lifecycle_status: {value}")
           return value
   ```

3. **Enable SQLite Foreign Keys PRAGMA (`src/database/session.py`)**:
   Add an event listener to enable foreign keys on SQLite connections:
   ```python
   from sqlalchemy import event

   @event.listens_for(engine.sync_engine, "connect")
   def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
       if "sqlite" in str(url):
           cursor = dbapi_connection.cursor()
           cursor.execute("PRAGMA foreign_keys=ON")
           cursor.close()
   ```

4. **Fix Concurrency and Connection Pooling (`src/database/session.py`)**:
   - For SQLite in-memory concurrency: Either serialize transactions with an `asyncio.Lock()` inside `get_db()` when `StaticPool` is active, or use a shared memory cache URI with `NullPool` / separate connections.
   - For PostgreSQL: Explicitly configure connection pool parameters in `create_async_engine`:
     `pool_size=20`, `max_overflow=30`, `pool_timeout=30.0`.

---

## 6. Verification Method

To independently verify these findings:
```bash
# Run the empirical stress test suite:
pytest tests/test_database_stress.py -v

# Run the original unit tests:
pytest tests/test_database.py -v
```

Invalidation conditions:
- All 8 tests in `tests/test_database_stress.py` pass with 0 failures.
- 50 concurrent coroutines write and read 50 channels, 50 products, and 50 video jobs with zero lost records.
- Mutating `evaluation_data['score']` in-place reflects in subsequent database sessions without manual reassignment.
