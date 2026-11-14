"use client";

import React, { useState } from "react";
import {
  Calendar as CalendarIcon,
  Clock,
  Plus,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  List,
  Grid,
} from "lucide-react";
import { useProject } from "@/context/ProjectContext";

interface ScheduleItem {
  id: string;
  title: string;
  channelName: string;
  platform: "tiktok" | "facebook_reels" | "facebook_group" | "instagram";
  scheduledTime: string;
  dayOfWeek: string;
  status: "Scheduled" | "Publishing" | "Published" | "Failed";
  videoUrl?: string;
  captionSnippet?: string;
}

const GOLDEN_HOURS = [
  { platform: "tiktok", label: "TikTok Giờ Vàng Trưa", time: "11:30", note: "Lượt lướt video giờ ăn trưa" },
  { platform: "tiktok", label: "TikTok Giờ Vàng Tối", time: "20:00", note: "Khung giờ mua sắm đỉnh cao" },
  { platform: "facebook_reels", label: "FB Reels Buổi Sáng", time: "08:00", note: "Khởi động ngày mới" },
  { platform: "facebook_reels", label: "FB Reels Buổi Tối", time: "20:30", note: "Tương tác mạnh nhất tuần" },
  { platform: "facebook_group", label: "FB Group Thảo Luận", time: "14:00", note: "Dân văn phòng rảnh tay" },
  { platform: "instagram", label: "Instagram Visual Peak", time: "19:00", note: "Khách xem ảnh & story" },
];

export const ContentCalendarTab: React.FC = () => {
  const { activeProject } = useProject();
  const [viewMode, setViewMode] = useState<"weekly" | "timeline">("weekly");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [schedules, setSchedules] = useState<ScheduleItem[]>([
    {
      id: "sch_01",
      title: "Lookbook Phối Đồ Đi Làm Hack Tuổi",
      channelName: "Thoitrang.koc.viet",
      platform: "tiktok",
      scheduledTime: "11:30 Thứ 2",
      dayOfWeek: "Thứ 2",
      status: "Published",
      captionSnippet: "Set đồ công sở nhẹ nhàng mà cực kỳ tôn dáng...",
    },
    {
      id: "sch_02",
      title: "Review Kệ Xoay Nhà Bếp Chịu Lực",
      channelName: "Review.giadung.thongminh",
      platform: "tiktok",
      scheduledTime: "20:00 Thứ 3",
      dayOfWeek: "Thứ 3",
      status: "Scheduled",
      captionSnippet: "Bếp nhỏ thành bếp to chỉ sau 1 phút lắp đặt...",
    },
    {
      id: "sch_03",
      title: "Đầm Lụa Dự Tiệc Cao Cấp Che Bụng",
      channelName: "Đầm Xinh Dự Tiệc VIP",
      platform: "facebook_reels",
      scheduledTime: "20:30 Thứ 4",
      dayOfWeek: "Thứ 4",
      status: "Scheduled",
      captionSnippet: "Chất lụa bay bổng mềm mịn, tôn eo cực đỉnh...",
    },
    {
      id: "sch_04",
      title: "Top 3 Món Đồ Gia Dụng Tiện Ích Mùa Này",
      channelName: "Hội Review Đồ Bếp",
      platform: "facebook_group",
      scheduledTime: "14:00 Thứ 5",
      dayOfWeek: "Thứ 5",
      status: "Publishing",
      captionSnippet: "Chia sẻ với cả nhà 3 món mình ưng ý nhất...",
    },
    {
      id: "sch_05",
      title: "OOTD Cà Phê Cuối Tuần Năng Động",
      channelName: "Thoitrang.koc.viet",
      platform: "instagram",
      scheduledTime: "19:00 Thứ 7",
      dayOfWeek: "Thứ 7",
      status: "Scheduled",
      captionSnippet: "Đơn giản mà nổi bật cùng tone be pastel...",
    },
  ]);

  // Form states for creating schedule
  const [newTitle, setNewTitle] = useState("");
  const [newChannel, setNewChannel] = useState("");
  const [newPlatform, setNewPlatform] = useState<ScheduleItem["platform"]>("tiktok");
  const [newTime, setNewTime] = useState("20:00 Thứ 6");
  const [newCaption, setNewCaption] = useState("");

  const handleCreateSchedule = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    const newItem: ScheduleItem = {
      id: `sch_${Date.now()}`,
      title: newTitle,
      channelName: newChannel || "Kênh Mặc Định",
      platform: newPlatform,
      scheduledTime: newTime,
      dayOfWeek: newTime.split(" ")[1] || "Thứ 6",
      status: "Scheduled",
      captionSnippet: newCaption || undefined,
    };
    setSchedules([newItem, ...schedules]);
    setIsModalOpen(false);
    setNewTitle("");
    setNewCaption("");
  };

  const handleApplyGoldenHour = (gh: typeof GOLDEN_HOURS[0]) => {
    setNewPlatform(gh.platform as ScheduleItem["platform"]);
    setNewTime(`${gh.time} Hôm nay`);
  };

  const daysOfWeek = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"];

  const getStatusBadge = (status: ScheduleItem["status"]) => {
    switch (status) {
      case "Published":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#41AA6C]/15 text-[#41AA6C] border border-[#41AA6C]/30">
            <CheckCircle2 className="w-2.5 h-2.5" /> Đã Đăng
          </span>
        );
      case "Publishing":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <Clock className="w-2.5 h-2.5 animate-spin" /> Đang Đăng...
          </span>
        );
      case "Scheduled":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
            <Clock className="w-2.5 h-2.5" /> Đã Lên Lịch
          </span>
        );
      case "Failed":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <AlertCircle className="w-2.5 h-2.5" /> Lỗi Đăng
          </span>
        );
    }
  };

  const getPlatformLabel = (platform: ScheduleItem["platform"]) => {
    switch (platform) {
      case "tiktok":
        return "TikTok Video";
      case "facebook_reels":
        return "Facebook Reels";
      case "facebook_group":
        return "FB Group Post";
      case "instagram":
        return "Instagram";
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#41AA6C]/10 border border-[#41AA6C]/30 flex items-center justify-center">
            <CalendarIcon className="w-5 h-5 text-[#41AA6C]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white tracking-tight">Lịch Đăng Bài & Video Đa Kênh</h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[#181828] text-[#41AA6C] border border-[#252538]">
                {activeProject?.name || "Project"}
              </span>
            </div>
            <p className="text-xs text-[#94A3B8]">Quản lý lịch xuất bản tự động trên TikTok, Facebook Reels, Group và Instagram</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* View toggle */}
          <div className="flex items-center bg-[#0B0B14] p-1 rounded-xl border border-[#252538]">
            <button
              onClick={() => setViewMode("weekly")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 cursor-pointer ${
                viewMode === "weekly" ? "bg-[#41AA6C] text-white shadow-sm" : "text-[#94A3B8] hover:text-white"
              }`}
            >
              <Grid className="w-3.5 h-3.5" />
              <span>Lưới Tuần</span>
            </button>
            <button
              onClick={() => setViewMode("timeline")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 cursor-pointer ${
                viewMode === "timeline" ? "bg-[#41AA6C] text-white shadow-sm" : "text-[#94A3B8] hover:text-white"
              }`}
            >
              <List className="w-3.5 h-3.5" />
              <span>Dòng Thời Gian</span>
            </button>
          </div>

          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#41AA6C] hover:bg-[#368f5b] text-white text-xs font-semibold transition-all duration-150 shadow-sm cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Lên Lịch Mới</span>
          </button>
        </div>
      </div>

      {/* 2. Khung Giờ Vàng (Golden Posting Hours) Gợi Ý 1-Click */}
      <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-[#41AA6C]" />
          <span className="text-xs font-semibold text-white uppercase tracking-wider">
            Gợi Ý Khung Giờ Vàng Xuất Bản (1-Click Chọn)
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {GOLDEN_HOURS.map((gh, i) => (
            <button
              key={i}
              onClick={() => {
                handleApplyGoldenHour(gh);
                setIsModalOpen(true);
              }}
              className="p-2.5 rounded-xl bg-[#0B0B14] hover:bg-[#41AA6C]/10 border border-[#252538] hover:border-[#41AA6C]/40 text-left transition-all duration-150 cursor-pointer group"
            >
              <div className="flex items-center justify-between text-[11px] font-semibold text-[#41AA6C]">
                <span>{gh.time}</span>
                <Clock className="w-3 h-3 text-[#94A3B8] group-hover:text-[#41AA6C]" />
              </div>
              <div className="text-xs font-medium text-white truncate mt-0.5">{gh.label}</div>
              <div className="text-[10px] text-[#94A3B8] truncate mt-0.5">{gh.note}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 3. Lịch View (Weekly Grid hoặc Timeline) */}
      {viewMode === "weekly" ? (
        <div className="grid grid-cols-1 md:grid-cols-7 gap-3">
          {daysOfWeek.map((day) => {
            const daySchedules = schedules.filter((s) => s.dayOfWeek === day);
            return (
              <div
                key={day}
                className="bg-[#12121E] border border-[#252538] rounded-2xl p-3 flex flex-col min-h-[320px]"
              >
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#252538]">
                  <span className="text-xs font-bold text-white">{day}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#181828] text-[#94A3B8] border border-[#252538]">
                    {daySchedules.length}
                  </span>
                </div>

                <div className="space-y-2 flex-1">
                  {daySchedules.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-[11px] text-[#94A3B8]/60 text-center py-8">
                      Trống
                    </div>
                  ) : (
                    daySchedules.map((item) => (
                      <div
                        key={item.id}
                        className="p-2.5 rounded-xl bg-[#0B0B14] border border-[#252538] hover:border-[#41AA6C]/40 transition-all duration-150 space-y-1.5 group"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-semibold text-slate-400">
                            {getPlatformLabel(item.platform)}
                          </span>
                          {getStatusBadge(item.status)}
                        </div>
                        <div className="text-xs font-semibold text-white line-clamp-2">
                          {item.title}
                        </div>
                        <div className="text-[10px] text-[#41AA6C] font-mono flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" />
                          <span>{item.scheduledTime}</span>
                        </div>
                        <div className="text-[10px] text-[#94A3B8] truncate">
                          {item.channelName}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Timeline View */
        <div className="bg-[#12121E] border border-[#252538] rounded-2xl overflow-hidden shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0B0B14] border-b border-[#252538] text-[#94A3B8] uppercase text-[11px] font-semibold">
              <tr>
                <th className="py-3.5 px-4">Tiêu Đề & Nội Dung</th>
                <th className="py-3.5 px-4">Nền Tảng & Kênh</th>
                <th className="py-3.5 px-4">Thời Gian Dự Kiến</th>
                <th className="py-3.5 px-4">Trạng Thái</th>
                <th className="py-3.5 px-4 text-right">Thao Tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#252538]">
              {schedules.map((item) => (
                <tr key={item.id} className="hover:bg-white/[0.02] transition-colors duration-150">
                  <td className="py-4 px-4 max-w-sm">
                    <div className="font-semibold text-white text-sm">{item.title}</div>
                    {item.captionSnippet && (
                      <div className="text-xs text-[#94A3B8] truncate mt-0.5">
                        {item.captionSnippet}
                      </div>
                    )}
                  </td>
                  <td className="py-4 px-4">
                    <div className="text-xs font-medium text-white">{getPlatformLabel(item.platform)}</div>
                    <div className="text-[11px] text-[#94A3B8]">{item.channelName}</div>
                  </td>
                  <td className="py-4 px-4 font-mono text-xs text-slate-300">
                    {item.scheduledTime}
                  </td>
                  <td className="py-4 px-4">
                    {getStatusBadge(item.status)}
                  </td>
                  <td className="py-4 px-4 text-right">
                    <button
                      onClick={() => alert(`Chỉnh sửa giờ xuất bản cho: ${item.title}`)}
                      className="px-2.5 py-1 rounded-lg bg-[#0B0B14] border border-[#252538] hover:border-[#41AA6C] text-[#94A3B8] hover:text-white transition-all duration-150 cursor-pointer"
                    >
                      Đổi Giờ
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal Lên Lịch Đăng Mới */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-md bg-[#0B0B14] border border-[#252538] rounded-2xl p-6 text-[#F8FAFC] shadow-2xl">
            <h3 className="text-base font-bold text-white mb-4">Lên Lịch Xuất Bản Mới</h3>
            <form onSubmit={handleCreateSchedule} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Tiêu Đề Video / Bài Viết</label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="VD: Review Phụ Kiện Sạc Nhanh Tiện Ích"
                  className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] focus:border-[#41AA6C] text-white focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Nền Tảng</label>
                  <select
                    value={newPlatform}
                    onChange={(e) => setNewPlatform(e.target.value as ScheduleItem["platform"])}
                    className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] text-white focus:outline-none"
                  >
                    <option value="tiktok">TikTok Video</option>
                    <option value="facebook_reels">Facebook Reels</option>
                    <option value="facebook_group">Facebook Group</option>
                    <option value="instagram">Instagram</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Tên Kênh</label>
                  <input
                    type="text"
                    value={newChannel}
                    onChange={(e) => setNewChannel(e.target.value)}
                    placeholder="VD: Thoitrang.koc.viet"
                    className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] text-white focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Thời Gian Lên Lịch</label>
                <input
                  type="text"
                  value={newTime}
                  onChange={(e) => setNewTime(e.target.value)}
                  placeholder="VD: 20:00 Thứ 6"
                  className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Nội Dung Caption / Hashtags</label>
                <textarea
                  rows={2}
                  value={newCaption}
                  onChange={(e) => setNewCaption(e.target.value)}
                  placeholder="Caption thu hút kèm CTA mua hàng..."
                  className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] text-white focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#252538]">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-lg text-[#94A3B8] hover:text-white cursor-pointer"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-[#41AA6C] hover:bg-[#368f5b] text-white font-semibold cursor-pointer"
                >
                  Lưu Lịch Đăng
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
