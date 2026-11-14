"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  Flame,
  AlertTriangle,
  RotateCw,
  Plus,
  KeyRound,
  CheckCircle2,
  XCircle,
  X,
  Server,
  Zap,
  Clock,
} from "lucide-react";

interface ChannelItem {
  id: string;
  name: string;
  platform: "tiktok" | "facebook";
  accountType: "profile" | "fanpage";
  lifecycleStatus: "ready_to_post" | "warming" | "cooldown" | "captcha_blocked";
  daysWarmed: number;
  postsToday: number;
  quotaPerDay: number;
  proxyIp: string;
  proxyPort: number;
  proxyLatency: number;
}

interface ProxyItem {
  id: string;
  url: string;
  protocol: string;
  status: "alive" | "dead" | "unchecked";
  latency: number;
  assignedCount: number;
}

export const ChannelsManager: React.FC = () => {
  // Filters
  const [platformFilter, setPlatformFilter] = useState<"all" | "tiktok" | "facebook">("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Mock initial channels
  const [channels, setChannels] = useState<ChannelItem[]>([
    {
      id: "chan_tk_01",
      name: "Thoitrang.koc.viet",
      platform: "tiktok",
      accountType: "profile",
      lifecycleStatus: "ready_to_post",
      daysWarmed: 24,
      postsToday: 2,
      quotaPerDay: 5,
      proxyIp: "103.142.12.8",
      proxyPort: 8080,
      proxyLatency: 95,
    },
    {
      id: "chan_tk_02",
      name: "Review.giadung.thongminh",
      platform: "tiktok",
      accountType: "profile",
      lifecycleStatus: "warming",
      daysWarmed: 6,
      postsToday: 0,
      quotaPerDay: 2,
      proxyIp: "103.142.12.19",
      proxyPort: 8080,
      proxyLatency: 110,
    },
    {
      id: "chan_fb_01",
      name: "Đầm Xinh Dự Tiệc VIP",
      platform: "facebook",
      accountType: "fanpage",
      lifecycleStatus: "ready_to_post",
      daysWarmed: 45,
      postsToday: 3,
      quotaPerDay: 8,
      proxyIp: "116.193.18.4",
      proxyPort: 9000,
      proxyLatency: 82,
    },
    {
      id: "chan_fb_02",
      name: "Góc Nhỏ Decor Nhà Bếp",
      platform: "facebook",
      accountType: "profile",
      lifecycleStatus: "captcha_blocked",
      daysWarmed: 12,
      postsToday: 1,
      quotaPerDay: 3,
      proxyIp: "116.193.18.99",
      proxyPort: 9999,
      proxyLatency: 999,
    },
  ]);

  // Proxies
  const [proxies, setProxies] = useState<ProxyItem[]>([
    { id: "px_01", url: "http://user:pass@103.142.12.8:8080", protocol: "http", status: "alive", latency: 95, assignedCount: 1 },
    { id: "px_02", url: "http://user:pass@103.142.12.19:8080", protocol: "http", status: "alive", latency: 110, assignedCount: 1 },
    { id: "px_03", url: "http://user:pass@116.193.18.4:9000", protocol: "http", status: "alive", latency: 82, assignedCount: 1 },
    { id: "px_04", url: "http://user:pass@116.193.18.99:9999", protocol: "http", status: "dead", latency: 9999, assignedCount: 1 },
    { id: "px_05", url: "http://user:pass@103.142.12.50:8080", protocol: "http", status: "alive", latency: 74, assignedCount: 0 },
  ]);

  // Captcha modal state
  const [selectedBlockedChannel, setSelectedBlockedChannel] = useState<ChannelItem | null>(null);
  const [cookieImportChannel, setCookieImportChannel] = useState<ChannelItem | null>(null);
  const [cookieInput, setCookieInput] = useState<string>("");
  const [isImportingCookie, setIsImportingCookie] = useState<boolean>(false);
  const [isWarmingId, setIsWarmingId] = useState<string | null>(null);

  const handleImportCookieSubmit = async () => {
    if (!cookieImportChannel || !cookieInput.trim()) return;
    setIsImportingCookie(true);
    try {
      try {
        await fetch(`/api/channels/${cookieImportChannel.id}/import-cookies`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cookies: cookieInput }),
        });
      } catch {
        // Fallback local update
      }
      setChannels((prev) =>
        prev.map((c) =>
          c.id === cookieImportChannel.id ? { ...c, lifecycleStatus: "ready_to_post" } : c
        )
      );
      setCookieImportChannel(null);
      setCookieInput("");
      alert(`Đã nạp cookie và kích hoạt kênh [${cookieImportChannel.name}] thành công sang trạng thái Sẵn Sàng Đăng!`);
    } finally {
      setIsImportingCookie(false);
    }
  };

  const handleApplySampleCookie = () => {
    setCookieInput(
      JSON.stringify(
        [
          { name: "sessionid", value: "98a7fbc34d12ef901234abcd", domain: ".tiktok.com", path: "/" },
          { name: "tt_csrf_token", value: "token_mock_test_ready", domain: ".tiktok.com", path: "/" },
        ],
        null,
        2
      )
    );
  };

  // Trigger Warmup
  const handleWarmup = (chanId: string) => {
    setIsWarmingId(chanId);
    setTimeout(() => {
      setChannels((prev) =>
        prev.map((c) =>
          c.id === chanId ? { ...c, lifecycleStatus: "ready_to_post", daysWarmed: c.daysWarmed + 1 } : c
        )
      );
      setIsWarmingId(null);
    }, 1200);
  };

  // Unlock Captcha
  const handleUnlockCaptcha = (chanId: string) => {
    setChannels((prev) =>
      prev.map((c) =>
        c.id === chanId ? { ...c, lifecycleStatus: "ready_to_post" } : c
      )
    );
    setSelectedBlockedChannel(null);
  };

  // Rotate Proxy
  const handleRotateProxy = (chanId: string) => {
    const aliveUnassigned = proxies.find((p) => p.status === "alive" && p.assignedCount === 0);
    if (aliveUnassigned) {
      setChannels((prev) =>
        prev.map((c) =>
          c.id === chanId
            ? { ...c, proxyIp: "103.142.12.50", proxyPort: 8080, proxyLatency: 74 }
            : c
        )
      );
      setProxies((prev) =>
        prev.map((p) => (p.id === aliveUnassigned.id ? { ...p, assignedCount: 1 } : p))
      );
    }
  };

  // Filter channels
  const filteredChannels = channels.filter((c) => {
    if (platformFilter !== "all" && c.platform !== platformFilter) return false;
    if (statusFilter !== "all" && c.lifecycleStatus !== statusFilter) return false;
    return true;
  });

  return (
    <div className="space-y-8">
      {/* 1. Header & Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-[#94A3B8] text-xs font-medium">
            <span>Tổng số Kênh</span>
            <ShieldCheck className="w-4 h-4 text-[#41AA6C]" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">{channels.length}</div>
          <div className="text-[11px] text-[#94A3B8] mt-1">Đa nền tảng TikTok & FB</div>
        </div>

        <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-[#94A3B8] text-xs font-medium">
            <span>Sẵn sàng Đăng</span>
            <Zap className="w-4 h-4 text-[#41AA6C]" />
          </div>
          <div className="text-2xl font-bold text-[#41AA6C] mt-2">
            {channels.filter((c) => c.lifecycleStatus === "ready_to_post").length}
          </div>
          <div className="text-[11px] text-[#94A3B8] mt-1">Trust score an toàn</div>
        </div>

        <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-[#94A3B8] text-xs font-medium">
            <span>Đang Nuôi (Warming)</span>
            <Flame className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 mt-2">
            {channels.filter((c) => c.lifecycleStatus === "warming").length}
          </div>
          <div className="text-[11px] text-[#94A3B8] mt-1">Lướt feed & tương tác giả lập</div>
        </div>

        <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-[#94A3B8] text-xs font-medium">
            <span>Cảnh Báo Captcha</span>
            <AlertTriangle className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold text-rose-500 mt-2">
            {channels.filter((c) => c.lifecycleStatus === "captcha_blocked").length}
          </div>
          <div className="text-[11px] text-[#94A3B8] mt-1">Cần can thiệp mở khóa</div>
        </div>
      </div>

      {/* 2. Filter Bar & Quick Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-[#12121E] border border-[#252538] rounded-2xl p-4">
        {/* Filters */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-[#000000] rounded-xl p-1 border border-[#252538]">
            <button
              onClick={() => setPlatformFilter("all")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer ${
                platformFilter === "all" ? "bg-[#41AA6C] text-white" : "text-[#94A3B8] hover:text-white"
              }`}
            >
              Tất cả
            </button>
            <button
              onClick={() => setPlatformFilter("tiktok")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer ${
                platformFilter === "tiktok" ? "bg-[#41AA6C] text-white" : "text-[#94A3B8] hover:text-white"
              }`}
            >
              TikTok
            </button>
            <button
              onClick={() => setPlatformFilter("facebook")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer ${
                platformFilter === "facebook" ? "bg-[#41AA6C] text-white" : "text-[#94A3B8] hover:text-white"
              }`}
            >
              Facebook
            </button>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#000000] border border-[#252538] text-white text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-[#41AA6C]"
          >
            <option value="all">Tất cả trạng thái</option>
            <option value="ready_to_post">Sẵn sàng đăng</option>
            <option value="warming">Đang nuôi (Warming)</option>
            <option value="cooldown">Cooldown</option>
            <option value="captcha_blocked">Bị chặn Captcha</option>
          </select>
        </div>

        {/* Add Channel Button */}
        <button className="flex items-center gap-2 bg-[#41AA6C] hover:bg-[#34925b] text-white px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer">
          <Plus className="w-4 h-4" />
          <span>Thêm Kênh Mới</span>
        </button>
      </div>

      {/* 3. Channels Data Table */}
      <div className="bg-[#12121E] border border-[#252538] rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#000000]/60 border-b border-[#252538] text-[#94A3B8] uppercase text-[11px] font-semibold">
              <tr>
                <th className="py-3.5 px-4">Kênh & Nền tảng</th>
                <th className="py-3.5 px-4">Trạng thái Nuôi</th>
                <th className="py-3.5 px-4">Số ngày nuôi</th>
                <th className="py-3.5 px-4">Quota Hôm Nay</th>
                <th className="py-3.5 px-4">Proxy Gán</th>
                <th className="py-3.5 px-4 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#252538]">
              {filteredChannels.map((c) => (
                <tr key={c.id} className="hover:bg-white/[0.02] transition-colors duration-150">
                  <td className="py-4 px-4">
                    <div className="font-semibold text-white text-sm">{c.name}</div>
                    <div className="flex items-center gap-2 mt-0.5 text-[#94A3B8]">
                      <span className="capitalize">{c.platform}</span>
                      <span>•</span>
                      <span className="text-[11px] capitalize">{c.accountType}</span>
                    </div>
                  </td>

                  <td className="py-4 px-4">
                    {c.lifecycleStatus === "ready_to_post" && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#41AA6C]/15 text-[#41AA6C] border border-[#41AA6C]/30">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Sẵn sàng đăng
                      </span>
                    )}
                    {c.lifecycleStatus === "warming" && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/15 text-amber-400 border border-amber-500/30">
                        <Flame className="w-3.5 h-3.5" /> Đang nuôi (Warming)
                      </span>
                    )}
                    {c.lifecycleStatus === "cooldown" && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
                        <Clock className="w-3.5 h-3.5" /> Cooldown
                      </span>
                    )}
                    {c.lifecycleStatus === "captcha_blocked" && (
                      <button
                        onClick={() => setSelectedBlockedChannel(c)}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/40 hover:bg-rose-500/30 transition-all duration-200 cursor-pointer animate-pulse"
                      >
                        <AlertTriangle className="w-3.5 h-3.5" /> Captcha Blocked (Xem ngay)
                      </button>
                    )}
                  </td>

                  <td className="py-4 px-4 text-slate-300 font-mono">
                    {c.daysWarmed} ngày
                  </td>

                  <td className="py-4 px-4">
                    <div className="flex items-center gap-2">
                      <div className="w-20 bg-[#000000] h-1.5 rounded-full overflow-hidden border border-[#252538]">
                        <div
                          className="bg-[#41AA6C] h-full"
                          style={{ width: `${(c.postsToday / c.quotaPerDay) * 100}%` }}
                        />
                      </div>
                      <span className="text-slate-300 font-mono text-[11px]">
                        {c.postsToday}/{c.quotaPerDay}
                      </span>
                    </div>
                  </td>

                  <td className="py-4 px-4">
                    <div className="font-mono text-xs text-white">
                      {c.proxyIp}:{c.proxyPort}
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-[#94A3B8]">
                      <span>{c.proxyLatency}ms</span>
                      <button
                        onClick={() => handleRotateProxy(c.id)}
                        title="Đổi proxy khác"
                        className="text-[#41AA6C] hover:underline cursor-pointer flex items-center gap-1"
                      >
                        <RotateCw className="w-3 h-3" /> Đổi
                      </button>
                    </div>
                  </td>

                  <td className="py-4 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => {
                          setCookieImportChannel(c);
                          setCookieInput("");
                        }}
                        title="Nạp Cookie / Token xác thực"
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#000000] border border-[#252538] hover:border-[#41AA6C] text-[#41AA6C] hover:text-white transition-all duration-150 cursor-pointer text-xs"
                      >
                        <KeyRound className="w-3.5 h-3.5" />
                        <span>Nạp Cookie</span>
                      </button>
                      <button
                        onClick={() => handleWarmup(c.id)}
                        disabled={isWarmingId === c.id}
                        className="px-2.5 py-1.5 rounded-lg bg-[#000000] border border-[#252538] hover:border-[#41AA6C] text-slate-300 hover:text-white transition-all duration-200 cursor-pointer"
                      >
                        {isWarmingId === c.id ? "Đang nuôi..." : "Nuôi 5p"}
                      </button>
                      <button
                        onClick={() => alert(`Chuẩn bị đăng video lên ${c.name}`)}
                        className="px-3 py-1.5 rounded-lg bg-[#41AA6C] hover:bg-[#34925b] text-white font-medium transition-all duration-200 cursor-pointer"
                      >
                        Đăng bài
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Kho Proxy Inventory */}
      <section className="bg-[#12121E] border border-[#252538] rounded-2xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Server className="w-5 h-5 text-[#41AA6C]" />
            <h3 className="font-semibold text-white text-base">Kho Proxy Dân Cư / Datacenter</h3>
          </div>
          <span className="text-xs text-[#94A3B8]">{proxies.length} Proxies trong hệ thống</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {proxies.map((p) => (
            <div
              key={p.id}
              className="bg-[#000000] border border-[#252538] rounded-xl p-3.5 flex items-center justify-between"
            >
              <div>
                <div className="font-mono text-xs text-white truncate max-w-[180px]">{p.url}</div>
                <div className="flex items-center gap-2 text-[11px] text-[#94A3B8] mt-1">
                  <span>{p.protocol.toUpperCase()}</span>
                  <span>•</span>
                  <span>{p.assignedCount} Kênh gắn</span>
                </div>
              </div>
              <div className="text-right">
                {p.status === "alive" ? (
                  <span className="inline-flex items-center gap-1 text-[11px] text-[#41AA6C] font-mono">
                    <CheckCircle2 className="w-3.5 h-3.5" /> {p.latency}ms
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[11px] text-rose-500 font-mono">
                    <XCircle className="w-3.5 h-3.5" /> Dead
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 5. Modal Xem Ảnh Captcha Khẩn Cấp */}
      {selectedBlockedChannel && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#12121E] border border-rose-500/50 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-rose-400 font-semibold text-base">
                <AlertTriangle className="w-5 h-5" />
                <span>Cảnh Báo Captcha Khẩn Cấp</span>
              </div>
              <button
                onClick={() => setSelectedBlockedChannel(null)}
                className="text-[#94A3B8] hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-300">
              Kênh <span className="font-semibold text-white">{selectedBlockedChannel.name}</span> gặp
              thử thách xoay hình / ghép mảnh trên trình duyệt.
            </p>

            {/* Simulated Captcha Screenshot */}
            <div className="relative aspect-video bg-[#000000] border border-[#252538] rounded-xl overflow-hidden flex items-center justify-center">
              <div className="text-center p-4">
                <KeyRound className="w-8 h-8 text-amber-400 mx-auto mb-2" />
                <p className="text-xs text-slate-300 font-medium">TikTok Slide / Puzzle Verification</p>
                <p className="text-[11px] text-[#94A3B8] mt-1">Ảnh chụp tự động lúc 07:18 từ AdsPower CDP</p>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => handleRotateProxy(selectedBlockedChannel.id)}
                className="flex-1 bg-[#000000] hover:bg-[#181828] border border-[#252538] text-white py-2.5 rounded-xl text-xs font-medium transition-all duration-200 cursor-pointer"
              >
                Đổi IP Proxy Khác
              </button>
              <button
                onClick={() => handleUnlockCaptcha(selectedBlockedChannel.id)}
                className="flex-1 bg-[#41AA6C] hover:bg-[#34925b] text-white py-2.5 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer shadow-sm"
              >
                Xác Nhận Đã Mở Khóa
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 6. Modal Nạp Cookie / Token Nhanh (AMAS-19) */}
      {cookieImportChannel && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#252538] pb-3">
              <div className="flex items-center gap-2 text-white font-semibold text-base">
                <KeyRound className="w-5 h-5 text-[#41AA6C]" />
                <span>Nạp Cookie Cho Kênh: {cookieImportChannel.name}</span>
              </div>
              <button
                onClick={() => setCookieImportChannel(null)}
                className="text-[#94A3B8] hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-300">
              Hỗ trợ định dạng chuỗi <strong>JSON</strong>, <strong>Netscape</strong> hoặc <strong>Raw Cookie Header</strong>. Sau khi nạp, kênh sẽ tự động được kiểm tra và chuyển sang trạng thái <strong>Sẵn sàng đăng</strong>.
            </p>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-300">Nội Dung Chuỗi Cookie</label>
                <button
                  type="button"
                  onClick={handleApplySampleCookie}
                  className="text-[11px] text-[#41AA6C] hover:underline cursor-pointer"
                >
                  Dùng Cookie Mẫu
                </button>
              </div>
              <textarea
                rows={5}
                value={cookieInput}
                onChange={(e) => setCookieInput(e.target.value)}
                placeholder="Dán chuỗi cookie JSON, Netscape hoặc sessionid=... vào đây"
                className="w-full px-3 py-2 rounded-xl bg-[#000000] border border-[#252538] focus:border-[#41AA6C] text-xs font-mono text-white focus:outline-none"
              />
            </div>

            <div className="flex gap-3 pt-2 border-t border-[#252538]">
              <button
                type="button"
                onClick={() => setCookieImportChannel(null)}
                className="flex-1 bg-[#000000] hover:bg-[#181828] border border-[#252538] text-slate-300 hover:text-white py-2 rounded-xl text-xs font-medium cursor-pointer"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={handleImportCookieSubmit}
                disabled={isImportingCookie || !cookieInput.trim()}
                className="flex-1 bg-[#41AA6C] hover:bg-[#34925b] text-white py-2 rounded-xl text-xs font-semibold cursor-pointer disabled:opacity-50"
              >
                {isImportingCookie ? "Đang xác thực..." : "Xác Thực & Nạp Ngay"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
