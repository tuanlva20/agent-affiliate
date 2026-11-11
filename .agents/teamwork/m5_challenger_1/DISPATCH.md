## 2026-11-10T11:47:35Z

You are m5_challenger_1, a teamwork_challenger conducting empirical adversarial stress testing on Milestone 5 (specifically Script Generator F15 and ToneValidator compliance) of the Autonomous TikTok Affiliate System (AMAS v1.4.0).

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_challenger_1/
Project root: /Users/tuanlva/Folder/workSpace/affiliate

### Inputs
1. User Request: Read `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md`
2. Target Module: `src/services/script_generator.py` and its interaction with `src/core/tone_validator.py` and `src/core/prompt_templates.py`.

### Mission & Stress Testing Directives
You must create an adversarial stress harness script (e.g. `scripts/m5_adversarial_script_harness.py`) and execute it against `ScriptGenerator`.
Specifically test:
1. **Adversarial Title Injections**:
   - Obfuscated trademark names: `Z.a.r.a`, `C.h.a.n.e.l`, `G.u.c.c.i`, `N.i.k.e`, `r.e.p 1:1`, `s.u.p.e.r f.a.k.e`, `l.i.k.e a.u.t.h`, `t.u.ồ.n a.u.t.h`.
   - Exaggerated & medical claims: `trị dứt điểm 100%`, `vĩnh viễn không bám bẩn`, `chữa khỏi hoàn toàn`, `100% không bao giờ hỏng`.
   - Robotic clichés in title: `sản phẩm hoàn hảo đáp ứng mọi nhu cầu`, `kính chào quý khách`, `hãy nhanh tay sở hữu`.
   - Verify that generated scripts NEVER leak these into `full_voiceover` and that `ToneValidator.validate(full_voiceover)` ALWAYS returns `True`.
2. **KOC Marker Guarantee**:
   - Test across 50+ diverse and unusual product titles.
   - Verify that `ToneValidator.has_koc_markers(full_voiceover)` is ALWAYS `True`.
   - Verify that all 5 contract keys (`hook_3s`, `body`, `cta_yellow_cart`, `caption`, `full_voiceover`) exist and are non-empty strings.
3. **Extreme/Corrupt Metadata Inputs**:
   - `None`, empty dict, dictionary with missing keys, non-string titles, negative or NaN prices, huge strings (10,000 characters).
   - Ensure `generate_script` handles all gracefully without unhandled exceptions or crashes.
4. **Persona & Voice Mapping Integrity**:
   - Verify that fashion products (`thoi_trang_nu`) always select `vi-VN-HoaiMyNeural` and female KOC markers (`chị em`, `mấy bà`, `tui`).
   - Verify that homelife products (`do_gia_dung`) always select `vi-VN-NamMinhNeural` and male KOC markers (`các bác`, `tui`, `3s`/`nhàn`).

### Reporting
- Execute your adversarial harness, record exact metrics (number of test assertions, passes, failures).
- Issue an explicit verdict: **APPROVE** (if 100% pass) or **REQUEST_CHANGES** (if any violation or bypass detected).
- Write your handoff report to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m5_challenger_1/handoff.md`.
- Send a completion message with your verdict to the orchestrator.
