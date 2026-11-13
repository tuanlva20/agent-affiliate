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
} from "lucide-react";

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
  views: number;
  salesCount: number;
  revenueEstimate: number;
  url: string;
  date: string;
}

interface HistoryHubProps {
  onSelectMotionReference: (videoUrl: string) => void;
}

export const HistoryHub: React.FC<HistoryHubProps> = ({ onSelectMotionReference }) => {
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
  const competitorVideos: CompetitorVideoItem[] = [
    {
      id: "cv_01",
      creator: "@trend.fashion.bkk",
      title: "Visual Hook 3s cực cuốn: Đổi form dáng người chỉ trong 1 nốt nhạc",
      views: 1250000,
      salesCount: 840,
      revenueEstimate: 168000000,
      url: "https://www.tiktok.com/@trend.fashion.bkk/video/73111",
      date: "12/11/2026",
    },
    {
      id: "cv_02",
      creator: "@home_lifestyle_pro",
      title: "Giải pháp bếp chật: Kệ góc xoay 360 độ gọn gàng ngăn nắp",
      views: 840000,
      salesCount: 620,
      revenueEstimate: 111600000,
      url: "https://www.tiktok.com/@home_lifestyle_pro/video/73222",
      date: "11/11/2026",
    },
    {
      id: "cv_03",
      creator: "@ootd_daily_viet",
      title: "Set đồ công sở che bụng dưới cho nàng công sở tự tin",
      views: 650000,
      salesCount: 450,
      revenueEstimate: 94500000,
      url: "https://www.tiktok.com/@ootd_daily_viet/video/73333",
      date: "10/11/2026",
    },
  ];

  const handleApproveReply = (commentId: string) => {
    setComments((prev) =>
      prev.map((c) => (c.id === commentId ? { ...c, status: "replied" as const } : c))
    );
  };

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(amount);
  };

  const totalViews = publishes.reduce((acc, curr) => acc + curr.views, 0);
  const totalOrders = publishes.reduce((acc, curr) => acc + curr.orders, 0);
  const totalRevenue = publishes.reduce((acc, curr) => acc + curr.revenue, 0);

  return (
    <div className="space-y-8">
      {/* 1. Sub-navigation tabs */}
      <div className="flex items-center gap-2 bg-[#12121E] p-1.5 rounded-2xl border border-[#252538] w-fit">
        <button
          onClick={() => setSubTab("publishes")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer ${
            subTab === "publishes" ? "bg-[#41AA6C] text-white" : "text-[#94A3B8] hover:text-white"
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          <span>Lịch sử Đăng & Hiệu Suất</span>
        </button>

        <button
          onClick={() => setSubTab("comments")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer ${
            subTab === "comments" ? "bg-[#41AA6C] text-white" : "text-[#94A3B8] hover:text-white"
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span>Chăm sóc Comment KOC</span>
        </button>

        <button
          onClick={() => setSubTab("competitors")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer ${
            subTab === "competitors" ? "bg-[#41AA6C] text-white" : "text-[#94A3B8] hover:text-white"
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>Kho Video Đối Thủ & Motion</span>
        </button>
      </div>

      {/* 2. SUBTAB 1: Lịch sử Đăng & Hiệu Suất */}
      {subTab === "publishes" && (
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
              <div className="flex items-center justify-between text-[#94A3B8] text-xs font-medium">
                <span>Video Đã Đăng</span>
                <Play className="w-4 h-4 text-[#41AA6C]" />
              </div>
              <div className="text-2xl font-bold text-white mt-2">{publishes.length}</div>
              <div className="text-[11px] text-[#94A3B8] mt-1">TikTok & Facebook Reels</div>
            </div>

            <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
              <div className="flex items-center justify-between text-[#94A3B8] text-xs font-medium">
                <span>Tổng Lượt Xem (Views)</span>
                <Eye className="w-4 h-4 text-sky-400" />
              </div>
              <div className="text-2xl font-bold text-white mt-2">
                {totalViews.toLocaleString("vi-VN")}
              </div>
              <div className="text-[11px] text-[#41AA6C] mt-1">+24.5% tuần này</div>
            </div>

            <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
              <div className="flex items-center justify-between text-[#94A3B8] text-xs font-medium">
                <span>Đơn Hàng Thành Công</span>
                <ShoppingCart className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-bold text-amber-400 mt-2">{totalOrders} đơn</div>
              <div className="text-[11px] text-[#94A3B8] mt-1">Tỷ lệ chuyển đổi ~3.8%</div>
            </div>

            <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
              <div className="flex items-center justify-between text-[#94A3B8] text-xs font-medium">
                <span>Doanh Thu Ước Tính</span>
                <DollarSign className="w-4 h-4 text-[#41AA6C]" />
              </div>
              <div className="text-2xl font-bold text-[#41AA6C] mt-2">
                {formatVND(totalRevenue)}
              </div>
              <div className="text-[11px] text-[#94A3B8] mt-1">Hoa hồng affiliate 15%</div>
            </div>
          </div>

          {/* Publishing Table */}
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#000000]/60 border-b border-[#252538] text-[#94A3B8] uppercase text-[11px] font-semibold">
                  <tr>
                    <th className="py-3.5 px-4">Video & Kênh</th>
                    <th className="py-3.5 px-4">Ngày đăng</th>
                    <th className="py-3.5 px-4">Views</th>
                    <th className="py-3.5 px-4">Likes</th>
                    <th className="py-3.5 px-4">Đơn hàng</th>
                    <th className="py-3.5 px-4">Doanh thu VNĐ</th>
                    <th className="py-3.5 px-4 text-right">Xem bài</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#252538]">
                  {publishes.map((p) => (
                    <tr key={p.id} className="hover:bg-white/[0.02] transition-colors duration-150">
                      <td className="py-4 px-4">
                        <div className="font-semibold text-white text-sm max-w-xs truncate">
                          {p.title}
                        </div>
                        <div className="text-[#94A3B8] text-[11px] mt-0.5">
                          {p.channel} ({p.platform.toUpperCase()})
                        </div>
                      </td>

                      <td className="py-4 px-4 text-slate-300 font-mono text-[11px]">{p.date}</td>

                      <td className="py-4 px-4 font-mono text-slate-200">
                        {p.views.toLocaleString("vi-VN")}
                      </td>

                      <td className="py-4 px-4 font-mono text-slate-300">
                        {p.likes.toLocaleString("vi-VN")}
                      </td>

                      <td className="py-4 px-4 font-semibold text-amber-400 font-mono">
                        {p.orders}
                      </td>

                      <td className="py-4 px-4 font-bold text-[#41AA6C] font-mono">
                        {formatVND(p.revenue)}
                      </td>

                      <td className="py-4 px-4 text-right">
                        <a
                          href={p.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-[#41AA6C] hover:underline cursor-pointer"
                        >
                          <span>Mở</span>
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 3. SUBTAB 2: Chăm sóc Comment KOC */}
      {subTab === "comments" && (
        <div className="space-y-6">
          {/* Intent Filters */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#94A3B8] flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Lọc Intent:
            </span>
            <button
              onClick={() => setIntentFilter("all")}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium cursor-pointer transition-all duration-200 ${
                intentFilter === "all"
                  ? "bg-[#41AA6C] text-white"
                  : "bg-[#12121E] text-[#94A3B8] border border-[#252538] hover:text-white"
              }`}
            >
              Tất cả
            </button>
            <button
              onClick={() => setIntentFilter("ask_price")}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium cursor-pointer transition-all duration-200 ${
                intentFilter === "ask_price"
                  ? "bg-[#41AA6C] text-white"
                  : "bg-[#12121E] text-[#94A3B8] border border-[#252538] hover:text-white"
              }`}
            >
              Hỏi Giá
            </button>
            <button
              onClick={() => setIntentFilter("ask_material")}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium cursor-pointer transition-all duration-200 ${
                intentFilter === "ask_material"
                  ? "bg-[#41AA6C] text-white"
                  : "bg-[#12121E] text-[#94A3B8] border border-[#252538] hover:text-white"
              }`}
            >
              Tư Vấn Phom/Vải
            </button>
            <button
              onClick={() => setIntentFilter("complaint")}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium cursor-pointer transition-all duration-200 ${
                intentFilter === "complaint"
                  ? "bg-[#41AA6C] text-white"
                  : "bg-[#12121E] text-[#94A3B8] border border-[#252538] hover:text-white"
              }`}
            >
              Khiếu Nại
            </button>
          </div>

          {/* Comment Cards */}
          <div className="space-y-4">
            {comments
              .filter((c) => intentFilter === "all" || c.intent === intentFilter)
              .map((c) => (
                <div
                  key={c.id}
                  className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-3"
                >
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

      {/* 4. SUBTAB 3: Kho Video Đối Thủ & Motion Reference */}
      {subTab === "competitors" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-white text-base">Kho Dữ Liệu Video Đối Thủ Viral</h3>
              <p className="text-xs text-[#94A3B8] mt-0.5">
                Cào tự động qua Kalodata & TikTok Scraper, sẵn sàng làm mẫu chuyển động
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {competitorVideos.map((cv) => (
              <div
                key={cv.id}
                className="bg-[#12121E] border border-[#252538] rounded-2xl overflow-hidden shadow-sm flex flex-col justify-between"
              >
                <div>
                  <div className="relative aspect-video bg-[#000000] flex items-center justify-center border-b border-[#252538]">
                    <Play className="w-10 h-10 text-[#41AA6C]/60" />
                    <span className="absolute bottom-2 right-2 text-[10px] bg-black/70 px-2 py-0.5 rounded text-white font-mono">
                      Viral 30s
                    </span>
                  </div>

                  <div className="p-4 space-y-2">
                    <div className="text-xs font-semibold text-[#41AA6C]">{cv.creator}</div>
                    <h4 className="text-xs font-semibold text-white line-clamp-2">{cv.title}</h4>

                    <div className="flex items-center justify-between text-[11px] text-[#94A3B8] pt-2 border-t border-[#252538]">
                      <span>{cv.views.toLocaleString("vi-VN")} views</span>
                      <span className="text-amber-400 font-medium">{cv.salesCount} đơn</span>
                    </div>
                  </div>
                </div>

                <div className="p-4 pt-0">
                  <button
                    onClick={() => onSelectMotionReference(cv.url)}
                    className="w-full flex items-center justify-center gap-2 bg-[#41AA6C] hover:bg-[#34925b] text-white py-2.5 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer shadow-sm"
                  >
                    <span>Dùng làm Motion Reference</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
