export const imageSizes = [
  "1024x1024",
  "1536x1024",
  "1024x1536",
  "2048x2048",
  "2048x1152",
  "3840x2160",
  "2160x3840",
] as const;

export type ImageSize = (typeof imageSizes)[number];
export type ToolId = "product";

export type ImageTool = {
  id: ToolId;
  title: string;
  defaultSize: ImageSize;
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
    description: "突出活动氛围和核心卖点，预留促销文案表达空间。",
  },
  {
    id: "detail-hero",
    label: "详情页首屏",
    description: "适合详情页开头，信息层级更丰富，强化商品价值。",
  },
];

export const imageTools: ImageTool[] = [
  {
    id: "product",
    title: "电商商品图工作台",
    defaultSize: "1536x1024",
  },
];

export function getToolById(id: string): ImageTool | undefined {
  return imageTools.find((tool) => tool.id === id);
}
