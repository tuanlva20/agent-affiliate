"use client";

import React, { useState, useRef, useEffect } from "react";
import { ChevronDown, Check, Plus, Search, FolderKanban } from "lucide-react";
import { useProject } from "@/context/ProjectContext";
import { CreateProjectModal } from "./CreateProjectModal";

export const ProjectSwitcher: React.FC = () => {
  const { projects, activeProject, setActiveProject } = useProject();
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredProjects = projects.filter((p) =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.project_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const shortenId = (id: string) => {
    if (id.length <= 14) return id;
    return `${id.slice(0, 12)}...`;
  };

  return (
    <>
      <div className="relative" ref={dropdownRef}>
        {/* Trigger Button - Google Cloud Console Style */}
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-[#12121E] hover:bg-[#181828] border border-[#252538] hover:border-[#41AA6C]/40 text-left transition-all duration-150 cursor-pointer max-w-[280px]"
        >
          <div className="w-6 h-6 rounded-lg bg-[#41AA6C]/10 border border-[#41AA6C]/30 flex items-center justify-center shrink-0">
            <FolderKanban className="w-3.5 h-3.5 text-[#41AA6C]" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold text-white truncate">
                {activeProject ? activeProject.name : "Chọn Project"}
              </span>
            </div>
            <div className="text-[10px] text-[#94A3B8] font-mono truncate">
              {activeProject ? shortenId(activeProject.project_id) : "Chưa chọn"}
            </div>
          </div>
          <ChevronDown
            className={`w-3.5 h-3.5 text-[#94A3B8] transition-transform duration-200 shrink-0 ${
              isOpen ? "rotate-180 text-white" : ""
            }`}
          />
        </button>

        {/* Dropdown Menu */}
        {isOpen && (
          <div className="absolute left-0 mt-2 w-80 rounded-2xl bg-[#0B0B14] border border-[#252538] shadow-2xl p-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
            {/* Search Box */}
            <div className="relative mb-2">
              <Search className="w-3.5 h-3.5 text-[#94A3B8] absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Tìm nhanh project..."
                className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-[#12121E] border border-[#252538] focus:border-[#41AA6C] text-xs text-white placeholder-[#94A3B8] focus:outline-none transition-all duration-150"
                autoFocus
              />
            </div>

            {/* Project List */}
            <div className="max-h-60 overflow-y-auto space-y-1 pr-1">
              {filteredProjects.length === 0 ? (
                <div className="py-4 text-center text-xs text-[#94A3B8]">
                  Không tìm thấy project nào
                </div>
              ) : (
                filteredProjects.map((p) => {
                  const isSelected = activeProject?.project_id === p.project_id;
                  return (
                    <button
                      key={p.project_id}
                      type="button"
                      onClick={() => {
                        setActiveProject(p);
                        setIsOpen(false);
                      }}
                      className={`w-full flex items-center justify-between p-2 rounded-xl text-left transition-all duration-150 cursor-pointer ${
                        isSelected
                          ? "bg-[#41AA6C]/10 border border-[#41AA6C]/30 text-white"
                          : "hover:bg-white/5 border border-transparent text-slate-300"
                      }`}
                    >
                      <div className="min-w-0 flex-1 mr-2">
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-medium text-white truncate">{p.name}</span>
                          {p.niche_brief && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-[#181828] text-[#94A3B8] border border-[#252538] shrink-0">
                              Ngách
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-[#94A3B8] font-mono truncate">
                          {p.project_id}
                        </div>
                      </div>
                      {isSelected && (
                        <Check className="w-4 h-4 text-[#41AA6C] shrink-0" />
                      )}
                    </button>
                  );
                })
              )}
            </div>

            {/* Divider */}
            <div className="my-2 border-t border-[#252538]" />

            {/* Create Project Button */}
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                setIsModalOpen(true);
              }}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-[#41AA6C] hover:bg-[#368f5b] text-white text-xs font-semibold transition-all duration-150 shadow-sm cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Tạo Project Mới</span>
            </button>
          </div>
        )}
      </div>

      {/* Modal */}
      <CreateProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </>
  );
};
