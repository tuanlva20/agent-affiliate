# Handoff Report — m5_explorer_2: KOC Natural Script Generator (Feature F15)

## 1. Observation

### 1.1 Existing Contract and Codebase Baseline
1. **Contract Test in E2E Suite**:
   In `/Users/tuanlva/Folder/workSpace/affiliate/tests/e2e/test_tier1_features.py` (lines 371-380):
   ```python
   def test_f15_koc_script_generator(sample_fashion_product):
       """F15: Validates natural KOC viral script generation with Hook 3s and yellow cart CTA."""
       gen = ScriptGenerator()
       script = gen.generate_script(sample_fashion_product, {"tone": "koc"})
       assert "hook_3s" in script
       assert "cta_yellow_cart" in script
       assert "caption" in script
       # Verify no robotic AI smells
       assert ToneValidator.validate(script["full_voiceover"]) is True
   ```
2. **Mock Implementation in E2E conftest**:
   In `/Users/tuanlva/Folder/workSpace/affiliate/tests/e2e/conftest.py` (lines 597-614):
   ```python
   class ScriptGenerator:
       def generate_script(self, product_meta: Dict[str, Any], persona: Dict[str, Any]) -> Dict[str, str]:
           title = product_meta.get("title", "Sản phẩm hot")
           hook = f"Chị em ơi, ai bảo eo to không mặc đẹp được? Nhìn ngay chiếc {title} này!"
           body = "Chất vải cực mát, form may tôn dáng, che trọn khuyết điểm bụng dưới chỉ sau 1 giây."
           cta = "Chị em bấm ngay góc trái màn hình nhận mã freeship và rinh về nhé!"
           caption = f"{title} tôn dáng cực đỉnh #fashion #xuhuong #thoitrang"

           full_text = f"{hook} {body} {cta}"
           assert ToneValidator.validate(full_text), "Generated script contains banned robotic phrases"

           return {
               "hook_3s": hook,
               "body": body,
               "cta_yellow_cart": cta,
               "caption": caption,
               "full_voiceover": full_text,
           }
   ```
3. **Consumer Contract in Video Studio Agent**:
   In `/Users/tuanlva/Folder/workSpace/affiliate/tests/e2e/conftest.py` (lines 643-647):
   ```python
   async def produce_video(self, job_id: str, product_meta: Dict[str, Any], persona: Dict[str, Any]) -> str:
       # 1. Generate KOC script
       script_data = self.script_gen.generate_script(product_meta, persona)
       # 2. Synthesize natural TTS audio
       audio_file = await self.tts.synthesize(script_data["full_voiceover"])
   ```
4. **Target Location**:
   `src/services/script_generator.py` currently does not exist. `PROJECT.md` specifies `src/services/script_generator.py` and `tests/test_script_generator.py` under Task 5.

### 1.2 ToneValidator Engine Observations
From `/Users/tuanlva/Folder/workSpace/affiliate/src/core/tone_validator.py`:
- `ToneValidator.validate(text: str) -> bool` (line 207):
  Returns `True` iff `len(check_violations(text)) == 0`.
- Three banned categories:
  - `ROBOTIC_PATTERNS` (lines 21-45): Banned bot clichés ("chào quý khách", "kính chào quý khách", "sau đây là danh sách", "tôi là trợ lý ảo/AI", "sản phẩm này rất tốt và tiện ích", "sự lựa chọn hoàn hảo", "giải pháp hoàn hảo", "đáp ứng mọi nhu cầu", "đừng bỏ lỡ cơ hội này", "hãy nhanh tay sở hữu", "sở hữu ngay hôm nay"...).
  - `COUNTERFEIT_PATTERNS` (lines 48-70): Trademark violations ("rep 1:1", "super fake", "fake", "nhái", "like/chuẩn/tuồn auth", "Zara", "Chanel", "Gucci", "Dior", "Louis Vuitton", "LV", "Hermes", "Prada", "Nike", "Adidas"...).
  - `EXAGGERATED_PATTERNS` (lines 73-93): Medical / excessive claims ("trị dứt điểm 100%", "chữa khỏi", "vĩnh viễn không bám bẩn", "vĩnh viễn không hỏng", "100% không bao giờ hỏng", "tốt nhất thị trường", "số 1 thế giới/việt nam"...).
- `ToneValidator.has_koc_markers(text: str) -> bool` (line 214):
  Returns `True` if `text` contains at least one of the 3 KOC marker groups:
  1. Address markers: `\b(chị em ơi|mấy bà ơi|các bà ơi|bà nào|chị nào|mấy bác ơi|các bác ơi|bà con ơi|team chân ngắn|team bụng mỡ)\b`
  2. Experience / pain-point markers: `\b(nhàn hẳn|nhàn tênh|mê chữ ê kéo dài|chân ái|đỉnh chóp|hack dáng|che khuyết điểm|bụng dưới to|bắp tay to)\b`
  3. Yellow cart CTA markers: `\b(giỏ hàng góc trái|góc trái màn hình|bấm ngay góc trái|giỏ hàng vàng|mã freeship|săn sale|săn voucher)\b`

### 1.3 Personas & Prompt Core Observations
In `/Users/tuanlva/Folder/workSpace/affiliate/src/core/prompt_templates.py`:
- `HOAI_MY_PERSONA` (lines 20-72): Name "Hoài My", voice `vi-VN-HoaiMyNeural`, tone: thân mật, ngọt ngào, xưng chị em / mấy bà / tui, che khuyết điểm (eo bánh mì, bụng dưới to, chân ngắn).
- `NAM_MINH_PERSONA` (lines 78-131): Name "Nam Minh", voice `vi-VN-NamMinhNeural`, tone: thực tế, mộc mạc, xưng các bác / mấy bà / tui, giải phóng sức lao động, Before/After 3s.
- `FASHION_KOC_SYSTEM_PROMPT` (lines 170-186) & `HOMELIFE_SYSTEM_PROMPT` (lines 188-198): Provide rigorous anti-robotic system instructions.
- `FASHION_VIDEO_SCRIPT_PROMPT` (lines 309-323) & `HOMELIFE_SCRIPT_TEMPLATE` (lines 325-336): Outline script generation structures.

### 1.4 Runtime Environment Observations
- Executed `python3 -c "for pkg in ['google', 'google.genai', 'google.generativeai', 'edge_tts', 'yt_dlp', 'whisper']: ..."`
  - `google`, `google.genai`, `google.generativeai` are NOT installed in the workspace environment.
  - Standard libraries, `requests`, `aiohttp`, `pydantic`, `SQLAlchemy`, and `pytest` are available.
- **Direct implication**: The production `ScriptGenerator` must have a self-contained, deterministic offline generator engine that functions without external packages or active network connections, while optionally supporting direct REST API or dependency-injected LLM client when credentials and dependencies are available.

---

## 2. Logic Chain

1. **Contract Invariance**:
   From Observation 1.1, `test_f15_koc_script_generator` calls `gen.generate_script(sample_fashion_product, {"tone": "koc"})` synchronously and asserts keys `hook_3s`, `cta_yellow_cart`, `caption`, and validates `ToneValidator.validate(script["full_voiceover"]) is True`. Consumer `VideoStudioAgent.produce_video` passes `script_data["full_voiceover"]` directly into `TTSService.synthesize()`.
   *Therefore*, `ScriptGenerator.generate_script` must be a synchronous method (with an optional `generate_script_async` mirror), return a dictionary (or dict-like object) containing at least `hook_3s`, `body`, `cta_yellow_cart`, `caption`, and `full_voiceover`.

2. **Persona Resolution**:
   From Observation 1.3, two personas exist: "hoai_my" (`vi-VN-HoaiMyNeural`, women's fashion) and "nam_minh" (`vi-VN-NamMinhNeural`, smart home utilities).
   *Therefore*, `ScriptGenerator` must resolve persona dynamically from:
   - Explicit persona parameter (`str` e.g. `"hoai_my"`, or `dict` e.g. `{"name": "hoai_my"}` or `{"tone": "koc"}`).
   - If not explicitly set or generic (like `{"tone": "koc"}`), infer from `product_meta.get("niche_id")` (`"thoi_trang_nu"` -> "hoai_my", `"do_gia_dung"` -> "nam_minh").
   - If niche_id is missing, infer from product title keywords (fashion terms vs home utility terms).
   - Fallback to "hoai_my" as default.

3. **Formulaic 3-Part Architecture (Hook 3s, Core Body, Yellow Cart CTA)**:
   From Observation 1.2 & 1.3:
   - **Hook 3s** (0-3s):
     - Hoài My: Must hit physical pain points (`bụng`, `eo`, `hack dáng`, `che khuyết điểm`, `bụng dưới to`) + KOC greeting (`Chị em ơi`, `Mấy bà ơi`, `Bà nào bụng dưới to bơi hết vào đây`).
     - Nam Minh: Must hit labor-saving / speed (`3s`, `3 giây`, `nhàn`, `nhàn tênh`, `nhàn hẳn`) + KOC greeting (`Các bác ơi`, `Bà nào ngại dọn nhà bơi vào đây`, `Từ ngày tậu em này việc nhà nhàn hẳn`).
   - **Body (Problem & Solution)** (3-25s):
     - Hoài My: Realistic fitting experience, fabric breathability, silhouette concealing belly fat, small honest caveat (e.g., recommend ironing before wearing).
     - Nam Minh: Pain of traditional chore (back pain, dirty hands, lost hours) vs 3s Before/After clean solution (self-wringing 360-degree mop, effortless grease removal).
   - **CTA Yellow Cart** (25-35s):
     - Must guide viewers to the yellow cart at the lower-left corner ("giỏ hàng góc trái", "góc trái màn hình", "giỏ hàng vàng", "mã freeship", "săn voucher").
   - **Caption**:
     - TikTok format with hashtags for the respective niche.

4. **Guaranteed ToneValidator & KOC Markers Compliance**:
   From Observation 1.2, any generated text will fail if it contains any phrase from `ROBOTIC_PATTERNS`, `COUNTERFEIT_PATTERNS`, or `EXAGGERATED_PATTERNS`. Furthermore, it must return `True` for `ToneValidator.has_koc_markers()`.
   *Therefore*:
   - The generator must run `ToneValidator.check_violations(full_voiceover)` on all candidates.
   - If violations are found (e.g. LLM halluncinated a cliché or brand name, or input product title contains counterfeit keywords like "Z.a.r.a" or "rep 1:1"), the engine must run automated sanitization (cleansing forbidden tokens, titles, and claims).
   - If sanitized text still fails `ToneValidator.validate()`, the engine must automatically fall back to pre-certified clean KOC templates.
   - The engine must verify `ToneValidator.has_koc_markers(full_voiceover) is True`.

5. **Offline Reliability**:
   From Observation 1.4, external LLM SDKs are absent.
   *Therefore*, the offline deterministic generator must be a primary first-class citizen, fully tested, with diverse templates and dynamic parameter injection, while providing seamless hook points for REST or mock LLM clients.

---

## 3. Detailed Technical Architecture for `src/services/script_generator.py`

### 3.1 Class & Method Interface Specification

```python
"""AMAS v1.4.0 — Natural KOC Script Generator Service (Feature F15)."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from src.core.config import AppConfig, load_config
from src.core.prompt_templates import (
    HOAI_MY_PERSONA,
    NAM_MINH_PERSONA,
    FASHION_KOC_SYSTEM_PROMPT,
    HOMELIFE_SYSTEM_PROMPT,
    get_fashion_persona,
    get_homelife_persona,
)
from src.core.tone_validator import ToneValidator

logger = logging.getLogger(__name__)


@dataclass
class KOCScriptResult:
    """Structured KOC video script result adhering to F15 contract."""
    hook_3s: str
    body: str
    cta_yellow_cart: str
    caption: str
    full_voiceover: str
    persona: str = "hoai_my"
    voice_id: str = "vi-VN-HoaiMyNeural"
    estimated_duration_sec: float = 35.0
    generation_mode: str = "offline_template"  # "llm" or "offline_template"

    def __getitem__(self, item: str) -> Any:
        """Enables dictionary-style indexing for backwards-compatibility with contracts."""
        return getattr(self, item)

    def __contains__(self, item: str) -> bool:
        """Enables 'in script' checks for contracts."""
        return hasattr(self, item)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to standard Python dictionary."""
        return {
            "hook_3s": self.hook_3s,
            "body": self.body,
            "cta_yellow_cart": self.cta_yellow_cart,
            "caption": self.caption,
            "full_voiceover": self.full_voiceover,
            "persona": self.persona,
            "voice_id": self.voice_id,
            "estimated_duration_sec": self.estimated_duration_sec,
            "generation_mode": self.generation_mode,
        }


class ScriptGenerator:
    """Service generating authentic Vietnamese KOC video scripts complying with ToneValidator."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        llm_client: Optional[Any] = None,
    ) -> None:
        self.config = config or load_config()
        self.llm_client = llm_client
```

### 3.2 Dynamic Persona & Product Input Resolution Logic
`product_meta` can be:
- `dict`: e.g. `{"title": "...", "niche_id": "...", "price": 189000.0, ...}`
- `ProductCandidate` dataclass
- SQLAlchemy `Product` ORM model
- `SpecialistEvaluation` dataclass

```python
def _normalize_product_meta(self, item: Any) -> Dict[str, Any]:
    """Safely converts input product representations to a clean dictionary."""
    if item is None:
        return {"title": "Sản phẩm xu hướng", "niche_id": "thoi_trang_nu", "price": 0.0}
    if hasattr(item, "to_dict") and callable(getattr(item, "to_dict")):
        return item.to_dict()
    if isinstance(item, dict):
        return dict(item)
    # SQLAlchemy model
    result = {}
    for attr in ["product_id", "title", "niche_id", "price", "commission_rate", "rating", "sales_count", "sales_30d"]:
        if hasattr(item, attr):
            result[attr] = getattr(item, attr)
    return result

def _resolve_persona(
    self,
    persona_param: Optional[Union[Dict[str, Any], str]],
    product_meta: Dict[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    """Resolves persona key ('hoai_my' or 'nam_minh') and metadata."""
    p_name = ""
    if isinstance(persona_param, str):
        p_name = persona_param.lower().strip()
    elif isinstance(persona_param, dict):
        p_name = str(persona_param.get("name") or persona_param.get("persona") or "").lower().strip()

    # Niche ID inference if persona is generic (e.g. {"tone": "koc"}) or empty
    niche_id = str(product_meta.get("niche_id") or "").lower()
    title = str(product_meta.get("title") or "").lower()

    if p_name in ("nam_minh", "homelife", "do_gia_dung"):
        return "nam_minh", NAM_MINH_PERSONA
    if p_name in ("hoai_my", "fashion", "thoi_trang_nu"):
        return "hoai_my", HOAI_MY_PERSONA

    if niche_id == "do_gia_dung":
        return "nam_minh", NAM_MINH_PERSONA
    if niche_id == "thoi_trang_nu":
        return "hoai_my", HOAI_MY_PERSONA

    # Heuristic keyword check on product title
    home_keywords = ["lau nhà", "nồi", "bếp", "máy", "thông minh", "gia dụng", "chổi", "kệ", "dao", "rửa"]
    if any(k in title for k in home_keywords):
        return "nam_minh", NAM_MINH_PERSONA

    return "hoai_my", HOAI_MY_PERSONA
```

### 3.3 Offline Deterministic Template Formulas

To ensure scripts never violate `ToneValidator` while having rich variations, formulate rotating template banks:

#### Fashion Persona ("Hoài My" - `vi-VN-HoaiMyNeural`)
- **Hook 3s Bank** (All contain body-hack keywords & KOC marker):
  1. `"Chị em ơi, ai bảo eo to không mặc đẹp được? Nhìn ngay chiếc {clean_title} này!"`
  2. `"Mấy bà ơi, bà nào bụng dưới to bơi hết vào đây, chiếc {clean_title} này cứu cánh cực đỉnh!"`
  3. `"Team chân ngắn đâu rồi bơi vào đây, chiếc {clean_title} này hack dáng đỉnh chóp luôn nha!"`
  4. `"Chị em ơi, mặc chiếc {clean_title} này lên là eo thon gọn hẳn 5 phân không cần nịt bụng luôn!"`
- **Body Bank** (Realistic problem/solution + authentic review with mild caveat):
  1. `"Form may chiết eo cao giấu nhẹm mỡ thừa chỉ trong tích tắc, chất vải xịn sò mát rượi đứng form cực kỳ. Đi làm hay đi cà phê cuối tuần cũng tôn dáng hết nấc, mỗi tội chị em nhớ ủi nhẹ trước khi mặc là chuẩn đét luôn."`
  2. `"Chất vải cực mát, form may tôn dáng, che trọn khuyết điểm bụng dưới chỉ sau 1 giây. Đường may tỉ mỉ, mặc lên nhẹ tênh mà giấu mỡ bắp tay đỉnh thực sự. Nhìn ở ngoài xinh xỉu hơn trên hình nhiều nha."`
  3. `"Bà nào hay ngồi văn phòng sợ lộ bụng mỡ thì chiếc này đúng là chân ái. Xếp ly xòe nhẹ che sạch mỡ bụng dưới, tạo cảm giác chân dài miên man. Tui test cả ngày không hề nhăn nhúm hay bí bách gì cả."`
- **CTA Bank** (Yellow cart guidance + freeship/voucher):
  1. `"Chị em bấm ngay góc trái màn hình nhận mã freeship và rinh về nhé!"`
  2. `"Mấy bà bấm ngay giỏ hàng góc trái săn voucher giảm giá nha, số lượng có hạn đó!"`
  3. `"Link tui để sẵn ở giỏ hàng vàng góc trái màn hình nè, nhanh tay kẻo hết size nha chị em!"`
- **Caption Bank**:
  1. `"{clean_title} tôn dáng cực đỉnh #fashion #xuhuong #thoitrang #koc"`
  2. `"{clean_title} hack dáng che khuyết điểm cho chị em #outfit #thoitrangnu #xuhuong"`

#### HomeLife Persona ("Nam Minh" - `vi-VN-NamMinhNeural`)
- **Hook 3s Bank** (All contain '3s' / 'nhàn' & KOC marker):
  1. `"Các bác ơi, từ ngày tậu em {clean_title} này việc nhà nhàn hẳn, 3s là nhà sạch bóng!"`
  2. `"Bỏ ngay mấy cái giẻ lau cũ đi các bác, dùng em {clean_title} này nhàn tênh!"`
  3. `"Các bác ơi, 3 giây sạch bóng kin kít không tốn một giọt mồ hôi, chân ái dọn nhà đây rồi!"`
  4. `"Bà nào ngại dọn nhà bơi vào đây, có em {clean_title} này việc nhà nhàn hẳn!"`
- **Body Bank** (Before/After 3s + labor saving + objective review):
  1. `"Cơ chế thông minh tự vắt ráo nước trong một nốt nhạc, lau sạch kin kít vết dầu mỡ cứng đầu mà không cần cúi còng cả lưng. Bác nào nhà có con nhỏ hay nuôi thú cưng thì rinh em này về giải phóng sức lao động cực kỳ nhàn luôn."`
  2. `"Test thực tế cho các bác xem, chỉ cần đẩy nhẹ 3 giây là sàn nhà khô ráo sạch bong kin kít. Không tốn sức, không bẩn tay, khay chứa rác thông minh dễ vệ sinh cực kỳ, mỗi tội lúc mới dùng phải đọc kỹ hướng dẫn lắp một chút thôi."`
  3. `"Từ ngày có em này tui tiết kiệm được nửa tiếng dọn dẹp mỗi ngày. Vết bẩn cứng đầu trên sàn bếp chà nhẹ là sạch bóng, thiết kế gọn gàng dựng góc nhà nhàn tênh."`
- **CTA Bank**:
  1. `"Các bác bấm ngay vào giỏ hàng góc trái màn hình nhận mã ưu đãi nha!"`
  2. `"Đang có mã giảm giá ở giỏ hàng vàng kìa các bác ơi, bấm góc trái màn hình đặt ngay nhé!"`
  3. `"Link mua chính hãng tui ghim ở giỏ hàng góc trái màn hình rồi, các bác bấm vào xem nha!"`
- **Caption Bank**:
  1. `"{clean_title} giải phóng việc nhà nhàn tênh 3s #dogiadung #giadungthongminh #xuhuong #koc"`
  2. `"{clean_title} chân ái cho hội lười dọn dẹp #meovat #giadungtienich #xuhuong"`

### 3.4 Title Sanitization & Self-Correction Pipeline

If an input title or LLM text carries dirty brand names (e.g. "Váy Z.a.r.a rep 1:1"), it must be cleansed before script injection:

```python
def _sanitize_title(self, raw_title: str) -> str:
    """Removes counterfeit trademarks, robotic keywords, and exaggerated claims from product title."""
    title = raw_title.strip()
    # Strip known trademarks & counterfeit markers
    banned_terms = [
        r"\bz\.?a\.?r\.?a\b", r"\bc\.?h\.?a\.?n\.?e\.?l\b", r"\bg\.?u\.?c\.?c\.?i\b",
        r"\bd\.?i\.?o\.?r\b", r"\bl\.?v\b", r"\blouis\s*vuitton\b", r"\bhermes\b",
        r"\bnike\b", r"\badidas\b", r"\brep\s*1[\:\/\.]1\b", r"\bsuper\s*fake\b",
        r"\bfake\s*1\b", r"\bfake\b", r"\bnhái\b", r"\blike\s*auth\b", r"\btuồn\s*auth\b",
        r"\btrị\s*dứt\s*điểm\s*100\%\b", r"\bvĩnh\s*viễn\s*không\s*hỏng\b"
    ]
    for pattern in banned_terms:
        title = re.sub(pattern, "", title, flags=re.IGNORECASE)
    # Collapse leftover whitespace and punctuation
    title = re.sub(r"\s+", " ", title).strip(" -_:,.")
    return title or "sản phẩm hot"
```

### 3.5 Generation Orchestration Flow

```
Input: product_meta, persona
  │
  ▼
1. Normalize product_meta (dict/dataclass/ORM model)
  │
  ▼
2. Resolve persona (Hoài My vs Nam Minh, Voice ID, Target Niche)
  │
  ▼
3. Sanitize product title (strip trademarks, fake words, exaggerated claims)
  │
  ▼
4. Attempt LLM Generation (if llm_client or REST configured)
   ├── Success -> Parse JSON {hook_3s, body, cta_yellow_cart, caption}
   └── Failure / Missing -> Fallback to Deterministic Template Engine
  │
  ▼
5. Assemble candidate: full_voiceover = f"{hook_3s} {body} {cta_yellow_cart}"
  │
  ▼
6. Strict Validation Gate:
   ├── ToneValidator.validate(full_voiceover) == True
   └── ToneValidator.has_koc_markers(full_voiceover) == True
   │
   ├── If BOTH True: Proceed to packaging
   └── If ANY False: Swap candidate with Pre-Certified Offline Template
  │
  ▼
7. Package KOCScriptResult (includes duration estimate, voice_id, caption)
  │
  ▼
Return: KOCScriptResult (supports dict indexation)
```

---

## 4. Test Suite Specification (`tests/test_script_generator.py`)

The test suite must be exhaustive, verifying all contract bounds, edge cases, persona differences, ToneValidator enforcement, and mocking scenarios.

### Proposed Test Plan (20 Test Cases)

| Test Function | Target Feature / Verification Objective | Expected Outcome |
| :--- | :--- | :--- |
| `test_contract_tier1_compatibility` | Verifies full compliance with `test_f15_koc_script_generator` contract | All 5 keys present; `ToneValidator.validate()` is `True` |
| `test_input_types_dictionary` | Test with standard dictionary product input | Valid `KOCScriptResult` returned |
| `test_input_types_product_candidate` | Test with `ProductCandidate` dataclass from `base_scout` | Valid `KOCScriptResult` returned |
| `test_input_types_specialist_evaluation` | Test with `SpecialistEvaluation` dataclass from `fashion_scout` | Valid `KOCScriptResult` returned |
| `test_input_types_orm_product_model` | Test with SQLAlchemy `Product` model instance | Valid `KOCScriptResult` returned |
| `test_input_types_corrupted_or_none` | Test with `None`, empty dict, or non-dict input | Graceful recovery with fallback script; no crash |
| `test_persona_fashion_hoai_my` | Fashion niche selects Hoài My persona and `vi-VN-HoaiMyNeural` voice | Voice ID is `vi-VN-HoaiMyNeural`; pronouns include `chị em` / `tui` |
| `test_persona_homelife_nam_minh` | HomeLife niche selects Nam Minh persona and `vi-VN-NamMinhNeural` voice | Voice ID is `vi-VN-NamMinhNeural`; pronouns include `các bác` / `tui` |
| `test_auto_persona_inference_by_niche` | When persona is not specified, auto-select based on `niche_id` | Correct persona and voice assigned |
| `test_auto_persona_inference_by_title` | When persona and `niche_id` are absent, infer from title keywords | Title with "lau nhà" chooses Nam Minh; "váy" chooses Hoài My |
| `test_hook_3s_fashion_rules` | Fashion hook contains body-hack keywords ('bụng'/'eo') and KOC marker | Substring assertions match hook guidelines |
| `test_hook_3s_homelife_rules` | HomeLife hook contains labor-saving ('3s'/'nhàn') and KOC marker | Substring assertions match hook guidelines |
| `test_cta_yellow_cart_navigation` | CTA explicitly directs to yellow cart / lower-left screen | Contains 'giỏ hàng góc trái' / 'góc trái màn hình' / 'giỏ hàng vàng' |
| `test_tone_validator_zero_robotic_cliches` | Generated script contains 0 robotic phrases from `ROBOTIC_PATTERNS` | `ToneValidator.validate(full_voiceover) is True` |
| `test_tone_validator_has_koc_markers` | Generated script contains at least 1 natural KOC marker | `ToneValidator.has_koc_markers(full_voiceover) is True` |
| `test_dirty_title_sanitization` | Input product title has "Z.a.r.a rep 1:1" or "trị dứt điểm" | Cleansed title used; final script has 0 violations |
| `test_template_rotation_hash_diversity` | Different product titles generate diverse script variations | Multiple distinct script variations observed across 5 products |
| `test_duration_estimation_bounds` | Voiceover pacing calculation matches 30-45s TikTok duration | `estimated_duration_sec` between 20.0s and 55.0s |
| `test_mock_llm_successful_generation` | Pluggable LLM returns valid JSON response | LLM output parsed and validated |
| `test_mock_llm_failure_triggers_offline_fallback` | LLM returns robotic cliché, invalid JSON, or raises exception | Engine seamlessly falls back to certified template without error |

---

## 5. Verification Method

### 5.1 Independent Test Commands

Once implemented, the following test commands verify compliance:

1. **Unit Test Suite for Script Generator**:
   ```bash
   pytest tests/test_script_generator.py -v
   ```
2. **Contract Compatibility in E2E Suite**:
   ```bash
   pytest tests/e2e/test_tier1_features.py -k "test_f15_koc_script_generator" -v
   ```
3. **Cross-Feature Tone Validation**:
   ```bash
   pytest tests/test_specialist_scouts.py -k "test_generated_hook_angles_satisfy_tone_validator" -v
   ```

### 5.2 Standalone Python Verification Script
Execute in workspace shell:
```python
from src.services.script_generator import ScriptGenerator
from src.core.tone_validator import ToneValidator

gen = ScriptGenerator()

# 1. Fashion Product Test
fashion_prod = {
    "product_id": "fash_01",
    "niche_id": "thoi_trang_nu",
    "title": "Váy hoa nhí dáng xòe chiết eo hack dáng",
    "price": 189000.0,
}
script_f = gen.generate_script(fashion_prod, {"tone": "koc"})
assert "hook_3s" in script_f
assert "cta_yellow_cart" in script_f
assert "caption" in script_f
assert ToneValidator.validate(script_f["full_voiceover"]) is True
assert ToneValidator.has_koc_markers(script_f["full_voiceover"]) is True
assert script_f["voice_id"] == "vi-VN-HoaiMyNeural"

# 2. HomeLife Product Test
home_prod = {
    "product_id": "home_01",
    "niche_id": "do_gia_dung",
    "title": "Cây lau nhà tự vắt xoay 360 độ thông minh",
    "price": 149000.0,
}
script_h = gen.generate_script(home_prod, {"tone": "koc"})
assert "hook_3s" in script_h
assert "cta_yellow_cart" in script_h
assert "caption" in script_h
assert ToneValidator.validate(script_h["full_voiceover"]) is True
assert ToneValidator.has_koc_markers(script_h["full_voiceover"]) is True
assert script_h["voice_id"] == "vi-VN-NamMinhNeural"
```

### 5.3 Invalidation Conditions
The technical design is invalidated if:
1. `ToneValidator.validate(script["full_voiceover"])` returns `False` under any valid product title input.
2. `ToneValidator.has_koc_markers(script["full_voiceover"])` returns `False`.
3. The method signature cannot be called synchronously by `test_f15_koc_script_generator` or `VideoStudioAgent.produce_video`.
4. The output lacks any of the required keys (`hook_3s`, `cta_yellow_cart`, `caption`, `full_voiceover`).
5. A missing internet connection or uninstalled LLM package causes `generate_script` to crash with an unhandled exception.

---

## 6. Caveats
1. **Network & LLM SDK Constraints**: As observed in Section 1.4, `google-genai` is not installed in the workspace Python environment. Therefore, the service relies fundamentally on its robust offline deterministic generator for 100% test reliability, while providing clean interfaces for REST calls or mock injection.
2. **Audio Duration Estimation**: Estimated reading duration is approximated based on normal Vietnamese conversational pace (~2.8 to 3.2 words per second). Exact audio length will be determined downstream by `TTSService` using `mutagen` or `ffprobe`.
3. **Database Integration**: `VideoJob.script` field stores the script string. Storing either `full_voiceover` or a JSON string of `KOCScriptResult.to_dict()` is recommended for persistence compatibility.
