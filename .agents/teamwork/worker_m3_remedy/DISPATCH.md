## 2026-11-10T09:51:29Z
You are worker_m3_remedy, implementing the remediation for Milestone 3 (Specialist Scout Agents & ToneValidator) to fix all adversarial test failures.

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/worker_m3_remedy/
Write ownership:
- `src/core/tone_validator.py`
- `src/agents/fashion_scout.py`
- `src/agents/homelife_scout.py`
- `tests/test_specialist_scouts.py`
- `.agents/teamwork/worker_m3_remedy/`

You MUST read:
- ORIGINAL_REQUEST.md at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
- PROJECT.md at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
- m3_challenger_1 handoff at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_challenger_1/handoff.md
- m3_challenger_2 handoff at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_challenger_2/handoff.md
- m3_reviewer_1 handoff at /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m3_reviewer_1/handoff.md
- scripts/m3_fashion_adversarial_harness.py at /Users/tuanlva/Folder/workSpace/affiliate/scripts/m3_fashion_adversarial_harness.py
- scripts/m3_homelife_adversarial_harness.py at /Users/tuanlva/Folder/workSpace/affiliate/scripts/m3_homelife_adversarial_harness.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Detailed Tasks:
1. In `src/core/tone_validator.py`:
   - Implement an auxiliary brand de-obfuscation / canonicalization method for trademark checks:
     * Remove inter-character punctuation `[_\-.\/:]`
     * Collapse spaced single letters into words (e.g. `z a r a` -> `zara`, `c h a n e l` -> `chanel`, `g u c c i` -> `gucci`, `d i o r` -> `dior`, `n i k e` -> `nike`, `l v` -> `lv`, `h e r m e s` -> `hermes`, `a d i d a s` -> `adidas`)
     * Common leetspeak substitutions on latin tokens: `4/@ -> a`, `3 -> e`, `1/! -> i`, `0 -> o`, `5/$ -> s`
     * Strip accents from brand tokens (e.g. `zàra -> zara`, `chánel -> chanel`, `gùcci -> gucci`)
     * Broaden `rep 1:1` and `super fake` regex patterns to tolerate internal punctuation/dots: e.g. `r[\.\s\-_]*e[\.\s\-_]*p[\.\s\-_]*(1[\.\s\-_]*[:\/\-\.][\.\s\-_]*1|1[\.\s\-_]*1)` and `s[\.\s\-_]*u[\.\s\-_]*p[\.\s\-_]*e[\.\s\-_]*r[\.\s\-_]*f[\.\s\-_]*a[\.\s\-_]*k[\.\s\-_]*e`
   - In `ToneValidator.EXAGGERATED_PATTERNS`:
     * Normalize slang: `\bko\b`, `\bkhong\b` -> `không`
     * Normalize separators: `_`, `-`, `.` to whitespace, collapse multiple spaces `\s+`
     * Update patterns to tolerate variable whitespace, underscores, hyphens, and dots:
       - `r"\btrị[\s_\-\.]+dứt[\s_\-\.]+điểm([\s_\-\.]+100[\s_\-\.]*%)?\b"`
       - `r"\bvĩnh[\s_\-\.]+viễn[\s_\-\.]+(không|ko|khong)[\s_\-\.]+bám[\s_\-\.]+bẩn\b"`
       - `r"\bthần[\s_\-\.]+dược\b"`
       - `r"\b100[\s_\-\.]*%[\s_\-\.]*(không|ko|khong)[\s_\-\.]+bao[\s_\-\.]+giờ[\s_\-\.]+hỏng\b"`
       - `r"\bvĩnh[\s_\-\.]+viễn[\s_\-\.]+(không|ko|khong)[\s_\-\.]+hỏng\b"`
       - `r"\bvĩnh[\s_\-\.]+viễn[\s_\-\.]+(không|ko|khong)[\s_\-\.]+(rỉ|gỉ)[\s_\-\.]+sét\b"`
       - `r"\bbảo[\s_\-\.]+hành[\s_\-\.]+trọn[\s_\-\.]+đời[\s_\-\.]+(không|ko|khong)[\s_\-\.]+hỏng\b"`

2. In `src/agents/fashion_scout.py`:
   - In `evaluate_product`:
     * Use canonicalized checks for trademark / counterfeit detection. If any violation detected: `passed_filter = False`, `score = 0.0`, `rejection_reason = "Violates trademark policy: ..."`
     * Guard numeric inputs against NaN / Inf:
       `if math.isnan(price) or math.isinf(price) or math.isnan(comm_rate) or math.isinf(comm_rate) or price < 0 or comm_rate < 0 or sales_30d < 0: raise ValueError("Invalid numeric value: negative, NaN, or Inf not permitted")`
   - In `SpecialistEvaluation.from_dict`:
     * Add `if not isinstance(data, dict): data = {}` guard to avoid `AttributeError` on non-dict input.

3. In `src/agents/homelife_scout.py`:
   - In `__init__`:
     * Load `self.banned_keywords: List[str] = []` from `config.get_niche(self.NICHE_ID).banned_keywords` if config is available.
   - In `evaluate_product`:
     * Guard numeric inputs against NaN / Inf:
       `if math.isnan(price) or math.isinf(price) or math.isnan(comm_rate) or math.isinf(comm_rate) or price < 0 or comm_rate < 0 or sales_30d < 0: raise ValueError("Invalid numeric value: negative, NaN, or Inf not permitted")`
     * Check both `ToneValidator.check_violations(title)` and `self.banned_keywords`: if matched, immediately return `SpecialistEvaluation(..., passed_filter=False, score=0.0, rejection_reason="Violates exaggerated policy: ...")`

4. Verification Requirements (Worker must run and document verbatim outputs):
   - `python3 scripts/m3_fashion_adversarial_harness.py`: MUST be 93/93 PASSED (100%)
   - `python3 scripts/m3_homelife_adversarial_harness.py`: MUST be 62/62 PASSED (100%)
   - `pytest tests/test_specialist_scouts.py -v`: MUST be 100% PASSED
   - `pytest tests/e2e/ -v`: MUST be 100% PASSED
   - `pytest tests/ -v`: MUST be 100% PASSED (all tests in repo)
   - `python3 scripts/m1_stress_harness.py`: MUST be 100% PASSED
   - `python3 scripts/m2_stress_harness.py`: MUST be 100% PASSED
   - `python3 scripts/m2_kalodata_stress_harness.py`: MUST be 100% PASSED


## 2026-11-10T10:02:00Z
Status check from parent (f5177315-7404-4813-b8ba-56081885cdd4):
Safety timer fired after 10 minutes. Please update your progress.md and report current status.
