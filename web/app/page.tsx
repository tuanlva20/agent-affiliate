"use client";

import React, { useState } from "react";
import { Header, NavTabType } from "@/components/Header";
import { MotionStudio } from "@/components/MotionStudio";
import { ChannelsManager } from "@/components/ChannelsManager";
import { HistoryHub } from "@/components/HistoryHub";
import { ContentCalendarTab } from "@/components/ContentCalendarTab";
import { GroupSeedingTab } from "@/components/GroupSeedingTab";
import { OpenSEOTab } from "@/components/OpenSEOTab";
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

      <main className="w-full max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
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
          <OpenSEOTab key={activeProject?.project_id} />
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
