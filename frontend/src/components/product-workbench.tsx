"use client";

import Image from "next/image";
import { useMemo, useRef, useState, type KeyboardEvent } from "react";
import {
  AlertCircle,
  BadgePercent,
  Boxes,
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

function classNames(...values: Array<string | false>) {
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

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
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
    <div className="grid gap-5 xl:grid-cols-[minmax(18rem,0.68fr)_minmax(22rem,0.82fr)_minmax(24rem,1fr)]">
      <form onSubmit={handleSubmit} className="contents">
        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-md bg-amber-100 text-amber-800">
              <PackageOpen aria-hidden="true" className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-zinc-950">商品素材</h2>
              <p className="text-sm leading-6 text-zinc-500">
                先上传商品原图，再补齐运营信息。
              </p>
            </div>
          </div>

          <label
            htmlFor="product-image"
            className={classNames(
              "mt-5 block",
              isSubmitting && "cursor-not-allowed opacity-70",
            )}
          >
            <span className="text-sm font-semibold text-zinc-900">
              上传商品原图
            </span>
            <span className="mt-3 flex min-h-32 items-center gap-3 rounded-md border border-dashed border-zinc-300 bg-zinc-50 px-4 py-4 text-zinc-600 transition hover:border-zinc-950">
              <Upload aria-hidden="true" className="h-5 w-5 shrink-0" />
              <span className="min-w-0 truncate">{fileLabel}</span>
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

          <label className="mt-5 block text-sm font-semibold text-zinc-900">
            商品类目
            <input
              value={productCategory}
              onChange={(event) => setProductCategory(event.target.value)}
              placeholder="例如：小家电、美妆、食品、服饰"
              disabled={isSubmitting}
              className="mt-2 w-full rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            />
          </label>

          <label className="mt-4 block text-sm font-semibold text-zinc-900">
            核心卖点
            <textarea
              value={sellingPoints}
              onChange={(event) => setSellingPoints(event.target.value)}
              placeholder="例如：三档风力、静音、USB 充电、宿舍可用"
              rows={4}
              disabled={isSubmitting}
              className="mt-2 w-full resize-none rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm leading-6 text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            />
          </label>

          <label className="mt-4 block text-sm font-semibold text-zinc-900">
            输出尺寸
            <select
              value={size}
              onChange={(event) => setSize(event.target.value as ImageSize)}
              disabled={isSubmitting}
              className="mt-2 w-full rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            >
              {imageSizes.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </section>

        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-md bg-rose-100 text-rose-700">
              <BadgePercent aria-hidden="true" className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-zinc-950">运营策略</h2>
              <p className="text-sm leading-6 text-zinc-500">
                平台和用途会决定画面重点。
              </p>
            </div>
          </div>

          <OptionGroup
            title="平台风格"
            value={platformStyle}
            options={productPlatformStyles}
            onChange={(value) => setPlatformStyle(value)}
            disabled={isSubmitting}
          />

          <OptionGroup
            title="图片用途"
            value={imagePurpose}
            options={productImagePurposes}
            onChange={(value) => setImagePurpose(value)}
            disabled={isSubmitting}
          />

          <OptionGroup
            title="背景场景"
            value={sceneStyle}
            options={productSceneStyles}
            onChange={(value) => setSceneStyle(value)}
            disabled={isSubmitting}
          />

          <OptionGroup
            title="视觉风格"
            value={visualTone}
            options={productVisualTones}
            onChange={(value) => setVisualTone(value)}
            disabled={isSubmitting}
          />

          <label className="mt-5 block text-sm font-semibold text-zinc-900">
            促销文案
            <input
              value={promotionText}
              onChange={(event) => setPromotionText(event.target.value)}
              placeholder="例如：限时立减 20 元、买一送一"
              disabled={isSubmitting}
              className="mt-2 w-full rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            />
          </label>

          <div className="mt-5 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-950">
            当前策略：{selectedPlatform?.label} · {selectedPurpose?.label}
          </div>
        </section>

        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm xl:row-span-2">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-md bg-zinc-900 text-white">
              <ImageIcon aria-hidden="true" className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-zinc-950">生成结果</h2>
              <p className="text-sm leading-6 text-zinc-500">
                商品细节优先保真，场景按策略生成。
              </p>
            </div>
          </div>

          <div className="mt-5 grid min-h-[32rem] place-items-center rounded-lg bg-zinc-950 p-4 text-white">
            {result ? (
              <div className="w-full">
                <Image
                  unoptimized
                  src={result.src}
                  alt="电商商品图生成结果"
                  width={previewDimensions.width}
                  height={previewDimensions.height}
                  className="mx-auto h-auto max-h-[30rem] w-auto max-w-full rounded-md object-contain"
                />
                {result.revisedPrompt && (
                  <p className="mt-4 break-words text-sm leading-6 text-zinc-300 [overflow-wrap:anywhere]">
                    {result.revisedPrompt}
                  </p>
                )}
              </div>
            ) : (
              <div className="max-w-sm text-center">
                <Boxes
                  aria-hidden="true"
                  className="mx-auto h-10 w-10 text-zinc-400"
                />
                <p className="mt-4 text-xl font-semibold">等待生成商品图</p>
                <p className="mt-3 text-sm leading-6 text-zinc-400">
                  上传商品原图并完成策略配置后，结果会显示在这里。
                </p>
              </div>
            )}
          </div>

          {error && (
            <div className="mt-5 flex gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-800">
              <AlertCircle
                aria-hidden="true"
                className="mt-0.5 h-5 w-5 shrink-0"
              />
              <p className="min-w-0 break-words [overflow-wrap:anywhere]">
                {error}
              </p>
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-5 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-md bg-zinc-950 px-5 py-3 text-base font-semibold text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-500"
          >
            {isSubmitting ? (
              <Loader2 aria-hidden="true" className="h-5 w-5 animate-spin" />
            ) : (
              <Sparkles aria-hidden="true" className="h-5 w-5" />
            )}
            {isSubmitting ? "生成中" : "生成电商商品图"}
          </button>
        </section>

        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-zinc-950">保真和限制</h2>
          <label className="mt-4 block text-sm font-semibold text-zinc-900">
            必须保留
            <textarea
              value={preserveRequirements}
              onChange={(event) => setPreserveRequirements(event.target.value)}
              rows={3}
              disabled={isSubmitting}
              className="mt-2 w-full resize-none rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm leading-6 text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            />
          </label>
          <label className="mt-4 block text-sm font-semibold text-zinc-900">
            禁止出现
            <textarea
              value={avoidElements}
              onChange={(event) => setAvoidElements(event.target.value)}
              rows={3}
              disabled={isSubmitting}
              className="mt-2 w-full resize-none rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm leading-6 text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            />
          </label>
          <label className="mt-4 block text-sm font-semibold text-zinc-900">
            补充说明
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="例如：商品放右侧，左侧留出卖点文字空间"
              rows={3}
              disabled={isSubmitting}
              className="mt-2 w-full resize-none rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm leading-6 text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            />
          </label>
        </section>
      </form>
    </div>
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
    <fieldset className="mt-5">
      <legend className="text-sm font-semibold text-zinc-900">{title}</legend>
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
                "rounded-md border px-3 py-2.5 text-left transition disabled:cursor-not-allowed disabled:opacity-60",
                isSelected
                  ? "border-zinc-950 bg-zinc-950 text-white"
                  : "border-zinc-200 bg-white text-zinc-700 hover:border-zinc-950",
              )}
            >
              <span className="block text-sm font-semibold">
                {option.label}
              </span>
              <span
                className={classNames(
                  "mt-1 block text-xs leading-5",
                  isSelected ? "text-zinc-300" : "text-zinc-500",
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
