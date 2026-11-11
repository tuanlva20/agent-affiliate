## 2026-11-10T15:26:24Z
You are m6_challenger_2, an adversarial verifier for Milestone 6 (Task 6: Human Behavioral Biometrics Engine & Smart Publisher với AliasMode).

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m6_challenger_2/
Read ORIGINAL_REQUEST.md first: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
Also read:
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md
- /Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md (Sections 4 & 5: Channel Lifecycle States & Schema)
- Implementation:
  * /Users/tuanlva/Folder/workSpace/affiliate/src/services/browser_adapter.py
  * /Users/tuanlva/Folder/workSpace/affiliate/src/agents/smart_publisher.py
- Tests:
  * /Users/tuanlva/Folder/workSpace/affiliate/tests/test_browser_adapter.py
  * /Users/tuanlva/Folder/workSpace/affiliate/tests/test_smart_publisher.py

Your Mandate — Adversarial Stress Testing of BrowserAdapter & SmartPublisher:
1. Write a standalone adversarial stress test harness: `scripts/m6_adversarial_publisher_harness.py`.
2. Attack vectors to stress test:
   - BrowserAdapter Proxy Torture:
     * Invalid schemes: `ftp://proxy:8080`, `ssh://1.2.3.4:22`, `socks4://1.2.3.4:1080` -> MUST raise `BrowserProxyError` (subclass of `ValueError`).
     * Invalid ports: port 0, port 65536, port -1, non-numeric port -> MUST raise `BrowserProxyError`.
     * Missing host: `http://:8080`, `http://user:pass@` -> MUST raise `BrowserProxyError`.
     * Valid edge schemes: `http://user:p@ss!word@1.2.3.4:8080`, `socks5://127.0.0.1:1080` -> MUST parse successfully.
   - Missing Profile Boundary:
     * `start_browser("non_existent_profile")` -> MUST raise `BrowserProfileNotFoundError` which MUST be catchable as `KeyError`.
     * `stop_browser("non_existent_profile")` -> MUST raise `KeyError`.
   - SmartPublisher Lifecycle State Machine Torture:
     * Fuzz all lifecycle statuses: `warming`, `captcha_blocked`, `cooldown`, `unknown_status`, `None`, empty string `""`.
     * Verify `warming` is rejected 100% of the time with error containing "warming stage".
     * Verify `captcha_blocked` is rejected 100% of the time with error containing "blocked by Captcha" or "captcha blocked".
     * Dict vs ORM `Channel` model equivalence: test both forms with identical inputs and verify identical results.
   - Concurrency & Race Conditions:
     * Simulate 20 concurrent `publish_video` requests on the same channel: verify status transitions remain consistent.
     * Mid-flight Captcha detection: verify channel transitions to `captcha_blocked`, db_session commits change, and error result is returned.
     * Simulate browser start failure: verify publisher catches error gracefully and does not leave channel in invalid state.
3. Execute the harness: `python3 scripts/m6_adversarial_publisher_harness.py`.
4. Report:
   - Document number of test cases passed, failure count, execution output.
   - If ANY assertion fails, issue `REQUEST_CHANGES` with exact reproducible evidence.
   - If ALL assertions pass, issue `APPROVE`.
   - Write `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m6_challenger_2/handoff.md`.
   - Send message back to parent with verdict.
