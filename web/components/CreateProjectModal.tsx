"use client";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { X, Info, Sparkles, Layers, Check, Plus, Tag } from "lucide-react";
import { useProject, PresetItem } from "@/context/ProjectContext";

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const FIELD_INFOS = {
  name: {
    meaning: "Tên nhận diện không gian làm việc của dự án.",
    aiUsage: "AI dùng tên này để phân loại báo cáo và hiển thị trên dashboard quản trị.",
    chips: ["Thời Trang GenZ Y2K", "Gia Dụng Thông Minh", "Mỹ Phẩm Trị Mụn", "Setup Góc Công Nghệ"],
  },
  niche_brief: {
    meaning: "Mô tả chi tiết ngách ngành hàng mục tiêu và các nhóm sản phẩm chủ lực.",
    aiUsage: "AI dùng thông tin này để định hướng chủ đề video, lựa chọn phong cách quay dựng và phân tích đối thủ.",
    chips: ["Streetwear & Y2K cá tính", "Thiết bị nhà bếp tiện ích", "Chăm sóc da dầu mụn khoa học", "Phụ kiện sạc nhanh & âm thanh"],
  },
  target_audience: {
    meaning: "Đặc điểm nhân khẩu học, độ tuổi và nỗi đau (pain points) của khách hàng.",
    aiUsage: "AI dùng để cá nhân hóa xưng hô, đánh trúng tâm lý người xem trong 3 giây Hook đầu tiên.",
    chips: ["GenZ 18-24 tuổi mê thời trang", "Người nội trợ 25-40 tuổi", "Sinh viên & dân văn phòng", "Game thủ & tín đồ công nghệ"],
  },
  tone_of_voice: {
    meaning: "Giọng điệu và tính cách thương hiệu khi giao tiếp với khách hàng.",
    aiUsage: "AI áp dụng văn phong này khi viết kịch bản video, caption mạng xã hội và trả lời seeding comment.",
    chips: ["Hài hước, bắt trend TikTok", "Chuyên gia uy tín, chân thành", "Nhiệt huyết, dí dỏm", "Trẻ trung, gần gũi"],
  },
  trigger_keywords: {
    meaning: "Danh sách từ khóa kích hoạt bot tự động comment seeding trong Facebook Groups.",
    aiUsage: "Khi phát hiện bài viết thành viên có chứa từ khóa này, bot tự động sinh câu trả lời KOC tự nhiên.",
    chips: ["tìm mua", "giá bao nhiêu", "review uy tín", "cần tư vấn", "chỗ nào bán tốt"],
  },
  negative_keywords: {
    meaning: "Các từ cấm kỵ, nhạy cảm hoặc đối thủ cạnh tranh tuyệt đối không được nhắc đến.",
    aiUsage: "AI sẽ lọc sạch và loại trừ các từ này trong toàn bộ kịch bản, caption và câu trả lời tự động.",
    chips: ["hàng giả", "kém chất lượng", "lừa đảo", "kem trộn", "cháy nổ"],
  },
};

export const CreateProjectModal: React.FC<CreateProjectModalProps> = ({ isOpen, onClose }) => {
  const { createProject, presets } = useProject();

  const [name, setName] = useState("");
  const [nicheBrief, setNicheBrief] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [toneOfVoice, setToneOfVoice] = useState("");
  const [triggerKeywords, setTriggerKeywords] = useState("");
  const [negativeKeywords, setNegativeKeywords] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTooltip, setActiveTooltip] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  // Client-side portal mounting check
  useEffect(() => {
    setMounted(true);
  }, []);

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !mounted) return null;

  const handleApplyPreset = (preset: PresetItem) => {
    setName(preset.name);
    setNicheBrief(preset.niche_brief);
    setTargetAudience(preset.target_audience);
    setToneOfVoice(preset.tone_of_voice);
    setTriggerKeywords(preset.trigger_keywords.join(", "));
    setNegativeKeywords(preset.negative_keywords.join(", "));
  };

  const handleAddChip = (field: string, chipValue: string) => {
    switch (field) {
      case "name":
        setName(chipValue);
        break;
      case "niche_brief":
        setNicheBrief((prev) => (prev ? `${prev}, ${chipValue}` : chipValue));
        break;
      case "target_audience":
        setTargetAudience((prev) => (prev ? `${prev}, ${chipValue}` : chipValue));
        break;
      case "tone_of_voice":
        setToneOfVoice((prev) => (prev ? `${prev}, ${chipValue}` : chipValue));
        break;
      case "trigger_keywords":
        setTriggerKeywords((prev) => (prev ? `${prev}, ${chipValue}` : chipValue));
        break;
      case "negative_keywords":
        setNegativeKeywords((prev) => (prev ? `${prev}, ${chipValue}` : chipValue));
        break;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    try {
      await createProject({
        name: name.trim(),
        niche_brief: nicheBrief.trim() || undefined,
        target_audience: targetAudience.trim() || undefined,
        tone_of_voice: toneOfVoice.trim() || undefined,
        trigger_keywords: triggerKeywords ? triggerKeywords.split(",").map((k) => k.trim()).filter(Boolean) : undefined,
        negative_keywords: negativeKeywords ? negativeKeywords.split(",").map((k) => k.trim()).filter(Boolean) : undefined,
        website_url: websiteUrl.trim() || undefined,
      });
      onClose();
    } catch {
      // Error handled in context
    } finally {
      setIsSubmitting(false);
    }
  };

  const modalContent = (
    <div
      onClick={onClose}
      className="fixed top-16 inset-x-0 bottom-0 z-40 flex items-center justify-center p-4 md:p-6 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-2xl max-h-[calc(100vh-6rem)] flex flex-col bg-[#0B0B14] border border-[#252538] rounded-2xl shadow-2xl text-[#F8FAFC] overflow-hidden"
      >
        {/* Sticky Header */}
        <div className="shrink-0 flex items-center justify-between p-5 border-b border-[#252538] bg-[#0E0E18]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#41AA6C]/10 border border-[#41AA6C]/30 flex items-center justify-center">
              <Layers className="w-5 h-5 text-[#41AA6C]" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">Tạo Project Mới</h2>
              <p className="text-xs text-[#94A3B8]">
                Cấu hình không gian làm việc và huấn luyện ngữ cảnh AI cho ngách affiliate
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-[#94A3B8] hover:text-white hover:bg-white/5 transition-all duration-150 cursor-pointer"
            aria-label="Đóng"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-5 md:p-6 space-y-4">
          {/* 1-Click Presets Header */}
          <div className="p-3 rounded-xl bg-[#12121E] border border-[#252538]">
            <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-[#41AA6C] uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Mẫu Dự Án Có Sẵn (1-Click Preset)</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {presets.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handleApplyPreset(p)}
                  className="text-left p-2 rounded-lg bg-[#181828] hover:bg-[#41AA6C]/15 border border-[#252538] hover:border-[#41AA6C]/40 transition-all duration-150 cursor-pointer group"
                >
                  <div className="text-xs font-medium text-white group-hover:text-[#41AA6C] truncate">{p.name}</div>
                  <div className="text-[10px] text-[#94A3B8] truncate">{p.target_audience.split(",")[0]}</div>
                </button>
              ))}
            </div>
          </div>

          {/* 1. Tên Dự Án */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-1.5">
                <label className="text-xs font-semibold text-slate-200">1. Tên Dự Án</label>
                <span className="text-rose-500">*</span>
                <div className="relative">
                  <button
                    type="button"
                    onMouseEnter={() => setActiveTooltip("name")}
                    onMouseLeave={() => setActiveTooltip(null)}
                    onFocus={() => setActiveTooltip("name")}
                    onBlur={() => setActiveTooltip(null)}
                    className="text-[#94A3B8] hover:text-[#41AA6C] transition-colors p-0.5 cursor-pointer"
                  >
                    <Info className="w-3.5 h-3.5" />
                  </button>
                  {activeTooltip === "name" && (
                    <div className="absolute left-6 top-0 z-50 w-64 p-2.5 rounded-lg bg-[#181828] border border-[#252538] text-xs text-slate-200 shadow-xl pointer-events-none">
                      <p className="font-semibold text-[#41AA6C] mb-1">Ý nghĩa:</p>
                      <p className="text-[#94A3B8] mb-1.5">{FIELD_INFOS.name.meaning}</p>
                      <p className="font-semibold text-indigo-400 mb-1">AI sử dụng ra sao:</p>
                      <p className="text-[#94A3B8]">{FIELD_INFOS.name.aiUsage}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="VD: Thời Trang GenZ Y2K"
              className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] focus:border-[#41AA6C] text-sm text-white focus:outline-none transition-all duration-150"
            />
            {/* Quick chips */}
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {FIELD_INFOS.name.chips.map((c, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleAddChip("name", c)}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-[#181828] hover:bg-[#41AA6C]/10 text-[#94A3B8] hover:text-[#41AA6C] border border-[#252538] transition-all duration-150 cursor-pointer"
                >
                  <Plus className="w-2.5 h-2.5" />
                  <span>{c}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 2. Mô Tả Ngành Hàng */}
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <label className="text-xs font-semibold text-slate-200">2. Mô Tả Ngành Hàng (Niche Brief)</label>
              <div className="relative">
                <button
                  type="button"
                  onMouseEnter={() => setActiveTooltip("niche_brief")}
                  onMouseLeave={() => setActiveTooltip(null)}
                  className="text-[#94A3B8] hover:text-[#41AA6C] p-0.5 cursor-pointer"
                >
                  <Info className="w-3.5 h-3.5" />
                </button>
                {activeTooltip === "niche_brief" && (
                  <div className="absolute left-6 top-0 z-50 w-72 p-2.5 rounded-lg bg-[#181828] border border-[#252538] text-xs text-slate-200 shadow-xl pointer-events-none">
                    <p className="font-semibold text-[#41AA6C] mb-1">Ý nghĩa:</p>
                    <p className="text-[#94A3B8] mb-1.5">{FIELD_INFOS.niche_brief.meaning}</p>
                    <p className="font-semibold text-indigo-400 mb-1">AI sử dụng ra sao:</p>
                    <p className="text-[#94A3B8]">{FIELD_INFOS.niche_brief.aiUsage}</p>
                  </div>
                )}
              </div>
            </div>
            <textarea
              rows={2}
              value={nicheBrief}
              onChange={(e) => setNicheBrief(e.target.value)}
              placeholder="VD: Thời trang GenZ xu hướng Y2K, đồ công sở trẻ..."
              className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] focus:border-[#41AA6C] text-sm text-white focus:outline-none transition-all duration-150"
            />
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {FIELD_INFOS.niche_brief.chips.map((c, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleAddChip("niche_brief", c)}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-[#181828] hover:bg-[#41AA6C]/10 text-[#94A3B8] hover:text-[#41AA6C] border border-[#252538] transition-all duration-150 cursor-pointer"
                >
                  <Plus className="w-2.5 h-2.5" />
                  <span>{c}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 3. Chân Dung Khách Hàng Mục Tiêu */}
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <label className="text-xs font-semibold text-slate-200">3. Chân Dung Khách Hàng Mục Tiêu</label>
              <div className="relative">
                <button
                  type="button"
                  onMouseEnter={() => setActiveTooltip("target_audience")}
                  onMouseLeave={() => setActiveTooltip(null)}
                  className="text-[#94A3B8] hover:text-[#41AA6C] p-0.5 cursor-pointer"
                >
                  <Info className="w-3.5 h-3.5" />
                </button>
                {activeTooltip === "target_audience" && (
                  <div className="absolute left-6 top-0 z-50 w-72 p-2.5 rounded-lg bg-[#181828] border border-[#252538] text-xs text-slate-200 shadow-xl pointer-events-none">
                    <p className="font-semibold text-[#41AA6C] mb-1">Ý nghĩa:</p>
                    <p className="text-[#94A3B8] mb-1.5">{FIELD_INFOS.target_audience.meaning}</p>
                    <p className="font-semibold text-indigo-400 mb-1">AI sử dụng ra sao:</p>
                    <p className="text-[#94A3B8]">{FIELD_INFOS.target_audience.aiUsage}</p>
                  </div>
                )}
              </div>
            </div>
            <input
              type="text"
              value={targetAudience}
              onChange={(e) => setTargetAudience(e.target.value)}
              placeholder="VD: Nữ giới 18-26 tuổi, học sinh, sinh viên..."
              className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] focus:border-[#41AA6C] text-sm text-white focus:outline-none transition-all duration-150"
            />
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {FIELD_INFOS.target_audience.chips.map((c, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleAddChip("target_audience", c)}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-[#181828] hover:bg-[#41AA6C]/10 text-[#94A3B8] hover:text-[#41AA6C] border border-[#252538] transition-all duration-150 cursor-pointer"
                >
                  <Plus className="w-2.5 h-2.5" />
                  <span>{c}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 4. Văn Phong Thương Hiệu */}
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <label className="text-xs font-semibold text-slate-200">4. Văn Phong Thương Hiệu (Tone of Voice)</label>
              <div className="relative">
                <button
                  type="button"
                  onMouseEnter={() => setActiveTooltip("tone_of_voice")}
                  onMouseLeave={() => setActiveTooltip(null)}
                  className="text-[#94A3B8] hover:text-[#41AA6C] p-0.5 cursor-pointer"
                >
                  <Info className="w-3.5 h-3.5" />
                </button>
                {activeTooltip === "tone_of_voice" && (
                  <div className="absolute left-6 top-0 z-50 w-72 p-2.5 rounded-lg bg-[#181828] border border-[#252538] text-xs text-slate-200 shadow-xl pointer-events-none">
                    <p className="font-semibold text-[#41AA6C] mb-1">Ý nghĩa:</p>
                    <p className="text-[#94A3B8] mb-1.5">{FIELD_INFOS.tone_of_voice.meaning}</p>
                    <p className="font-semibold text-indigo-400 mb-1">AI sử dụng ra sao:</p>
                    <p className="text-[#94A3B8]">{FIELD_INFOS.tone_of_voice.aiUsage}</p>
                  </div>
                )}
              </div>
            </div>
            <input
              type="text"
              value={toneOfVoice}
              onChange={(e) => setToneOfVoice(e.target.value)}
              placeholder="VD: GenZ gần gũi, hài hước, bắt trend TikTok..."
              className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] focus:border-[#41AA6C] text-sm text-white focus:outline-none transition-all duration-150"
            />
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {FIELD_INFOS.tone_of_voice.chips.map((c, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleAddChip("tone_of_voice", c)}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-[#181828] hover:bg-[#41AA6C]/10 text-[#94A3B8] hover:text-[#41AA6C] border border-[#252538] transition-all duration-150 cursor-pointer"
                >
                  <Plus className="w-2.5 h-2.5" />
                  <span>{c}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 5. Từ Khóa Kích Hoạt Seeding Group */}
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <label className="text-xs font-semibold text-slate-200">
                5. Từ Khóa Kích Hoạt Seeding Group (phân tách bởi dấu phẩy)
              </label>
              <div className="relative">
                <button
                  type="button"
                  onMouseEnter={() => setActiveTooltip("trigger_keywords")}
                  onMouseLeave={() => setActiveTooltip(null)}
                  className="text-[#94A3B8] hover:text-[#41AA6C] p-0.5 cursor-pointer"
                >
                  <Info className="w-3.5 h-3.5" />
                </button>
                {activeTooltip === "trigger_keywords" && (
                  <div className="absolute left-6 top-0 z-50 w-72 p-2.5 rounded-lg bg-[#181828] border border-[#252538] text-xs text-slate-200 shadow-xl pointer-events-none">
                    <p className="font-semibold text-[#41AA6C] mb-1">Ý nghĩa:</p>
                    <p className="text-[#94A3B8] mb-1.5">{FIELD_INFOS.trigger_keywords.meaning}</p>
                    <p className="font-semibold text-indigo-400 mb-1">AI sử dụng ra sao:</p>
                    <p className="text-[#94A3B8]">{FIELD_INFOS.trigger_keywords.aiUsage}</p>
                  </div>
                )}
              </div>
            </div>
            <input
              type="text"
              value={triggerKeywords}
              onChange={(e) => setTriggerKeywords(e.target.value)}
              placeholder="VD: váy xinh, outfit, set đồ, phối đồ, áo thun"
              className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] focus:border-[#41AA6C] text-sm text-white focus:outline-none transition-all duration-150"
            />
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {FIELD_INFOS.trigger_keywords.chips.map((c, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleAddChip("trigger_keywords", c)}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-[#181828] hover:bg-[#41AA6C]/10 text-[#94A3B8] hover:text-[#41AA6C] border border-[#252538] transition-all duration-150 cursor-pointer"
                >
                  <Tag className="w-2.5 h-2.5" />
                  <span>{c}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 6. Từ Khóa Cấm / Tiêu Cực */}
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <label className="text-xs font-semibold text-slate-200">
                6. Từ Khóa Cấm / Tiêu Cực (phân tách bởi dấu phẩy)
              </label>
              <div className="relative">
                <button
                  type="button"
                  onMouseEnter={() => setActiveTooltip("negative_keywords")}
                  onMouseLeave={() => setActiveTooltip(null)}
                  className="text-[#94A3B8] hover:text-[#41AA6C] p-0.5 cursor-pointer"
                >
                  <Info className="w-3.5 h-3.5" />
                </button>
                {activeTooltip === "negative_keywords" && (
                  <div className="absolute left-6 top-0 z-50 w-72 p-2.5 rounded-lg bg-[#181828] border border-[#252538] text-xs text-slate-200 shadow-xl pointer-events-none">
                    <p className="font-semibold text-[#41AA6C] mb-1">Ý nghĩa:</p>
                    <p className="text-[#94A3B8] mb-1.5">{FIELD_INFOS.negative_keywords.meaning}</p>
                    <p className="font-semibold text-indigo-400 mb-1">AI sử dụng ra sao:</p>
                    <p className="text-[#94A3B8]">{FIELD_INFOS.negative_keywords.aiUsage}</p>
                  </div>
                )}
              </div>
            </div>
            <input
              type="text"
              value={negativeKeywords}
              onChange={(e) => setNegativeKeywords(e.target.value)}
              placeholder="VD: hàng lỗi, vải mỏng rách, kém chất lượng, lừa đảo"
              className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] focus:border-[#41AA6C] text-sm text-white focus:outline-none transition-all duration-150"
            />
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {FIELD_INFOS.negative_keywords.chips.map((c, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleAddChip("negative_keywords", c)}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-[#181828] hover:bg-rose-500/10 text-[#94A3B8] hover:text-rose-400 border border-[#252538] transition-all duration-150 cursor-pointer"
                >
                  <Tag className="w-2.5 h-2.5" />
                  <span>{c}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Website URL (optional for OpenSEO) */}
          <div>
            <label className="block text-xs font-semibold text-slate-200 mb-1.5">
              Website Domain / Landing Page (Tùy chọn)
            </label>
            <input
              type="url"
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
              placeholder="https://thoitranggenz.vn"
              className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] focus:border-[#41AA6C] text-sm text-white focus:outline-none transition-all duration-150"
            />
          </div>
        </form>

        {/* Sticky Actions Footer */}
        <div className="shrink-0 flex items-center justify-end gap-3 p-4 px-6 border-t border-[#252538] bg-[#0E0E18]">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-xl text-xs font-medium text-[#94A3B8] hover:text-white bg-[#181828] border border-[#252538] hover:border-slate-700 transition-all duration-150 cursor-pointer"
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting || !name.trim()}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-[#41AA6C] hover:bg-[#34925b] text-white text-xs font-semibold transition-all duration-150 shadow-sm shadow-[#41AA6C]/25 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                <span>Đang tạo...</span>
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                <span>Tạo Project & Áp Dụng Ngay</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
};
