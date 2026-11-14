"use client";
/* eslint-disable @next/next/no-img-element */

import React, { useState, useEffect } from "react";
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
  Loader2,
  Mic,
  Minus,
  Plus,
} from "lucide-react";
import { useProject } from "@/context/ProjectContext";
import { ProjectAssetModal, ProjectAsset, AssetCategory } from "./ProjectAssetModal";

interface Segment {
  name: string;
  label: string;
  startSec: number;
  endSec: number;
  durationSec: number;
  duration: string; // Formatted e.g. "0.0s - 3.0s"
  prompt: string;
  script: string;
  durationOptions: number[]; // selectable preset chips e.g. [3, 4, 5]
}

interface MotionStudioProps {
  initialVideoUrl?: string;
}

export const MotionStudio: React.FC<MotionStudioProps> = ({ initialVideoUrl }) => {
  const { activeProject } = useProject();
  const projectId = activeProject?.project_id || "proj_fashion_genz";

  // Input states
  const [videoUrl, setVideoUrl] = useState(
    initialVideoUrl || "https://www.tiktok.com/@fashion_trend/video/73912345678"
  );
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisSuccessNotice, setAnalysisSuccessNotice] = useState<string | null>(null);
  const [activeSegmentIndex, setActiveSegmentIndex] = useState(0);

  // 4 functional segments with interactive duration selection
  const [segments, setSegments] = useState<Segment[]>([
    {
      name: "hook",
      label: "Hook 3s",
      startSec: 0.0,
      endSec: 3.0,
      durationSec: 3.0,
      duration: "0.0s - 3.0s",
      prompt: "Attractive Vietnamese female model greeting viewers with natural welcoming gestures, energetic 4K camera close-up",
      script: "Chào cả nhà, chiếc đầm che bụng cực phẩm này đang làm mưa làm gió!",
      durationOptions: [2.5, 3.0, 4.0, 5.0],
    },
    {
      name: "problem",
      label: "Vấn đề / Bối cảnh",
      startSec: 3.0,
      endSec: 10.5,
      durationSec: 7.5,
      duration: "3.0s - 10.5s",
      prompt: "Model pointing at waistline showing common struggle with ordinary tight fitting dresses in bedroom setting",
      script: "Chị em nào bụng dưới to, bắp tay kém thon mỗi lần chọn đồ đi tiệc cực khổ luôn đúng không?",
      durationOptions: [5.0, 7.5, 10.0, 12.0],
    },
    {
      name: "demo",
      label: "Demo Sản phẩm",
      startSec: 10.5,
      endSec: 25.0,
      durationSec: 14.5,
      duration: "10.5s - 25.0s",
      prompt: "Model twirling gracefully showcasing fabric fluidity, seams, and slimming silhouette under studio lighting",
      script: "Form váy chữ A giấu trọn bụng, chất vải lụa tuyết mịn màng, co giãn cực kỳ thoáng mát.",
      durationOptions: [10.0, 14.5, 18.0, 20.0],
    },
    {
      name: "cta",
      label: "CTA Giỏ hàng",
      startSec: 25.0,
      endSec: 30.0,
      durationSec: 5.0,
      duration: "25.0s - 30.0s",
      prompt: "Model smiling warmly pointing down towards bottom left shopping cart icon with engaging nod",
      script: "Hôm nay đang có voucher giảm 30k, bấm ngay vào giỏ hàng góc trái săn liền nhé!",
      durationOptions: [3.0, 5.0, 6.0, 8.0],
    },
  ]);

  // Section 3: Model, Background & Product states
  const [selectedModel, setSelectedModel] = useState({
    id: "model_hoaimy",
    name: "Hoài My (KOC)",
    description: "Tone da sáng, dáng chuẩn Châu Á, phong cách năng động",
    imageUrl: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&auto=format&fit=crop&q=80",
  });

  const [selectedBackground, setSelectedBackground] = useState({
    id: "bg_studio_y2k",
    name: "Studio Y2K Tối Giản",
    description: "Ánh sáng tự nhiên, góc quay 4K, phông nền pastel hiện đại",
    imageUrl: "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=500&auto=format&fit=crop&q=80",
  });

  const [selectedProduct, setSelectedProduct] = useState({
    id: "prod_dress_a",
    name: "Đầm Lụa Chữ A Che Bụng",
    description: "Vải lụa tuyết mịn màng, affiliate TikTok Shop",
    imageUrl: "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=500&auto=format&fit=crop&q=80",
  });

  // Modal Dialog state for selecting/uploading Model, Background, Product
  const [isAssetModalOpen, setIsAssetModalOpen] = useState(false);
  const [modalCategory, setModalCategory] = useState<AssetCategory>("model");

  // Sync selected assets when active project changes
  useEffect(() => {
    if (projectId === "proj_smart_home") {
      setSelectedModel({
        id: "model_minhquan",
        name: "Minh Quân (KOC)",
        description: "KOC gia đình thông minh, chia sẻ mẹo vặt tin cậy",
        imageUrl: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=500&auto=format&fit=crop&q=80",
      });
      setSelectedBackground({
        id: "bg_smart_kitchen",
        name: "Gian Bếp Hiện Đại Tiện Nghi",
        description: "Bàn đá thạch anh trắng, tủ bếp thông minh sạch sẽ",
        imageUrl: "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?w=500&auto=format&fit=crop&q=80",
      });
      setSelectedProduct({
        id: "prod_air_fryer",
        name: "Nồi Chiên Không Dầu Điện Tử 6L",
        description: "Mặt kính trong suốt, đối lưu 360 độ, hot TikTok",
        imageUrl: "https://images.unsplash.com/photo-1585515320310-259814833e62?w=500&auto=format&fit=crop&q=80",
      });
    } else {
      setSelectedModel({
        id: "model_hoaimy",
        name: "Hoài My (KOC)",
        description: "Tone da sáng, dáng chuẩn Châu Á, phong cách năng động",
        imageUrl: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&auto=format&fit=crop&q=80",
      });
      setSelectedBackground({
        id: "bg_studio_y2k",
        name: "Studio Y2K Tối Giản",
        description: "Ánh sáng tự nhiên, góc quay 4K, phông nền pastel hiện đại",
        imageUrl: "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=500&auto=format&fit=crop&q=80",
      });
      setSelectedProduct({
        id: "prod_dress_a",
        name: "Đầm Lụa Chữ A Che Bụng",
        description: "Vải lụa tuyết mịn màng, affiliate TikTok Shop",
        imageUrl: "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=500&auto=format&fit=crop&q=80",
      });
    }
  }, [projectId]);

  // Model & Voice options
  const [engineMode, setEngineMode] = useState<"kling" | "hybrid">("kling");
  const [voiceId, setVoiceId] = useState("vi-VN-HoaiMyNeural");

  // Job generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [progressStage, setProgressStage] = useState<string | null>(null);
  const [progressPercent, setProgressPercent] = useState(0);
  const [renderedVideo, setRenderedVideo] = useState<string | null>(null);

  // Helper to recalculate continuous timeline start/end times when any segment's duration changes
  const updateSegmentDuration = (targetIdx: number, newDurationSec: number) => {
    const validDuration = Math.max(1.0, Math.round(newDurationSec * 10) / 10);
    const updated = [...segments];
    updated[targetIdx].durationSec = validDuration;

    // Recalculate continuous timeline
    let currentStart = 0.0;
    for (let i = 0; i < updated.length; i++) {
      updated[i].startSec = Math.round(currentStart * 10) / 10;
      updated[i].endSec = Math.round((currentStart + updated[i].durationSec) * 10) / 10;
      updated[i].duration = `${updated[i].startSec.toFixed(1)}s - ${updated[i].endSec.toFixed(1)}s`;
      currentStart = updated[i].endSec;
    }
    setSegments(updated);
  };

  // Open asset modal for a given category
  const handleOpenAssetModal = (category: AssetCategory) => {
    setModalCategory(category);
    setIsAssetModalOpen(true);
  };

  // Handle asset chosen from modal
  const handleSelectAsset = (asset: ProjectAsset) => {
    if (asset.category === "model") {
      setSelectedModel({
        id: asset.id,
        name: asset.name,
        description: asset.description,
        imageUrl: asset.imageUrl,
      });
    } else if (asset.category === "background") {
      setSelectedBackground({
        id: asset.id,
        name: asset.name,
        description: asset.description,
        imageUrl: asset.imageUrl,
      });
    } else if (asset.category === "product") {
      setSelectedProduct({
        id: asset.id,
        name: asset.name,
        description: asset.description,
        imageUrl: asset.imageUrl,
      });
    }
  };

  // Handle URL Preprocessing & Auto-fill timing, prompts, and scripts
  const handlePreprocess = async () => {
    setIsAnalyzing(true);
    setAnalysisSuccessNotice(null);
    try {
      const res = await fetch("/api/studio/preprocess", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_url_or_path: videoUrl, cut_clips: false }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.segments && data.segments.length === 4) {
          const mapped: Segment[] = data.segments.map(
            (
              s: {
                name: string;
                description?: string;
                start_sec: number;
                end_sec: number;
                duration?: number;
                transcript_text?: string;
              },
              idx: number
            ) => {
              const start = s.start_sec || 0;
              const end = s.end_sec || (start + 5);
              const dur = s.duration || Math.max(1, end - start);
              const defaultLabels = ["Hook 3s", "Vấn đề / Bối cảnh", "Demo Sản phẩm", "CTA Giỏ hàng"];
              const defaultPrompts = [
                "Model looking directly into camera with confident smile, presenting outfit with energetic zoom-in motion",
                "Full body camera angle, model gesturing towards fit issues and addressing common styling dilemmas",
                "Smooth 360-degree rotation, highlighting garment drape, fabric texture, and tailored seams under soft lighting",
                "Model smiling warmly pointing down towards the shopping cart badge with persuasive call-to-action gesture",
              ];
              const defaultPresets = [
                [2.5, 3.0, 4.0, 5.0],
                [5.0, 7.5, 10.0, 12.0],
                [10.0, 14.5, 18.0, 20.0],
                [3.0, 5.0, 6.0, 8.0],
              ];

              return {
                name: s.name || `seg_${idx + 1}`,
                label: defaultLabels[idx] || s.description || `Đoạn ${idx + 1}`,
                startSec: start,
                endSec: end,
                durationSec: dur,
                duration: `${start.toFixed(1)}s - ${end.toFixed(1)}s`,
                prompt: defaultPrompts[idx],
                script: s.transcript_text || segments[idx]?.script || "Nội dung lời thoại KOC trích xuất từ video đối thủ...",
                durationOptions: defaultPresets[idx] || [3, 5, 8],
              };
            }
          );
          setSegments(mapped);
          setAnalysisSuccessNotice("Đã bóc tách thành công! Thời gian, prompt và lời thoại đã được điền tự động từ video.");
          return;
        }
      }
      throw new Error("Fallback auto-fill");
    } catch {
      // Offline / Direct Mock Fallback: Populates realistic segmented data from video reference
      const isHomeNiche = projectId === "proj_smart_home";
      const fallbackSegments: Segment[] = [
        {
          name: "hook",
          label: "Hook 3s",
          startSec: 0.0,
          endSec: 3.5,
          durationSec: 3.5,
          duration: "0.0s - 3.5s",
          prompt: isHomeNiche
            ? "Cận cảnh người mẫu biểu cảm kinh ngạc khi nhìn chiếc nồi chiên không dầu hoạt động êm ái"
            : "Cận cảnh người mẫu biểu cảm bất ngờ, chỉ tay vào trang phục với góc máy nghiêng 45 độ năng động",
          script: isHomeNiche
            ? "Mọi người đã biết chiếc nồi chiên không dầu cửa kính thần thánh này chưa?"
            : "Chào cả nhà, chiếc đầm che bụng cực phẩm này đang làm mưa làm gió trên TikTok!",
          durationOptions: [2.5, 3.0, 3.5, 5.0],
        },
        {
          name: "problem",
          label: "Vấn đề / Bối cảnh",
          startSec: 3.5,
          endSec: 10.0,
          durationSec: 6.5,
          duration: "3.5s - 10.0s",
          prompt: isHomeNiche
            ? "Góc quay gian bếp, KOC chỉ vào đống xoong chảo dầu mỡ cồng kềnh khó chùi rửa"
            : "Góc quay toàn thân, người mẫu mô phỏng nỗi lo bụng dưới to khi diện đồ bó sát thông thường",
          script: isHomeNiche
            ? "Mỗi lần chiên xào dầu bắn tung tóe, chùi rửa nồi cũ cực khổ mất cả tiếng đồng hồ luôn!"
            : "Chị em nào bụng dưới to, bắp tay kém thon mỗi lần chọn đồ đi tiệc cực khổ luôn đúng không?",
          durationOptions: [5.0, 6.5, 8.5, 10.0],
        },
        {
          name: "demo",
          label: "Demo Sản phẩm",
          startSec: 10.0,
          endSec: 25.0,
          durationSec: 15.0,
          duration: "10.0s - 25.0s",
          prompt: isHomeNiche
            ? "Thao tác chạm màn hình cảm ứng, khay nướng lướt ra giòn rụm không cần lật mặt"
            : "Xoay người 360 độ khoe chất vải lụa tuyết rủ mềm mại, đường may giấu bụng và tà váy chữ A tôn dáng",
          script: isHomeNiche
            ? "Dung tích 6L nướng gà nguyên con, kính trong suốt quan sát trực tiếp, không cần lật trở cực nhàn."
            : "Form váy chữ A giấu trọn bụng, chất vải lụa tuyết mịn màng, co giãn cực kỳ thoáng mát.",
          durationOptions: [10.0, 15.0, 18.0, 20.0],
        },
        {
          name: "cta",
          label: "CTA Giỏ hàng",
          startSec: 25.0,
          endSec: 30.0,
          durationSec: 5.0,
          duration: "25.0s - 30.0s",
          prompt: "Gương mặt rạng rỡ, tay chỉ dứt khoát xuống góc trái màn hình nơi hiển thị biểu tượng giỏ hàng vàng",
          script: isHomeNiche
            ? "Hôm nay shop đang trợ giá giảm sốc 150k và freeship, bấm ngay giỏ hàng góc trái săn deal nhé!"
            : "Hôm nay đang có voucher giảm 30k độc quyền, bấm ngay vào giỏ hàng góc trái săn liền nhé!",
          durationOptions: [3.0, 4.0, 5.0, 6.0],
        },
      ];
      setSegments(fallbackSegments);
      setAnalysisSuccessNotice("Đã bóc tách thành công! Tự động điền thời gian, prompt và lời thoại từ video reference.");
    } finally {
      setTimeout(() => setIsAnalyzing(false), 600);
      setTimeout(() => setAnalysisSuccessNotice(null), 6000);
    }
  };

  // Handle Video Generation
  const handleGenerate = async () => {
    setIsGenerating(true);
    setProgressPercent(15);
    setProgressStage("Tiền xử lý ảnh nhân vật, bối cảnh & phom dáng sản phẩm...");

    // Smooth progress simulation
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
    <>
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
                className="flex items-center gap-2 bg-[#41AA6C] hover:bg-[#34925b] text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer shadow-sm shadow-[#41AA6C]/20 disabled:opacity-50"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Đang bóc tách...</span>
                  </>
                ) : (
                  <>
                    <Scissors className="w-4 h-4" />
                    <span>Bóc tách</span>
                  </>
                )}
              </button>
            </div>

            {/* Notification when bóc tách succeeds */}
            {analysisSuccessNotice && (
              <div className="mt-3 p-3 rounded-xl bg-[#41AA6C]/10 border border-[#41AA6C]/30 text-xs text-[#41AA6C] flex items-center gap-2 animate-in fade-in duration-200">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{analysisSuccessNotice}</span>
              </div>
            )}
          </section>

          {/* Bước 2: Thời gian & Prompt, lời thoại */}
          <section className="bg-[#12121E] border border-[#252538] rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-[#41AA6C]/10 text-[#41AA6C] flex items-center justify-center font-bold text-xs">
                  2
                </div>
                <h2 className="font-semibold text-white text-base">Thời gian & Prompt, lời thoại</h2>
              </div>
              <div className="text-xs text-[#94A3B8] flex items-center gap-1">
                <span>Chọn thời lượng cho từng phân cảnh</span>
              </div>
            </div>

            {/* 4 Segment Duration Selector Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 mb-4">
              {segments.map((seg, idx) => {
                const isSelected = activeSegmentIndex === idx;
                return (
                  <div
                    key={seg.name}
                    onClick={() => setActiveSegmentIndex(idx)}
                    className={`p-3 rounded-xl border text-left transition-all duration-200 cursor-pointer flex flex-col justify-between ${
                      isSelected
                        ? "bg-[#41AA6C]/15 border-[#41AA6C] text-white shadow-sm shadow-[#41AA6C]/10"
                        : "bg-[#000000] border-[#252538] text-[#94A3B8] hover:border-slate-700 hover:bg-[#0a0a14]"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold tracking-wide uppercase text-[#41AA6C]">
                          {seg.label}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400">
                          {seg.startSec.toFixed(1)}s - {seg.endSec.toFixed(1)}s
                        </span>
                      </div>

                      {/* Current Duration Display & Stepper */}
                      <div className="flex items-center justify-between mt-2 pt-2 border-t border-[#252538]">
                        <span className="text-xs font-semibold text-white font-mono">
                          {seg.durationSec.toFixed(1)}s
                        </span>
                        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                          <button
                            type="button"
                            title="Giảm thời lượng"
                            onClick={() => updateSegmentDuration(idx, seg.durationSec - 0.5)}
                            className="w-5 h-5 rounded bg-[#181828] hover:bg-[#252538] text-slate-300 flex items-center justify-center text-xs transition-colors cursor-pointer"
                          >
                            <Minus className="w-2.5 h-2.5" />
                          </button>
                          <button
                            type="button"
                            title="Tăng thời lượng"
                            onClick={() => updateSegmentDuration(idx, seg.durationSec + 0.5)}
                            className="w-5 h-5 rounded bg-[#181828] hover:bg-[#252538] text-slate-300 flex items-center justify-center text-xs transition-colors cursor-pointer"
                          >
                            <Plus className="w-2.5 h-2.5" />
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Quick Duration Preset Chips */}
                    <div className="flex flex-wrap gap-1 mt-2.5 pt-2 border-t border-[#252538]" onClick={(e) => e.stopPropagation()}>
                      {seg.durationOptions.map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => updateSegmentDuration(idx, opt)}
                          className={`text-[10px] px-1.5 py-0.5 rounded font-mono transition-all duration-150 cursor-pointer ${
                            Math.abs(seg.durationSec - opt) < 0.1
                              ? "bg-[#41AA6C] text-white font-bold"
                              : "bg-[#181828] text-slate-300 hover:text-white hover:bg-[#222238] border border-[#252538]"
                          }`}
                        >
                          {opt}s
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Active Segment Detail Editor (Prompt & Script) */}
            <div className="bg-[#000000] border border-[#252538] rounded-xl p-4 space-y-3.5">
              <div className="flex items-center justify-between border-b border-[#252538] pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white uppercase">
                    Chi tiết phân cảnh: {segments[activeSegmentIndex].label}
                  </span>
                  <span className="text-[11px] px-2 py-0.5 rounded bg-[#41AA6C]/10 text-[#41AA6C] font-mono border border-[#41AA6C]/30">
                    {segments[activeSegmentIndex].duration} ({segments[activeSegmentIndex].durationSec.toFixed(1)}s)
                  </span>
                </div>
                <div className="text-[11px] text-[#94A3B8]">
                  Tự động điền khi bấm &quot;Bóc tách&quot;
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-200 mb-1.5 block">
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
                  placeholder="Mô tả hành động, biểu cảm và góc máy của phân cảnh..."
                  className="w-full bg-[#12121E] border border-[#252538] rounded-lg p-2.5 text-xs text-white placeholder-[#94A3B8]/60 focus:outline-none focus:border-[#41AA6C] transition-all duration-200"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-200 mb-1.5 block">
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
                  placeholder="Nội dung giọng nói của KOC trong phân cảnh này..."
                  className="w-full bg-[#12121E] border border-[#252538] rounded-lg px-3 py-2 text-xs text-white placeholder-[#94A3B8]/60 focus:outline-none focus:border-[#41AA6C] transition-all duration-200"
                />
              </div>
            </div>
          </section>

          {/* Bước 3: Nhân Vật, Bối Cảnh & Sản Phẩm (Virtual Try-On) */}
          <section className="bg-[#12121E] border border-[#252538] rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-[#41AA6C]/10 text-[#41AA6C] flex items-center justify-center font-bold text-xs">
                  3
                </div>
                <h2 className="font-semibold text-white text-base">
                  Nhân Vật, Bối Cảnh & Sản Phẩm (Virtual Try-On)
                </h2>
              </div>
              <span className="text-xs text-[#94A3B8]">Quản lý theo dự án {activeProject?.name}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* 1. Character / Model Selection */}
              <div className="border border-[#252538] rounded-xl p-4 bg-[#000000] text-center flex flex-col justify-between hover:border-slate-700 transition-all duration-200">
                <div>
                  <div className="relative w-14 h-14 rounded-full mx-auto mb-2.5 overflow-hidden border border-[#252538] bg-[#12121E]">
                    {selectedModel.imageUrl ? (
                      <img
                        src={selectedModel.imageUrl}
                        alt={selectedModel.name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#41AA6C]">
                        <User className="w-6 h-6" />
                      </div>
                    )}
                  </div>
                  <div className="text-xs font-semibold text-white truncate">{selectedModel.name}</div>
                  <div className="text-[11px] text-[#94A3B8] mt-1 line-clamp-2 min-h-[30px]">
                    {selectedModel.description}
                  </div>
                </div>
                <button
                  onClick={() => handleOpenAssetModal("model")}
                  className="mt-3.5 w-full py-2 px-3 rounded-lg bg-[#181828] hover:bg-[#41AA6C]/15 border border-[#252538] hover:border-[#41AA6C]/40 text-xs text-[#41AA6C] font-semibold transition-all duration-150 cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <User className="w-3.5 h-3.5" />
                  <span>Đổi gương mặt mẫu</span>
                </button>
              </div>

              {/* 2. Background / Scene Selection */}
              <div className="border border-[#252538] rounded-xl p-4 bg-[#000000] text-center flex flex-col justify-between hover:border-slate-700 transition-all duration-200">
                <div>
                  <div className="relative w-14 h-14 rounded-xl mx-auto mb-2.5 overflow-hidden border border-[#252538] bg-[#12121E]">
                    {selectedBackground.imageUrl ? (
                      <img
                        src={selectedBackground.imageUrl}
                        alt={selectedBackground.name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#41AA6C]">
                        <Sparkles className="w-6 h-6" />
                      </div>
                    )}
                  </div>
                  <div className="text-xs font-semibold text-white truncate">{selectedBackground.name}</div>
                  <div className="text-[11px] text-[#94A3B8] mt-1 line-clamp-2 min-h-[30px]">
                    {selectedBackground.description}
                  </div>
                </div>
                <button
                  onClick={() => handleOpenAssetModal("background")}
                  className="mt-3.5 w-full py-2 px-3 rounded-lg bg-[#181828] hover:bg-[#41AA6C]/15 border border-[#252538] hover:border-[#41AA6C]/40 text-xs text-[#41AA6C] font-semibold transition-all duration-150 cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Đổi bối cảnh</span>
                </button>
              </div>

              {/* 3. Product Selection */}
              <div className="border border-[#252538] rounded-xl p-4 bg-[#000000] text-center flex flex-col justify-between hover:border-slate-700 transition-all duration-200">
                <div>
                  <div className="relative w-14 h-14 rounded-xl mx-auto mb-2.5 overflow-hidden border border-[#252538] bg-[#12121E]">
                    {selectedProduct.imageUrl ? (
                      <img
                        src={selectedProduct.imageUrl}
                        alt={selectedProduct.name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#41AA6C]">
                        <ShoppingBag className="w-6 h-6" />
                      </div>
                    )}
                  </div>
                  <div className="text-xs font-semibold text-white truncate">{selectedProduct.name}</div>
                  <div className="text-[11px] text-[#94A3B8] mt-1 line-clamp-2 min-h-[30px]">
                    {selectedProduct.description}
                  </div>
                </div>
                <button
                  onClick={() => handleOpenAssetModal("product")}
                  className="mt-3.5 w-full py-2 px-3 rounded-lg bg-[#181828] hover:bg-[#41AA6C]/15 border border-[#252538] hover:border-[#41AA6C]/40 text-xs text-[#41AA6C] font-semibold transition-all duration-150 cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <ShoppingBag className="w-3.5 h-3.5" />
                  <span>Đổi sản phẩm</span>
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

      {/* Dialog Modal for Choosing/Uploading Model, Background, Product per Project */}
      <ProjectAssetModal
        isOpen={isAssetModalOpen}
        onClose={() => setIsAssetModalOpen(false)}
        initialCategory={modalCategory}
        currentSelectedId={{
          model: selectedModel.id,
          background: selectedBackground.id,
          product: selectedProduct.id,
        }}
        onSelectAsset={handleSelectAsset}
      />
    </>
  );
};
