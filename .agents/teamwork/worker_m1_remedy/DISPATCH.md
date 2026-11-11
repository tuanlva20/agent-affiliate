## 2026-11-10T07:50:01Z

You are worker_m1_remedy, assigned to remediate the empirical adversarial flaws identified during Milestone 1 Gate verification.

Your working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m1_remedy/
Maintain progress.md in your working directory.
Original request file: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
Project plan: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Failure Reports to Read First:
1. /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m1_challenger_1/handoff.md
2. /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m1_challenger_2/handoff.md

## Write Ownership:
You have exclusive write ownership of:
- `src/core/tone_validator.py`
- `src/core/config.py`
- `src/database/models.py`
- `src/database/session.py`
- Your working directory: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m1_remedy/`

## Concrete Tasks to Implement:

### 1. Harden Counterfeit & Robotic Regexes (`src/core/tone_validator.py`):
- Line 48: Add dot `\.` to the separator class in rep 1:1 regex:
  `(r"(?:\b|^|\s)rep\s*(1\s*[:\/\-\.]\s*1|1\s*1)(?:\b|$|\s)", "rep 1:1")`
- Lines 49, 53: Allow hyphens, underscores, and flexible spacing in `super-fake` and `like-auth`:
  `(r"\bsuper[\s\-_]*fake\b", "super fake")`
  `(r"\b(like|chuẩn|tuồn)[\s\-_]*auth\b", "like/chuẩn/tuồn auth")`
- Line 50-51: Support standalone `fake 1:1`, `fake 1`, and noun-preceded fake (`áo fake`, `giày fake`, `túi fake`, `đầm fake`):
  `(r"\b(hàng|hang|áo|quần|giày|dép|túi|ví|đầm|bản)?\s*fake(\s*1(?:\s*[:\/\-\.]\s*1)?)?\b", "fake")`
- Line 22: Allow optional `dạ em`, `xin`, `mừng` in greetings:
  `(r"\b(dạ\s+)?(em\s+)?(xin\s+|kính\s+)?chào\s+(mừng\s+)?quý\s+khách\b", "chào quý khách")`
  `(r"\bchào\s+mừng\s+(bạn|quý\s+vị|mọi\s+người)\s+đến\s+với\b", "chào mừng bạn đến với")`
- Lines 28-31: Match variations of AI self-identification:
  `(r"\btôi là\s+(một\s+)?trợ lý\s+(ảo|ai|thông minh|ngôn ngữ)\b", "tôi là trợ lý ảo/AI")`
  `(r"\b(như|là)\s+một\s+(trợ lý|mô hình)\s+(ảo|ai|ngôn ngữ)\b", "như một trợ lý/mô hình AI")`
  `(r"\bhy vọng\s+(thông tin\s+này\s+)?hữu ích\s+(cho\s+bạn|với\s+bạn)?\b", "hy vọng thông tin hữu ích")`

### 2. Fix Empty Section Handling in Env Overrides (`src/core/config.py`):
- Ensure nested dictionaries are created if the existing key is `None` (which PyYAML parses for empty sections like `database:\n`):
  ```python
  def _ensure_dict(data: Dict[str, Any], key: str) -> Dict[str, Any]:
      val = data.get(key)
      if not isinstance(val, dict):
          val = {}
          data[key] = val
      return val
  ```
  Replace unsafe `raw_data.setdefault(...)` calls with `_ensure_dict(raw_data, ...)`.

### 3. Database Models In-Place Mutation & Constraints (`src/database/models.py`):
- Wrap `JSONType` with `MutableDict.as_mutable`:
  ```python
  from sqlalchemy.ext.mutable import MutableDict
  JSONType = MutableDict.as_mutable(JSONB().with_variant(JSON(), "sqlite"))
  ```
- In `Channel` model:
  - Add `CheckConstraint("lifecycle_status IN ('warming', 'ready_to_post', 'cooldown', 'captcha_blocked')", name="chk_channel_lifecycle_status")` to `__table_args__`.
  - Add `VALID_LIFECYCLE_STATUSES = {"warming", "ready_to_post", "cooldown", "captcha_blocked"}`.
  - Add `@validates("lifecycle_status")` validator that raises `ValueError(f"Invalid lifecycle_status: {value}")` if `value not in self.VALID_LIFECYCLE_STATUSES`.

### 4. Database Session Concurrency, PRAGMA & Engine Cache (`src/database/session.py`):
- Enable SQLite foreign keys via SQLAlchemy event listener on `connect`:
  ```python
  from sqlalchemy import event

  # For SQLite engines:
  @event.listens_for(engine.sync_engine, "connect")
  def _set_sqlite_pragma(dbapi_connection, connection_record):
      cursor = dbapi_connection.cursor()
      cursor.execute("PRAGMA foreign_keys=ON")
      cursor.close()
  ```
- In `get_async_engine()`, when `force_new=True`: also pop the url from `_session_factories` (`_session_factories.pop(url, None)`) so sessions don't stay bound to the discarded engine.
- For SQLite concurrency under `get_db()`:
  Because in-memory SQLite with `StaticPool` shares a single DBAPI connection across all coroutines, protect concurrent transactions on SQLite by using an `asyncio.Lock()` per SQLite engine inside `get_db()`, ensuring that concurrent coroutines do not cross-pollute uncommitted transactions or reset shared connections.
  For PostgreSQL: ensure `pool_size=20, max_overflow=30, pool_timeout=30.0` are configured.

## Verification Protocol:
You MUST run and verify 100% PASS for:
1. `python3 scripts/m1_stress_harness.py` -> All 59 test cases must PASS!
2. `pytest tests/test_database_stress.py -v` -> All 8 stress tests must PASS!
3. `pytest tests/test_config.py tests/test_database.py -v` -> All 16 unit tests must PASS!
4. `pytest tests/e2e/ -v` -> All 61 E2E tests must PASS!

Write a comprehensive `handoff.md` in `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m1_remedy/` with full command outputs, and notify me with `send_message` when done.
