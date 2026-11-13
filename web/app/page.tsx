"use client";

import React, { useState } from "react";
import { Header } from "@/components/Header";
import { MotionStudio } from "@/components/MotionStudio";
import { ChannelsManager } from "@/components/ChannelsManager";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"studio" | "channels" | "history">("studio");

  return (
    <div className="min-h-screen bg-[#000000] text-[#F8FAFC]">
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === "studio" && <MotionStudio />}
        {activeTab === "channels" && <ChannelsManager />}

        {activeTab === "history" && (
          <div className="bg-[#12121E] border border-[#252538] rounded-2xl p-12 text-center text-[#94A3B8]">
            <p className="text-base font-medium text-white mb-1">Tab 3: Lịch sử Đăng & Đối thủ</p>
            <p className="text-sm">Đang được chuẩn bị cho sprint tiếp theo.</p>
          </div>
        )}
      </main>
    </div>
  );
}
