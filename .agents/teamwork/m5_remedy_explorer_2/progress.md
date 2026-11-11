# Progress — m5_remedy_explorer_2
Last visited: 2026-11-10T12:09:45Z
- [x] Investigate ToneValidator counterfeit pattern accent fixes and ScriptGenerator persona-aware fallback
- [x] Discovered root cause of `t.u.ồ.n a.u.t.h` evasion: `Mn` stripping vs `tuồn` regex requirement
- [x] Discovered secondary pitfall: leetspeak `!` replacement in `canonicalize_brand_text` turning Vietnamese `nha!` into `nhai`, triggering false positive with `(nhai|nhái)`
- [x] Formulated exact regex patterns for `_sanitize_title` and persona-aware emergency fallback
- [x] Finalized handoff.md with exact code replacement blocks and verification evidence (737/737 assertions passing, 100% pass rate)
