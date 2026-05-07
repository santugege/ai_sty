export const imageSizes = ["1024x1024", "1536x1024", "1024x1536"] as const;

export type ImageSize = (typeof imageSizes)[number];
export type ToolId = "creator" | "restore" | "avatar" | "product";
export type ToolMode = "generate" | "edit";
export type ToolIcon = "sparkles" | "wand" | "user" | "package";

export type ImageTool = {
  id: ToolId;
  title: string;
  eyebrow: string;
  description: string;
  mode: ToolMode;
  icon: ToolIcon;
  accent: "teal" | "red" | "blue" | "gold";
  promptLabel: string;
  promptPlaceholder: string;
  promptRequired: boolean;
  imageRequired: boolean;
  imageLabel: string;
  defaultSize: ImageSize;
  sizeOptions: ImageSize[];
  examples: string[];
};

export const imageTools: ImageTool[] = [
  {
    id: "creator",
    title: "AI 图片创作",
    eyebrow: "Text to image",
    description: "输入画面描述，生成完整原创图片。",
    mode: "generate",
    icon: "sparkles",
    accent: "teal",
    promptLabel: "画面描述",
    promptPlaceholder:
      "例如：一间清晨阳光里的木质咖啡馆，窗边有绿植，写实摄影风格",
    promptRequired: true,
    imageRequired: false,
    imageLabel: "参考图",
    defaultSize: "1024x1024",
    sizeOptions: [...imageSizes],
    examples: ["写实摄影", "儿童绘本", "电影海报", "水彩插画"],
  },
  {
    id: "restore",
    title: "老照片修复",
    eyebrow: "Photo restoration",
    description: "修复划痕、褪色、模糊和年代感损伤。",
    mode: "edit",
    icon: "wand",
    accent: "red",
    promptLabel: "修复要求",
    promptPlaceholder:
      "例如：保留人物五官和年代感，修复划痕，提升清晰度，恢复自然色彩",
    promptRequired: false,
    imageRequired: true,
    imageLabel: "上传旧照片",
    defaultSize: "1024x1024",
    sizeOptions: [...imageSizes],
    examples: ["黑白上色", "划痕修复", "清晰增强", "褪色恢复"],
  },
  {
    id: "avatar",
    title: "头像/写真生成",
    eyebrow: "Portrait studio",
    description: "用参考图或风格描述生成头像、写真和社媒形象。",
    mode: "edit",
    icon: "user",
    accent: "blue",
    promptLabel: "头像风格",
    promptPlaceholder:
      "例如：商务头像，深色西装，自然微笑，干净灰色背景，柔和棚拍光",
    promptRequired: true,
    imageRequired: false,
    imageLabel: "上传参考图",
    defaultSize: "1024x1024",
    sizeOptions: ["1024x1024", "1024x1536"],
    examples: ["商务头像", "证件照风格", "社媒头像", "电影感写真"],
  },
  {
    id: "product",
    title: "商品图生成",
    eyebrow: "Product visuals",
    description: "为商品换背景、做场景图和电商展示图。",
    mode: "edit",
    icon: "package",
    accent: "gold",
    promptLabel: "商品场景",
    promptPlaceholder:
      "例如：保留商品外观，放在浅色石材台面上，背景是现代厨房，自然日光",
    promptRequired: false,
    imageRequired: true,
    imageLabel: "上传商品图",
    defaultSize: "1536x1024",
    sizeOptions: [...imageSizes],
    examples: ["白底图", "生活方式场景", "节日背景", "电商主图"],
  },
];

export function getToolById(id: string): ImageTool | undefined {
  return imageTools.find((tool) => tool.id === id);
}
