"use client";

import React, { useState } from "react";
import {
  LayoutDashboard,
  KeyRound,
  Globe,
  Link2,
  Bot,
  Search,
  LineChart,
  BarChart3,
  TrendingUp,
  MapPin,
  Bookmark,
  ShieldCheck,
  FileText,
  Sliders,
  Cpu,
  MessageSquare,
  Settings,
  Sparkles,
  ExternalLink,
  Download,
  Send,
  RotateCw,
  AlertTriangle,
  X,
} from "lucide-react";
import { useProject } from "@/context/ProjectContext";

export type OpenSEOScreen =
  | "dashboard"
  | "keyword_research"
  | "domain_overview"
  | "backlinks"
  | "prompt_research"
  | "prompt_explorer"
  | "prompt_tracking"
  | "gsc_insights"
  | "rank_tracking"
  | "local_seo"
  | "saved_keywords"
  | "site_audit"
  | "reports"
  | "brand_context"
  | "agent_setup"
  | "sam_assistant"
  | "settings";

interface NavGroup {
  title: string;
  items: {
    id: OpenSEOScreen;
    name: string;
    icon: React.ElementType;
    badge?: string;
  }[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    title: "1. Overview",
    items: [
      { id: "dashboard", name: "01. Dashboard", icon: LayoutDashboard },
    ],
  },
  {
    title: "2. Research",
    items: [
      { id: "keyword_research", name: "02. Keyword Research", icon: KeyRound },
      { id: "domain_overview", name: "03. Domain Overview", icon: Globe },
      { id: "backlinks", name: "04. Backlinks", icon: Link2 },
    ],
  },
  {
    title: "3. AI Visibility",
    items: [
      { id: "prompt_research", name: "05. Prompt Research", icon: Bot },
      { id: "prompt_explorer", name: "06. Prompt Explorer", icon: Search },
      { id: "prompt_tracking", name: "07. Prompt Tracking", icon: LineChart, badge: "SoV" },
    ],
  },
  {
    title: "4. My Site",
    items: [
      { id: "gsc_insights", name: "08. GSC Insights", icon: BarChart3 },
      { id: "rank_tracking", name: "09. Rank Tracking", icon: TrendingUp },
      { id: "local_seo", name: "10. Local SEO", icon: MapPin },
      { id: "saved_keywords", name: "11. Saved Keywords", icon: Bookmark },
      { id: "site_audit", name: "12. Site Audit", icon: ShieldCheck, badge: "91" },
    ],
  },
  {
    title: "5. AI Tools",
    items: [
      { id: "reports", name: "13. Reports", icon: FileText },
      { id: "brand_context", name: "14. Context", icon: Sliders },
      { id: "agent_setup", name: "15. Agent Setup", icon: Cpu, badge: "MCP" },
    ],
  },
];

export const OpenSEOTab: React.FC = () => {
  const { activeProject } = useProject();
  const [activeScreen, setActiveScreen] = useState<OpenSEOScreen>("dashboard");
  const [isSamDrawerOpen, setIsSamDrawerOpen] = useState(false);

  // States for interactive sub-views
  const [keywordQuery, setKeywordQuery] = useState("thời trang genz");
  const [backlinkSubTab, setBacklinkSubTab] = useState<"backlinks" | "referring" | "anchors" | "new_lost">("backlinks");
  const [geoGridKeyword, setGeoGridKeyword] = useState("váy xinh");
  const [samMessages, setSamMessages] = useState<{ sender: "user" | "sam"; text: string }[]>([
    { sender: "sam", text: "Chào bạn! Tôi là SAM AI Assistant. Tôi có thể hỗ trợ phân tích dữ liệu SEO, tối ưu từ khóa hoặc kiểm tra AI Citations cho dự án của bạn." },
  ]);
  const [samInput, setSamInput] = useState("");
  const [isSamThinking, setIsSamThinking] = useState(false);

  // Saved keywords local state
  const [savedKeywords, setSavedKeywords] = useState([
    { id: "sk_01", keyword: "váy lụa chữ a", volume: 14800, kd: 36, cpc: 0.42, intent: "Commercial" },
    { id: "sk_02", keyword: "outfit streetwear y2k", volume: 22100, kd: 45, cpc: 0.55, intent: "Informational" },
    { id: "sk_03", keyword: "củ sạc 65w gan", volume: 9400, kd: 28, cpc: 0.60, intent: "Transactional" },
  ]);

  const domain = activeProject?.website_url || "https://thoitranggenz.vn";

  const handleSendSamMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!samInput.trim()) return;

    const userText = samInput;
    setSamMessages((prev) => [...prev, { sender: "user", text: userText }]);
    setSamInput("");
    setIsSamThinking(true);

    try {
      await new Promise((r) => setTimeout(r, 900));
      let reply = `Dựa trên dữ liệu của dự án [${activeProject?.name || "AMAS"}], trang web ${domain} đang có tiềm năng tăng trưởng mạnh với các từ khóa ngách liên quan đến "${activeProject?.niche_brief || "sản phẩm"}".`;
      if (userText.toLowerCase().includes("từ khóa") || userText.toLowerCase().includes("keyword")) {
        reply = `Bạn nên tập trung đẩy mạnh cụm từ khóa KD dưới 40 như "đầm lụa chữ A" và "outfit y2k" vì lượng tìm kiếm đang tăng 18.5% trong tháng này.`;
      } else if (userText.toLowerCase().includes("audit") || userText.toLowerCase().includes("lỗi")) {
        reply = `Điểm Health Score của ${domain} là 91/100. Hãy tối ưu dung lượng ảnh sang WebP và thêm Meta Description ở các trang bài viết mới để đạt 98/100.`;
      }
      setSamMessages((prev) => [...prev, { sender: "sam", text: reply }]);
    } finally {
      setIsSamThinking(false);
    }
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6 items-start">
      {/* =================================================================== */}
      {/* LEFT SIDEBAR: 5 Navigation Groups & 17 Screens                      */}
      {/* =================================================================== */}
      <aside className="w-full lg:w-64 bg-[#12121E] border border-[#252538] rounded-2xl p-3 shrink-0 shadow-sm space-y-4">
        {/* Project Header Info */}
        <div className="p-2.5 rounded-xl bg-[#0B0B14] border border-[#252538]">
          <div className="text-[10px] text-[#41AA6C] font-semibold uppercase tracking-wider flex items-center gap-1.5">
            <Globe className="w-3 h-3" />
            <span>OpenSEO Suite</span>
          </div>
          <div className="text-xs font-bold text-white truncate mt-1">
            {activeProject?.name || "Dự Án"}
          </div>
          <div className="text-[11px] text-[#94A3B8] font-mono truncate">
            {domain}
          </div>
        </div>

        {/* 5 Navigation Groups */}
        <div className="space-y-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="space-y-1">
              <div className="px-2 text-[10px] font-bold text-[#94A3B8] uppercase tracking-wider">
                {group.title}
              </div>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeScreen === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveScreen(item.id)}
                      className={`w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-xs font-medium transition-all duration-150 cursor-pointer ${
                        isActive
                          ? "bg-[#41AA6C] text-white shadow-sm font-semibold"
                          : "text-slate-300 hover:text-white hover:bg-white/5"
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <Icon className="w-4 h-4 shrink-0" />
                        <span className="truncate">{item.name}</span>
                      </div>
                      {item.badge && (
                        <span
                          className={`text-[9px] px-1.5 py-0.2 rounded-full font-bold ${
                            isActive
                              ? "bg-black/30 text-white"
                              : "bg-[#181828] text-[#41AA6C] border border-[#41AA6C]/30"
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}

          {/* Global / Drawer Actions */}
          <div className="pt-2 border-t border-[#252538] space-y-1">
            <div className="px-2 text-[10px] font-bold text-[#94A3B8] uppercase tracking-wider">
              6. Global & Setup
            </div>
            <button
              onClick={() => setIsSamDrawerOpen(true)}
              className="w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-white/5 transition-all duration-150 cursor-pointer"
            >
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-[#41AA6C]" />
                <span>16. SAM AI Assistant</span>
              </div>
              <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-[#41AA6C]/20 text-[#41AA6C] font-semibold">
                AI
              </span>
            </button>
            <button
              onClick={() => setActiveScreen("settings")}
              className={`w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-xs font-medium transition-all duration-150 cursor-pointer ${
                activeScreen === "settings"
                  ? "bg-[#41AA6C] text-white shadow-sm font-semibold"
                  : "text-slate-300 hover:text-white hover:bg-white/5"
              }`}
            >
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4" />
                <span>17. Settings & Integrations</span>
              </div>
            </button>
          </div>
        </div>
      </aside>

      {/* =================================================================== */}
      {/* MAIN CONTENT AREA: Renders 1 of the 17 Screens                      */}
      {/* =================================================================== */}
      <main className="flex-1 w-full space-y-6">
        {/* SCREEN 01: DASHBOARD */}
        {activeScreen === "dashboard" && (
          <div className="space-y-6">
            <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-white tracking-tight">01. OpenSEO Dashboard Tổng Quan</h2>
                  <p className="text-xs text-[#94A3B8]">Dữ liệu hiệu suất tìm kiếm và hiển thị AI cho {domain}</p>
                </div>
                <button
                  onClick={() => setIsSamDrawerOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#41AA6C] hover:bg-[#368f5b] text-white text-xs font-semibold shadow-sm transition-all duration-150 cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Hỏi Trợ Lý SAM</span>
                </button>
              </div>

              {/* KPI Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                <div className="p-3.5 rounded-xl bg-[#0B0B14] border border-[#252538]">
                  <div className="text-[11px] text-[#94A3B8]">Organic Traffic</div>
                  <div className="text-xl font-bold text-white mt-1">48,200</div>
                  <div className="text-[10px] text-[#41AA6C] mt-0.5">+18.2% tháng này</div>
                </div>
                <div className="p-3.5 rounded-xl bg-[#0B0B14] border border-[#252538]">
                  <div className="text-[11px] text-[#94A3B8]">Từ Khóa Top Rank</div>
                  <div className="text-xl font-bold text-white mt-1">1,250</div>
                  <div className="text-[10px] text-amber-400 mt-0.5">142 từ Top 3</div>
                </div>
                <div className="p-3.5 rounded-xl bg-[#0B0B14] border border-[#252538]">
                  <div className="text-[11px] text-[#94A3B8]">Audit Health Score</div>
                  <div className="text-xl font-bold text-[#41AA6C] mt-1">88/100</div>
                  <div className="text-[10px] text-slate-300 mt-0.5">2 lỗi cần sửa</div>
                </div>
                <div className="p-3.5 rounded-xl bg-[#0B0B14] border border-[#252538]">
                  <div className="text-[11px] text-[#94A3B8]">AI Share of Voice</div>
                  <div className="text-xl font-bold text-indigo-400 mt-1">24.5%</div>
                  <div className="text-[10px] text-indigo-300 mt-0.5">Top trích dẫn ChatGPT</div>
                </div>
              </div>
            </div>

            {/* GSC Performance Chart Summary & Recent Keywords */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-[#41AA6C]" />
                    <span>Google Search Console (7 Ngày Gần Nhất)</span>
                  </h3>
                </div>
                <div className="space-y-2">
                  {[
                    { day: "14/11", clicks: 2340, imps: 45800 },
                    { day: "13/11", clicks: 2100, imps: 41200 },
                    { day: "12/11", clicks: 1950, imps: 38100 },
                    { day: "11/11", clicks: 1820, imps: 35400 },
                  ].map((row, i) => (
                    <div key={i} className="flex items-center justify-between text-xs p-2 rounded-lg bg-[#0B0B14] border border-[#252538]">
                      <span className="font-mono text-slate-300">{row.day}</span>
                      <span className="font-semibold text-[#41AA6C]">{row.clicks} clicks</span>
                      <span className="text-[#94A3B8] font-mono">{row.imps.toLocaleString()} views</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-3">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-[#41AA6C]" />
                  <span>Từ Khóa Tăng Hạng Nhanh</span>
                </h3>
                <div className="space-y-2">
                  {[
                    { kw: "váy lụa chữ A", rank: 3, change: "+2", vol: "14,800" },
                    { kw: "set đồ y2k streetwear", rank: 5, change: "+1", vol: "22,100" },
                    { kw: "củ sạc 65w gan", rank: 2, change: "0", vol: "9,400" },
                  ].map((k, i) => (
                    <div key={i} className="flex items-center justify-between text-xs p-2.5 rounded-lg bg-[#0B0B14] border border-[#252538]">
                      <div>
                        <div className="font-semibold text-white">{k.kw}</div>
                        <div className="text-[10px] text-[#94A3B8]">{k.vol} tìm kiếm/tháng</div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-[#41AA6C]">Top #{k.rank}</div>
                        <div className="text-[10px] text-slate-300">{k.change} bậc</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SCREEN 02: KEYWORD RESEARCH */}
        {activeScreen === "keyword_research" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <div>
              <h2 className="text-base font-bold text-white">02. Keyword Research</h2>
              <p className="text-xs text-[#94A3B8]">Nghiên cứu từ khóa hạt giống, độ khó KD%, CPC và Search Intent</p>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={keywordQuery}
                onChange={(e) => setKeywordQuery(e.target.value)}
                placeholder="Nhập từ khóa hạt giống..."
                className="flex-1 px-3 py-2 rounded-xl bg-[#0B0B14] border border-[#252538] focus:border-[#41AA6C] text-xs text-white focus:outline-none"
              />
              <button
                onClick={() => alert(`Đang tra cứu từ khóa [${keywordQuery}] qua DataForSEO API...`)}
                className="px-4 py-2 rounded-xl bg-[#41AA6C] hover:bg-[#368f5b] text-white text-xs font-semibold cursor-pointer shadow-sm"
              >
                Tra Cứu
              </button>
            </div>

            <table className="w-full text-left text-xs">
              <thead className="bg-[#0B0B14] border-b border-[#252538] text-[#94A3B8] uppercase text-[10px] font-semibold">
                <tr>
                  <th className="p-3">Từ Khóa Gợi Ý</th>
                  <th className="p-3">Volume</th>
                  <th className="p-3">Độ Khó KD%</th>
                  <th className="p-3">CPC</th>
                  <th className="p-3">Search Intent</th>
                  <th className="p-3 text-right">Lưu Bookmark</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#252538]">
                {[
                  { kw: keywordQuery, vol: "24,000", kd: 38, cpc: "$0.45", intent: "Commercial" },
                  { kw: `review ${keywordQuery} chính hãng`, vol: "15,600", kd: 28, cpc: "$0.35", intent: "Informational" },
                  { kw: `mua ${keywordQuery} giá rẻ`, vol: "10,800", kd: 32, cpc: "$0.60", intent: "Transactional" },
                ].map((row, i) => (
                  <tr key={i} className="hover:bg-white/[0.02]">
                    <td className="p-3 font-semibold text-white">{row.kw}</td>
                    <td className="p-3 font-mono text-slate-300">{row.vol}</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#41AA6C]/20 text-[#41AA6C]">
                        {row.kd}% Dễ
                      </span>
                    </td>
                    <td className="p-3 font-mono text-slate-300">{row.cpc}</td>
                    <td className="p-3">
                      <span className="text-[10px] px-2 py-0.5 rounded bg-[#181828] text-slate-300 border border-[#252538]">
                        {row.intent}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => {
                          setSavedKeywords((prev) => [
                            { id: `sk_${Date.now()}`, keyword: row.kw, volume: 20000, kd: row.kd, cpc: 0.45, intent: row.intent },
                            ...prev,
                          ]);
                          alert(`Đã lưu từ khóa [${row.kw}] vào Bookmark!`);
                        }}
                        className="p-1.5 rounded-lg bg-[#0B0B14] hover:bg-[#41AA6C]/20 text-[#41AA6C] border border-[#252538] hover:border-[#41AA6C] cursor-pointer"
                      >
                        <Bookmark className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* SCREEN 03: DOMAIN OVERVIEW */}
        {activeScreen === "domain_overview" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-white">03. Domain Overview: {domain}</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="p-4 rounded-xl bg-[#0B0B14] border border-[#252538]">
                <div className="text-xs text-[#94A3B8]">Domain Rank</div>
                <div className="text-2xl font-bold text-[#41AA6C] mt-1">48/100</div>
              </div>
              <div className="p-4 rounded-xl bg-[#0B0B14] border border-[#252538]">
                <div className="text-xs text-[#94A3B8]">Organic Keywords</div>
                <div className="text-2xl font-bold text-white mt-1">3,400</div>
              </div>
              <div className="p-4 rounded-xl bg-[#0B0B14] border border-[#252538]">
                <div className="text-xs text-[#94A3B8]">Top 3 SERP</div>
                <div className="text-2xl font-bold text-amber-400 mt-1">142 từ khóa</div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-xs font-bold text-white">Top Trang Có Lưu Lượng Lớn Nhất:</div>
              {[
                { url: `${domain}/blog/top-outfit-y2k`, traffic: "18,200/tháng", kw: 124 },
                { url: `${domain}/san-pham/dam-lua-du-tiec`, traffic: "14,500/tháng", kw: 98 },
              ].map((p, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-[#0B0B14] border border-[#252538] text-xs">
                  <span className="font-mono text-slate-300">{p.url}</span>
                  <span className="font-semibold text-[#41AA6C]">{p.traffic} ({p.kw} keywords)</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SCREEN 04: BACKLINKS */}
        {activeScreen === "backlinks" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-white">04. Backlink Profile</h2>
                <p className="text-xs text-[#94A3B8]">12,850 Backlinks từ 342 Referring Domains (78% Dofollow)</p>
              </div>
              <div className="flex gap-1 bg-[#0B0B14] p-1 rounded-xl border border-[#252538] text-xs">
                {(["backlinks", "referring", "anchors", "new_lost"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setBacklinkSubTab(t)}
                    className={`px-3 py-1 rounded-lg capitalize transition-all ${
                      backlinkSubTab === t ? "bg-[#41AA6C] text-white" : "text-[#94A3B8] hover:text-white"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <table className="w-full text-left text-xs">
              <thead className="bg-[#0B0B14] border-b border-[#252538] text-[#94A3B8] uppercase text-[10px] font-semibold">
                <tr>
                  <th className="p-3">Source URL</th>
                  <th className="p-3">Anchor Text</th>
                  <th className="p-3">Type</th>
                  <th className="p-3 text-right">Domain Rank</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#252538]">
                {[
                  { src: "https://kenh14.vn/fashion/trend-2026", anchor: "đầm lụa cao cấp", type: "dofollow", dr: 74 },
                  { src: "https://vnexpress.net/doi-song/tieu-dung", anchor: "thời trang genz", type: "dofollow", dr: 88 },
                  { src: "https://afamily.vn/goc-review", anchor: "mua tại shop", type: "nofollow", dr: 68 },
                ].map((row, i) => (
                  <tr key={i} className="hover:bg-white/[0.02]">
                    <td className="p-3 font-mono text-slate-300 truncate max-w-xs">{row.src}</td>
                    <td className="p-3 font-semibold text-white">{row.anchor}</td>
                    <td className="p-3">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full ${row.type === "dofollow" ? "bg-[#41AA6C]/20 text-[#41AA6C]" : "bg-slate-700 text-slate-300"}`}>
                        {row.type}
                      </span>
                    </td>
                    <td className="p-3 text-right font-bold text-[#41AA6C]">{row.dr}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* SCREEN 05: PROMPT RESEARCH */}
        {activeScreen === "prompt_research" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-white">05. AI Prompt Research</h2>
            <p className="text-xs text-[#94A3B8]">Khám phá các câu hỏi phổ biến người dùng đang hỏi ChatGPT, Gemini & Perplexity trong ngành hàng</p>
            <div className="space-y-2.5">
              {[
                { q: "Gợi ý các shop bán thời trang GenZ Y2K uy tín và giá tốt nhất", vol: "8,400 lượt hỏi/tháng", platforms: ["ChatGPT", "Gemini", "Perplexity"] },
                { q: "Làm sao để phối đồ che khuyết điểm tôn dáng đi chơi tiệc?", vol: "6,200 lượt hỏi/tháng", platforms: ["ChatGPT", "Claude"] },
                { q: "So sánh chất liệu đầm lụa và đầm tuyết mưa loại nào bền mát hơn?", vol: "4,900 lượt hỏi/tháng", platforms: ["Perplexity"] },
              ].map((p, i) => (
                <div key={i} className="p-4 rounded-xl bg-[#0B0B14] border border-[#252538] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white text-xs">&quot;{p.q}&quot;</span>
                    <span className="text-[11px] text-[#41AA6C] font-mono">{p.vol}</span>
                  </div>
                  <div className="flex gap-1.5">
                    {p.platforms.map((pl, j) => (
                      <span key={j} className="text-[10px] px-2 py-0.5 rounded bg-[#181828] text-indigo-400 border border-[#252538]">
                        {pl}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SCREEN 06: PROMPT EXPLORER */}
        {activeScreen === "prompt_explorer" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-white">06. AI Prompt Explorer</h2>
            <p className="text-xs text-[#94A3B8]">Xem câu trả lời thực tế của các mô hình LLM và danh sách nguồn trích dẫn Citations</p>
            <div className="p-4 rounded-xl bg-[#0B0B14] border border-[#252538] space-y-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-[#41AA6C]">
                <Bot className="w-4 h-4" />
                <span>ChatGPT-4o Search Response</span>
              </div>
              <p className="text-xs text-slate-200">
                &quot;Đối với phong cách Y2K và thời trang nữ tôn dáng năm 2026, các thương hiệu nổi bật có <strong>AMAS Studio</strong> và Shein với các mẫu đầm lụa trễ vai chữ A được người tiêu dùng đánh giá cao...&quot;
              </p>
              <div className="pt-2 border-t border-[#252538] space-y-1">
                <div className="text-[11px] font-semibold text-indigo-400">Nguồn AI Đã Trích Dẫn (Citations):</div>
                <a href={domain} target="_blank" rel="noreferrer" className="text-xs text-[#41AA6C] hover:underline flex items-center gap-1">
                  <span>1. {domain}/blog/y2k-review</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          </div>
        )}

        {/* SCREEN 07: PROMPT TRACKING */}
        {activeScreen === "prompt_tracking" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-white">07. AI Prompt Tracking & Share of Voice</h2>
                <p className="text-xs text-[#94A3B8]">Theo dõi định kỳ độ phủ thương hiệu trên các công cụ tìm kiếm AI</p>
              </div>
              <span className="text-xs font-bold text-[#41AA6C] px-3 py-1 rounded-full bg-[#41AA6C]/10 border border-[#41AA6C]/30">
                Tổng SoV: 28.4%
              </span>
            </div>
            <div className="space-y-2">
              {[
                { prompt: "Top shop thời trang GenZ Y2K giá sinh viên", sov: "35%", pos: "Vị trí #1", engine: "ChatGPT" },
                { prompt: "Review đầm lụa trễ vai chữ A", sov: "22%", pos: "Vị trí #2", engine: "Perplexity" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between p-3.5 rounded-xl bg-[#0B0B14] border border-[#252538] text-xs">
                  <div>
                    <div className="font-semibold text-white">&quot;{item.prompt}&quot;</div>
                    <div className="text-[10px] text-[#94A3B8]">{item.engine}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-[#41AA6C]">{item.sov} SoV</div>
                    <div className="text-[10px] text-amber-400">{item.pos}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SCREEN 08: GSC INSIGHTS */}
        {activeScreen === "gsc_insights" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-white">08. Google Search Console Performance</h2>
            <div className="grid grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-[#0B0B14] border border-[#252538]">
                <div className="text-[10px] text-[#94A3B8]">Total Clicks</div>
                <div className="text-lg font-bold text-[#41AA6C]">42,150</div>
              </div>
              <div className="p-3 rounded-xl bg-[#0B0B14] border border-[#252538]">
                <div className="text-[10px] text-[#94A3B8]">Total Impressions</div>
                <div className="text-lg font-bold text-white">894,000</div>
              </div>
              <div className="p-3 rounded-xl bg-[#0B0B14] border border-[#252538]">
                <div className="text-[10px] text-[#94A3B8]">Average CTR</div>
                <div className="text-lg font-bold text-indigo-400">4.71%</div>
              </div>
              <div className="p-3 rounded-xl bg-[#0B0B14] border border-[#252538]">
                <div className="text-[10px] text-[#94A3B8]">Average Position</div>
                <div className="text-lg font-bold text-amber-400">8.4</div>
              </div>
            </div>
          </div>
        )}

        {/* SCREEN 09: RANK TRACKING */}
        {activeScreen === "rank_tracking" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-white">09. Rank Tracking Tự Động Hàng Ngày</h2>
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0B0B14] border-b border-[#252538] text-[#94A3B8] uppercase text-[10px]">
                <tr>
                  <th className="p-3">Từ Khóa</th>
                  <th className="p-3">Thiết Bị</th>
                  <th className="p-3">Vị Trí Hiện Tại</th>
                  <th className="p-3 text-right">Biến Động</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#252538]">
                {[
                  { kw: "váy xinh dự tiệc", dev: "Mobile", rank: 2, prev: 3, delta: "+1" },
                  { kw: "set đồ genz y2k", dev: "Desktop", rank: 5, prev: 7, delta: "+2" },
                  { kw: "củ sạc gan 65w", dev: "Mobile", rank: 1, prev: 1, delta: "0" },
                ].map((row, i) => (
                  <tr key={i} className="hover:bg-white/[0.02]">
                    <td className="p-3 font-semibold text-white">{row.kw}</td>
                    <td className="p-3 text-slate-300">{row.dev}</td>
                    <td className="p-3 font-bold text-[#41AA6C]">Top #{row.rank}</td>
                    <td className="p-3 text-right font-mono text-emerald-400">{row.delta}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* SCREEN 10: LOCAL SEO GEO-GRID */}
        {activeScreen === "local_seo" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-white">10. Local SEO Geo-Grid Heatmap</h2>
                <p className="text-xs text-[#94A3B8]">Bản đồ lưới 5x5 kiểm tra thứ hạng Google Maps theo bán kính thực tế</p>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={geoGridKeyword}
                  onChange={(e) => setGeoGridKeyword(e.target.value)}
                  className="px-2.5 py-1 rounded-lg bg-[#0B0B14] border border-[#252538] text-xs text-white"
                />
                <button
                  onClick={() => alert(`Đang quét Geo-Grid cho từ khóa [${geoGridKeyword}]...`)}
                  className="px-3 py-1 rounded-lg bg-[#41AA6C] text-white text-xs font-semibold cursor-pointer"
                >
                  Quét Lưới
                </button>
              </div>
            </div>

            {/* 5x5 Visual Geo-Grid */}
            <div className="p-4 rounded-xl bg-[#0B0B14] border border-[#252538] flex flex-col items-center">
              <div className="grid grid-cols-5 gap-3 max-w-md w-full">
                {Array.from({ length: 25 }).map((_, idx) => {
                  const rank = idx === 12 ? 1 : idx % 2 === 0 ? 2 : 4;
                  return (
                    <div
                      key={idx}
                      className={`h-12 rounded-xl flex flex-col items-center justify-center font-bold text-xs text-white shadow-sm ${
                        rank <= 2 ? "bg-[#41AA6C]" : "bg-amber-500"
                      }`}
                    >
                      <span>#{rank}</span>
                      <span className="text-[9px] opacity-80">{rank <= 2 ? "Top 3" : "Top 5"}</span>
                    </div>
                  );
                })}
              </div>
              <div className="text-[11px] text-[#94A3B8] mt-3">
                Thứ hạng trung bình khu vực trung tâm: <strong className="text-[#41AA6C]">2.4</strong>
              </div>
            </div>
          </div>
        )}

        {/* SCREEN 11: SAVED KEYWORDS */}
        {activeScreen === "saved_keywords" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-white">11. Saved Target Keywords</h2>
                <p className="text-xs text-[#94A3B8]">{savedKeywords.length} từ khóa mục tiêu đã bookmark</p>
              </div>
              <button
                onClick={() => alert("Đã xuất danh sách từ khóa ra file CSV chuẩn bị đẩy sang Rank Tracking!")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0B0B14] border border-[#252538] text-xs text-slate-200 hover:text-white cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Xuất CSV</span>
              </button>
            </div>

            <table className="w-full text-left text-xs">
              <thead className="bg-[#0B0B14] border-b border-[#252538] text-[#94A3B8] uppercase text-[10px]">
                <tr>
                  <th className="p-3">Từ Khóa Đã Lưu</th>
                  <th className="p-3">Search Volume</th>
                  <th className="p-3">KD%</th>
                  <th className="p-3">CPC</th>
                  <th className="p-3">Intent</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#252538]">
                {savedKeywords.map((sk) => (
                  <tr key={sk.id} className="hover:bg-white/[0.02]">
                    <td className="p-3 font-semibold text-white">{sk.keyword}</td>
                    <td className="p-3 font-mono text-slate-300">{sk.volume.toLocaleString()}</td>
                    <td className="p-3 text-[#41AA6C] font-semibold">{sk.kd}%</td>
                    <td className="p-3 text-slate-300">${sk.cpc}</td>
                    <td className="p-3 text-slate-300">{sk.intent}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* SCREEN 12: SITE AUDIT */}
        {activeScreen === "site_audit" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-white">12. Site Audit (OpenSEO-Audit/1.0 & Lighthouse)</h2>
                <p className="text-xs text-[#94A3B8]">Kiểm tra toàn diện lỗi kỹ thuật Core Web Vitals và On-Page SEO</p>
              </div>
              <button
                onClick={() => alert(`Đang quét kiểm tra website ${domain}...`)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[#41AA6C] hover:bg-[#368f5b] text-white text-xs font-semibold cursor-pointer shadow-sm"
              >
                <RotateCw className="w-3.5 h-3.5" />
                <span>Quét Lại Audit</span>
              </button>
            </div>

            <div className="flex items-center gap-6 p-4 rounded-xl bg-[#0B0B14] border border-[#252538]">
              <div className="w-20 h-20 rounded-full border-4 border-[#41AA6C] flex items-center justify-center shrink-0">
                <span className="text-2xl font-bold text-[#41AA6C]">91</span>
              </div>
              <div className="space-y-1">
                <div className="text-sm font-bold text-white">Sức Khỏe Kỹ Thuật Rất Tốt</div>
                <p className="text-xs text-[#94A3B8]">0 Lỗi Nghiêm Trọng, 1 Cảnh Báo, 1 Lưu Ý Nhỏ</p>
              </div>
            </div>

            <div className="space-y-2">
              <div className="p-3 rounded-xl bg-[#0B0B14] border border-amber-500/30 text-xs space-y-1">
                <div className="flex items-center gap-1.5 text-amber-400 font-semibold">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Cảnh Báo: Thiếu thẻ Meta Description (3 URLs)</span>
                </div>
                <p className="text-slate-300">Bổ sung thẻ mô tả để tăng CTR tự nhiên trên trang kết quả tìm kiếm.</p>
              </div>
            </div>
          </div>
        )}

        {/* SCREEN 13: REPORTS */}
        {activeScreen === "reports" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-white">13. Báo Cáo SEO Chuyên Sâu Tự Động (AI Reports)</h2>
            <div className="p-4 rounded-xl bg-[#0B0B14] border border-[#252538] space-y-3">
              <div className="text-xs font-bold text-[#41AA6C]">Tóm Tắt Báo Cáo Tăng Trưởng Tháng 11/2026:</div>
              <p className="text-xs text-slate-200">
                Lưu lượng Organic Traffic của {activeProject?.name || "dự án"} tăng trưởng 18.2%, đạt 48,200 lượt truy cập. Tỷ lệ nhắc tên thương hiệu trên công cụ tìm kiếm AI (AI Share of Voice) đạt 24.5%.
              </p>
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => alert("Đang xuất file PDF báo cáo...")}
                  className="px-3 py-1.5 rounded-lg bg-[#41AA6C] text-white text-xs font-semibold cursor-pointer"
                >
                  Tải PDF Báo Cáo
                </button>
              </div>
            </div>
          </div>
        )}

        {/* SCREEN 14: BRAND CONTEXT */}
        {activeScreen === "brand_context" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-white">14. Brand & Website Context</h2>
                <p className="text-xs text-[#94A3B8]">Đồng bộ hai chiều với cấu hình Project trong AMAS</p>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#41AA6C]/20 text-[#41AA6C] font-semibold">
                Đã Đồng Bộ
              </span>
            </div>
            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl bg-[#0B0B14] border border-[#252538]">
                <div className="text-[#94A3B8] font-semibold mb-1">Mô tả ngách:</div>
                <div className="text-white">{activeProject?.niche_brief || "Chưa thiết lập"}</div>
              </div>
              <div className="p-3 rounded-xl bg-[#0B0B14] border border-[#252538]">
                <div className="text-[#94A3B8] font-semibold mb-1">Đối tượng mục tiêu:</div>
                <div className="text-white">{activeProject?.target_audience || "Chưa thiết lập"}</div>
              </div>
              <div className="p-3 rounded-xl bg-[#0B0B14] border border-[#252538]">
                <div className="text-[#94A3B8] font-semibold mb-1">Văn phong thương hiệu:</div>
                <div className="text-white">{activeProject?.tone_of_voice || "Chưa thiết lập"}</div>
              </div>
            </div>
          </div>
        )}

        {/* SCREEN 15: AGENT SETUP (MCP) */}
        {activeScreen === "agent_setup" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-white">15. Cấu Hình MCP Server Cho Coding Agents</h2>
            <p className="text-xs text-[#94A3B8]">Kết nối OpenSEO với Claude Code, Cursor, ChatGPT và NousResearch Hermes</p>
            <div className="p-4 rounded-xl bg-[#0B0B14] border border-[#252538] space-y-2">
              <div className="text-xs font-semibold text-[#41AA6C]">Claude Code / Cursor Config:</div>
              <pre className="p-3 rounded-lg bg-black text-[11px] font-mono text-emerald-400 overflow-x-auto">
{`"mcpServers": {
  "openseo": {
    "command": "python",
    "args": ["-m", "src.mcp.server"],
    "env": { "AMAS_PROJECT_ID": "${activeProject?.project_id || "default"}" }
  }
}`}
              </pre>
            </div>
          </div>
        )}

        {/* SCREEN 17: SETTINGS & INTEGRATIONS */}
        {activeScreen === "settings" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-5 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-white">17. Project Settings & Integrations</h2>
            <div className="space-y-3">
              {[
                { name: "DataForSEO API", desc: "Tra cứu chỉ số Search Volume, KD% và SERP dữ liệu lớn", status: "Đã Kết Nối" },
                { name: "OpenRouter LLM", desc: "Định tuyến model Claude 3.5 Sonnet / GPT-4o sinh báo cáo", status: "Đã Kết Nối" },
                { name: "Google Search Console OAuth", desc: "Tự động đồng bộ Clicks & Impressions thực tế", status: "Đã Kết Nối" },
                { name: "Google Analytics 4 (GA4)", desc: "Đo lường chuyển đổi và đơn hàng Affiliate", status: "Đã Kết Nối" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between p-3.5 rounded-xl bg-[#0B0B14] border border-[#252538] text-xs">
                  <div>
                    <div className="font-semibold text-white">{item.name}</div>
                    <div className="text-[11px] text-[#94A3B8]">{item.desc}</div>
                  </div>
                  <span className="text-[10px] font-semibold text-[#41AA6C] px-2 py-0.5 rounded-full bg-[#41AA6C]/10 border border-[#41AA6C]/30">
                    {item.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* =================================================================== */}
      {/* DRAWER: 16. SAM AI ASSISTANT                                        */}
      {/* =================================================================== */}
      {isSamDrawerOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-md bg-[#0B0B14] border-l border-[#252538] h-full flex flex-col shadow-2xl p-5 text-white">
            <div className="flex items-center justify-between border-b border-[#252538] pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-[#41AA6C]/20 border border-[#41AA6C]/40 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-[#41AA6C]" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">SAM AI Assistant</h3>
                  <p className="text-[10px] text-[#94A3B8]">Trợ Lý SEO Dự Án {activeProject?.name}</p>
                </div>
              </div>
              <button
                onClick={() => setIsSamDrawerOpen(false)}
                className="text-[#94A3B8] hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Chat Message History */}
            <div className="flex-1 overflow-y-auto py-4 space-y-3 pr-1 text-xs">
              {samMessages.map((msg, i) => (
                <div
                  key={i}
                  className={`p-3 rounded-xl max-w-[85%] ${
                    msg.sender === "user"
                      ? "ml-auto bg-[#41AA6C] text-white"
                      : "mr-auto bg-[#12121E] border border-[#252538] text-slate-200"
                  }`}
                >
                  {msg.text}
                </div>
              ))}
              {isSamThinking && (
                <div className="mr-auto p-3 rounded-xl bg-[#12121E] border border-[#252538] text-xs text-[#94A3B8] flex items-center gap-2">
                  <RotateCw className="w-3.5 h-3.5 animate-spin text-[#41AA6C]" />
                  <span>SAM đang suy nghĩ...</span>
                </div>
              )}
            </div>

            {/* Chat Input */}
            <form onSubmit={handleSendSamMessage} className="pt-3 border-t border-[#252538] flex gap-2">
              <input
                type="text"
                value={samInput}
                onChange={(e) => setSamInput(e.target.value)}
                placeholder="Hỏi SAM về từ khóa, audit hoặc AI search..."
                className="flex-1 px-3 py-2 rounded-xl bg-[#12121E] border border-[#252538] text-xs text-white focus:outline-none focus:border-[#41AA6C]"
              />
              <button
                type="submit"
                disabled={!samInput.trim() || isSamThinking}
                className="px-3.5 py-2 rounded-xl bg-[#41AA6C] hover:bg-[#368f5b] text-white text-xs font-semibold cursor-pointer disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
