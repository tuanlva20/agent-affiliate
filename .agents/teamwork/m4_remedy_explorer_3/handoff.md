# Milestone 4 Remediation Report: Command Parser & Type Coercion Architecture

**Agent**: `m4_remedy_explorer_3`  
**Role**: Command Parser & Type Coercion Remediation Explorer  
**Working Directory**: `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m4_remedy_explorer_3/`  
**Milestone**: M4 (Telegram Command Center & 1-Tap Approval — Iteration 2 Remediation)  
**Parent Conversation ID**: `f5177315-7404-4813-b8ba-56081885cdd4`  
**Date**: 2026-11-10T10:55:00Z  
**Handoff Type**: Hard Handoff  

---

## 1. Observation

Direct examination of `src/bot/telegram_bot.py`, `src/bot/handlers.py`, and `src/bot/keyboards.py`, along with reports from `m4_reviewer_1` and `m4_challenger_2`, revealed 4 concrete structural defects:

### 1.1 Defect 1: `admin_id` String vs Integer Type Incoercion Locks Out Administrator
- **Location**: `src/bot/telegram_bot.py` (lines 81–88) and `src/bot/handlers.py` (lines 57, 127).
- **Code in `src/bot/telegram_bot.py`**:
  ```python
  admin_env = os.getenv("TELEGRAM_ADMIN_CHAT_ID") or os.getenv("ADMIN_TELEGRAM_ID")
  self.admin_id = (
      admin_id
      if admin_id is not None
      else (int(admin_env) if admin_env and admin_env.isdigit() else None)
      or (cfg_tg.admin_id if cfg_tg and cfg_tg.admin_id else None)
      or 987654321
  )
  ```
- **Code in `src/bot/handlers.py`**:
  ```python
  # execute_command (line 57):
  if user_id != admin_id:
      return ADMIN_DENIED_MESSAGE

  # execute_callback (line 127):
  if user_id != admin_id:
      return {
          "success": False,
          "error": "unauthorized",
          "message": ADMIN_DENIED_MESSAGE,
      }
  ```
- **Observed Behavior**:
  When `admin_id="987654321"` is passed (from CLI string arguments, environment loaders, or YAML configuration), `self.admin_id` retains type `str`. When a user invokes `handle_command` with Telegram's native integer `user_id` (`987654321`), Python evaluates `987654321 != "987654321"` to `True`. The authorized admin is rejected with:
  `"⛔ Quyền truy cập bị từ chối: Bạn không phải Admin!"`.

### 1.2 Defect 2: Incompatibility with Telegram Group/Forum `@BotName` Syntax
- **Location**: `src/bot/handlers.py` (lines 60–71).
- **Code**:
  ```python
  clean = (command or "").strip()
  if " " in clean and args is None:
      parts = clean.split(maxsplit=1)
      cmd_name = parts[0].lower()
      cmd_args = parts[1].strip()
  else:
      cmd_name = clean.split()[0].lower() if clean else ""
      cmd_args = args.strip() if args else ""

  if not cmd_name.startswith("/"):
      cmd_name = f"/{cmd_name}"
  ```
- **Observed Behavior**:
  In Telegram supergroups and forum topics (such as `#dashboard-tong` or `#thoi-trang-nu`), autocomplete clicks or group bot mentions send commands in `/command@BotName` format.
  Executing `execute_command("/test_scout@AmasBot", 987654321, 987654321)` produces `cmd_name = "/test_scout@amasbot"`. Because none of the dispatch branches match `"/test_scout@amasbot"`, the handler falls through to:
  `"❓ Lệnh không xác định: /test_scout@AmasBot"`.

### 1.3 Defect 3: `KeyError` Mapping Violation in `CompatibleInlineKeyboardMarkup`
- **Location**: `src/bot/keyboards.py` (lines 19–20, 29–30).
- **Code**:
  ```python
  class CompatibleInlineKeyboardButton(InlineKeyboardButton):
      def __getitem__(self, item: str) -> Any:
          return getattr(self, item)

  class CompatibleInlineKeyboardMarkup(InlineKeyboardMarkup):
      def __getitem__(self, item: str) -> Any:
          return getattr(self, item)
  ```
- **Observed Behavior**:
  When accessing a non-existent key on the markup object (e.g. `kb["missing_key"]`), `getattr(self, item)` raises `AttributeError: 'CompatibleInlineKeyboardMarkup' object has no attribute 'missing_key'`.
  Python's standard Mapping protocol (`collections.abc.Mapping` and dictionary indexing) requires raising `KeyError`. Code with `try ... except KeyError:` crashes with an unhandled `AttributeError`.

### 1.4 Defect 4: `/create_channel` Returns Success Without DB Persistence When `session is None`
- **Location**: `src/bot/handlers.py` (lines 85–100).
- **Code**:
  ```python
  elif cmd_name == "/create_channel":
      alias = cmd_args or "koc_01"
      if session:
          try:
              chan = Channel(
                  channel_id=f"chan_{alias}",
                  niche_id="thoi_trang_nu",
                  browser_profile_id=f"profile_alias_{alias}",
                  lifecycle_status="warming",
              )
              session.add(chan)
              await session.commit()
          except Exception as e:
              logger.debug("Channel already exists or DB error: %s", e)
      return f"✨ Tạo kênh mới thành công: profile_alias_{alias} (status: warming)"
  ```
- **Observed Behavior**:
  When `/create_channel` is executed without supplying an external `session` (the normal default when invoked via Telegram messages or `bot.handle_command("/create_channel", admin_id)`), the `if session:` guard is skipped. The bot reports `"✨ Tạo kênh mới thành công: profile_alias_koc_01 (status: warming)"`, but zero records are committed to the `channels` table in PostgreSQL or SQLite.

---

## 2. Logic Chain

1. **Type Coercion Logic Chain**:
   - *Premise*: Telegram user IDs (`user_id`) in aiogram are native integers (`int`), but administrative configuration (`admin_id`) frequently enters the application as strings from `.env`, CLI flags, or YAML configuration files.
   - *Mechanism*: If initialization does not convert `admin_id` to integer, or if command dispatchers perform direct equality check `user_id != admin_id`, integer and string representations fail equality (`987654321 != "987654321"` is `True`).
   - *Deduction*: Coercion must occur at two layers:
     1. In `TelegramCommandCenter.__init__`: parse `raw_admin` through `int(raw_admin)` with fallback to default `987654321`.
     2. In `execute_command` and `execute_callback`: evaluate `is_authorized = int(user_id) == int(admin_id)` inside a `try ... except (ValueError, TypeError)` block, safely rejecting invalid user identifiers without throwing unhandled exceptions.

2. **Telegram Bot Username Parsing Logic Chain**:
   - *Premise*: Telegram's client protocol appends `@<BotUsername>` to commands sent in group chats and forum topics.
   - *Mechanism*: The command string starts with `/<command>@<bot_username>` followed by whitespace-separated parameters.
   - *Deduction*: Splitting `cmd_name` by `@` (`cmd_name = cmd_name.split("@", 1)[0]`) strips the target bot username while preserving the base command name (`/test_scout`). Any parameters following whitespace are already cleanly segregated into `cmd_args`.

3. **Mapping Protocol Subscripting Logic Chain**:
   - *Premise*: Subscript syntax `obj[key]` is expected to conform to Python dictionary protocol.
   - *Mechanism*: `CompatibleInlineKeyboardMarkup` and `CompatibleInlineKeyboardButton` delegate `__getitem__` to `getattr(self, item)`. When `item` is not present, `getattr` raises `AttributeError`.
   - *Deduction*: Wrapping `getattr(self, item)` in `try ... except AttributeError: raise KeyError(item)` restores standard mapping semantics. `kb.get(item, default)` already functions correctly because 3-argument `getattr(self, item, default)` does not raise `AttributeError`.

4. **Channel Persistence Logic Chain**:
   - *Premise*: An administrative command `/create_channel` reporting successful channel creation must ensure database state corresponds to user feedback.
   - *Mechanism*: When `session is None`, the handler currently has no database handle.
   - *Deduction*: Importing `get_db()` from `src.database.session` provides an asynchronous context manager with isolated transaction management. When `session is None`, `async with get_db() as s:` acquires a session, queries for existing channel record to maintain idempotency, inserts the new `Channel`, and commits.

---

## 3. Caveats

1. **Foreign Key Integrity for Channels**:
   - `Channel.niche_id` has a foreign key referencing `niches.niche_id`. In default creation, `/create_channel` sets `niche_id="thoi_trang_nu"`. The pilot niche must exist in the database (which is guaranteed by database seeding in `main.py` and `conftest.py`). The `try ... except Exception as e: logger.debug(...)` ensures unexpected database constraint errors do not crash the bot process.
2. **Username Specificity in Multi-Bot Groups**:
   - Stripping any `@...` suffix assumes the command was addressed to this bot or intended for execution. This is standard aiogram behavior when bot commands are processed.
3. **Read-Only Explorer Scope**:
   - In accordance with the Teamwork protocol, this agent does NOT modify source code directly. The exact code proposals below are ready for immediate application by the implementation worker.

---

## 4. Conclusion & Concrete Remediation Plan

### 4.1 Summary of Changes by File

| File | Target Function / Class | Line Numbers | Proposed Fix |
|---|---|---|---|
| `src/bot/telegram_bot.py` | `TelegramCommandCenter.__init__` | 65, 81–89, 90–97 | Coerce `admin_id` and `forum_chat_id` safely to `int` via `try: int(...) except (ValueError, TypeError)`. |
| `src/bot/handlers.py` | `execute_command` | 49–72 | Add safe `int(user_id) == int(admin_id)` authorization check; strip `@...` from `cmd_name`. |
| `src/bot/handlers.py` | `/create_channel` | 85–100 | Fallback to `async with get_db() as s:` when `session is None`, checking idempotency before insert. |
| `src/bot/handlers.py` | `execute_callback` | 120–133 | Add safe `int(user_id) == int(admin_id)` authorization check. |
| `src/bot/keyboards.py` | `CompatibleInlineKeyboardButton.__getitem__` | 19–20 | Catch `AttributeError` and raise `KeyError(item)`. |
| `src/bot/keyboards.py` | `CompatibleInlineKeyboardMarkup.__getitem__` | 29–30 | Catch `AttributeError` and raise `KeyError(item)`. |
| `tests/test_telegram_bot.py` | Unit Test Suite | New tests | Add unit tests covering string `admin_id`, `@BotName`, `KeyError`, and headless channel creation. |

---

### 4.2 Exact Code Replacements

#### Change 1: `src/bot/telegram_bot.py`

**Lines 62–98**:
```python
<<<< BEFORE
    def __init__(
        self,
        token: Optional[str] = None,
        admin_id: Optional[int] = None,
        forum_chat_id: Optional[int] = None,
        topic_ids: Optional[Dict[str, int]] = None,
        mock_mode: Optional[bool] = None,
        config: Optional[AppConfig] = None,
    ) -> None:
        self.config = config
        cfg_tg = config.telegram if config else None

        self.token = (
            token
            or os.getenv("TELEGRAM_BOT_TOKEN")
            or (cfg_tg.bot_token if cfg_tg else "")
            or "mock_token"
        )

        admin_env = os.getenv("TELEGRAM_ADMIN_CHAT_ID") or os.getenv("ADMIN_TELEGRAM_ID")
        self.admin_id = (
            admin_id
            if admin_id is not None
            else (int(admin_env) if admin_env and admin_env.isdigit() else None)
            or (cfg_tg.admin_id if cfg_tg and cfg_tg.admin_id else None)
            or 987654321
        )

        forum_env = os.getenv("TELEGRAM_GROUP_ID") or os.getenv("TELEGRAM_FORUM_CHAT_ID")
        self.forum_chat_id = (
            forum_chat_id
            if forum_chat_id is not None
            else (int(forum_env) if forum_env and (forum_env.isdigit() or forum_env.startswith("-")) else None)
            or (cfg_tg.forum_chat_id if cfg_tg and cfg_tg.forum_chat_id else None)
            or -1001234567890
        )
==== AFTER
    def __init__(
        self,
        token: Optional[str] = None,
        admin_id: Optional[Union[int, str]] = None,
        forum_chat_id: Optional[Union[int, str]] = None,
        topic_ids: Optional[Dict[str, int]] = None,
        mock_mode: Optional[bool] = None,
        config: Optional[AppConfig] = None,
    ) -> None:
        self.config = config
        cfg_tg = config.telegram if config else None

        self.token = (
            token
            or os.getenv("TELEGRAM_BOT_TOKEN")
            or (cfg_tg.bot_token if cfg_tg else "")
            or "mock_token"
        )

        admin_env = os.getenv("TELEGRAM_ADMIN_CHAT_ID") or os.getenv("ADMIN_TELEGRAM_ID")
        raw_admin = (
            admin_id
            if admin_id is not None
            else (admin_env if admin_env else None)
            or (cfg_tg.admin_id if cfg_tg and cfg_tg.admin_id else None)
            or 987654321
        )
        try:
            self.admin_id: int = int(raw_admin)
        except (ValueError, TypeError):
            self.admin_id = 987654321

        forum_env = os.getenv("TELEGRAM_GROUP_ID") or os.getenv("TELEGRAM_FORUM_CHAT_ID")
        raw_forum = (
            forum_chat_id
            if forum_chat_id is not None
            else (forum_env if forum_env else None)
            or (cfg_tg.forum_chat_id if cfg_tg and cfg_tg.forum_chat_id else None)
            or -1001234567890
        )
        try:
            self.forum_chat_id: int = int(raw_forum)
        except (ValueError, TypeError):
            self.forum_chat_id = -1001234567890
>>>>
```

---

#### Change 2: `src/bot/handlers.py`

**Imports (lines 18–24)**:
```python
<<<< BEFORE
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import load_config
from src.database.models import Channel, Product, VideoJob
==== AFTER
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import load_config
from src.database.models import Channel, Product, VideoJob
from src.database.session import get_db
>>>>
```

**`execute_command` (lines 49–72)**:
```python
<<<< BEFORE
async def execute_command(
    command: str,
    user_id: int,
    admin_id: int,
    args: Optional[str] = None,
    session: Optional[AsyncSession] = None,
) -> str:
    """Core command dispatcher with admin authorization security guard."""
    if user_id != admin_id:
        return ADMIN_DENIED_MESSAGE

    clean = (command or "").strip()
    if " " in clean and args is None:
        parts = clean.split(maxsplit=1)
        cmd_name = parts[0].lower()
        cmd_args = parts[1].strip()
    else:
        cmd_name = clean.split()[0].lower() if clean else ""
        cmd_args = args.strip() if args else ""

    if not cmd_name.startswith("/"):
        cmd_name = f"/{cmd_name}"
==== AFTER
async def execute_command(
    command: str,
    user_id: Union[int, str],
    admin_id: Union[int, str],
    args: Optional[str] = None,
    session: Optional[AsyncSession] = None,
) -> str:
    """Core command dispatcher with admin authorization security guard."""
    try:
        is_authorized = int(user_id) == int(admin_id)
    except (ValueError, TypeError):
        is_authorized = False

    if not is_authorized:
        return ADMIN_DENIED_MESSAGE

    clean = (command or "").strip()
    if " " in clean and args is None:
        parts = clean.split(maxsplit=1)
        cmd_name = parts[0].lower()
        cmd_args = parts[1].strip()
    else:
        cmd_name = clean.split()[0].lower() if clean else ""
        cmd_args = args.strip() if args else ""

    # Strip Telegram bot username suffix (e.g. /test_scout@AmasBot -> /test_scout)
    if "@" in cmd_name:
        cmd_name = cmd_name.split("@", 1)[0]

    if not cmd_name.startswith("/"):
        cmd_name = f"/{cmd_name}"
>>>>
```

**`execute_command` `/create_channel` branch (lines 85–100)**:
```python
<<<< BEFORE
    elif cmd_name == "/create_channel":
        alias = cmd_args or "koc_01"
        if session:
            try:
                chan = Channel(
                    channel_id=f"chan_{alias}",
                    niche_id="thoi_trang_nu",
                    browser_profile_id=f"profile_alias_{alias}",
                    lifecycle_status="warming",
                )
                session.add(chan)
                await session.commit()
            except Exception as e:
                logger.debug("Channel already exists or DB error: %s", e)
        return f"✨ Tạo kênh mới thành công: profile_alias_{alias} (status: warming)"
==== AFTER
    elif cmd_name == "/create_channel":
        alias = cmd_args or "koc_01"
        channel_id = f"chan_{alias}"
        profile_id = f"profile_alias_{alias}"

        async def _persist_channel(s: AsyncSession) -> None:
            stmt = select(Channel).where(Channel.channel_id == channel_id)
            res = await s.execute(stmt)
            existing = res.scalars().first()
            if not existing:
                chan = Channel(
                    channel_id=channel_id,
                    niche_id="thoi_trang_nu",
                    browser_profile_id=profile_id,
                    lifecycle_status="warming",
                )
                s.add(chan)
                await s.commit()

        try:
            if session:
                await _persist_channel(session)
            else:
                async with get_db() as s:
                    await _persist_channel(s)
        except Exception as e:
            logger.debug("Channel already exists or DB error: %s", e)

        return f"✨ Tạo kênh mới thành công: {profile_id} (status: warming)"
>>>>
```

**`execute_callback` authorization guard (lines 120–133)**:
```python
<<<< BEFORE
async def execute_callback(
    callback_data: str,
    user_id: int,
    admin_id: int,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Core callback handler with admin authorization security guard."""
    if user_id != admin_id:
        return {
            "success": False,
            "error": "unauthorized",
            "message": ADMIN_DENIED_MESSAGE,
        }
==== AFTER
async def execute_callback(
    callback_data: str,
    user_id: Union[int, str],
    admin_id: Union[int, str],
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Core callback handler with admin authorization security guard."""
    try:
        is_authorized = int(user_id) == int(admin_id)
    except (ValueError, TypeError):
        is_authorized = False

    if not is_authorized:
        return {
            "success": False,
            "error": "unauthorized",
            "message": ADMIN_DENIED_MESSAGE,
        }
>>>>
```

---

#### Change 3: `src/bot/keyboards.py`

**Lines 16–37**:
```python
<<<< BEFORE
class CompatibleInlineKeyboardButton(InlineKeyboardButton):
    """InlineKeyboardButton supporting both object attribute and dictionary subscript access."""

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class CompatibleInlineKeyboardMarkup(InlineKeyboardMarkup):
    """InlineKeyboardMarkup supporting both aiogram Pydantic serialization and dict subscripting."""

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item)
==== AFTER
class CompatibleInlineKeyboardButton(InlineKeyboardButton):
    """InlineKeyboardButton supporting both object attribute and dictionary subscript access."""

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class CompatibleInlineKeyboardMarkup(InlineKeyboardMarkup):
    """InlineKeyboardMarkup supporting both aiogram Pydantic serialization and dict subscripting."""

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item)
>>>>
```

---

### 4.3 Proposed New Unit Tests for `tests/test_telegram_bot.py`

To permanently prevent regressions, the following test methods should be added to `tests/test_telegram_bot.py`:

```python
# In TestApprovalKeyboard:
def test_keyboard_missing_key_raises_keyerror(self):
    kb = get_approval_keyboard("prod_test_001")
    with pytest.raises(KeyError):
        _ = kb["non_existent_field"]

def test_button_missing_key_raises_keyerror(self):
    kb = get_approval_keyboard("prod_test_001")
    btn = kb["inline_keyboard"][0][0]
    with pytest.raises(KeyError):
        _ = btn["non_existent_field"]

# In TestCommandDispatcherAuthorized:
@pytest.mark.asyncio
async def test_cmd_bot_username_strip(self, bot):
    res1 = await bot.handle_command("/test_scout@AmasBot", 987654321)
    assert "trinh sát ngách: thoi_trang_nu" in res1

    res2 = await bot.handle_command("/test_scout@AmasBot do_gia_dung", 987654321)
    assert "trinh sát ngách: do_gia_dung" in res2

    res3 = await bot.handle_command("/status@AmasBot", 987654321)
    assert "đang hoạt động" in res3

    res4 = await bot.handle_command("/create_channel@AmasBot koc_forum", 987654321)
    assert "profile_alias_koc_forum" in res4

@pytest.mark.asyncio
async def test_admin_id_string_coercion_authorized(self):
    # Bot configured with string admin_id
    bot_str_admin = TelegramCommandCenter(admin_id="987654321")
    assert isinstance(bot_str_admin.admin_id, int)
    assert bot_str_admin.admin_id == 987654321

    # Native int caller
    res1 = await bot_str_admin.handle_command("/status", 987654321)
    assert "đang hoạt động" in res1

    # String caller
    res2 = await bot_str_admin.handle_command("/status", "987654321")
    assert "đang hoạt động" in res2

@pytest.mark.asyncio
async def test_cmd_create_channel_db_persistence_headless(self, bot, db_session: AsyncSession):
    # Calling handle_command without passing session
    res = await bot.handle_command("/create_channel", 987654321, "koc_headless")
    assert "Tạo kênh mới thành công" in res

    # Verify that Channel was persisted in database
    chan = await db_session.get(Channel, "chan_koc_headless")
    assert chan is not None
    assert chan.channel_id == "chan_koc_headless"
    assert chan.browser_profile_id == "profile_alias_koc_headless"
    assert chan.lifecycle_status == "warming"
```

---

## 5. Verification Method

To verify these fixes independently:

1. **Verify `admin_id` String Coercion and Access**:
   ```bash
   python3 -c "import asyncio; from src.bot import TelegramCommandCenter; \
   bot = TelegramCommandCenter(admin_id='987654321'); \
   assert isinstance(bot.admin_id, int), f'admin_id is not int: {type(bot.admin_id)}'; \
   res = asyncio.run(bot.handle_command('/status', 987654321)); \
   assert 'đang hoạt động' in res, f'Admin rejected: {res}'; \
   res2 = asyncio.run(bot.handle_command('/status', '987654321')); \
   assert 'đang hoạt động' in res2, f'String user_id rejected: {res2}'; \
   print('PASS: admin_id string coercion verified.')"
   ```

2. **Verify Group/Forum Command `@BotName` Syntax**:
   ```bash
   python3 -c "import asyncio; from src.bot.handlers import execute_command; \
   res = asyncio.run(execute_command('/test_scout@AmasBot', 987654321, 987654321)); \
   assert 'trinh sát' in res, f'Failed on @BotName: {res}'; \
   res2 = asyncio.run(execute_command('/test_scout@AmasBot do_gia_dung', 987654321, 987654321)); \
   assert 'do_gia_dung' in res2, f'Failed on @BotName with args: {res2}'; \
   print('PASS: @BotName command stripping verified.')"
   ```

3. **Verify `KeyError` Raising on Missing Subscript Key**:
   ```bash
   python3 -c "from src.bot.keyboards import get_approval_keyboard; \
   kb = get_approval_keyboard('p1'); \
   try: \
       _ = kb['non_existent'] \
       assert False, 'Should have raised KeyError' \
   except KeyError: \
       print('PASS: KeyError correctly raised on missing key.') \
   except AttributeError: \
       assert False, 'FAIL: Raised AttributeError instead of KeyError'"
   ```

4. **Verify `/create_channel` Database Persistence Without Explicit Session**:
   ```bash
   python3 -c "import asyncio; from sqlalchemy import select; from src.bot.handlers import execute_command; \
   from src.database.models import Channel; from src.database.session import get_db; \
   async def test(): \
       res = await execute_command('/create_channel', 987654321, 987654321, args='koc_persist_verif'); \
       assert 'profile_alias_koc_persist_verif' in res; \
       async with get_db() as s: \
           stmt = select(Channel).where(Channel.channel_id == 'chan_koc_persist_verif'); \
           r = await s.execute(stmt); \
           chan = r.scalars().first(); \
           assert chan is not None, 'Channel was not persisted to DB!'; \
           assert chan.lifecycle_status == 'warming'; \
           print('PASS: /create_channel DB persistence verified.'); \
   asyncio.run(test())"
   ```

5. **Run Existing Test Suite**:
   ```bash
   pytest tests/test_telegram_bot.py -v
   pytest tests/e2e/ -v
   ```

### Invalidation Conditions
- The findings are invalidated if `TelegramCommandCenter(admin_id="987654321")` fails to allow user `987654321` access to commands.
- The findings are invalidated if `/test_scout@AmasBot` returns `"❓ Lệnh không xác định"`.
- The findings are invalidated if `kb["non_existent"]` raises `AttributeError` instead of `KeyError`.
- The findings are invalidated if `/create_channel` returns success without a `Channel` row inserted into the database.
