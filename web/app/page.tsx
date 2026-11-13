"use client";

import React, { useState } from "react";
import { Header } from "@/components/Header";
import { MotionStudio } from "@/components/MotionStudio";
import { ChannelsManager } from "@/components/ChannelsManager";
import { HistoryHub } from "@/components/HistoryHub";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"studio" | "channels" | "history">("studio");
  const [selectedReferenceUrl, setSelectedReferenceUrl] = useState<string | null>(null);

  const handleSelectMotionReference = (videoUrl: string) => {
    setSelectedReferenceUrl(videoUrl);
    setActiveTab("studio");
  };

  return (
    <div className="min-h-screen bg-[#000000] text-[#F8FAFC]">
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === "studio" && (
          <MotionStudio initialVideoUrl={selectedReferenceUrl || undefined} />
        )}
        {activeTab === "channels" && <ChannelsManager />}
        {activeTab === "history" && (
          <HistoryHub onSelectMotionReference={handleSelectMotionReference} />
        )}
      </main>
    </div>
  );
}
