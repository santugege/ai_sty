export const imageSizes = ["1024x1024", "1536x1024", "1024x1536"] as const;

export type ImageSize = (typeof imageSizes)[number];
export type ToolId = "product";

export type ImageTool = {
  id: ToolId;
  title: string;
  description: string;
  defaultSize: ImageSize;
  sizeOptions: ImageSize[];
};

export type ProductPlatformStyleId =
  | "pinduoduo"
  | "taobao-tmall"
  | "jd"
  | "xiaohongshu"
  | "douyin";

export type ProductImagePurposeId =
  | "main-image"
  | "white-background"
  | "scene-image"
  | "promotion-image"
  | "detail-hero";

export type ProductSceneStyleId =
  | "studio"
  | "home"
  | "outdoor"
  | "gift"
  | "festival";

export type ProductVisualToneId =
  | "conversion"
  | "premium"
  | "lifestyle"
  | "minimal"
  | "vibrant";

export type ProductOption<TId extends string = string> = {
  id: TId;
  label: string;
  description: string;
};

export const productPlatformStyles: ProductOption<ProductPlatformStyleId>[] = [
  {
    id: "pinduoduo",
    label: "拼多多",
    description: "高转化、强促销、卖点醒目，适合快速抓住价格和利益点。",
  },
  {
    id: "taobao-tmall",
    label: "淘宝/天猫",
    description: "精致电商质感，商品主体清晰，兼顾品牌感和转化。",
  },
  {
    id: "jd",
    label: "京东",
    description: "品质可信、参数清楚、画面干净，突出专业和可靠。",
  },
  {
    id: "xiaohongshu",
    label: "小红书",
    description: "生活方式种草感，自然真实，适合内容化商品展示。",
  },
  {
    id: "douyin",
    label: "抖音电商",
    description: "强节奏、强钩子、短视频货架感，第一眼更有冲击。",
  },
];

export const productImagePurposes: ProductOption<ProductImagePurposeId>[] = [
  {
    id: "main-image",
    label: "主图",
    description: "商品主体最大化，第一眼说明卖什么、为什么值得点。",
  },
  {
    id: "white-background",
    label: "白底图",
    description: "干净白底，适合商品列表、审核、抠图和基础素材。",
  },
  {
    id: "scene-image",
    label: "场景图",
    description: "把商品放进真实使用环境，强调氛围和使用想象。",
  },
  {
    id: "promotion-image",
    label: "促销图",
    description: "突出活动气氛和核心卖点，预留促销文案表达空间。",
  },
  {
    id: "detail-hero",
    label: "详情页首屏",
    description: "适合详情页开头，信息层级更丰富，强化商品价值。",
  },
];

export const productSceneStyles: ProductOption<ProductSceneStyleId>[] = [
  { id: "studio", label: "纯色棚拍", description: "干净、可控、突出主体。" },
  { id: "home", label: "居家生活", description: "真实日常环境，适合种草。" },
  { id: "outdoor", label: "户外使用", description: "强调便携、耐用和场景感。" },
  { id: "gift", label: "礼盒陈列", description: "适合节日、送礼和套装表达。" },
  { id: "festival", label: "节日活动", description: "更强活动氛围和购买冲动。" },
];

export const productVisualTones: ProductOption<ProductVisualToneId>[] = [
  { id: "conversion", label: "高转化促销", description: "明亮、直接、利益点突出。" },
  { id: "premium", label: "品质轻奢", description: "克制、高级、强调质感。" },
  { id: "lifestyle", label: "真实种草", description: "自然光、生活化、可信赖。" },
  { id: "minimal", label: "简约白净", description: "留白充分，适合干净主图。" },
  { id: "vibrant", label: "鲜明活力", description: "色彩更强，适合短视频货架。" },
];

export const imageTools: ImageTool[] = [
  {
    id: "product",
    title: "电商商品图工作台",
    description: "按平台、用途、卖点和场景生成更贴近真实运营需求的商品图。",
    defaultSize: "1536x1024",
    sizeOptions: [...imageSizes],
  },
];

export function getToolById(id: string): ImageTool | undefined {
  return imageTools.find((tool) => tool.id === id);
}
