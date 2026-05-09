"use client";

/* eslint-disable @next/next/no-img-element */

import Link from "next/link";
import {
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  AlertCircle,
  ChevronRight,
  Image as ImageIcon,
  Loader2,
  Package,
  Settings2,
  Sparkles,
} from "lucide-react";
import {
  productImagePurposes,
  type ImageSize,
  type ImageTool,
  type ProductImagePurposeId,
  type ProductPlatformStyleId,
} from "@/lib/tools";
import {
  genericErrorMessage,
  submitImageGenerationForm,
  type GeneratedImage,
} from "@/lib/image-api";

type HomeProductWorkbenchProps = {
  tool: ImageTool;
};

type NavItem = {
  label: string;
  href: string;
  icon: typeof Package;
  active?: boolean;
};

const topNavItems: NavItem[] = [
  { label: "商品图", href: "/", icon: Package, active: true },
];

const bottomNavItems: NavItem[] = [
  { label: "设置", href: "/", icon: Settings2 },
];

const platformPresets: Array<{
  id: ProductPlatformStyleId;
  label: string;
  size: string;
}> = [
  { id: "taobao-tmall", label: "淘宝/天猫", size: "800x800" },
  { id: "jd", label: "京东", size: "800x800" },
  { id: "pinduoduo", label: "拼多多", size: "750x1334" },
  { id: "xiaohongshu", label: "小红书", size: "1080x1350" },
  { id: "douyin", label: "抖音电商", size: "1080x1920" },
];

const aspectSizeOptions: Array<{ label: string; size: ImageSize }> = [
  { label: "1:1", size: "1024x1024" },
  { label: "3:2", size: "1536x1024" },
  { label: "2:3", size: "1024x1536" },
];

export function HomeProductWorkbench({ tool }: HomeProductWorkbenchProps) {
  const [platformStyle, setPlatformStyle] =
    useState<ProductPlatformStyleId>("taobao-tmall");
  const [imagePurpose, setImagePurpose] =
    useState<ProductImagePurposeId>("main-image");
  const [notes, setNotes] = useState("");
  const [size, setSize] = useState<ImageSize>(tool.defaultSize);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<GeneratedImage | null>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submitLockRef = useRef(false);

  const selectedPlatformLabel =
    platformPresets.find((preset) => preset.id === platformStyle)?.label ||
    platformStyle;
  const selectedPurposeLabel =
    productImagePurposes.find((purpose) => purpose.id === imagePurpose)?.label ||
    imagePurpose;
  const fileLabel = file?.name || "上传商品原图";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (submitLockRef.current) {
      return;
    }

    submitLockRef.current = true;
    setError("");
    setResult(null);
    setIsSubmitting(true);

    const formData = new FormData();
    formData.append("toolId", tool.id);
    formData.append("prompt", notes);
    formData.append("size", size);
    formData.append("platformStyle", platformStyle);
    formData.append("imagePurpose", imagePurpose);

    if (file) {
      formData.append("image", file);
    }

    try {
      const generatedImage = await submitImageGenerationForm(formData);
      setResult(generatedImage);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : genericErrorMessage);
    } finally {
      submitLockRef.current = false;
      setIsSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="conceptChrome relative min-h-screen overflow-hidden bg-paper text-ink"
    >
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.024)_1px,transparent_1px)] bg-[size:32px_32px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_33%_0%,rgba(77,122,177,0.13),transparent_28rem)]" />

      <div className="relative z-10 grid min-h-screen xl:grid-cols-[204px_minmax(0,1fr)_381px]">
        <aside className="leftStudioRail hidden border-r border-white/10 bg-[#0a0e15]/80 xl:flex xl:flex-col">
          <div className="px-7 pt-9">
            <Link href="/" className="block text-[26px] font-black leading-none">
              视觉创作台
            </Link>
          </div>

          <nav className="mt-10 grid gap-4 pr-3" aria-label="主导航">
            {topNavItems.map((item) => (
              <RailLink key={item.label} item={item} />
            ))}
          </nav>

          <nav className="mt-auto grid gap-4 pb-8 pr-3" aria-label="设置导航">
            {bottomNavItems.map((item) => (
              <RailLink key={item.label} item={item} />
            ))}
          </nav>
        </aside>

        <section className="mainStudioStage relative min-w-0 px-4 pb-[132px] pt-8 sm:px-8 xl:px-[42px] xl:pb-[146px] xl:pt-[38px]">
          <header>
            <h1 className="text-[28px] font-black leading-none text-ink">电商商品图</h1>
          </header>

          <section className="heroCanvas mt-[31px]" aria-label="商品图生成画布">
            {result ? (
              <div className="grid min-h-[672px] place-items-center overflow-hidden rounded-[10px] border border-white/10 bg-surface p-6 shadow-soft">
                <img
                  src={result.src}
                  alt="商品图生成结果"
                  className="max-h-[620px] max-w-full rounded-[10px] object-contain shadow-refined"
                />
              </div>
            ) : (
              <div className="emptyCanvas relative grid min-h-[672px] place-items-center overflow-hidden rounded-[10px] border border-white/10 bg-surface shadow-soft">
                <div className="absolute inset-8 rounded-[8px] border border-dashed border-white/10" />
                <div className="absolute left-10 top-10 h-20 w-px bg-coral/60 shadow-[0_0_22px_rgba(255,92,74,0.36)]" />
                <div className="absolute right-10 top-10 h-20 w-px bg-gold/55 shadow-[0_0_22px_rgba(215,183,114,0.24)]" />
                <div className="relative grid max-w-[420px] place-items-center px-6 text-center">
                  <div className="grid h-[104px] w-[104px] place-items-center rounded-[10px] border border-white/10 bg-[rgba(255,255,255,0.035)] text-coral">
                    <ImageIcon aria-hidden="true" className="h-10 w-10" />
                  </div>
                  <p className="mt-8 text-[22px] font-bold leading-none text-ink">
                    等待生成商品图
                  </p>
                  <p className="mt-4 text-sm leading-6 text-ink-lighter">
                    {file ? file.name : "上传商品原图后，提示词会直接提交给商品图生成接口。"}
                  </p>
                </div>
              </div>
            )}
          </section>

          {result?.revisedPrompt ? (
            <section className="mt-4 rounded-[10px] border border-white/10 bg-[rgba(255,255,255,0.035)] p-4 text-xs leading-6 text-ink-light">
              {result.revisedPrompt}
            </section>
          ) : null}
        </section>

        <aside className="rightInspector hidden py-9 pl-[11px] pr-[89px] xl:block">
          <div className="rightInspectorPanel studio-panel h-[875px] overflow-y-auto rounded-[10px] px-5 py-6">
            <section className="purposeInspectorPanel" aria-label="商品图类型">
              <div className="flex items-center justify-between">
                <h2 className="text-[16px] font-bold leading-none">图片类型</h2>
                <span className="text-xs text-ink-lighter">{selectedPurposeLabel}</span>
              </div>
              <div className="mt-5 grid gap-2">
                {productImagePurposes.map((purpose) => (
                  <button
                    key={purpose.id}
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => setImagePurpose(purpose.id)}
                    className={`min-h-11 rounded-[6px] border px-3 text-left text-[14px] font-semibold transition-refined disabled:opacity-60 ${
                      imagePurpose === purpose.id
                        ? "border-coral bg-coral/12 text-ink shadow-[0_0_20px_rgba(255,92,74,0.22)]"
                        : "border-white/10 bg-[rgba(255,255,255,0.025)] text-ink-light hover:border-coral/70 hover:text-ink"
                    }`}
                  >
                    {purpose.label}
                  </button>
                ))}
              </div>
            </section>

            <section className="mt-6 border-t border-white/10 pt-6">
            <div className="flex items-center justify-between">
              <h2 className="text-[16px] font-bold leading-none">平台预设</h2>
              <span className="inline-flex items-center gap-1 text-xs text-ink-lighter">
                更多
                <ChevronRight aria-hidden="true" className="h-3.5 w-3.5" />
              </span>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-2">
              {platformPresets.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => setPlatformStyle(preset.id)}
                  className={`rounded-[5px] border px-3 py-3 text-left transition-refined disabled:opacity-60 ${
                    platformStyle === preset.id
                      ? "border-coral bg-coral/8"
                      : "border-white/10 bg-[rgba(255,255,255,0.025)] hover:border-coral/70"
                  }`}
                >
                  <span className="block text-[14px] font-semibold leading-none text-ink">
                    {preset.label}
                  </span>
                  <span className="mt-2 block text-[13px] leading-none text-ink-lighter">
                    {preset.size}
                  </span>
                </button>
              ))}
            </div>
            </section>

            <InspectorSection title="画面比例">
              <div className="flex gap-[9px]">
                {aspectSizeOptions.map((option) => (
                  <button
                    key={option.size}
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => setSize(option.size)}
                    className={`h-10 min-w-0 flex-1 rounded-[5px] border text-[13px] transition-refined disabled:opacity-60 ${
                      size === option.size
                        ? "border-coral bg-coral/8 text-ink"
                        : "border-white/10 bg-[rgba(255,255,255,0.025)] text-ink-lighter hover:border-white/25 hover:text-ink"
                    }`}
                    title={option.size}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              <p className="mt-3 text-xs text-ink-lighter">{size}</p>
            </InspectorSection>
          </div>
        </aside>
      </div>

      <section className="floatingPrompt fixed bottom-4 left-4 right-4 z-20 xl:bottom-[23px] xl:left-[244px] xl:right-[423px]">
        <div className="studio-panel min-h-[114px] rounded-[16px] px-[18px] py-4">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_240px] lg:items-end">
            <div className="min-w-0">
              <textarea
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                disabled={isSubmitting}
                rows={4}
                placeholder="输入商品图提示词内容"
                className="promptComposer block min-h-[112px] w-full resize-none bg-transparent text-[22px] leading-8 text-ink outline-none placeholder:text-ink-lighter disabled:opacity-60"
              />
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <label
                  htmlFor="home-product-image"
                  className="inline-flex h-9 cursor-pointer items-center gap-2 rounded-[6px] border border-white/10 bg-[rgba(255,255,255,0.025)] px-4 text-[14px] text-ink-light transition-refined hover:border-coral/70 hover:text-ink"
                >
                  <ImageIcon aria-hidden="true" className="h-4 w-4" />
                  参考图
                </label>
                <span className="max-w-[18rem] truncate text-xs text-ink-lighter">{fileLabel}</span>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => {
                    if (!notes.trim()) {
                      setNotes("保留商品主体真实结构，强化电商转化氛围，预留卖点文案空间");
                    }
                  }}
                  className="inline-flex h-9 items-center gap-2 rounded-[6px] border border-white/10 bg-[rgba(255,255,255,0.025)] px-4 text-[14px] text-ink-light transition-refined hover:border-coral/70 hover:text-ink disabled:opacity-60"
                >
                  <Sparkles aria-hidden="true" className="h-4 w-4" />
                  智能优化
                </button>
              </div>
              <input
                id="home-product-image"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                required
                disabled={isSubmitting}
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                className="sr-only"
              />
            </div>
            <div className="flex items-center justify-end gap-7">
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex h-[62px] w-[158px] items-center justify-center gap-2 rounded-[8px] bg-coral text-[18px] font-bold text-white shadow-[0_14px_34px_rgba(255,92,74,0.28)] transition-refined hover:-translate-y-0.5 hover:bg-[#ff6f62] disabled:cursor-not-allowed disabled:bg-surface-soft disabled:text-ink-lighter"
              >
                {isSubmitting ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : null}
                商品图生成
                {!isSubmitting ? <Sparkles aria-hidden="true" className="h-4 w-4" /> : null}
              </button>
            </div>
          </div>
          {error ? (
            <div className="mt-3 flex items-start gap-2 text-sm leading-5 text-error">
              <AlertCircle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
              <span className="min-w-0 [overflow-wrap:anywhere]">{error}</span>
            </div>
          ) : (
            <p className="mt-3 truncate text-xs text-ink-lighter">
              当前策略：{selectedPlatformLabel} / {selectedPurposeLabel} / {size}
            </p>
          )}
        </div>
      </section>
    </form>
  );
}

function RailLink({ item }: { item: NavItem }) {
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      className={`relative flex h-[59px] items-center gap-5 rounded-r-[3px] px-7 text-[15px] font-semibold transition-refined ${
        item.active
          ? "bg-[rgba(255,255,255,0.055)] text-ink before:absolute before:left-0 before:top-0 before:h-full before:w-[2px] before:rounded-r-full before:bg-coral before:shadow-[0_0_16px_rgba(255,92,74,0.9)]"
          : "text-ink-light hover:bg-[rgba(255,255,255,0.035)] hover:text-ink"
      }`}
    >
      <Icon aria-hidden="true" className={`h-[22px] w-[22px] ${item.active ? "text-gold" : ""}`} />
      <span>{item.label}</span>
    </Link>
  );
}

function InspectorSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-6 border-t border-white/10 pt-6">
      <h3 className="mb-4 text-[16px] font-bold leading-none">{title}</h3>
      {children}
    </section>
  );
}
