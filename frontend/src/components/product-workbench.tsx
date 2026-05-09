"use client";

/* eslint-disable @next/next/no-img-element */

import Image from "next/image";
import {
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import {
  AlertCircle,
  BadgePercent,
  ImageIcon,
  Loader2,
  PackageOpen,
  Sparkles,
  Upload,
} from "lucide-react";
import {
  imageSizes,
  productImagePurposes,
  productPlatformStyles,
  productSceneStyles,
  productVisualTones,
  type ImageSize,
  type ImageTool,
  type ProductImagePurposeId,
  type ProductPlatformStyleId,
  type ProductSceneStyleId,
  type ProductVisualToneId,
} from "@/lib/tools";
import {
  genericErrorMessage,
  getImageDimensions,
  submitImageGenerationForm,
  type GeneratedImage,
} from "@/lib/image-api";

type ProductWorkbenchProps = {
  tool: ImageTool;
};

const sampleShowcase = [
  {
    title: "促销主图",
    image:
      "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80",
  },
  {
    title: "详情页氛围图",
    image:
      "https://images.unsplash.com/photo-1541643600914-78b084683601?auto=format&fit=crop&w=900&q=80",
  },
  {
    title: "场景种草图",
    image:
      "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=900&q=80",
  },
];

function classNames(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function ProductWorkbench({ tool }: ProductWorkbenchProps) {
  const [platformStyle, setPlatformStyle] =
    useState<ProductPlatformStyleId>("pinduoduo");
  const [imagePurpose, setImagePurpose] =
    useState<ProductImagePurposeId>("promotion-image");
  const [sceneStyle, setSceneStyle] = useState<ProductSceneStyleId>("studio");
  const [visualTone, setVisualTone] =
    useState<ProductVisualToneId>("conversion");
  const [productCategory, setProductCategory] = useState("");
  const [sellingPoints, setSellingPoints] = useState("");
  const [promotionText, setPromotionText] = useState("");
  const [preserveRequirements, setPreserveRequirements] = useState(
    "保留商品外观、品牌 logo、包装结构和可见文字",
  );
  const [avoidElements, setAvoidElements] = useState(
    "不要额外配件、虚假价格、夸大功效或改变包装颜色",
  );
  const [notes, setNotes] = useState("");
  const [size, setSize] = useState<ImageSize>(tool.defaultSize);
  const [resultSize, setResultSize] = useState<ImageSize>(tool.defaultSize);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<GeneratedImage | null>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submitLockRef = useRef(false);

  const selectedPlatform = productPlatformStyles.find(
    (option) => option.id === platformStyle,
  );
  const selectedPurpose = productImagePurposes.find(
    (option) => option.id === imagePurpose,
  );
  const selectedScene = productSceneStyles.find(
    (option) => option.id === sceneStyle,
  );
  const selectedTone = productVisualTones.find(
    (option) => option.id === visualTone,
  );
  const previewDimensions = useMemo(
    () => getImageDimensions(resultSize),
    [resultSize],
  );
  const fileLabel = file?.name || "上传 PNG、JPG 或 WebP 商品原图";

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
    formData.append("productCategory", productCategory);
    formData.append("sellingPoints", sellingPoints);
    formData.append("sceneStyle", selectedScene?.label || sceneStyle);
    formData.append("visualTone", selectedTone?.label || visualTone);
    formData.append("promotionText", promotionText);
    formData.append("preserveRequirements", preserveRequirements);
    formData.append("avoidElements", avoidElements);

    if (file) {
      formData.append("image", file);
    }

    try {
      const generatedImage = await submitImageGenerationForm(formData);

      setResultSize(size);
      setResult(generatedImage);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : genericErrorMessage);
    } finally {
      submitLockRef.current = false;
      setIsSubmitting(false);
    }
  }

  return (
    <div className="px-4 pb-6 text-ink sm:px-6 lg:px-8">
      <form
        onSubmit={handleSubmit}
        className="conceptStudioShell mx-auto grid min-w-0 max-w-[1800px] grid-cols-1 gap-px overflow-hidden rounded-[1.5rem] border border-border bg-border shadow-refined xl:grid-cols-[21rem_minmax(0,1fr)_22rem]"
      >
        <section className="leftControlPanel min-w-0 bg-surface p-5 sm:p-6">
          <PanelHeader
            icon={<PackageOpen aria-hidden="true" className="h-5 w-5" />}
            eyebrow="Source Asset"
            title="商品原始资产"
          />

          <label
            htmlFor="product-image"
            className={classNames(
              "mt-6 block group cursor-pointer",
              isSubmitting && "cursor-not-allowed opacity-50",
            )}
          >
            <span className="font-mono text-[10px] font-bold uppercase tracking-[0.24em] text-ink-lighter group-hover:text-cyan">
              01 // Image Upload
            </span>
            <span className="mt-4 flex min-h-40 flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-border bg-paper-subtle px-5 py-8 text-ink-lighter transition-refined group-hover:border-cyan group-hover:text-cyan">
              <Upload
                aria-hidden="true"
                className="h-6 w-6 shrink-0 transition-refined group-hover:-translate-y-1"
              />
              <span className="max-w-full truncate text-sm">{fileLabel}</span>
            </span>
            <input
              id="product-image"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              required
              disabled={isSubmitting}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="sr-only"
            />
          </label>

          <div className="mt-6 grid gap-6">
            <FieldLabel title="02 // Product Category">
              <input
                value={productCategory}
                onChange={(event) => setProductCategory(event.target.value)}
                placeholder="例如：小家电、美妆、食品、服饰"
                disabled={isSubmitting}
                className="mt-3 w-full rounded-2xl border border-border bg-paper-subtle px-4 py-3 text-sm text-ink outline-none transition-refined placeholder:text-ink-lighter focus:border-cyan disabled:opacity-50"
              />
            </FieldLabel>

            <FieldLabel title="03 // Key Selling Points">
              <textarea
                value={sellingPoints}
                onChange={(event) => setSellingPoints(event.target.value)}
                placeholder="例如：三档风力、静音、USB 充电、宿舍可用"
                rows={4}
                disabled={isSubmitting}
                className="mt-3 w-full resize-none rounded-2xl border border-border bg-paper-subtle px-4 py-3 text-sm leading-6 text-ink outline-none transition-refined placeholder:text-ink-lighter focus:border-cyan disabled:opacity-50"
              />
            </FieldLabel>

            <FieldLabel title="04 // Output Resolution">
              <select
                value={size}
                onChange={(event) => setSize(event.target.value as ImageSize)}
                disabled={isSubmitting}
                className="mt-3 w-full cursor-pointer appearance-none rounded-2xl border border-border bg-paper-subtle px-4 py-3 font-mono text-sm text-ink outline-none transition-refined focus:border-cyan disabled:opacity-50"
              >
                {imageSizes.map((option) => (
                  <option
                    key={option}
                    value={option}
                    className="bg-surface text-ink"
                  >
                    {option}
                  </option>
                ))}
              </select>
            </FieldLabel>
          </div>
        </section>

        <section className="centerStage flex min-h-[48rem] min-w-0 flex-col bg-[#090c12] p-4 sm:p-5">
          <div className="flex items-center justify-between rounded-2xl border border-border bg-surface/70 px-4 py-3">
            <div>
              <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.28em] text-gold">
                Output Canvas
              </p>
              <h2 className="mt-1 font-serif text-2xl font-light text-ink">
                商业图像预览
              </h2>
            </div>
            <ImageIcon aria-hidden="true" className="h-5 w-5 text-cyan" />
          </div>

          <div className="relative mt-4 flex flex-1 overflow-hidden rounded-[1.35rem] border border-border bg-paper">
            {result ? (
              <div className="flex h-full w-full flex-col p-5">
                <div className="flex flex-1 items-center justify-center">
                  <Image
                    unoptimized
                    src={result.src}
                    alt="电商商品图生成结果"
                    width={previewDimensions.width}
                    height={previewDimensions.height}
                    className="max-h-[68vh] w-auto max-w-full rounded-2xl border border-border object-contain shadow-refined"
                  />
                </div>
                {result.revisedPrompt && (
                  <div className="mt-6 border-t border-border pt-5">
                    <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.24em] text-cyan">
                      Revised Prompt Log
                    </p>
                    <p className="text-xs leading-6 text-ink-lighter [overflow-wrap:anywhere]">
                      {result.revisedPrompt}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="grid h-full w-full grid-cols-3 gap-px bg-border">
                {sampleShowcase.map((sample) => (
                  <div
                    key={sample.title}
                    className="relative overflow-hidden bg-surface"
                  >
                    <img
                      src={sample.image}
                      alt={sample.title}
                      className="h-full w-full object-cover opacity-88"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-paper via-paper/25 to-transparent" />
                    <p className="absolute bottom-4 left-4 right-4 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-light">
                      {sample.title}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="mt-4 rounded-2xl border border-border bg-surface/80 p-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-gold">
              Active Strategy
            </p>
            <p className="mt-2 text-sm leading-6 text-ink-light">
              {selectedPlatform?.label} / {selectedPurpose?.label} /{" "}
              {selectedTone?.label}
            </p>
          </div>
        </section>

        <aside className="rightInspector flex min-w-0 max-h-[calc(100vh-8rem)] flex-col overflow-y-auto bg-surface p-5 sm:p-6 xl:max-h-none">
          <PanelHeader
            icon={<BadgePercent aria-hidden="true" className="h-5 w-5" />}
            eyebrow="Generation Strategy"
            title="重构与视觉策略"
          />

          <div className="mt-6 grid gap-6">
            <OptionGroup
              title="05 // Platform Identity"
              value={platformStyle}
              options={productPlatformStyles}
              onChange={(value) => setPlatformStyle(value)}
              disabled={isSubmitting}
            />

            <OptionGroup
              title="06 // Image Purpose"
              value={imagePurpose}
              options={productImagePurposes}
              onChange={(value) => setImagePurpose(value)}
              disabled={isSubmitting}
            />

            <OptionGroup
              title="07 // Scene Context"
              value={sceneStyle}
              options={productSceneStyles}
              onChange={(value) => setSceneStyle(value)}
              disabled={isSubmitting}
            />

            <OptionGroup
              title="08 // Visual Tone"
              value={visualTone}
              options={productVisualTones}
              onChange={(value) => setVisualTone(value)}
              disabled={isSubmitting}
            />

            <FieldLabel title="09 // Promotion Text Layer">
              <input
                value={promotionText}
                onChange={(event) => setPromotionText(event.target.value)}
                placeholder="例如：限时立减 20 元、买一送一"
                disabled={isSubmitting}
                className="mt-3 w-full rounded-2xl border border-border bg-paper-subtle px-4 py-3 text-sm text-ink outline-none transition-refined placeholder:text-ink-lighter focus:border-cyan disabled:opacity-50"
              />
            </FieldLabel>

            <FieldLabel title="10 // Strict Preservation">
              <textarea
                value={preserveRequirements}
                onChange={(event) => setPreserveRequirements(event.target.value)}
                rows={3}
                disabled={isSubmitting}
                className="mt-3 w-full resize-none rounded-2xl border border-border bg-paper-subtle px-4 py-3 text-sm leading-6 text-ink outline-none transition-refined focus:border-cyan disabled:opacity-50"
              />
            </FieldLabel>

            <FieldLabel title="11 // Negative Constraints">
              <textarea
                value={avoidElements}
                onChange={(event) => setAvoidElements(event.target.value)}
                rows={3}
                disabled={isSubmitting}
                className="mt-3 w-full resize-none rounded-2xl border border-border bg-paper-subtle px-4 py-3 text-sm leading-6 text-ink outline-none transition-refined focus:border-error disabled:opacity-50"
              />
            </FieldLabel>

            <FieldLabel title="12 // Additional Directives">
              <textarea
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="例如：商品放右侧，左侧留出卖点文字空间"
                rows={3}
                disabled={isSubmitting}
                className="mt-3 w-full resize-none rounded-2xl border border-border bg-paper-subtle px-4 py-3 text-sm leading-6 text-ink outline-none transition-refined placeholder:text-ink-lighter focus:border-cyan disabled:opacity-50"
              />
            </FieldLabel>
          </div>

          {error && (
            <div className="mt-6 flex gap-4 border-l-2 border-error bg-error/10 px-5 py-4 text-sm leading-6 text-ink">
              <AlertCircle
                aria-hidden="true"
                className="mt-0.5 h-5 w-5 shrink-0 text-error"
              />
              <p className="min-w-0 break-words [overflow-wrap:anywhere]">
                {error}
              </p>
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="group mt-6 inline-flex min-h-14 w-full items-center justify-center gap-3 rounded-2xl bg-coral px-6 py-4 text-sm font-semibold text-paper shadow-[0_0_34px_rgba(255,107,74,0.28)] transition-refined hover:-translate-y-0.5 hover:bg-cyan disabled:cursor-not-allowed disabled:bg-surface-soft disabled:text-ink-lighter"
          >
            {isSubmitting ? (
              <Loader2 aria-hidden="true" className="h-5 w-5 animate-spin" />
            ) : (
              <Sparkles
                aria-hidden="true"
                className="h-5 w-5 transition-refined group-hover:scale-110"
              />
            )}
            {isSubmitting ? "生成中..." : "生成商品图"}
          </button>
        </aside>
      </form>
    </div>
  );
}

function PanelHeader({
  icon,
  eyebrow,
  title,
}: {
  icon: ReactNode;
  eyebrow: string;
  title: string;
}) {
  return (
    <header className="flex items-center gap-4 border-b border-border pb-5">
      <div className="grid h-12 w-12 place-items-center rounded-2xl border border-border bg-paper-subtle text-cyan">
        {icon}
      </div>
      <div>
        <h2 className="font-mono text-[10px] font-bold uppercase tracking-[0.26em] text-ink-lighter">
          {eyebrow}
        </h2>
        <p className="mt-2 font-serif text-2xl font-light text-ink">{title}</p>
      </div>
    </header>
  );
}

function FieldLabel({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <label className="block font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-ink-lighter focus-within:text-cyan">
      {title}
      {children}
    </label>
  );
}

function OptionGroup<TId extends string>({
  title,
  value,
  options,
  onChange,
  disabled,
}: {
  title: string;
  value: TId;
  options: Array<{ id: TId; label: string; description: string }>;
  onChange: (value: TId) => void;
  disabled: boolean;
}) {
  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (disabled) {
      return;
    }

    const currentIndex = options.findIndex((option) => option.id === value);
    let nextIndex: number | null = null;

    switch (event.key) {
      case "ArrowDown":
      case "ArrowRight":
        nextIndex = (currentIndex + 1) % options.length;
        break;
      case "ArrowUp":
      case "ArrowLeft":
        nextIndex = (currentIndex - 1 + options.length) % options.length;
        break;
      case "Home":
        nextIndex = 0;
        break;
      case "End":
        nextIndex = options.length - 1;
        break;
      default:
        return;
    }

    event.preventDefault();
    const group = event.currentTarget;
    const nextOption = options[nextIndex];
    onChange(nextOption.id);
    requestAnimationFrame(() => {
      group
        .querySelector<HTMLButtonElement>(`[data-option-index="${nextIndex}"]`)
        ?.focus();
    });
  }

  return (
    <fieldset>
      <legend className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-ink-lighter">
        {title}
      </legend>
      <div
        role="radiogroup"
        aria-label={title}
        onKeyDown={handleKeyDown}
        className="mt-3 grid gap-2"
      >
        {options.map((option, index) => {
          const isSelected = option.id === value;

          return (
            <button
              key={option.id}
              type="button"
              role="radio"
              aria-checked={isSelected}
              tabIndex={isSelected ? 0 : -1}
              data-option-index={index}
              disabled={disabled}
              onClick={() => onChange(option.id)}
              className={classNames(
                "group rounded-2xl border px-4 py-3 text-left transition-refined disabled:cursor-not-allowed disabled:opacity-50",
                isSelected
                  ? "border-cyan bg-cyan text-paper shadow-[0_0_28px_rgba(73,245,212,0.18)]"
                  : "border-border bg-paper-subtle text-ink hover:border-cyan/60",
              )}
            >
              <span className="block text-sm font-semibold tracking-tight">
                {option.label}
              </span>
              <span
                className={classNames(
                  "mt-1.5 block text-[11px] leading-5",
                  isSelected ? "text-paper/75" : "text-ink-lighter",
                )}
              >
                {option.description}
              </span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
