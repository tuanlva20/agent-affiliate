"use client";

import React, { useState } from "react";
import { Header } from "@/components/Header";
import { MotionStudio } from "@/components/MotionStudio";
import { ChannelsManager } from "@/components/ChannelsManager";
import { HistoryHub } from "@/components/HistoryHub";
import { ProjectProvider, useProject } from "@/context/ProjectContext";

function MainContent() {
  const [activeTab, setActiveTab] = useState<"studio" | "channels" | "history" | "calendar" | "seeding" | "openseo">("studio");
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
