## 2026-11-10T16:10:26Z

You are m7_explorer_3, an exploration agent investigating KOC Conversion Reply Generation and Test Architecture for Milestone 7 (Task 7: Comment Engagement & Conversion Agent).

Working directory: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_explorer_3/
Read ORIGINAL_REQUEST.md first: /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/ORIGINAL_REQUEST.md
Also read:
- /Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/PROJECT.md (Feature F27)
- /Users/tuanlva/Folder/workSpace/affiliate/SYSTEM_SPEC.md (Persona guidelines)
- /Users/tuanlva/Folder/workSpace/affiliate/src/core/prompt_templates.py (`HOAI_MY_PERSONA`, `NAM_MINH_PERSONA`, `FASHION_COMMENT_REPLY_PROMPT`)
- /Users/tuanlva/Folder/workSpace/affiliate/src/core/tone_validator.py (`ToneValidator.validate`)
- /Users/tuanlva/Folder/workSpace/affiliate/tests/e2e/test_tier1_features.py (F27 contract, lines 573-590)

Your Focus:
1. Detailed design for `CommentAgent.generate_reply`:
   - Signature:
     `def generate_reply(self, comment_text: str, product_meta: Dict[str, Any], persona: Dict[str, Any]) -> str`
   - Conversational KOC Voice & Conversion Strategy:
     * When `ASK_PRICE`: Cite exact price (formatted as `189,000đ` or `189k`), mention promotion/freeship, and direct buyer to the yellow cart ("giỏ hàng vàng góc trái", "nhận mã freeship").
     * When `ASK_MATERIAL_USAGE`: Highlight material benefits (e.g. đũi 2 lớp mát, thấm hút mồ hôi, che bụng) or sizing advice (e.g. form tôn dáng, tư vấn size theo cân nặng/chiều cao), and guide to size chart in yellow cart.
     * When `COMPLAINT`: Empathize, apologize sincerely for any inconvenience ("Dạ chị yêu thông cảm giúp shop...", "Nam Minh xin lỗi bác..."), ask them to inbox/DM directly for priority resolution.
     * When `OTHER`: Thank the user warmly, friendly banter, suggest checking out the yellow cart.
   - Persona Awareness:
     * Hoài My (`thoi_trang_nu`): Sweet, friendly, "chị em ơi", "mấy bà", "nha!", "tôn dáng", "hack eo".
     * Nam Minh (`do_gia_dung`): Practical, relatable, "các bác ơi", "bà nào ngại dọn nhà", "nhàn", "3s".
   - Anti-Robotic Tone Guarantee:
     * All generated replies MUST strictly pass `ToneValidator.validate(reply)`.
     * Zero robotic AI cliches ("Kính chào quý khách", "Sản phẩm này rất tốt", "chúc một ngày tốt lành").
     * Zero counterfeit or policy-violating words.
2. Complete Test Suite Architecture for `tests/test_comment_agent.py`:
   - Testing `CommentScanner` (mock and offline tests).
   - Testing `CommentIntent` classification (positive and negative cases).
   - Testing `generate_reply` across both personas (Fashion & HomeLife) and all intents.
   - Testing `ToneValidator.validate` verification on 100% of generated replies.
   - Testing integration with database `VideoComment`.

Deliverables:
- Write comprehensive blueprint and analysis to `/Users/tuanlva/Folder/workSpace/affiliate/.agents/teamwork/m7_explorer_3/handoff.md`.
- Include exact response templates, persona conditioning rules, tone validation safeguards, and unit tests.
- DO NOT edit or create any source code outside your directory.
- Send a completion message back when done.
