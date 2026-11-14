"use client";

import React, { useState } from "react";
import {
  Users,
  MessageSquare,
  Sparkles,
  Plus,
  Send,
  CheckCircle2,
  RotateCw,
  Tag,
} from "lucide-react";
import { useProject } from "@/context/ProjectContext";

interface GroupItem {
  id: string;
  name: string;
  url: string;
  memberCount: number;
  moderationMode: "auto_approve" | "manual_admin";
  status: "active" | "paused";
  lastSeededAt: string;
}

interface SeedingLogItem {
  id: string;
  groupName: string;
  postSnippet: string;
  matchedKeyword: string;
  kocReply: string;
  status: "posted" | "pending";
  timestamp: string;
}

export const GroupSeedingTab: React.FC = () => {
  const { activeProject } = useProject();

  const [groups, setGroups] = useState<GroupItem[]>([
    {
      id: "grp_01",
      name: "Hội Mê Đồ Gia Dụng Tiện Ích & Bếp Xinh",
      url: "https://facebook.com/groups/giadungthongminh",
      memberCount: 145000,
      moderationMode: "auto_approve",
      status: "active",
      lastSeededAt: "10 phút trước",
    },
    {
      id: "grp_02",
      name: "Góc Thanh Lý & Review Thời Trang GenZ",
      url: "https://facebook.com/groups/thoitranggenz",
      memberCount: 89000,
      moderationMode: "manual_admin",
      status: "active",
      lastSeededAt: "1 giờ trước",
    },
    {
      id: "grp_03",
      name: "Cộng Đồng Nghiện Setup Góc Làm Việc & Công Nghệ",
      url: "https://facebook.com/groups/setupitcongnghe",
      memberCount: 210000,
      moderationMode: "auto_approve",
      status: "active",
      lastSeededAt: "3 giờ trước",
    },
  ]);

  const [logs, setLogs] = useState<SeedingLogItem[]>([
    {
      id: "log_01",
      groupName: "Hội Mê Đồ Gia Dụng Tiện Ích & Bếp Xinh",
      postSnippet: "Các chị ơi có ai dùng kệ xoay góc bếp chưa? Có tiện và chắc chắn như quảng cáo không?",
      matchedKeyword: "kệ xoay",
      kocReply: "Mình đang dùng loại xoay 360 này 6 tháng nay rồi mom ơi, thép sơn tĩnh điện nặng trịch chịu lực 50kg để nồi chiên với gia vị vô tư nha, nên mua loại có chốt khóa ấy!",
      status: "posted",
      timestamp: "5 phút trước",
    },
    {
      id: "log_02",
      groupName: "Góc Thanh Lý & Review Thời Trang GenZ",
      postSnippet: "Cần tìm set đồ đi tiệc cưới tone be nhẹ nhàng thanh lịch cho nữ m6 52kg...",
      matchedKeyword: "set đồ",
      kocReply: "Form bạn chuẩn mặc đầm lụa trễ vai chữ A siêu tôn dáng nha! Vừa giấu bụng vừa hack chân, mình mua bên shop này chất lụa tuyết mịn không nhăn mà giá có hơn trăm thôi.",
      status: "posted",
      timestamp: "25 phút trước",
    },
    {
      id: "log_03",
      groupName: "Cộng Đồng Nghiện Setup Góc Làm Việc & Công Nghệ",
      postSnippet: "Em sinh viên IT mới vào nghề, anh em tư vấn củ sạc nhanh 65W nhỏ gọn tiện mang đi học với?",
      matchedKeyword: "sạc nhanh 65W",
      kocReply: "Tham khảo củ GaN 65W 3 cổng Type-C này nhé bác, công nghệ tản nhiệt mát rượi, sạc cùng lúc cả MacBook lẫn iPhone không bị ngắt điện gián đoạn đâu.",
      status: "posted",
      timestamp: "1 giờ trước",
    },
  ]);

  const [isScanning, setIsScanning] = useState(false);
  const [isAutoPosting, setIsAutoPosting] = useState(false);
  const [newGroupName, setNewGroupName] = useState("");
  const [newGroupUrl, setNewGroupUrl] = useState("");
  const [isAddGroupOpen, setIsAddGroupOpen] = useState(false);

  const handleScanAndSeed = async () => {
    setIsScanning(true);
    try {
      await new Promise((r) => setTimeout(r, 1200));
      const newLog: SeedingLogItem = {
        id: `log_${Date.now()}`,
        groupName: groups[0]?.name || "Facebook Group",
        postSnippet: "Cho em hỏi chỗ nào bán củ sạc uy tín bảo hành 1 đổi 1 ạ?",
        matchedKeyword: "củ sạc",
        kocReply: "Bạn ghé xem gian hàng chính hãng bên TikTok Shop này nè, đợt này áp mã trợ giá giảm 30k mà bảo hành 12 tháng điện tử an tâm lắm!",
        status: "posted",
        timestamp: "Vừa xong",
      };
      setLogs([newLog, ...logs]);
    } finally {
      setIsScanning(false);
    }
  };

  const handleAutoPost = async () => {
    setIsAutoPosting(true);
    try {
      await new Promise((r) => setTimeout(r, 1500));
      alert(`Đã tự động spin và đăng bài mẫu cho ngành [${activeProject?.name || "Affiliate"}] lên ${groups.length} nhóm thành công!`);
    } finally {
      setIsAutoPosting(false);
    }
  };

  const handleAddGroup = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGroupName.trim() || !newGroupUrl.trim()) return;

    const newG: GroupItem = {
      id: `grp_${Date.now()}`,
      name: newGroupName,
      url: newGroupUrl,
      memberCount: 50000,
      moderationMode: "auto_approve",
      status: "active",
      lastSeededAt: "Chưa",
    };
    setGroups([...groups, newG]);
    setNewGroupName("");
    setNewGroupUrl("");
    setIsAddGroupOpen(false);
  };

  return (
    <div className="space-y-6">
      {/* 1. Header & Quick Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#41AA6C]/10 border border-[#41AA6C]/30 flex items-center justify-center">
            <Users className="w-5 h-5 text-[#41AA6C]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white tracking-tight">Hệ Thống Group Seeding Tự Động</h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[#181828] text-[#41AA6C] border border-[#252538]">
                {activeProject?.name || "Project"}
              </span>
            </div>
            <p className="text-xs text-[#94A3B8]">Quét từ khóa thảo luận & tự động comment KOC theo ngữ cảnh văn phong của Project</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleAutoPost}
            disabled={isAutoPosting}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#181828] hover:bg-[#252538] border border-[#252538] text-slate-200 text-xs font-semibold transition-all duration-150 cursor-pointer disabled:opacity-50"
          >
            {isAutoPosting ? (
              <RotateCw className="w-3.5 h-3.5 text-[#41AA6C] animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5 text-[#41AA6C]" />
            )}
            <span>Auto Đăng Bài Group</span>
          </button>

          <button
            onClick={handleScanAndSeed}
            disabled={isScanning}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#41AA6C] hover:bg-[#368f5b] text-white text-xs font-semibold transition-all duration-150 shadow-sm cursor-pointer disabled:opacity-50"
          >
            {isScanning ? (
              <RotateCw className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            <span>Quét Từ Khóa & Auto Comment</span>
          </button>
        </div>
      </div>

      {/* 2. Project Keywords Snapshot */}
      <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <Tag className="w-4 h-4 text-[#41AA6C]" />
          <span className="text-slate-300 font-semibold">Từ Khóa Kích Hoạt Seeding Của Project:</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {activeProject?.trigger_keywords && activeProject.trigger_keywords.length > 0 ? (
            activeProject.trigger_keywords.map((k, i) => (
              <span
                key={i}
                className="px-2.5 py-0.5 rounded-full bg-[#181828] text-[#41AA6C] border border-[#41AA6C]/30 text-[11px] font-mono font-medium"
              >
                #{k}
              </span>
            ))
          ) : (
            <span className="text-[#94A3B8]">Chưa cấu hình từ khóa kích hoạt</span>
          )}
        </div>
      </div>

      {/* 3. Danh Sách Facebook Groups Đã Kết Nối */}
      <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-[#41AA6C]" />
            <h3 className="text-sm font-bold text-white">Danh Sách Facebook Groups ({groups.length})</h3>
          </div>
          <button
            onClick={() => setIsAddGroupOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0B0B14] border border-[#252538] hover:border-[#41AA6C] text-xs font-medium text-slate-200 hover:text-white transition-all duration-150 cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5 text-[#41AA6C]" />
            <span>Thêm Group Mới</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {groups.map((g) => (
            <div
              key={g.id}
              className="p-4 rounded-xl bg-[#0B0B14] border border-[#252538] hover:border-[#41AA6C]/30 transition-all duration-150 space-y-2"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-semibold text-xs text-white line-clamp-1">{g.name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#181828] text-[#41AA6C] border border-[#41AA6C]/30 shrink-0">
                  {g.moderationMode === "auto_approve" ? "Duyệt Tự Động" : "Admin Duyệt"}
                </span>
              </div>
              <div className="text-[11px] text-[#94A3B8] font-mono truncate">{g.url}</div>
              <div className="flex items-center justify-between pt-2 border-t border-[#252538] text-[11px] text-slate-400">
                <span>{g.memberCount.toLocaleString()} thành viên</span>
                <span className="text-[#41AA6C]">Seeded: {g.lastSeededAt}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4. Bảng Lịch Sử Bắt Từ Khóa & Seeding Comment */}
      <div className="bg-[#12121E] border border-[#252538] rounded-2xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-[#252538] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-[#41AA6C]" />
            <h3 className="text-sm font-bold text-white">Lịch Sử Bắt Từ Khóa & Comment Seeding Tự Động</h3>
          </div>
          <span className="text-xs text-[#94A3B8]">{logs.length} bản ghi ghi nhận</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0B0B14] border-b border-[#252538] text-[#94A3B8] uppercase text-[11px] font-semibold">
              <tr>
                <th className="py-3.5 px-4">Bài Viết Thành Viên</th>
                <th className="py-3.5 px-4">Từ Khóa Khớp</th>
                <th className="py-3.5 px-4 max-w-md">Câu Trả Lời KOC Đã Comment</th>
                <th className="py-3.5 px-4">Trạng Thái</th>
                <th className="py-3.5 px-4 text-right">Thời Gian</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#252538]">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-white/[0.02] transition-colors duration-150">
                  <td className="py-4 px-4 max-w-xs">
                    <div className="text-xs text-white font-medium line-clamp-2">{log.postSnippet}</div>
                    <div className="text-[10px] text-[#94A3B8] mt-1">{log.groupName}</div>
                  </td>
                  <td className="py-4 px-4">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-[#41AA6C]/15 text-[#41AA6C] border border-[#41AA6C]/30">
                      #{log.matchedKeyword}
                    </span>
                  </td>
                  <td className="py-4 px-4 max-w-md">
                    <p className="text-xs text-slate-300 bg-[#0B0B14] p-2.5 rounded-xl border border-[#252538]">
                      {log.kocReply}
                    </p>
                  </td>
                  <td className="py-4 px-4">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#41AA6C]/15 text-[#41AA6C] border border-[#41AA6C]/30">
                      <CheckCircle2 className="w-3 h-3" /> Đã Comment
                    </span>
                  </td>
                  <td className="py-4 px-4 text-right font-mono text-[11px] text-[#94A3B8]">
                    {log.timestamp}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Thêm Group Mới */}
      {isAddGroupOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-md bg-[#0B0B14] border border-[#252538] rounded-2xl p-6 text-[#F8FAFC] shadow-2xl">
            <h3 className="text-base font-bold text-white mb-4">Thêm Facebook Group Mới</h3>
            <form onSubmit={handleAddGroup} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Tên Nhóm Facebook</label>
                <input
                  type="text"
                  required
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  placeholder="VD: Hội Chị Em Mê Đồ Gia Dụng Tiện Ích"
                  className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] focus:border-[#41AA6C] text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Đường Dẫn Group (URL)</label>
                <input
                  type="url"
                  required
                  value={newGroupUrl}
                  onChange={(e) => setNewGroupUrl(e.target.value)}
                  placeholder="https://facebook.com/groups/..."
                  className="w-full px-3 py-2 rounded-lg bg-[#12121E] border border-[#252538] focus:border-[#41AA6C] text-white focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#252538]">
                <button
                  type="button"
                  onClick={() => setIsAddGroupOpen(false)}
                  className="px-3.5 py-1.5 rounded-lg text-[#94A3B8] hover:text-white cursor-pointer"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-[#41AA6C] hover:bg-[#368f5b] text-white font-semibold cursor-pointer"
                >
                  Lưu Group
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
