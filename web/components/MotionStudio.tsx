"use client";

import React, { useState } from "react";
import {
  Video,
  Scissors,
  User,
  ShoppingBag,
  Sparkles,
  Play,
  RotateCw,
  Send,
  Zap,
  CheckCircle2,
  Clock,
  Loader2,
  Mic,
} from "lucide-react";

interface Segment {
  name: string;
  label: string;
  duration: string;
  prompt: string;
  script: string;
}

export const MotionStudio: React.FC = () => {
  // Input states
  const [videoUrl, setVideoUrl] = useState("https://www.tiktok.com/@fashion_trend/video/73912345678");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeSegmentIndex, setActiveSegmentIndex] = useState(0);

  // 4 functional segments
  const [segments, setSegments] = useState<Segment[]>([
    {
      name: "hook",
      label: "Hook 3s",
      duration: "0.0s - 3.0s",
      prompt: "Attractive Vietnamese female model greeting viewers with natural welcoming gestures",
      script: "Chào cả nhà, chiếc đầm che bụng cực phẩm này đang làm mưa làm gió!",
    },
    {
      name: "problem",
      label: "Vấn đề / Bối cảnh",
      duration: "3.0s - 10.5s",
      prompt: "Model pointing at waistline showing common struggle with ordinary tight fitting dresses",
      script: "Chị em nào bụng dưới to, bắp tay kém thon mỗi lần chọn đồ đi tiệc cực khổ luôn đúng không?",
    },
    {
      name: "demo",
      label: "Demo Sản phẩm",
      duration: "10.5s - 25.0s",
      prompt: "Model twirling gracefully showcasing fabric fluidity, seams, and slimming silhouette",
      script: "Form váy chữ A giấu trọn bụng, chất vải lụa tuyết mịn màng, co giãn cực kỳ thoáng mát.",
    },
    {
      name: "cta",
      label: "CTA Giỏ hàng",
      duration: "25.0s - 30.0s",
      prompt: "Model smiling warmly pointing down towards bottom left shopping cart icon",
      script: "Hôm nay đang có voucher giảm 30k, bấm ngay vào giỏ hàng góc trái săn liền nhé!",
    },
  ]);

  // Model & Voice options
  const [engineMode, setEngineMode] = useState<"kling" | "hybrid">("kling");
  const [voiceId, setVoiceId] = useState("vi-VN-HoaiMyNeural");

  // Job generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [progressStage, setProgressStage] = useState<string | null>(null);
  const [progressPercent, setProgressPercent] = useState(0);
  const [renderedVideo, setRenderedVideo] = useState<string | null>(null);

  // Handle URL Preprocessing
  const handlePreprocess = async () => {
    setIsAnalyzing(true);
    try {
      const res = await fetch("http://localhost:8000/api/studio/preprocess", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_url_or_path: videoUrl, cut_clips: false }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.segments && data.segments.length === 4) {
          setSegments(
            data.segments.map((s: { name: string; description?: string; start_sec: number; end_sec: number; transcript_text?: string }, idx: number) => ({
              name: s.name,
              label: s.description || `Đoạn ${idx + 1}`,
              duration: `${s.start_sec}s - ${s.end_sec}s`,
              prompt: `Model motion replicating ${s.name} segment with authentic physics`,
              script: s.transcript_text || segments[idx]?.script || "",
            }))
          );
        }
      }
    } catch {
      // Fallback in case local server port is quiet
    } finally {
      setTimeout(() => setIsAnalyzing(false), 500);
    }
  };

  // Handle Video Generation
  const handleGenerate = async () => {
    setIsGenerating(true);
    setProgressPercent(15);
    setProgressStage("Tiền xử lý ảnh nhân vật & phom dáng sản phẩm...");

    // SSE-like smooth progress simulation
    setTimeout(() => {
      setProgressPercent(45);
      setProgressStage("Replicate Kling v3: Đang tổng hợp chuyển động 4 phân đoạn...");
    }, 1200);

    setTimeout(() => {
      setProgressPercent(75);
      setProgressStage("Lồng tiếng KOC tiếng Việt & khử chữ ký số video AI...");
    }, 2400);

    setTimeout(() => {
      setProgressPercent(100);
      setProgressStage("Hoàn tất video chuẩn 1080x1920!");
      setRenderedVideo("https://assets.mixkit.co/videos/preview/mixkit-fashion-model-in-a-neon-room-41551-large.mp4");
      setIsGenerating(false);
    }, 3600);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      {/* CỘT TRÁI: ĐIỀU KHIỂN & CẤU HÌNH TIMELINE (7 Cột) */}
      <div className="lg:col-span-7 space-y-6">
        {/* Bước 1: Chọn Motion Reference Video */}
        <section className="bg-[#12121E] border border-[#252538] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-[#41AA6C]/10 text-[#41AA6C] flex items-center justify-center font-bold text-xs">
                1
              </div>
              <h2 className="font-semibold text-white text-base">Chọn Motion Reference Video</h2>
            </div>
            <span className="text-xs text-[#94A3B8]">TikTok / Reels / Douyin</span>
          </div>

          <div className="flex gap-2">
            <div className="relative flex-1">
              <Video className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94A3B8]" />
              <input
                type="text"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="Dán link video đối thủ vào đây..."
                className="w-full bg-[#000000] border border-[#252538] rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-[#94A3B8]/60 focus:outline-none focus:border-[#41AA6C] transition-all duration-200"
              />
            </div>
            <button
              onClick={handlePreprocess}
              disabled={isAnalyzing}
              className="flex items-center gap-2 bg-[#41AA6C] hover:bg-[#34925b] text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 cursor-pointer disabled:opacity-50"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Đang bóc tách...</span>
                </>
              ) : (
                <>
                  <Scissors className="w-4 h-4" />
                  <span>Bóc tách 4 Khúc</span>
                </>
              )}
            </button>
          </div>
        </section>

        {/* Bước 2: Timeline 4 Khúc (Hook 3s, Vấn đề, Demo, CTA) */}
        <section className="bg-[#12121E] border border-[#252538] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-[#41AA6C]/10 text-[#41AA6C] flex items-center justify-center font-bold text-xs">
                2
              </div>
              <h2 className="font-semibold text-white text-base">Timeline 4 Phân Đoạn Chuyển Động</h2>
            </div>
            <span className="text-xs text-[#41AA6C] font-medium flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" /> 30.0s Tổng thời lượng
            </span>
          </div>

          {/* Timeline Bar Badges */}
          <div className="grid grid-cols-4 gap-2 mb-4">
            {segments.map((seg, idx) => (
              <button
                key={seg.name}
                onClick={() => setActiveSegmentIndex(idx)}
                className={`p-3 rounded-xl border text-left transition-all duration-200 cursor-pointer ${
                  activeSegmentIndex === idx
                    ? "bg-[#41AA6C]/15 border-[#41AA6C] text-white"
                    : "bg-[#000000] border-[#252538] text-[#94A3B8] hover:border-slate-700"
                }`}
              >
                <div className="text-[11px] font-semibold tracking-wide uppercase text-[#41AA6C]">
                  {seg.label}
                </div>
                <div className="text-xs font-mono mt-0.5 text-slate-300">{seg.duration}</div>
              </button>
            ))}
          </div>

          {/* Active Segment Detail Editor */}
          <div className="bg-[#000000] border border-[#252538] rounded-xl p-4 space-y-3">
            <div>
              <label className="text-xs font-medium text-[#94A3B8] mb-1.5 block">
                Prompt Diễn Xuất ({segments[activeSegmentIndex].label}):
              </label>
              <textarea
                rows={2}
                value={segments[activeSegmentIndex].prompt}
                onChange={(e) => {
                  const updated = [...segments];
                  updated[activeSegmentIndex].prompt = e.target.value;
                  setSegments(updated);
                }}
                className="w-full bg-[#12121E] border border-[#252538] rounded-lg p-2.5 text-xs text-white placeholder-[#94A3B8]/60 focus:outline-none focus:border-[#41AA6C] transition-all duration-200"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-[#94A3B8] mb-1.5 block">
                Lời Thoại KOC Tiếng Việt:
              </label>
              <input
                type="text"
                value={segments[activeSegmentIndex].script}
                onChange={(e) => {
                  const updated = [...segments];
                  updated[activeSegmentIndex].script = e.target.value;
                  setSegments(updated);
                }}
                className="w-full bg-[#12121E] border border-[#252538] rounded-lg px-3 py-2 text-xs text-white placeholder-[#94A3B8]/60 focus:outline-none focus:border-[#41AA6C] transition-all duration-200"
              />
            </div>
          </div>
        </section>

        {/* Bước 3: Nhân Vật & Sản Phẩm */}
        <section className="bg-[#12121E] border border-[#252538] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-2.5 mb-4">
            <div className="w-7 h-7 rounded-lg bg-[#41AA6C]/10 text-[#41AA6C] flex items-center justify-center font-bold text-xs">
              3
            </div>
            <h2 className="font-semibold text-white text-base">Nhân Vật & Sản Phẩm (Virtual Try-On)</h2>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Character Selection */}
            <div className="border border-[#252538] rounded-xl p-4 bg-[#000000] text-center">
              <div className="w-12 h-12 rounded-full bg-[#41AA6C]/10 text-[#41AA6C] mx-auto flex items-center justify-center mb-2">
                <User className="w-6 h-6" />
              </div>
              <div className="text-xs font-semibold text-white">Người mẫu: Hoài My (KOC)</div>
              <div className="text-[11px] text-[#94A3B8] mt-0.5">Tone da sáng, dáng chuẩn Châu Á</div>
              <button className="mt-3 text-xs text-[#41AA6C] hover:underline font-medium cursor-pointer">
                Đổi gương mặt mẫu
              </button>
            </div>

            {/* Product Selection */}
            <div className="border border-[#252538] rounded-xl p-4 bg-[#000000] text-center">
              <div className="w-12 h-12 rounded-full bg-[#41AA6C]/10 text-[#41AA6C] mx-auto flex items-center justify-center mb-2">
                <ShoppingBag className="w-6 h-6" />
              </div>
              <div className="text-xs font-semibold text-white">Đầm lụa trễ vai chữ A</div>
              <div className="text-[11px] text-[#94A3B8] mt-0.5">Sản phẩm affiliate TikTok Shop</div>
              <button className="mt-3 text-xs text-[#41AA6C] hover:underline font-medium cursor-pointer">
                Đổi sản phẩm
              </button>
            </div>
          </div>
        </section>

        {/* Bước 4: AI Engine & Nút Tạo Video */}
        <section className="bg-[#12121E] border border-[#252538] rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-[#41AA6C]/10 text-[#41AA6C] flex items-center justify-center font-bold text-xs">
                4
              </div>
              <h2 className="font-semibold text-white text-base">Cấu hình Động cơ AI</h2>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full bg-[#41AA6C]/15 text-[#41AA6C] font-semibold border border-[#41AA6C]/30">
              Chi phí: {engineMode === "kling" ? "~15.000đ" : "≤ 850đ"}/video
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setEngineMode("kling")}
              className={`p-3.5 rounded-xl border text-left transition-all duration-200 cursor-pointer ${
                engineMode === "kling"
                  ? "bg-[#41AA6C]/15 border-[#41AA6C] text-white"
                  : "bg-[#000000] border-[#252538] text-[#94A3B8]"
              }`}
            >
              <div className="font-semibold text-xs text-white">Replicate Kling v3</div>
              <div className="text-[11px] text-[#94A3B8] mt-0.5">Motion Control AI thế hệ mới</div>
            </button>

            <button
              onClick={() => setEngineMode("hybrid")}
              className={`p-3.5 rounded-xl border text-left transition-all duration-200 cursor-pointer ${
                engineMode === "hybrid"
                  ? "bg-[#41AA6C]/15 border-[#41AA6C] text-white"
                  : "bg-[#000000] border-[#252538] text-[#94A3B8]"
              }`}
            >
              <div className="font-semibold text-xs text-white">Hybrid Face Swap (Low-cost)</div>
              <div className="text-[11px] text-[#94A3B8] mt-0.5">InsightFace + Lách AI (≤ 1.000đ)</div>
            </button>
          </div>

          {/* Voice Selector */}
          <div className="bg-[#000000] border border-[#252538] rounded-xl p-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Mic className="w-4 h-4 text-[#41AA6C]" />
              <span className="text-xs text-[#94A3B8]">Giọng đọc KOC:</span>
            </div>
            <select
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
              className="bg-[#12121E] border border-[#252538] text-white text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-[#41AA6C]"
            >
              <option value="vi-VN-HoaiMyNeural">Hoài My (Nữ, Thời trang KOC)</option>
              <option value="vi-VN-NamMinhNeural">Nam Minh (Nam, Gia dụng KOC)</option>
            </select>
          </div>

          {/* CTA Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="w-full flex items-center justify-center gap-2.5 bg-[#41AA6C] hover:bg-[#34925b] text-white py-3.5 rounded-xl font-semibold text-base transition-all duration-200 cursor-pointer shadow-lg shadow-[#41AA6C]/20 disabled:opacity-50"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Đang kết xuất video Motion Control...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                <span>Tạo Video Motion Control Ngay</span>
              </>
            )}
          </button>
        </section>
      </div>

      {/* CỘT PHẢI: TRÌNH PHÁT PREVIEW & HÀNH ĐỘNG HẬU KỲ (5 Cột) */}
      <div className="lg:col-span-5 space-y-6">
        <section className="bg-[#12121E] border border-[#252538] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white text-base flex items-center gap-2">
              <Play className="w-4 h-4 text-[#41AA6C]" />
              <span>Xem Trước Kết Quả</span>
            </h3>
            <span className="text-xs text-[#94A3B8] font-mono">1080x1920 • 9:16</span>
          </div>

          {/* Video Preview Frame */}
          <div className="relative aspect-[9/16] bg-[#000000] border border-[#252538] rounded-xl overflow-hidden flex items-center justify-center">
            {renderedVideo ? (
              <video
                src={renderedVideo}
                controls
                autoPlay
                loop
                className="w-full h-full object-cover"
              />
            ) : isGenerating ? (
              <div className="text-center p-6 space-y-3">
                <Loader2 className="w-10 h-10 animate-spin text-[#41AA6C] mx-auto" />
                <p className="text-xs text-slate-300 font-medium">{progressStage}</p>
                <div className="w-48 bg-[#181828] h-2 rounded-full overflow-hidden mx-auto border border-[#252538]">
                  <div
                    className="bg-[#41AA6C] h-full transition-all duration-500"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>
            ) : (
              <div className="text-center p-6 text-[#94A3B8]">
                <Video className="w-12 h-12 mx-auto mb-2 text-[#94A3B8]/40" />
                <p className="text-sm font-medium text-slate-300">Chưa có video render</p>
                <p className="text-xs text-[#94A3B8] mt-1">
                  Chọn video mẫu và bấm &quot;Tạo Video Motion Control&quot;
                </p>
              </div>
            )}
          </div>

          {/* Technical Specs Tags */}
          <div className="flex items-center justify-between gap-2 mt-4 pt-4 border-t border-[#252538] text-xs text-[#94A3B8]">
            <span className="flex items-center gap-1 text-[#41AA6C]">
              <CheckCircle2 className="w-3.5 h-3.5" /> Khử chữ ký AI
            </span>
            <span>Micro-jitter: On</span>
            <span>Speed: 1.04x</span>
            <span>Duck audio: 12%</span>
          </div>
        </section>

        {/* Quick Actions Card */}
        {renderedVideo && (
          <section className="bg-[#12121E] border border-[#252538] rounded-2xl p-6 shadow-sm space-y-3">
            <h4 className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">
              Thao tác nhanh
            </h4>

            <button
              onClick={() => {
                setEngineMode("hybrid");
                handleGenerate();
              }}
              className="w-full flex items-center justify-center gap-2 bg-[#000000] hover:bg-[#181828] border border-[#252538] text-white py-2.5 rounded-xl text-xs font-medium transition-all duration-200 cursor-pointer"
            >
              <Zap className="w-4 h-4 text-[#41AA6C]" />
              <span>Tạo bản Hybrid Face Swap (≤ 1.000đ)</span>
            </button>

            <button
              onClick={handleGenerate}
              className="w-full flex items-center justify-center gap-2 bg-[#000000] hover:bg-[#181828] border border-[#252538] text-white py-2.5 rounded-xl text-xs font-medium transition-all duration-200 cursor-pointer"
            >
              <RotateCw className="w-4 h-4 text-[#94A3B8]" />
              <span>Đổi nhân vật tạo lại</span>
            </button>

            <button
              onClick={() => alert("Chuyển sang Tab 2 để đăng ngay!")}
              className="w-full flex items-center justify-center gap-2 bg-[#41AA6C] hover:bg-[#34925b] text-white py-2.5 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer shadow-sm"
            >
              <Send className="w-4 h-4" />
              <span>Đăng ngay qua Kênh</span>
            </button>
          </section>
        )}
      </div>
    </div>
  );
};
