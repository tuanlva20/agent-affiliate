# Milestone 1 Empirical Adversarial Challenge Report

**Date**: 2026-11-10T07:46:30Z  
**Author**: teamwork_challenger (empirical-challenger)  
**Target Milestone**: M1 (Scaffolding, Central Config & ToneValidator)  
**Verdict**: `REQUEST_CHANGES`

---

## 1. Observation

Direct empirical observations from executing tests and the stress test harness `scripts/m1_stress_harness.py`:

### Observation 1.1: Counterfeit Brand Evasions (`src/core/tone_validator.py:48-53`)
Running `python3 scripts/m1_stress_harness.py` revealed that multiple real-world counterfeit seller patterns evade `ToneValidator.validate()`:
1. **`rep 1.1` (dot separator)**:
   - Command: `python3 -c "from src.core.tone_validator import ToneValidator; print(ToneValidator.validate('Túi xách rep 1.1 bao đẹp'))"`
   - Output: `True` (Violations: `[]`).
   - Line in code: `src/core/tone_validator.py:48`:
     ```python
     (r"(?:\b|^|\s)rep\s*(1\s*[:\/\-]\s*1|1\s*1)(?:\b|$|\s)", "rep 1:1")
     ```
     The regex character class `[:\/\-]` allows colon, slash, or hyphen, but omits dot `\.`.
2. **`super-fake` and `like-auth` (hyphen/underscore separators)**:
   - Command: `python3 -c "from src.core.tone_validator import ToneValidator; print(ToneValidator.validate('Đầm body super-fake loại 1'), ToneValidator.validate('Giày like-auth cực xịn'))"`
   - Output: `True True` (Violations: `[]`).
   - Lines in code: `src/core/tone_validator.py:49, 53`:
     ```python
     (r"\bsuper\s*fake\b", "super fake"),
     (r"\b(like|chuẩn|tuồn)\s*auth\b", "like/chuẩn/tuồn auth"),
     ```
     `\s*` only matches whitespace characters and does not match `-` or `_`.
3. **Standalone `fake 1:1`, `fake 1`, `áo fake`, `giày fake`**:
   - Command: `python3 -c "from src.core.tone_validator import ToneValidator; print(ToneValidator.validate('Áo phông fake 1:1 cao cấp'), ToneValidator.validate('Giày fake loại 1 chất xịn'))"`
   - Output: `True True` (Violations: `[]`).
   - Line in code: `src/core/tone_validator.py:50-51`:
     ```python
     (r"\b(hàng|hang)\s*fake\b", "hang fake"),
     (r"\b(hàng|hang)\s*(fake|rep|f1)\b", "hàng fake/rep/f1"),
     ```
     Both rules strictly mandate the word `hàng` or `hang` preceding `fake`/`rep`/`f1`. Product titles lacking `hàng` (e.g. `áo fake`, `túi fake`, `fake 1:1`) evade detection completely.

### Observation 1.2: Robotic Clichés Evasions (`src/core/tone_validator.py:22-30`)
Subtle polite greeting and generic AI self-identification permutations evade `ToneValidator.validate()`:
1. `Dạ em chào quý khách ạ`: returns `True` (evades `\bxin chào quý khách\b`).
2. `Chào quý khách`: returns `True` (evades `\bxin chào quý khách\b`).
3. `Chào mừng bạn đến với shop`: returns `True` (evades `\bchào mừng quý khách\b`).
4. `Tôi là một trợ lý ảo`: returns `True` (evades `\btôi là trợ lý (ảo|ai)\b` because of the extra word `một`).
5. `Như một mô hình AI`: returns `True` (evades `\bnhư một trợ lý ai\b`).
6. `Hy vọng thông tin này hữu ích cho bạn`: returns `True` (no pattern exists).

### Observation 1.3: False Positive Resistance on Valid Vietnamese Words
Running `scripts/m1_stress_harness.py`:
- `Lực lượng lao động trẻ trung`: `Valid=True`, `Violations=[]` (PASS).
- `Hộp đựng thực phẩm giúp lưu trữ đồ ăn`: `Valid=True`, `Violations=[]` (PASS).
- `Ly nước thủy tinh chịu nhiệt siêu xinh`: `Valid=True`, `Violations=[]` (PASS).
- `Quản lý việc nhà nhàn tênh`: `Valid=True`, `Violations=[]` (PASS).
- `Shop ơi rep tin nhắn em check size với ạ`: `Valid=True`, `Violations=[]` (PASS).
- `Chị ơi nhớ rep inbox em đặt hàng nha`: `Valid=True`, `Violations=[]` (PASS).
- `Đang bận rep cmt cho các bà đây`: `Valid=True`, `Violations=[]` (PASS).
- `Chân váy chữ A chất vải crepe cao cấp`: `Valid=True`, `Violations=[]` (PASS).
- **Result**: 0 false positives across all 'lv' and 'rep' related Vietnamese language tests.
- **Minor over-match**: `Nồi chiên không dầu làm món nhái chiên giòn rụm` returns `Valid=False` with `COUNTERFEIT_KEYWORD: 'nhái'` due to bare `\bnhái\b` at line 52.

### Observation 1.4: Config Loader Unhandled Crash with Env Overrides (`src/core/config.py:155, 160, 165, 193`)
- Command:
  ```bash
  python3 -c "
  import os, tempfile
  from src.core.config import load_config
  os.environ['POSTGRES_URL'] = 'postgresql+asyncpg://u:p@localhost/db'
  with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
      f.write('database:\n')
      p = f.name
  load_config(p)
  "
  ```
- Output:
  ```
  TypeError: 'NoneType' object does not support item assignment
  ```
- Root Cause: In `src/core/config.py:155`:
  ```python
  raw_data.setdefault("database", {})["url"] = db_url
  ```
  When the YAML file contains a key with empty value (parsed by PyYAML as `None`), `setdefault("database", {})` returns the existing `None` value instead of replacing it with `{}`. Then `None["url"]` raises `TypeError`. The same issue affects `redis:`, `telegram:`, and `browser:`.

---

## 2. Logic Chain

1. **R1 & R2 Requirements (ORIGINAL_REQUEST.md)**: Mandates strict filtering of counterfeit products ("lọc bỏ vi phạm chính sách/hàng nhái") and zero tolerance for robotic AI bot tone ("cấm tuyệt đối giọng văn máy móc hoặc mùi bot").
2. **Counterfeit Impact**: Online counterfeit sellers systematically use punctuation bypasses such as `rep 1.1`, `super-fake`, `like-auth`, or omitting `hàng` (e.g., `áo fake 1:1`) to evade platform filters. Because `ToneValidator` is the primary policy enforcement gate (Feature F04) used throughout the pipeline (Fashion Scout, Script Generator, Comment Agent), undetected counterfeits will be approved and published, risking TikTok account suspension.
3. **Robotic Cliché Impact**: LLMs frequently produce polite variants such as `"Dạ em chào quý khách ạ"`, `"Tôi là một trợ lý ảo"`, and `"Như một mô hình AI"`. The rigid regex in `ToneValidator` fails to catch these, allowing robotic bot tone into scripts and replies.
4. **Config Stability**: In production and CI/CD pipelines, YAML configuration files often define sections with empty values (e.g., `database:`) intending to populate them strictly from environment variables (`POSTGRES_URL`). The resulting `TypeError` causes hard crashes on service startup instead of graceful initialization or Pydantic validation.
5. **Conclusion**: Because these are critical loopholes in the core policy validator and an unhandled crash in the config loader, Milestone 1 cannot be approved without hardening these components.

---

## 3. Caveats

1. Baseline unit test suite (`pytest tests/test_config.py tests/test_database.py`) currently passes 16/16 tests because the existing test suite only tests positive baseline samples and does not include these adversarial evasion vectors.
2. The word boundary implementation for `LV` (`(?:\b|^|\s)lv(?:\b|$|\s)`) successfully prevented false positives on legitimate Vietnamese words containing 'l' and 'v' (`lực lượng`, `lưu trữ`, `quản lý`, `ly nước`).
3. Biological/culinary use of `"nhái"` (`món nhái`) is an edge case that is rarely encountered in fashion/home utilities, but tightening the regex to `(r"\b(hàng|đồ|bản)?\s*nhái\b")` would prevent over-blocking.

---

## 4. Conclusion

**Verdict**: `REQUEST_CHANGES`

### Required Fixes:

#### Fix 1: Harden Counterfeit Regex Patterns in `src/core/tone_validator.py`
1. Line 48: Add dot `\.` to the separator class:
   ```python
   (r"(?:\b|^|\s)rep\s*(1\s*[:\/\-\.]\s*1|1\s*1)(?:\b|$|\s)", "rep 1:1")
   ```
2. Lines 49, 53: Allow hyphens and underscores in `super-fake` and `like-auth`:
   ```python
   (r"\bsuper[\s\-_]*fake\b", "super fake"),
   (r"\b(like|chuẩn|tuồn)[\s\-_]*auth\b", "like/chuẩn/tuồn auth"),
   ```
3. Line 50-51: Support standalone `fake 1:1`, `fake 1`, and noun-preceded fake (`áo fake`, `giày fake`):
   ```python
   (r"\b(hàng|hang|áo|quần|giày|dép|túi|ví|đầm|bản)?\s*fake(\s*1(?:\s*[:\/\-\.]\s*1)?)?\b", "fake"),
   ```

#### Fix 2: Harden Robotic Clichés in `src/core/tone_validator.py`
1. Line 22: Allow optional `dạ em`, `xin`, `mừng`:
   ```python
   (r"\b(dạ\s+)?(em\s+)?(xin\s+|kính\s+)?chào\s+(mừng\s+)?quý\s+khách\b", "chào quý khách"),
   (r"\bchào\s+mừng\s+(bạn|quý\s+vị|mọi\s+người)\s+đến\s+với\b", "chào mừng bạn đến với"),
   ```
2. Lines 28-31: Match variations of AI self-identification:
   ```python
   (r"\btôi là\s+(một\s+)?trợ lý\s+(ảo|ai|thông minh|ngôn ngữ)\b", "tôi là trợ lý ảo/AI"),
   (r"\b(như|là)\s+một\s+(trợ lý|mô hình)\s+(ảo|ai|ngôn ngữ)\b", "như một trợ lý/mô hình AI"),
   ```

#### Fix 3: Fix `_apply_env_overrides` in `src/core/config.py`
Ensure nested dictionaries are created if the existing key is `None`:
```python
def _ensure_dict(data: Dict[str, Any], key: str) -> Dict[str, Any]:
    val = data.get(key)
    if not isinstance(val, dict):
        val = {}
        data[key] = val
    return val
```
And replace calls to `raw_data.setdefault(...)` with `_ensure_dict(raw_data, ...)`.

---

## 5. Verification Method

To independently reproduce all findings and verify the fixes:

1. **Run the Empirical Stress Test Harness**:
   ```bash
   python3 scripts/m1_stress_harness.py
   ```
   Inspect the output summary. Currently, it reports:
   - Total: 59 test cases
   - Passed: 41
   - Failed/Gaps: 18

2. **Run Config Crash Reproduction**:
   ```bash
   python3 -c "
   import os, tempfile
   from src.core.config import load_config
   os.environ['POSTGRES_URL'] = 'postgresql+asyncpg://u:p@localhost/db'
   with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
       f.write('database:\n')
       p = f.name
   load_config(p)
   "
   ```
   Expected before fix: raises `TypeError: 'NoneType' object does not support item assignment`.
   Expected after fix: successfully returns `AppConfig(database=DatabaseConfig(url='postgresql+asyncpg://u:p@localhost/db'))`.

3. **Run Existing Test Suite**:
   ```bash
   pytest tests/test_config.py tests/test_database.py -v
   ```
   Must remain 100% PASS (16/16).
