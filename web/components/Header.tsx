"use client";

import React from "react";
import { Clapperboard, Share2, History, Radio, Sparkles } from "lucide-react";
import { ProjectSwitcher } from "./ProjectSwitcher";

interface HeaderProps {
  activeTab: "studio" | "channels" | "history" | "calendar" | "seeding" | "openseo";
  setActiveTab: (tab: "studio" | "channels" | "history" | "calendar" | "seeding" | "openseo") => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab }) => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-[#252538] bg-[#000000]/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand + Project Switcher */}
        <div className="flex items-center gap-4 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#41AA6C]/10 border border-[#41AA6C]/30 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-[#41AA6C]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg tracking-tight text-white">AMAS</span>
                <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-[#41AA6C]/15 text-[#41AA6C] border border-[#41AA6C]/30">
                  v1.5.0 Studio
                </span>
              </div>
              <p className="text-[11px] text-[#94A3B8]">Workspace & Affiliate OS</p>
            </div>
          </div>

          {/* Project Switcher - Google Cloud Console style */}
          <div className="hidden md:block pl-2 border-l border-[#252538]">
            <ProjectSwitcher />
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-[#12121E] p-1 rounded-xl border border-[#252538] overflow-x-auto">
          <button
            onClick={() => setActiveTab("studio")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all duration-200 cursor-pointer shrink-0 ${
              activeTab === "studio"
                ? "bg-[#41AA6C] text-white shadow-sm"
                : "text-[#94A3B8] hover:text-white hover:bg-white/5"
            }`}
          >
            <Clapperboard className="w-4 h-4" />
            <span>Motion Studio</span>
          </button>

          <button
            onClick={() => setActiveTab("channels")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all duration-200 cursor-pointer shrink-0 ${
              activeTab === "channels"
                ? "bg-[#41AA6C] text-white shadow-sm"
                : "text-[#94A3B8] hover:text-white hover:bg-white/5"
            }`}
          >
            <Share2 className="w-4 h-4" />
            <span>Kênh & Proxy</span>
          </button>

          <button
            onClick={() => setActiveTab("history")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all duration-200 cursor-pointer shrink-0 ${
              activeTab === "history"
                ? "bg-[#41AA6C] text-white shadow-sm"
                : "text-[#94A3B8] hover:text-white hover:bg-white/5"
            }`}
          >
            <History className="w-4 h-4" />
            <span>Lịch sử & Đối thủ</span>
          </button>
        </nav>

        {/* Status Indicator */}
        <div className="hidden lg:flex items-center gap-2 text-xs text-[#94A3B8] bg-[#12121E] px-3 py-1.5 rounded-lg border border-[#252538] shrink-0">
          <Radio className="w-3.5 h-3.5 text-[#41AA6C] animate-pulse" />
          <span className="text-slate-300 font-medium">Replicate API</span>
          <span className="w-1.5 h-1.5 rounded-full bg-[#41AA6C]" />
        </div>
      </div>

      {/* Mobile Project Switcher Row */}
      <div className="md:hidden px-4 pb-2">
        <ProjectSwitcher />
      </div>
    </header>
  );
};
