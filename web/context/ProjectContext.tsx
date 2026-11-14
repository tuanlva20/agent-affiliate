"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

export interface Project {
  project_id: string;
  name: string;
  niche_brief?: string | null;
  target_audience?: string | null;
  tone_of_voice?: string | null;
  trigger_keywords?: string[] | null;
  negative_keywords?: string[] | null;
  website_url?: string | null;
  created_at?: string;
}

export interface PresetItem {
  id: string;
  name: string;
  niche_brief: string;
  target_audience: string;
  tone_of_voice: string;
  trigger_keywords: string[];
  negative_keywords: string[];
}

interface ProjectContextType {
  projects: Project[];
  activeProject: Project | null;
  setActiveProject: (project: Project) => void;
  createProject: (data: Partial<Project>) => Promise<Project>;
  refreshProjects: () => Promise<void>;
  isLoading: boolean;
  presets: PresetItem[];
}

const FALLBACK_PROJECTS: Project[] = [
  {
    project_id: "proj_fashion_genz",
    name: "Thời Trang GenZ",
    niche_brief: "Thời trang GenZ xu hướng Y2K, đồ công sở trẻ và phong cách đường phố (streetwear)",
    target_audience: "Nữ giới 18-26 tuổi, học sinh, sinh viên và người mới đi làm",
    tone_of_voice: "GenZ gần gũi, hài hước, bắt trend TikTok, dùng từ ngữ thân thuộc",
    trigger_keywords: ["váy xinh", "outfit", "set đồ", "phối đồ", "áo thun form rộng"],
    negative_keywords: ["hàng lỗi", "vải mỏng rách", "kém chất lượng", "lừa đảo"],
    website_url: "https://thoitranggenz.vn",
  },
  {
    project_id: "proj_smart_home",
    name: "Đồ Gia Dụng Tiện Ích",
    niche_brief: "Đồ gia dụng thông minh, giải pháp tiện ích cho nhà bếp và không gian sống gọn gàng",
    target_audience: "Người nội trợ, gia đình trẻ và dân văn phòng từ 24-42 tuổi",
    tone_of_voice: "Chuyên gia uy tín, đánh giá thực tế, chân thành, tập trung tính ứng dụng",
    trigger_keywords: ["tiện ích", "thông minh", "máy hút bụi", "nồi chiên không dầu", "hộp đựng thực phẩm"],
    negative_keywords: ["hàng dỏm", "cháy nổ", "nhanh hỏng", "hàng nhái"],
    website_url: "https://giadungtienich.vn",
  },
];

export const FALLBACK_PRESETS: PresetItem[] = [
  {
    id: "preset_fashion_genz",
    name: "Thời Trang GenZ",
    niche_brief: "Thời trang GenZ xu hướng Y2K, đồ công sở trẻ và phong cách đường phố (streetwear)",
    target_audience: "Nữ giới 18-26 tuổi, học sinh, sinh viên và người mới đi làm",
    tone_of_voice: "GenZ gần gũi, hài hước, bắt trend TikTok, dùng từ ngữ thân thuộc",
    trigger_keywords: ["váy xinh", "outfit", "set đồ", "phối đồ", "áo thun form rộng"],
    negative_keywords: ["hàng lỗi", "vải mỏng rách", "kém chất lượng", "lừa đảo"],
  },
  {
    id: "preset_smart_home",
    name: "Đồ Gia Dụng Tiện Ích",
    niche_brief: "Đồ gia dụng thông minh, giải pháp tiện ích cho nhà bếp và không gian sống gọn gàng",
    target_audience: "Người nội trợ, gia đình trẻ và dân văn phòng từ 24-42 tuổi",
    tone_of_voice: "Chuyên gia uy tín, đánh giá thực tế, chân thành, tập trung tính ứng dụng",
    trigger_keywords: ["tiện ích", "thông minh", "máy hút bụi", "nồi chiên không dầu", "hộp đựng thực phẩm"],
    negative_keywords: ["hàng dỏm", "cháy nổ", "nhanh hỏng", "hàng nhái"],
  },
  {
    id: "preset_beauty_skincare",
    name: "Mỹ Phẩm & Skincare",
    niche_brief: "Mỹ phẩm chăm sóc da khoa học, phục hồi da mụn, chống nắng và dưỡng sáng da",
    target_audience: "Nam & Nữ từ 18-35 tuổi quan tâm đến chăm sóc da an toàn",
    tone_of_voice: "Bác sĩ / Chuyên gia da liễu thân thiện, dẫn chứng thành phần khoa học (KOL/KOC uy tín)",
    trigger_keywords: ["da mụn", "serum B5", "kem chống nắng", "kiềm dầu", "phục hồi"],
    negative_keywords: ["kem trộn", "bong tróc", "bào mòn da", "rượu thuốc"],
  },
  {
    id: "preset_tech_accessories",
    name: "Phụ Kiện Công Nghệ",
    niche_brief: "Củ sạc nhanh, cáp sạc, tai nghe bluetooth, phụ kiện setup góc làm việc và gaming",
    target_audience: "Dân công nghệ, game thủ, sinh viên IT và dân văn phòng 18-32 tuổi",
    tone_of_voice: "KOC công nghệ nhiệt huyết, phân tích thông số kỹ thuật rõ ràng, dí dỏm",
    trigger_keywords: ["cáp sạc", "sạc nhanh 65W", "tai nghe chống ồn", "bàn phím cơ", "chuột không dây"],
    negative_keywords: ["hàng fake", "nổ pin", "nhanh cháy", "chập điện"],
  },
];

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export const ProjectProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [projects, setProjects] = useState<Project[]>(FALLBACK_PROJECTS);
  const [activeProject, setActiveProjectState] = useState<Project | null>(FALLBACK_PROJECTS[0]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [presets, setPresets] = useState<PresetItem[]>(FALLBACK_PRESETS);

  const refreshProjects = async () => {
    setIsLoading(true);
    try {
      const res = await fetch("/api/projects/");
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setProjects(data);
          setActiveProjectState((prev) => {
            if (!prev) return data[0];
            const found = data.find((p) => p.project_id === prev.project_id);
            return found || data[0];
          });
        }
      }
    } catch {
      // Keep fallbacks on offline
    } finally {
      setIsLoading(false);
    }
  };

  const fetchPresets = async () => {
    try {
      const res = await fetch("/api/projects/presets");
      if (res.ok) {
        const data = await res.json();
        if (data.presets && Array.isArray(data.presets)) {
          setPresets(data.presets);
        }
      }
    } catch {
      // Use fallback
    }
  };

  useEffect(() => {
    refreshProjects();
    fetchPresets();
  }, []);

  const setActiveProject = (project: Project) => {
    setActiveProjectState(project);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem("amas_active_project_id", project.project_id);
      } catch {
        // Ignore
      }
    }
  };

  const createProject = async (data: Partial<Project>): Promise<Project> => {
    try {
      const res = await fetch("/api/projects/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        const newProj = await res.json();
        setProjects((prev) => [newProj, ...prev]);
        setActiveProject(newProj);
        return newProj;
      }
    } catch {
      // Mock create locally
    }
    const mockNew: Project = {
      project_id: `proj_${Date.now()}`,
      name: data.name || "Dự Án Mới",
      niche_brief: data.niche_brief,
      target_audience: data.target_audience,
      tone_of_voice: data.tone_of_voice,
      trigger_keywords: data.trigger_keywords,
      negative_keywords: data.negative_keywords,
      website_url: data.website_url,
      created_at: new Date().toISOString(),
    };
    setProjects((prev) => [mockNew, ...prev]);
    setActiveProject(mockNew);
    return mockNew;
  };

  return (
    <ProjectContext.Provider
      value={{
        projects,
        activeProject,
        setActiveProject,
        createProject,
        refreshProjects,
        isLoading,
        presets,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
};

export const useProject = (): ProjectContextType => {
  const ctx = useContext(ProjectContext);
  if (!ctx) {
    throw new Error("useProject must be used within a ProjectProvider");
  }
  return ctx;
};
