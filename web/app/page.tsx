"use client";

import React, { useState } from "react";
import { Header, NavTabType } from "@/components/Header";
import { MotionStudio } from "@/components/MotionStudio";
import { ChannelsManager } from "@/components/ChannelsManager";
import { HistoryHub } from "@/components/HistoryHub";
import { ContentCalendarTab } from "@/components/ContentCalendarTab";
import { GroupSeedingTab } from "@/components/GroupSeedingTab";
import { ProjectProvider, useProject } from "@/context/ProjectContext";

function MainContent() {
  const [activeTab, setActiveTab] = useState<NavTabType>("studio");
  const [selectedReferenceUrl, setSelectedReferenceUrl] = useState<string | null>(null);
  const { activeProject } = useProject();

  const handleSelectMotionReference = (videoUrl: string) => {
    setSelectedReferenceUrl(videoUrl);
    setActiveTab("studio");
  };

  return (
    <div className="min-h-screen bg-[#000000] text-[#F8FAFC]">
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === "studio" && (
          <MotionStudio
            key={activeProject?.project_id}
            initialVideoUrl={selectedReferenceUrl || undefined}
          />
        )}
        {activeTab === "channels" && (
          <ChannelsManager key={activeProject?.project_id} />
        )}
        {activeTab === "history" && (
          <HistoryHub
            key={activeProject?.project_id}
            onSelectMotionReference={handleSelectMotionReference}
          />
        )}
        {activeTab === "calendar" && (
          <ContentCalendarTab key={activeProject?.project_id} />
        )}
        {activeTab === "seeding" && (
          <GroupSeedingTab key={activeProject?.project_id} />
        )}
        {activeTab === "openseo" && (
          <div className="p-8 text-center bg-[#12121E] border border-[#252538] rounded-2xl">
            <h3 className="text-base font-bold text-white mb-2">OpenSEO Suite</h3>
            <p className="text-xs text-[#94A3B8]">Phân hệ SEO Website 17 màn hình (Phase 7.2) đang sẵn sàng kết nối.</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <ProjectProvider>
      <MainContent />
    </ProjectProvider>
  );
}
