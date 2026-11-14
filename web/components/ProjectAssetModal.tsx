"use client";
/* eslint-disable @next/next/no-img-element */

import React, { useState, useEffect, useRef } from "react";
import {
  X,
  Upload,
  User,
  ShoppingBag,
  Sparkles,
  Check,
  Trash2,
  Search,
  Plus,
  Image as ImageIcon,
  FolderKanban,
  CheckCircle2,
} from "lucide-react";
import { useProject } from "@/context/ProjectContext";

export type AssetCategory = "model" | "background" | "product";

export interface ProjectAsset {
  id: string;
  projectId: string;
  category: AssetCategory;
  name: string;
  description: string;
  imageUrl: string;
  tags?: string[];
  isCustom?: boolean;
  createdAt?: string;
}

interface ProjectAssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialCategory?: AssetCategory;
  currentSelectedId?: {
    model?: string;
    background?: string;
    product?: string;
  };
  onSelectAsset: (asset: ProjectAsset) => void;
}

// Preset assets per niche project
const DEFAULT_PRESET_ASSETS: Record<string, ProjectAsset[]> = {
  proj_fashion_genz: [
    // Models
    {
      id: "model_hoaimy",
      projectId: "proj_fashion_genz",
      category: "model",
      name: "Hoài My (KOC)",
      description: "Tone da sáng, dáng chuẩn Châu Á, phong cách năng động GenZ",
      imageUrl: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&auto=format&fit=crop&q=80",
      tags: ["Nữ", "GenZ", "18-24", "Tone sáng"],
    },
    {
      id: "model_linhchi",
      projectId: "proj_fashion_genz",
      category: "model",
      name: "Linh Chi (KOC)",
      description: "Gương mặt thanh tú, phong cách công sở trẻ và lookbook thanh lịch",
      imageUrl: "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=500&auto=format&fit=crop&q=80",
      tags: ["Nữ", "Công sở", "Thanh lịch"],
    },
    {
      id: "model_namminh",
      projectId: "proj_fashion_genz",
      category: "model",
      name: "Nam Minh (KOC)",
      description: "Nam tính tươi trẻ, phong cách streetwear unisex cá tính",
      imageUrl: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500&auto=format&fit=crop&q=80",
      tags: ["Nam", "Streetwear", "Cá tính"],
    },
    // Backgrounds
    {
      id: "bg_studio_y2k",
      projectId: "proj_fashion_genz",
      category: "background",
      name: "Studio Y2K Tối Giản",
      description: "Ánh sáng tự nhiên, phông nền xám pastel hiện đại, góc quay 4K",
      imageUrl: "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=500&auto=format&fit=crop&q=80",
      tags: ["Studio", "Y2K", "Pastel", "4K"],
    },
    {
      id: "bg_living_scandi",
      projectId: "proj_fashion_genz",
      category: "background",
      name: "Phòng Khách Scandi Gỗ Ấm",
      description: "Tone gỗ sáng, rèm voan mỏng đón nắng ven ban công, góc nhìn thoáng",
      imageUrl: "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=500&auto=format&fit=crop&q=80",
      tags: ["Scandi", "Tự nhiên", "Ánh sáng ấm"],
    },
    {
      id: "bg_street_cafe",
      projectId: "proj_fashion_genz",
      category: "background",
      name: "Góc Phố Cafe Ngoại Cảnh",
      description: "Góc phố hiện đại, hiệu ứng bokeh xóa phông điện ảnh chân thực",
      imageUrl: "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=500&auto=format&fit=crop&q=80",
      tags: ["Ngoại cảnh", "Cafe", "Bokeh"],
    },
    // Products
    {
      id: "prod_dress_a",
      projectId: "proj_fashion_genz",
      category: "product",
      name: "Đầm Lụa Chữ A Che Bụng",
      description: "Vải lụa tuyết mịn màng, form dáng tôn eo, giấu trọn khuyết điểm",
      imageUrl: "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=500&auto=format&fit=crop&q=80",
      tags: ["Đầm váy", "Che bụng", "Affiliate Hot"],
    },
    {
      id: "prod_blazer_crop",
      projectId: "proj_fashion_genz",
      category: "product",
      name: "Áo Blazer Cropped Hàn Quốc",
      description: "Vải tuyết mưa 2 lớp đứng phom, phối chân váy chữ A hoặc quần suông",
      imageUrl: "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=500&auto=format&fit=crop&q=80",
      tags: ["Áo khoác", "Hàn Quốc", "Công sở"],
    },
    {
      id: "prod_jeans_wide",
      projectId: "proj_fashion_genz",
      category: "product",
      name: "Quần Jeans Ống Rộng Cạp Cao",
      description: "Denim cotton wash mềm mại, hiệu ứng kéo dài chân hack dáng",
      imageUrl: "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=80",
      tags: ["Quần jeans", "Hack dáng", "Streetwear"],
    },
  ],
  proj_smart_home: [
    // Models
    {
      id: "model_minhquan",
      projectId: "proj_smart_home",
      category: "model",
      name: "Minh Quân (KOC)",
      description: "KOC gia đình thông minh, chia sẻ mẹo vặt chân thật và tin cậy",
      imageUrl: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=500&auto=format&fit=crop&q=80",
      tags: ["Nam", "Gia đình", "Chân thật"],
    },
    {
      id: "model_thutrang",
      projectId: "proj_smart_home",
      category: "model",
      name: "Thu Trang (KOC)",
      description: "Mẹ bỉm hiện đại, phong cách đánh giá sản phẩm tiện ích tỉ mỉ",
      imageUrl: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=500&auto=format&fit=crop&q=80",
      tags: ["Nữ", "Nội trợ", "Tiện ích"],
    },
    // Backgrounds
    {
      id: "bg_smart_kitchen",
      projectId: "proj_smart_home",
      category: "background",
      name: "Gian Bếp Hiện Đại Tiện Nghi",
      description: "Bàn đá thạch anh trắng, tủ bếp thông minh sạch sẽ, ánh sáng trung thực",
      imageUrl: "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?w=500&auto=format&fit=crop&q=80",
      tags: ["Nhà bếp", "Tiện nghi", "Sạch sẽ"],
    },
    {
      id: "bg_clean_living",
      projectId: "proj_smart_home",
      category: "background",
      name: "Phòng Khách Gia Đình Tối Giản",
      description: "Không gian sinh hoạt ngăn nắp, tone màu xám trắng thanh lịch",
      imageUrl: "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=500&auto=format&fit=crop&q=80",
      tags: ["Phòng khách", "Gọn gàng", "Ấm cúng"],
    },
    // Products
    {
      id: "prod_air_fryer",
      projectId: "proj_smart_home",
      category: "product",
      name: "Nồi Chiên Không Dầu Điện Tử 6L",
      description: "Mặt kính trong suốt quan sát thực phẩm, công nghệ đối lưu 360 độ",
      imageUrl: "https://images.unsplash.com/photo-1585515320310-259814833e62?w=500&auto=format&fit=crop&q=80",
      tags: ["Gia dụng", "Bếp", "Hot TikTok"],
    },
    {
      id: "prod_vacuum_handheld",
      projectId: "proj_smart_home",
      category: "product",
      name: "Máy Hút Bụi Mini Cầm Tay Không Dây",
      description: "Lực hút 12000Pa, pin sạc Type-C tiện lợi cho sofa và góc hẹp",
      imageUrl: "https://images.unsplash.com/photo-1558317374-067fb5f30001?w=500&auto=format&fit=crop&q=80",
      tags: ["Hút bụi", "Không dây", "Tiện ích"],
    },
  ],
};

// Generic fallback assets if project has no specialized presets
const GENERIC_ASSETS: ProjectAsset[] = [
  {
    id: "gen_model_1",
    projectId: "default",
    category: "model",
    name: "Hoài My (KOC)",
    description: "Tone da sáng, dáng chuẩn Châu Á, phong cách năng động",
    imageUrl: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&auto=format&fit=crop&q=80",
    tags: ["KOC", "Tone sáng"],
  },
  {
    id: "gen_bg_1",
    projectId: "default",
    category: "background",
    name: "Studio Y2K Tối Giản",
    description: "Ánh sáng tự nhiên, góc quay 4K, phông nền xám pastel",
    imageUrl: "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=500&auto=format&fit=crop&q=80",
    tags: ["Studio", "4K"],
  },
  {
    id: "gen_prod_1",
    projectId: "default",
    category: "product",
    name: "Đầm Lụa Chữ A Che Bụng",
    description: "Vải lụa tuyết mịn màng, form dáng tôn eo, giấu khuyết điểm",
    imageUrl: "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=500&auto=format&fit=crop&q=80",
    tags: ["Sản phẩm", "TikTok Shop"],
  },
];

export const ProjectAssetModal: React.FC<ProjectAssetModalProps> = ({
  isOpen,
  onClose,
  initialCategory = "model",
  currentSelectedId,
  onSelectAsset,
}) => {
  const { activeProject } = useProject();
  const projectId = activeProject?.project_id || "proj_fashion_genz";
  const projectName = activeProject?.name || "Dự án hiện tại";

  const [activeCategory, setActiveCategory] = useState<AssetCategory>(initialCategory);
  const [activeTab, setActiveTab] = useState<"library" | "upload">("library");
  const [searchTerm, setSearchTerm] = useState("");

  // Upload Form State
  const [uploadName, setUploadName] = useState("");
  const [uploadDesc, setUploadDesc] = useState("");
  const [uploadImagePreview, setUploadImagePreview] = useState<string | null>(null);
  const [uploadTag, setUploadTag] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Custom Assets stored in localStorage per project
  const [customAssets, setCustomAssets] = useState<ProjectAsset[]>([]);

  // Sync category when initialCategory changes
  useEffect(() => {
    if (initialCategory) {
      setActiveCategory(initialCategory);
    }
  }, [initialCategory]);

  // Load custom assets from localStorage when projectId changes
  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem(`amas_assets_${projectId}`);
        if (stored) {
          setCustomAssets(JSON.parse(stored));
        } else {
          setCustomAssets([]);
        }
      } catch (e) {
        console.error("Failed to load custom assets from localStorage:", e);
      }
    }
  }, [projectId]);

  // Save custom assets to localStorage
  const saveCustomAssets = (assets: ProjectAsset[]) => {
    setCustomAssets(assets);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(`amas_assets_${projectId}`, JSON.stringify(assets));
      } catch (e) {
        console.error("Failed to save custom assets to localStorage:", e);
      }
    }
  };

  if (!isOpen) return null;

  // Combine preset assets with custom assets
  const presetList =
    DEFAULT_PRESET_ASSETS[projectId] ||
    DEFAULT_PRESET_ASSETS["proj_fashion_genz"] ||
    GENERIC_ASSETS;

  const allAssets: ProjectAsset[] = [
    ...customAssets.filter((a) => a.projectId === projectId),
    ...presetList,
  ];

  // Filter by category and search term
  const categoryAssets = allAssets.filter((a) => a.category === activeCategory);
  const filteredAssets = categoryAssets.filter(
    (a) =>
      a.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.tags?.some((t) => t.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Handle direct file upload selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith("image/")) {
        alert("Vui lòng chọn file hình ảnh (PNG, JPG, WEBP).");
        return;
      }
      const reader = new FileReader();
      reader.onload = (event) => {
        setUploadImagePreview(event.target?.result as string);
        if (!uploadName) {
          // Default name based on file name
          const cleanName = file.name.replace(/\.[^/.]+$/, "");
          setUploadName(cleanName);
        }
      };
      reader.readAsDataURL(file);
    }
  };

  // Handle saving new uploaded asset
  const handleSaveUpload = () => {
    if (!uploadImagePreview) {
      alert("Vui lòng tải lên một hình ảnh trước khi lưu.");
      return;
    }
    if (!uploadName.trim()) {
      alert("Vui lòng nhập tên tài nguyên.");
      return;
    }

    setIsSaving(true);
    const newAsset: ProjectAsset = {
      id: `custom_${activeCategory}_${Date.now()}`,
      projectId: projectId,
      category: activeCategory,
      name: uploadName.trim(),
      description: uploadDesc.trim() || `Tài nguyên tải lên trực tiếp cho ${activeCategory}`,
      imageUrl: uploadImagePreview,
      tags: uploadTag ? uploadTag.split(",").map((t) => t.trim()).filter(Boolean) : ["Tải lên"],
      isCustom: true,
      createdAt: new Date().toISOString(),
    };

    const updated = [newAsset, ...customAssets];
    saveCustomAssets(updated);

    // Auto-select and close
    onSelectAsset(newAsset);
    setIsSaving(false);
    onClose();

    // Reset upload form
    setUploadImagePreview(null);
    setUploadName("");
    setUploadDesc("");
    setUploadTag("");
  };

  // Delete custom asset
  const handleDeleteCustomAsset = (assetId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("Bạn có chắc chắn muốn xóa tài nguyên này khỏi dự án?")) {
      const updated = customAssets.filter((a) => a.id !== assetId);
      saveCustomAssets(updated);
    }
  };

  const categoryLabels = {
    model: {
      title: "Hình Mẫu / KOC",
      icon: User,
      subtitle: "Gương mặt & hình thể mẫu biểu diễn chuyển động",
      emptyText: "Chưa có hình mẫu nào phù hợp",
    },
    background: {
      title: "Bối Cảnh / Studio",
      icon: Sparkles,
      subtitle: "Không gian, phòng quay và ánh sáng hậu cảnh",
      emptyText: "Chưa có bối cảnh nào phù hợp",
    },
    product: {
      title: "Sản Phẩm",
      icon: ShoppingBag,
      subtitle: "Sản phẩm affiliate (quần áo, đồ gia dụng, mỹ phẩm)",
      emptyText: "Chưa có sản phẩm nào phù hợp",
    },
  };

  const currentActiveId = currentSelectedId?.[activeCategory];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col bg-[#0B0B14] border border-[#252538] rounded-2xl shadow-2xl text-[#F8FAFC] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[#252538] bg-[#12121E]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#41AA6C]/10 border border-[#41AA6C]/30 flex items-center justify-center">
              <FolderKanban className="w-5 h-5 text-[#41AA6C]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-tight">Thư Viện Tài Nguyên Dự Án</h2>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#41AA6C]/15 text-[#41AA6C] font-medium border border-[#41AA6C]/30">
                  {projectName}
                </span>
              </div>
              <p className="text-xs text-[#94A3B8] mt-0.5">
                Quản lý hình mẫu KOC, bối cảnh studio và sản phẩm lưu riêng cho dự án này
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-[#94A3B8] hover:text-white hover:bg-white/5 transition-all duration-150 cursor-pointer"
            aria-label="Đóng"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Category Tabs (Model, Background, Product) */}
        <div className="flex items-center justify-between px-5 pt-4 pb-2 border-b border-[#252538] bg-[#0E0E18]">
          <div className="flex gap-2">
            {(["model", "background", "product"] as AssetCategory[]).map((cat) => {
              const cfg = categoryLabels[cat];
              const Icon = cfg.icon;
              const isActive = activeCategory === cat;
              return (
                <button
                  key={cat}
                  onClick={() => {
                    setActiveCategory(cat);
                    setSearchTerm("");
                  }}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-150 cursor-pointer ${
                    isActive
                      ? "bg-[#41AA6C] text-white shadow-sm shadow-[#41AA6C]/25"
                      : "bg-[#181828] text-[#94A3B8] hover:text-white hover:bg-[#202035] border border-[#252538]"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{cfg.title}</span>
                </button>
              );
            })}
          </div>

          {/* Sub-view switcher: Thư viện vs Tải lên trực tiếp */}
          <div className="flex items-center bg-[#12121E] border border-[#252538] rounded-xl p-1">
            <button
              onClick={() => setActiveTab("library")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 cursor-pointer ${
                activeTab === "library"
                  ? "bg-[#41AA6C]/20 text-[#41AA6C] font-semibold"
                  : "text-[#94A3B8] hover:text-white"
              }`}
            >
              Thư viện dự án ({categoryAssets.length})
            </button>
            <button
              onClick={() => setActiveTab("upload")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 cursor-pointer ${
                activeTab === "upload"
                  ? "bg-[#41AA6C]/20 text-[#41AA6C] font-semibold"
                  : "text-[#94A3B8] hover:text-white"
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              <span>+ Tải lên mới</span>
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {activeTab === "library" ? (
            <>
              {/* Search & Description Bar */}
              <div className="flex items-center justify-between gap-3">
                <div className="relative flex-1 max-w-sm">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94A3B8]" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder={`Tìm kiếm ${categoryLabels[activeCategory].title.toLowerCase()}...`}
                    className="w-full bg-[#12121E] border border-[#252538] rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-[#94A3B8]/60 focus:outline-none focus:border-[#41AA6C] transition-all duration-150"
                  />
                </div>
                <div className="text-xs text-[#94A3B8]">
                  {categoryLabels[activeCategory].subtitle}
                </div>
              </div>

              {/* Grid of Assets */}
              {filteredAssets.length === 0 ? (
                <div className="border border-dashed border-[#252538] rounded-2xl p-10 text-center space-y-3">
                  <div className="w-12 h-12 rounded-full bg-[#181828] text-[#94A3B8] mx-auto flex items-center justify-center">
                    <ImageIcon className="w-6 h-6" />
                  </div>
                  <p className="text-sm font-medium text-slate-300">
                    {categoryLabels[activeCategory].emptyText}
                  </p>
                  <p className="text-xs text-[#94A3B8]">
                    Bạn có thể tải lên hình ảnh mới cho dự án {projectName} ngay lập tức.
                  </p>
                  <button
                    onClick={() => setActiveTab("upload")}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#41AA6C] hover:bg-[#34925b] text-white text-xs font-semibold rounded-xl transition-all duration-150 cursor-pointer"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Tải lên {categoryLabels[activeCategory].title} mới</span>
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  {filteredAssets.map((asset) => {
                    const isSelected = currentActiveId === asset.id || currentActiveId === asset.name;
                    return (
                      <div
                        key={asset.id}
                        className={`group relative rounded-xl border p-3 flex flex-col justify-between bg-[#12121E] transition-all duration-200 ${
                          isSelected
                            ? "border-[#41AA6C] shadow-md shadow-[#41AA6C]/15 bg-[#12121E]"
                            : "border-[#252538] hover:border-slate-600 hover:bg-[#161625]"
                        }`}
                      >
                        <div>
                          {/* Image Thumbnail */}
                          <div className="relative aspect-video w-full rounded-lg bg-[#000000] border border-[#252538] overflow-hidden mb-3">
                            <img
                              src={asset.imageUrl}
                              alt={asset.name}
                              className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                              onError={(e) => {
                                // Fallback for image error
                                (e.target as HTMLElement).style.display = "none";
                              }}
                            />
                            {isSelected && (
                              <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-[#41AA6C] text-white text-[10px] font-bold flex items-center gap-1 shadow-sm">
                                <Check className="w-3 h-3" /> Đang dùng
                              </div>
                            )}
                            {asset.isCustom && (
                              <div className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-indigo-600/90 text-white text-[10px] font-semibold">
                                Tự tải lên
                              </div>
                            )}
                          </div>

                          {/* Info */}
                          <h4 className="text-sm font-semibold text-white group-hover:text-[#41AA6C] transition-colors truncate">
                            {asset.name}
                          </h4>
                          <p className="text-xs text-[#94A3B8] line-clamp-2 mt-1 min-h-[32px]">
                            {asset.description}
                          </p>

                          {/* Tag chips */}
                          {asset.tags && asset.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2.5">
                              {asset.tags.map((t, i) => (
                                <span
                                  key={i}
                                  className="text-[10px] px-2 py-0.5 rounded bg-[#181828] text-slate-300 border border-[#252538]"
                                >
                                  {t}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Action buttons */}
                        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-[#252538]">
                          <button
                            onClick={() => {
                              onSelectAsset(asset);
                              onClose();
                            }}
                            className={`flex-1 py-1.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all duration-150 cursor-pointer ${
                              isSelected
                                ? "bg-[#41AA6C]/15 text-[#41AA6C] border border-[#41AA6C]/30 hover:bg-[#41AA6C]/25"
                                : "bg-[#181828] hover:bg-[#41AA6C] text-slate-200 hover:text-white border border-[#252538] hover:border-[#41AA6C]"
                            }`}
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>{isSelected ? "Đã Chọn" : "Chọn Áp Dụng"}</span>
                          </button>

                          {asset.isCustom && (
                            <button
                              onClick={(e) => handleDeleteCustomAsset(asset.id, e)}
                              title="Xóa tài nguyên này"
                              className="p-1.5 rounded-lg bg-[#181828] text-[#94A3B8] hover:text-rose-400 hover:bg-rose-500/10 border border-[#252538] transition-all duration-150 cursor-pointer"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          ) : (
            /* Upload View */
            <div className="max-w-xl mx-auto space-y-4">
              <div className="text-center pb-2">
                <h3 className="text-sm font-bold text-white">
                  Tải Lên {categoryLabels[activeCategory].title} Mới
                </h3>
                <p className="text-xs text-[#94A3B8] mt-0.5">
                  Hình ảnh sẽ được lưu trữ an toàn trong dự án <span className="text-[#41AA6C] font-semibold">{projectName}</span>
                </p>
              </div>

              {/* Upload Dropzone */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-[#252538] hover:border-[#41AA6C] rounded-2xl p-6 text-center bg-[#12121E] hover:bg-[#151524] transition-all duration-200 cursor-pointer group"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  className="hidden"
                />

                {uploadImagePreview ? (
                  <div className="space-y-3">
                    <div className="relative aspect-video max-w-sm mx-auto rounded-xl overflow-hidden border border-[#252538]">
                      <img
                        src={uploadImagePreview}
                        alt="Preview"
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <p className="text-xs text-[#41AA6C] font-medium">
                      Nhấp để chọn hình ảnh khác
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2 py-4">
                    <div className="w-12 h-12 rounded-xl bg-[#41AA6C]/10 text-[#41AA6C] mx-auto flex items-center justify-center group-hover:scale-110 transition-transform duration-200">
                      <Upload className="w-6 h-6" />
                    </div>
                    <div className="text-sm font-semibold text-white">
                      Nhấp để tải ảnh lên hoặc kéo thả vào đây
                    </div>
                    <p className="text-xs text-[#94A3B8]">
                      Hỗ trợ định dạng PNG, JPG, WEBP dung lượng tối đa 10MB
                    </p>
                  </div>
                )}
              </div>

              {/* Form Inputs */}
              <div className="space-y-3 bg-[#12121E] border border-[#252538] rounded-xl p-4">
                <div>
                  <label className="text-xs font-semibold text-slate-200 mb-1.5 block">
                    Tên {categoryLabels[activeCategory].title} <span className="text-[#41AA6C]">*</span>
                  </label>
                  <input
                    type="text"
                    value={uploadName}
                    onChange={(e) => setUploadName(e.target.value)}
                    placeholder={`VD: ${
                      activeCategory === "model"
                        ? "Mẫu Phương Anh - KOC V-Line"
                        : activeCategory === "background"
                        ? "Studio Japandi Tone Gỗ Ấm"
                        : "Đầm Bodycon Ôm Dáng Sát Nách"
                    }`}
                    className="w-full px-3 py-2 rounded-lg bg-[#000000] border border-[#252538] focus:border-[#41AA6C] text-xs text-white focus:outline-none transition-all duration-150"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-200 mb-1.5 block">
                    Mô tả đặc điểm & ghi chú Prompt AI
                  </label>
                  <textarea
                    rows={2}
                    value={uploadDesc}
                    onChange={(e) => setUploadDesc(e.target.value)}
                    placeholder={`VD: ${
                      activeCategory === "model"
                        ? "Gương mặt trẻ trung, da sáng, nụ cười rạng rỡ, thích hợp đồ năng động"
                        : activeCategory === "background"
                        ? "Ánh sáng ven cửa sổ, không gian studio tối giản, tông màu ấm cúng"
                        : "Vải co giãn cao cấp, đường may tỉ mỉ, khóa kéo giọt nước"
                    }`}
                    className="w-full px-3 py-2 rounded-lg bg-[#000000] border border-[#252538] focus:border-[#41AA6C] text-xs text-white focus:outline-none transition-all duration-150"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-200 mb-1.5 block">
                    Thẻ phân loại (ngăn cách bằng dấu phẩy)
                  </label>
                  <input
                    type="text"
                    value={uploadTag}
                    onChange={(e) => setUploadTag(e.target.value)}
                    placeholder="VD: GenZ, Hot TikTok, Mới tải lên"
                    className="w-full px-3 py-2 rounded-lg bg-[#000000] border border-[#252538] focus:border-[#41AA6C] text-xs text-white focus:outline-none transition-all duration-150"
                  />
                </div>

                {/* Submit button */}
                <div className="pt-2 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setActiveTab("library")}
                    className="px-4 py-2 rounded-xl text-xs font-medium text-[#94A3B8] hover:text-white bg-[#181828] border border-[#252538] transition-all duration-150 cursor-pointer"
                  >
                    Hủy bỏ
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveUpload}
                    disabled={isSaving || !uploadImagePreview || !uploadName.trim()}
                    className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-xs font-semibold text-white bg-[#41AA6C] hover:bg-[#34925b] shadow-sm shadow-[#41AA6C]/25 transition-all duration-150 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Check className="w-4 h-4" />
                    <span>Lưu vào Dự Án & Áp Dụng Ngay</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
