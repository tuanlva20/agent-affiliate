"use client";

import React, { useState } from "react";
import {
  TrendingUp,
  MessageSquare,
  Sparkles,
  ExternalLink,
  Eye,
  ShoppingCart,
  DollarSign,
  Play,
  ArrowRight,
  Filter,
  CheckCircle2,
  Send,
  RotateCw,
  Wand2,
  Copy,
  Calendar,
  X,
  Share2,
} from "lucide-react";
import { useProject } from "@/context/ProjectContext";

interface PublishItem {
  id: string;
  title: string;
  channel: string;
  platform: "tiktok" | "facebook";
  date: string;
  views: number;
  likes: number;
  orders: number;
  revenue: number;
  url: string;
}

interface CommentItem {
  id: string;
  channel: string;
  author: string;
  text: string;
  intent: "ask_price" | "ask_material" | "complaint" | "other";
  reply: string;
  status: "replied" | "pending";
  time: string;
}

interface CompetitorVideoItem {
  id: string;
  creator: string;
  title: string;
  platform: "tiktok" | "facebook" | "instagram";
  views: number;
  salesCount: number;
  revenueEstimate: number;
  url: string;
  date: string;
  viralScore: number;
}

interface HistoryHubProps {
  onSelectMotionReference: (videoUrl: string) => void;
}

export const HistoryHub: React.FC<HistoryHubProps> = ({ onSelectMotionReference }) => {
  const { activeProject } = useProject();
  const [subTab, setSubTab] = useState<"publishes" | "comments" | "competitors">("publishes");
  const [intentFilter, setIntentFilter] = useState<string>("all");

  // Publishing history data
  const publishes: PublishItem[] = [
    {
      id: "pub_01",
      title: "Đầm lụa trễ vai chữ A che khuyết điểm bụng",
      channel: "Thoitrang.koc.viet",
      platform: "tiktok",
      date: "12/11/2026 18:30",
      views: 45200,
      likes: 3820,
      orders: 68,
      revenue: 12240000,
      url: "https://www.tiktok.com/@channel/video/7391",
    },
    {
      id: "pub_02",
      title: "Kệ bếp xoay thông minh 3 tầng chịu lực 50kg",
      channel: "Review.giadung.thongminh",
      platform: "tiktok",
      date: "11/11/2026 12:15",
      views: 28900,
      likes: 1940,
      orders: 42,
      revenue: 7560000,
      url: "https://www.tiktok.com/@channel/video/7392",
    },
    {
      id: "pub_03",
      title: "Váy hoa nhí dáng suông hack tuổi cực đỉnh",
      channel: "Đầm Xinh Dự Tiệc VIP",
      platform: "facebook",
      date: "10/11/2026 20:00",
      views: 89400,
      likes: 6200,
      orders: 114,
      revenue: 21660000,
      url: "https://www.facebook.com/reel/12345",
    },
  ];

  // Comments data
  const [comments, setComments] = useState<CommentItem[]>([
    {
      id: "cmt_01",
      channel: "Thoitrang.koc.viet",
      author: "Mai Phương",
      text: "Váy này giá bao nhiêu một chiếc vậy shop? Có size L không?",
      intent: "ask_price",
      reply: "Dạ váy đang có giá ưu đãi chỉ 180k kèm voucher 30k trong giỏ hàng góc trái video bạn nha!",
      status: "replied",
      time: "10 phút trước",
    },
    {
      id: "cmt_02",
      channel: "Thoitrang.koc.viet",
      author: "Ngọc Lan",
      text: "Vải này giặt máy có bị nhăn hay xù lông không shop?",
      intent: "ask_material",
      reply: "Dạ vải lụa tuyết dệt cao cấp giặt máy thoải mái không xù không phai bạn nha!",
      status: "replied",
      time: "25 phút trước",
    },
    {
      id: "cmt_03",
      channel: "Review.giadung.thongminh",
      author: "Minh Tuấn",
      text: "Mình nhận hàng hôm qua mà lắp bánh xe bị kẹt, đổi sao shop?",
      intent: "complaint",
      reply: "Dạ em đã inbox hỗ trợ bạn gửi bánh xe thay thế miễn phí ngay trong ngày ạ!",
      status: "pending",
      time: "1 giờ trước",
    },
  ]);

  // Competitor videos
  const [competitorVideos] = useState<CompetitorVideoItem[]>([
    {
      id: "cv_01",
      creator: "@trend.fashion.bkk",
      title: "Visual Hook 3s cực cuốn: Đổi form dáng người chỉ trong 1 nốt nhạc",
      platform: "tiktok",
      views: 1250000,
      salesCount: 840,
      revenueEstimate: 168000000,
      url: "https://www.tiktok.com/@trend.fashion.bkk/video/73111",
      date: "12/11/2026",
      viralScore: 94,
    },
    {
      id: "cv_02",
      creator: "@home_lifestyle_pro",
      title: "Giải pháp bếp chật: Kệ góc xoay 360 độ gọn gàng ngăn nắp",
      platform: "facebook",
      views: 840000,
      salesCount: 620,
      revenueEstimate: 111600000,
      url: "https://www.facebook.com/reel/73222",
      date: "11/11/2026",
      viralScore: 88,
    },
    {
      id: "cv_03",
      creator: "@tech_gadget_daily",
      title: "Top 3 phụ kiện sạc nhanh GaN đáng tiền nhất năm 2026",
      platform: "instagram",
      views: 620000,
      salesCount: 450,
      revenueEstimate: 90000000,
      url: "https://www.instagram.com/reel/73333",
      date: "10/11/2026",
      viralScore: 82,
    },
  ]);

  // Scraper controls
  const [scraperLinks, setScraperLinks] = useState("");
  const [scrapeInterval, setScrapeInterval] = useState("4");
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeNotification, setScrapeNotification] = useState<string | null>(null);

  // Recreate modal
  const [selectedVideoForRecreate, setSelectedVideoForRecreate] = useState<CompetitorVideoItem | null>(null);
  const [recreateTab, setRecreateTab] = useState<"script" | "remix">("script");
  const [generatedScript, setGeneratedScript] = useState<{ hook: string; body: string; cta: string } | null>(null);
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);

  const totalRevenue = publishes.reduce((acc, cur) => acc + cur.revenue, 0);
  const totalOrders = publishes.reduce((acc, cur) => acc + cur.orders, 0);
  const totalViews = publishes.reduce((acc, cur) => acc + cur.views, 0);

  const handleApproveReply = (id: string) => {
    setComments((prev) =>
      prev.map((c) => (c.id === id ? { ...c, status: "replied" } : c))
    );
  };

  const handleScrapeNow = async () => {
    if (!scraperLinks.trim()) return;
    setIsScraping(true);
    setScrapeNotification(null);
    try {
      await new Promise((r) => setTimeout(r, 1200));
      setScrapeNotification(
        "Đã thực hiện Cào Cưỡng Bức thành công. Hệ thống UPSERT tự động: cập nhật chỉ số cho các link đã tồn tại và thêm link mới."
      );
    } finally {
      setIsScraping(false);
    }
  };

  const handleOpenRecreateModal = (video: CompetitorVideoItem) => {
    setSelectedVideoForRecreate(video);
    setRecreateTab("script");
    setGeneratedScript(null);
  };

  const handleGenerateScript = async () => {
    if (!selectedVideoForRecreate) return;
    setIsGeneratingScript(true);
    try {
      await new Promise((r) => setTimeout(r, 1000));
      setGeneratedScript({
        hook: `[Hook 3s]: Đừng vội mua ${selectedVideoForRecreate.title.split(":")[0]} nếu bạn chưa biết bí mật này!`,
        body: `[Nội dung chính]: Giới thiệu trải nghiệm thực tế với góc quay cận cảnh, giải quyết trực tiếp nỗi đau của đối tượng khách hàng (${activeProject?.target_audience || "người tiêu dùng"}) theo văn phong ${activeProject?.tone_of_voice || "gần gũi, chân thực"}.`,
        cta: `[Kêu gọi hành động CTA]: Nhấp ngay vào giỏ hàng góc trái video hôm nay để nhận voucher giảm giá độc quyền!`,
      });
    } finally {
      setIsGeneratingScript(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Header & Financial Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-[#94A3B8] text-xs">
            <span>Tổng Doanh Thu Affiliate</span>
            <DollarSign className="w-4 h-4 text-[#41AA6C]" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {totalRevenue.toLocaleString("vi-VN")} đ
          </div>
          <div className="text-[11px] text-[#41AA6C] mt-1">+18.5% so với tuần trước</div>
        </div>

        <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-[#94A3B8] text-xs">
            <span>Tổng Đơn Hàng Thành Công</span>
            <ShoppingCart className="w-4 h-4 text-[#41AA6C]" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {totalOrders.toLocaleString("vi-VN")} đơn
          </div>
          <div className="text-[11px] text-slate-300 mt-1">Từ các kênh trong Project</div>
        </div>

        <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-[#94A3B8] text-xs">
            <span>Tổng Lượt Xem (Views)</span>
            <Eye className="w-4 h-4 text-[#41AA6C]" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {totalViews.toLocaleString("vi-VN")}
          </div>
          <div className="text-[11px] text-indigo-400 mt-1">TikTok & Facebook Reels</div>
        </div>
      </div>

      {/* 2. Sub-tab navigation */}
      <div className="flex items-center gap-2 border-b border-[#252538] pb-3">
        <button
          onClick={() => setSubTab("publishes")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer transition-all duration-200 ${
            subTab === "publishes"
              ? "bg-[#41AA6C] text-white shadow-sm"
              : "text-[#94A3B8] hover:text-white hover:bg-white/5"
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          <span>Lịch Sử Đăng Bài & Chỉ Số</span>
        </button>

        <button
          onClick={() => setSubTab("comments")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer transition-all duration-200 ${
            subTab === "comments"
              ? "bg-[#41AA6C] text-white shadow-sm"
              : "text-[#94A3B8] hover:text-white hover:bg-white/5"
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span>Tương Tác & Comment KOC ({comments.length})</span>
        </button>

        <button
          onClick={() => setSubTab("competitors")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer transition-all duration-200 ${
            subTab === "competitors"
              ? "bg-[#41AA6C] text-white shadow-sm"
              : "text-[#94A3B8] hover:text-white hover:bg-white/5"
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>Cào Đối Thủ & Làm Lại Nội Dung</span>
        </button>
      </div>

      {/* 3. SUBTAB 1: Lịch sử đăng bài */}
      {subTab === "publishes" && (
        <div className="bg-[#12121E] border border-[#252538] rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#000000]/60 border-b border-[#252538] text-[#94A3B8] uppercase text-[11px] font-semibold">
                <tr>
                  <th className="py-3.5 px-4">Video Đã Đăng</th>
                  <th className="py-3.5 px-4">Kênh & Nền Tảng</th>
                  <th className="py-3.5 px-4">Thời Gian</th>
                  <th className="py-3.5 px-4 text-right">Lượt Xem</th>
                  <th className="py-3.5 px-4 text-right">Đơn Hàng</th>
                  <th className="py-3.5 px-4 text-right">Doanh Thu</th>
                  <th className="py-3.5 px-4 text-right">Link Gốc</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#252538]">
                {publishes.map((p) => (
                  <tr key={p.id} className="hover:bg-white/[0.02] transition-colors duration-150">
                    <td className="py-4 px-4 font-semibold text-white max-w-xs">{p.title}</td>
                    <td className="py-4 px-4 text-[#94A3B8]">
                      <div>{p.channel}</div>
                      <span className="text-[10px] text-slate-400 capitalize">{p.platform}</span>
                    </td>
                    <td className="py-4 px-4 text-[#94A3B8] font-mono text-[11px]">{p.date}</td>
                    <td className="py-4 px-4 text-right font-mono text-slate-200">
                      {p.views.toLocaleString("vi-VN")}
                    </td>
                    <td className="py-4 px-4 text-right font-mono text-amber-400 font-semibold">
                      {p.orders}
                    </td>
                    <td className="py-4 px-4 text-right font-mono text-[#41AA6C] font-semibold">
                      {p.revenue.toLocaleString("vi-VN")} đ
                    </td>
                    <td className="py-4 px-4 text-right">
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-[#41AA6C] hover:underline"
                      >
                        <span>Mở</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 4. SUBTAB 2: Comment tương tác KOC */}
      {subTab === "comments" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#94A3B8] flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Lọc Theo Ý Định (Intent):
            </span>
            <button
              onClick={() => setIntentFilter("all")}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium cursor-pointer transition-all duration-200 ${
                intentFilter === "all" ? "bg-[#41AA6C] text-white" : "bg-[#12121E] text-[#94A3B8] border border-[#252538]"
              }`}
            >
              Tất Cả
            </button>
            <button
              onClick={() => setIntentFilter("ask_price")}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium cursor-pointer transition-all duration-200 ${
                intentFilter === "ask_price" ? "bg-[#41AA6C] text-white" : "bg-[#12121E] text-[#94A3B8] border border-[#252538]"
              }`}
            >
              Hỏi Giá
            </button>
            <button
              onClick={() => setIntentFilter("ask_material")}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium cursor-pointer transition-all duration-200 ${
                intentFilter === "ask_material" ? "bg-[#41AA6C] text-white" : "bg-[#12121E] text-[#94A3B8] border border-[#252538]"
              }`}
            >
              Tư Vấn Phom/Vải
            </button>
            <button
              onClick={() => setIntentFilter("complaint")}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium cursor-pointer transition-all duration-200 ${
                intentFilter === "complaint" ? "bg-[#41AA6C] text-white" : "bg-[#12121E] text-[#94A3B8] border border-[#252538]"
              }`}
            >
              Khiếu Nại
            </button>
          </div>

          <div className="space-y-4">
            {comments
              .filter((c) => intentFilter === "all" || c.intent === intentFilter)
              .map((c) => (
                <div key={c.id} className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white text-sm">{c.author}</span>
                      <span className="text-xs text-[#94A3B8]">trên {c.channel}</span>
                      <span className="text-[11px] text-[#94A3B8]">• {c.time}</span>
                    </div>

                    {c.intent === "ask_price" && (
                      <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#41AA6C]/15 text-[#41AA6C] border border-[#41AA6C]/30">
                        Hỏi Giá / Mua Hàng
                      </span>
                    )}
                    {c.intent === "ask_material" && (
                      <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-sky-500/15 text-sky-400 border border-sky-500/30">
                        Tư Vấn Phom / Chất
                      </span>
                    )}
                    {c.intent === "complaint" && (
                      <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                        Khiếu Nại / Bảo Hành
                      </span>
                    )}
                  </div>

                  <p className="text-sm text-slate-200 bg-[#000000] p-3 rounded-xl border border-[#252538]">
                    &quot;{c.text}&quot;
                  </p>

                  <div className="bg-[#181828] border border-[#252538] rounded-xl p-3 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-[#41AA6C] flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5" /> Phản hồi tự động KOC:
                      </span>
                      {c.status === "replied" ? (
                        <span className="text-xs text-[#41AA6C] flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Đã trả lời
                        </span>
                      ) : (
                        <button
                          onClick={() => handleApproveReply(c.id)}
                          className="text-xs text-[#41AA6C] hover:underline flex items-center gap-1 font-semibold cursor-pointer"
                        >
                          <Send className="w-3 h-3" /> Duyệt gửi ngay
                        </button>
                      )}
                    </div>
                    <p className="text-xs text-slate-300">{c.reply}</p>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* 5. SUBTAB 3: Cào Đối Thủ & Làm Lại Nội Dung (AMAS-19) */}
      {subTab === "competitors" && (
        <div className="space-y-6">
          {/* Panel Cào Đối Thủ Đa Nền Tảng */}
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Share2 className="w-5 h-5 text-[#41AA6C]" />
                <h3 className="font-semibold text-white text-base">Cào Đối Thủ Đa Nền Tảng (TikTok / Facebook / Instagram)</h3>
              </div>
              <span className="text-xs text-[#94A3B8]">Deduplication UPSERT tự động</span>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Danh Sách Link Video Đối Thủ (mỗi dòng một link)
                </label>
                <textarea
                  rows={3}
                  value={scraperLinks}
                  onChange={(e) => setScraperLinks(e.target.value)}
                  placeholder="https://www.tiktok.com/@creator/video/12345&#10;https://www.facebook.com/reel/67890&#10;https://www.instagram.com/reel/abcde"
                  className="w-full px-3 py-2 rounded-xl bg-[#000000] border border-[#252538] focus:border-[#41AA6C] text-xs font-mono text-white focus:outline-none"
                />
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-[#94A3B8]">Chu kỳ cào tự động:</span>
                  <select
                    value={scrapeInterval}
                    onChange={(e) => setScrapeInterval(e.target.value)}
                    className="bg-[#000000] border border-[#252538] text-white text-xs rounded-lg px-2.5 py-1.5 focus:outline-none"
                  >
                    <option value="2">2 tiếng / lần</option>
                    <option value="4">4 tiếng / lần (Khuyên dùng - Chống Checkpoint)</option>
                  </select>
                </div>

                <button
                  onClick={handleScrapeNow}
                  disabled={isScraping || !scraperLinks.trim()}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#41AA6C] hover:bg-[#368f5b] text-white text-xs font-semibold transition-all duration-150 cursor-pointer disabled:opacity-50"
                >
                  {isScraping ? (
                    <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5" />
                  )}
                  <span>Cào Cưỡng Bức Ngay</span>
                </button>
              </div>

              {scrapeNotification && (
                <div className="p-3 rounded-xl bg-[#41AA6C]/10 border border-[#41AA6C]/30 text-xs text-[#41AA6C] flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{scrapeNotification}</span>
                </div>
              )}
            </div>
          </div>

          {/* Danh Sách Video Đối Thủ Đã Cào */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {competitorVideos.map((cv) => (
              <div
                key={cv.id}
                className="bg-[#12121E] border border-[#252538] rounded-2xl overflow-hidden shadow-sm flex flex-col justify-between"
              >
                <div>
                  <div className="relative aspect-video bg-[#000000] flex items-center justify-center border-b border-[#252538]">
                    <Play className="w-10 h-10 text-[#41AA6C]/60" />
                    <div className="absolute top-2 left-2 flex items-center gap-1.5">
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-black/80 text-white font-semibold uppercase border border-[#252538]">
                        {cv.platform}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#41AA6C]/20 text-[#41AA6C] font-semibold border border-[#41AA6C]/40">
                        Viral Score: {cv.viralScore}/100
                      </span>
                    </div>
                  </div>

                  <div className="p-4 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-[#41AA6C]">{cv.creator}</span>
                      <span className="text-[11px] text-[#94A3B8] font-mono">{cv.date}</span>
                    </div>
                    <h4 className="text-xs font-semibold text-white line-clamp-2">{cv.title}</h4>

                    <div className="flex items-center justify-between text-[11px] text-[#94A3B8] pt-2 border-t border-[#252538]">
                      <span>{cv.views.toLocaleString("vi-VN")} views</span>
                      <a
                        href={cv.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-[#41AA6C] hover:underline"
                      >
                        <span>Link Gốc</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                </div>

                <div className="p-4 pt-0 space-y-2">
                  {/* Nút Làm Lại Nội Dung (AMAS-19) */}
                  <button
                    onClick={() => handleOpenRecreateModal(cv)}
                    className="w-full flex items-center justify-center gap-2 bg-[#181828] hover:bg-[#252538] border border-[#252538] hover:border-[#41AA6C] text-white py-2 rounded-xl text-xs font-semibold transition-all duration-150 cursor-pointer"
                  >
                    <Wand2 className="w-3.5 h-3.5 text-[#41AA6C]" />
                    <span>Làm Lại Nội Dung</span>
                  </button>

                  <button
                    onClick={() => onSelectMotionReference(cv.url)}
                    className="w-full flex items-center justify-center gap-2 bg-[#41AA6C] hover:bg-[#34925b] text-white py-2 rounded-xl text-xs font-semibold transition-all duration-150 cursor-pointer shadow-sm"
                  >
                    <span>Dùng làm Motion Reference</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal Làm Lại Nội Dung (AMAS-19) */}
      {selectedVideoForRecreate && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150">
          <div className="bg-[#0B0B14] border border-[#252538] rounded-2xl max-w-xl w-full p-6 text-[#F8FAFC] shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#252538] pb-3">
              <div className="flex items-center gap-2 text-white font-semibold text-base">
                <Wand2 className="w-5 h-5 text-[#41AA6C]" />
                <span>Làm Lại Nội Dung Đối Thủ</span>
              </div>
              <button
                onClick={() => setSelectedVideoForRecreate(null)}
                className="text-[#94A3B8] hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="text-xs text-[#94A3B8]">
              Video mục tiêu: <span className="text-white font-semibold">{selectedVideoForRecreate.title}</span>
            </div>

            {/* Options Tabs */}
            <div className="grid grid-cols-2 gap-2 bg-[#12121E] p-1 rounded-xl border border-[#252538]">
              <button
                onClick={() => setRecreateTab("script")}
                className={`py-2 text-xs font-semibold rounded-lg transition-all duration-150 cursor-pointer ${
                  recreateTab === "script" ? "bg-[#41AA6C] text-white" : "text-[#94A3B8] hover:text-white"
                }`}
              >
                1. Viết Lại Kịch Bản & Caption AI
              </button>
              <button
                onClick={() => {
                  onSelectMotionReference(selectedVideoForRecreate.url);
                  setSelectedVideoForRecreate(null);
                }}
                className="py-2 text-xs font-semibold rounded-lg text-[#94A3B8] hover:text-white hover:bg-white/5 transition-all duration-150 cursor-pointer"
              >
                2. Làm Mới Video (Studio)
              </button>
            </div>

            {/* Script Generator Box */}
            {recreateTab === "script" && (
              <div className="space-y-3 pt-2">
                {!generatedScript ? (
                  <div className="text-center py-6 space-y-3">
                    <p className="text-xs text-[#94A3B8]">
                      AI sẽ học văn phong ({activeProject?.tone_of_voice || "Chuyên gia"}) và đối tượng ({activeProject?.target_audience || "GenZ"}) để sinh mới kịch bản 3 phần (Hook 3s, Body, CTA).
                    </p>
                    <button
                      onClick={handleGenerateScript}
                      disabled={isGeneratingScript}
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#41AA6C] hover:bg-[#368f5b] text-white text-xs font-semibold cursor-pointer shadow-sm disabled:opacity-50"
                    >
                      {isGeneratingScript ? (
                        <RotateCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <Sparkles className="w-4 h-4" />
                      )}
                      <span>Sinh Kịch Bản AI Ngay</span>
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    <div className="p-3 rounded-xl bg-[#12121E] border border-[#252538] text-xs">
                      <div className="text-[11px] font-semibold text-[#41AA6C] mb-1">1. Hook 3 Giây Mở Đầu:</div>
                      <p className="text-slate-200">{generatedScript.hook}</p>
                    </div>

                    <div className="p-3 rounded-xl bg-[#12121E] border border-[#252538] text-xs">
                      <div className="text-[11px] font-semibold text-indigo-400 mb-1">2. Thân Bài (Body):</div>
                      <p className="text-slate-200">{generatedScript.body}</p>
                    </div>

                    <div className="p-3 rounded-xl bg-[#12121E] border border-[#252538] text-xs">
                      <div className="text-[11px] font-semibold text-amber-400 mb-1">3. Kêu Gọi Mua Hàng (CTA):</div>
                      <p className="text-slate-200">{generatedScript.cta}</p>
                    </div>

                    <div className="flex gap-2 pt-2">
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(
                            `${generatedScript.hook}\n\n${generatedScript.body}\n\n${generatedScript.cta}`
                          );
                          alert("Đã sao chép kịch bản vào bộ nhớ tạm!");
                        }}
                        className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl bg-[#181828] hover:bg-[#252538] border border-[#252538] text-slate-200 text-xs font-semibold cursor-pointer"
                      >
                        <Copy className="w-3.5 h-3.5" />
                        <span>Sao Chép Kịch Bản</span>
                      </button>
                      <button
                        onClick={() => {
                          alert("Đã đưa kịch bản sang hàng đợi Lịch Đăng Bài thành công!");
                          setSelectedVideoForRecreate(null);
                        }}
                        className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl bg-[#41AA6C] hover:bg-[#368f5b] text-white text-xs font-semibold cursor-pointer shadow-sm"
                      >
                        <Calendar className="w-3.5 h-3.5" />
                        <span>Lên Lịch Đăng Ngay</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
