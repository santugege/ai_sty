"use client";

/* eslint-disable @next/next/no-img-element */

import Image from "next/image";
import {
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  AlertCircle,
  ImageIcon,
  Loader2,
  MessageSquareText,
  PackageOpen,
  Send,
  Sparkles,
  Upload,
} from "lucide-react";
import {
  imageSizes,
  productImagePurposes,
  productPlatformStyles,
  type ImageSize,
  type ImageTool,
  type ProductImagePurposeId,
  type ProductPlatformStyleId,
} from "@/lib/tools";
import {
  genericErrorMessage,
  getImageDimensions,
  submitImageGenerationForm,
  type GeneratedImage,
} from "@/lib/image-api";

type ProductWorkbenchProps = {
  tool: ImageTool;
  variant?: ProductWorkbenchVariant;
};

type ProductWorkbenchVariant = "full" | "compact";

type AspectRatio = "1:1" | "3:2" | "2:3" | "16:9" | "9:16";

type ChatMessage = {
  id: string;
  role: "agent" | "user";
  content: string;
};

const sampleShowcase = [
  {
    title: "平台主图",
    image:
      "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80",
  },
  {
    title: "比例适配",
    image:
      "https://images.unsplash.com/photo-1541643600914-78b084683601?auto=format&fit=crop&w=900&q=80",
  },
  {
    title: "对话迭代",
    image:
      "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=900&q=80",
  },
];

const aspectRatioOptions: Array<{
  id: AspectRatio;
  label: string;
  description: string;
}> = [
  { id: "1:1", label: "1:1", description: "平台主图与商品卡片通用。" },
  { id: "3:2", label: "3:2", description: "横向橱窗和详情页首屏。" },
  { id: "2:3", label: "2:3", description: "竖向信息图和移动详情页。" },
  { id: "16:9", label: "16:9", description: "横版直播间与视频封面。" },
  { id: "9:16", label: "9:16", description: "短视频货架与竖屏素材。" },
];

const imageCountOptions = ["1", "2", "4"] as const;
const imageCountSelectOptions = imageCountOptions.map((option) => ({
  id: option,
  label: `${option} 张`,
  description:
    option === "1"
      ? "单张首版，适合快速确认方向。"
      : option === "2"
        ? "双图对比，便于挑选构图。"
        : "四图发散，适合批量探索方案。",
}));

function classNames(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function ProductWorkbench({
  tool,
  variant = "full",
}: ProductWorkbenchProps) {
  const isCompact = variant === "compact";
  const [platformStyle, setPlatformStyle] =
    useState<ProductPlatformStyleId>("pinduoduo");
  const [imagePurpose, setImagePurpose] =
    useState<ProductImagePurposeId>("promotion-image");
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>("1:1");
  const [imageCount, setImageCount] =
    useState<(typeof imageCountOptions)[number]>("1");
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: "agent-ready",
      role: "agent",
      content:
        "先选平台、比例、像素和数量。原图可以上传，也可以先空着生成方向稿。",
    },
  ]);
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
  const selectedAspectRatio = aspectRatioOptions.find(
    (option) => option.id === aspectRatio,
  );
  const previewDimensions = useMemo(
    () => getImageDimensions(resultSize),
    [resultSize],
  );
  const fileLabel = file?.name || "可选上传原图";
  const promptBrief = [
    `平台：${selectedPlatform?.label || platformStyle}`,
    `图片类型：${selectedPurpose?.label || imagePurpose}`,
    `画面比例：${selectedAspectRatio?.label || aspectRatio}`,
    `生成像素：${size}`,
    `生成数量：${imageCount}`,
    chatInput.trim() ? `对话要求：${chatInput.trim()}` : "",
  ]
    .filter(Boolean)
    .join("\n");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (submitLockRef.current) {
      return;
    }

    submitLockRef.current = true;
    setError("");
    setResult(null);
    setIsSubmitting(true);

    const message = chatInput.trim();
    if (message) {
      setChatMessages((currentMessages) => [
        ...currentMessages,
        { id: `user-${Date.now()}`, role: "user", content: message },
      ]);
    }

    const formData = new FormData();
    formData.append("toolId", tool.id);
    formData.append("prompt", promptBrief);
    formData.append("size", size);
    formData.append("platformStyle", platformStyle);
    formData.append("imagePurpose", imagePurpose);
    formData.append("aspectRatio", aspectRatio);
    formData.append("imageCount", imageCount);

    if (file) {
      formData.append("image", file);
    }

    try {
      const generatedImage = await submitImageGenerationForm(formData);

      setResultSize(size);
      setResult(generatedImage);
      setChatInput("");
      setChatMessages((currentMessages) => [
        ...currentMessages,
        {
          id: `agent-${Date.now()}`,
          role: "agent",
          content: "已按当前参数生成一版结果，可以继续用一句话让我调整。",
        },
      ]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : genericErrorMessage);
    } finally {
      submitLockRef.current = false;
      setIsSubmitting(false);
    }
  }

  return (
    <div
      className={classNames(
        "text-ink",
        isCompact
          ? "compactProductWorkbench px-3 py-3 sm:px-4 lg:px-5 xl:h-[calc(100vh-2.5rem)] xl:min-h-0"
          : "px-4 pb-6 sm:px-6 lg:px-8",
      )}
    >
      <form
        onSubmit={handleSubmit}
        className={classNames(
          "conceptStudioShell mx-auto grid min-w-0 grid-cols-1 gap-px overflow-hidden border border-border bg-border shadow-refined",
          isCompact
            ? "max-w-[1440px] rounded-xl xl:h-full xl:min-h-0 xl:grid-cols-[16rem_minmax(0,1fr)_18rem] xl:grid-rows-1"
            : "max-w-[1800px] rounded-[1.5rem] xl:grid-cols-[21rem_minmax(0,1fr)_24rem]",
        )}
      >
        <section
          className={classNames(
            "leftControlPanel min-w-0 bg-surface",
            isCompact
              ? "p-3 sm:p-4 xl:min-h-0 xl:overflow-y-auto"
              : "p-5 sm:p-6",
          )}
        >
          <PanelHeader
            icon={<PackageOpen aria-hidden="true" className="h-5 w-5" />}
            eyebrow="Quick Setup"
            title="生成参数"
            compact={isCompact}
          />

          <label
            htmlFor="product-image"
            className={classNames(
              "optionalSourcePanel block group cursor-pointer",
              isCompact ? "mt-4" : "mt-6",
              isSubmitting && "cursor-not-allowed opacity-50",
            )}
          >
            <span className="font-mono text-[10px] font-bold uppercase tracking-[0.24em] text-ink-lighter group-hover:text-cyan">
              01 // 可选上传原图
            </span>
            <span
              className={classNames(
                "flex flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-paper-subtle text-ink-lighter transition-refined group-hover:border-cyan group-hover:text-cyan",
                isCompact
                  ? "mt-2 min-h-20 gap-2 px-3 py-3"
                  : "mt-4 min-h-40 gap-4 px-5 py-8",
              )}
            >
              <Upload
                aria-hidden="true"
                className={classNames(
                  "shrink-0 transition-refined group-hover:-translate-y-1",
                  isCompact ? "h-5 w-5" : "h-6 w-6",
                )}
              />
              <span className="max-w-full truncate text-sm">{fileLabel}</span>
              <span
                className={classNames(
                  "text-center text-xs leading-5 text-ink-lighter",
                  isCompact && "sr-only",
                )}
              >
                支持 PNG / JPG / WebP；不上传时先生成方向稿。
              </span>
            </span>
            <input
              id="product-image"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              disabled={isSubmitting}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="sr-only"
            />
          </label>

          <div
            className={classNames(
              "generationSettingsPanel grid",
              isCompact ? "mt-4 gap-3" : "mt-6 gap-6",
            )}
          >
            <ParameterSelect
              title="02 // 电商平台"
              value={platformStyle}
              options={productPlatformStyles}
              onChange={(value) => setPlatformStyle(value)}
              disabled={isSubmitting}
              compact={isCompact}
            />

            <ParameterSelect
              title="03 // 图片类型"
              value={imagePurpose}
              options={productImagePurposes}
              onChange={(value) => setImagePurpose(value)}
              disabled={isSubmitting}
              compact={isCompact}
            />

            <ParameterSelect
              title="04 // 画面比例"
              value={aspectRatio}
              options={aspectRatioOptions}
              onChange={(value) => setAspectRatio(value)}
              disabled={isSubmitting}
              compact={isCompact}
            />

            <ParameterSelect
              title="05 // 生成像素"
              value={size}
              options={imageSizes.map((option) => ({
                id: option,
                label: option,
                description: "输出图片尺寸。",
              }))}
              onChange={(value) => setSize(value)}
              disabled={isSubmitting}
              compact={isCompact}
            />

            <ParameterSelect
              title="06 // 生成数量"
              value={imageCount}
              options={imageCountSelectOptions}
              onChange={(value) => setImageCount(value)}
              disabled={isSubmitting}
              compact={isCompact}
            />
          </div>
        </section>

        <section
          className={classNames(
            "centerStage flex min-w-0 flex-col bg-[#090c12]",
            isCompact
              ? "min-h-[32rem] p-3 xl:min-h-0 xl:overflow-hidden"
              : "min-h-[48rem] p-4 sm:p-5",
          )}
        >
          <div
            className={classNames(
              "flex items-center justify-between rounded-2xl border border-border bg-surface/70 px-4",
              isCompact ? "py-2.5" : "py-3",
            )}
          >
            <div>
              <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.28em] text-gold">
                Output Canvas
              </p>
              <h2
                className={classNames(
                  "mt-1 font-serif font-light text-ink",
                  isCompact ? "text-xl" : "text-2xl",
                )}
              >
                商业图像预览
              </h2>
            </div>
            <ImageIcon aria-hidden="true" className="h-5 w-5 text-cyan" />
          </div>

          <div
            className={classNames(
              "relative flex min-h-0 flex-1 overflow-hidden rounded-[1.35rem] border border-border bg-paper",
              isCompact ? "mt-3" : "mt-4",
            )}
          >
            {result ? (
              <div
                className={classNames(
                  "flex h-full w-full flex-col",
                  isCompact ? "p-3" : "p-5",
                )}
              >
                <div className="flex flex-1 items-center justify-center">
                  <Image
                    unoptimized
                    src={result.src}
                    alt="电商商品图生成结果"
                    width={previewDimensions.width}
                    height={previewDimensions.height}
                    className={classNames(
                      "w-auto max-w-full rounded-2xl border border-border object-contain shadow-refined",
                      isCompact ? "max-h-[44vh]" : "max-h-[68vh]",
                    )}
                  />
                </div>
                {result.revisedPrompt && (
                  <div
                    className={classNames(
                      "border-t border-border",
                      isCompact ? "mt-3 max-h-20 overflow-y-auto pt-3" : "mt-6 pt-5",
                    )}
                  >
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

          <div
            className={classNames(
              "compactSummaryStrip grid rounded-2xl border border-border bg-surface/80",
              isCompact
                ? "mt-3 gap-2 p-3 sm:grid-cols-4"
                : "mt-4 gap-3 p-4 sm:grid-cols-2",
            )}
          >
            <SummaryItem label="平台" value={selectedPlatform?.label || platformStyle} />
            <SummaryItem label="画面比例" value={aspectRatio} />
            <SummaryItem label="生成像素" value={size} />
            <SummaryItem label="生成数量" value={`${imageCount} 张`} />
          </div>
        </section>

        <aside
          className={classNames(
            "rightInspector agentConversationPanel flex min-w-0 flex-col bg-surface",
            isCompact
              ? "max-h-[34rem] overflow-hidden p-3 sm:p-4 xl:max-h-full xl:min-h-0"
              : "max-h-[calc(100vh-8rem)] overflow-y-auto p-5 sm:p-6 xl:max-h-none",
          )}
        >
          <PanelHeader
            icon={<MessageSquareText aria-hidden="true" className="h-5 w-5" />}
            eyebrow="Agent Conversation"
            title="Agent 对话调整"
            compact={isCompact}
          />

          <div
            className={classNames(
              "grid min-h-0 flex-1 content-start overflow-y-auto pr-1",
              isCompact ? "mt-4 gap-2" : "mt-6 gap-3",
            )}
          >
            {chatMessages.map((message) => (
              <article
                key={message.id}
                className={classNames(
                  "rounded-2xl border text-sm leading-6",
                  isCompact ? "px-3 py-2.5" : "px-4 py-3",
                  message.role === "user"
                    ? "border-cyan bg-accent-soft text-ink"
                    : "border-border bg-paper-subtle text-ink-light",
                )}
              >
                <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-cyan">
                  {message.role === "user" ? "You" : "Agent"}
                </p>
                {message.content}
              </article>
            ))}
          </div>

          <FieldLabel title="调整方向">
            <textarea
              value={chatInput}
              onChange={(event) => setChatInput(event.target.value)}
              placeholder="例如：背景更干净，商品放大，保留包装文字，右侧留促销空间"
              rows={isCompact ? 3 : 4}
              disabled={isSubmitting}
              className={classNames(
                "chatInput w-full resize-none rounded-2xl border border-border bg-paper-subtle px-4 text-sm leading-6 text-ink outline-none transition-refined placeholder:text-ink-lighter focus:border-cyan disabled:opacity-50",
                isCompact ? "mt-2 py-2.5" : "mt-3 py-3",
              )}
            />
          </FieldLabel>

          {error && (
            <div
              className={classNames(
                "flex gap-4 border-l-2 border-error bg-error/10 text-sm leading-6 text-ink",
                isCompact ? "mt-4 px-4 py-3" : "mt-6 px-5 py-4",
              )}
            >
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
            className={classNames(
              "group inline-flex w-full items-center justify-center gap-3 rounded-2xl bg-coral px-6 text-sm font-semibold text-paper shadow-[0_0_34px_rgba(255,107,74,0.28)] transition-refined hover:-translate-y-0.5 hover:bg-cyan disabled:cursor-not-allowed disabled:bg-surface-soft disabled:text-ink-lighter",
              isCompact ? "mt-4 min-h-12 py-3" : "mt-6 min-h-14 py-4",
            )}
          >
            {isSubmitting ? (
              <Loader2 aria-hidden="true" className="h-5 w-5 animate-spin" />
            ) : chatInput.trim() ? (
              <Send
                aria-hidden="true"
                className="h-5 w-5 transition-refined group-hover:scale-110"
              />
            ) : (
              <Sparkles
                aria-hidden="true"
                className="h-5 w-5 transition-refined group-hover:scale-110"
              />
            )}
            {isSubmitting
              ? "生成中..."
              : chatInput.trim()
                ? "发送调整并生成"
                : "生成商品图"}
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
  compact = false,
}: {
  icon: ReactNode;
  eyebrow: string;
  title: string;
  compact?: boolean;
}) {
  return (
    <header
      className={classNames(
        "flex items-center border-b border-border",
        compact ? "gap-3 pb-3" : "gap-4 pb-5",
      )}
    >
      <div
        className={classNames(
          "grid place-items-center rounded-2xl border border-border bg-paper-subtle text-cyan",
          compact ? "h-10 w-10" : "h-12 w-12",
        )}
      >
        {icon}
      </div>
      <div>
        <h2 className="font-mono text-[10px] font-bold uppercase tracking-[0.26em] text-ink-lighter">
          {eyebrow}
        </h2>
        <p
          className={classNames(
            "font-serif font-light text-ink",
            compact ? "mt-1 text-xl" : "mt-2 text-2xl",
          )}
        >
          {title}
        </p>
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

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-gold">
        {label}
      </p>
      <p className="mt-1 text-sm leading-6 text-ink-light">{value}</p>
    </div>
  );
}

function ParameterSelect<TId extends string>({
  title,
  value,
  options,
  onChange,
  disabled,
  compact = false,
}: {
  title: string;
  value: TId;
  options: Array<{ id: TId; label: string; description: string }>;
  onChange: (value: TId) => void;
  disabled: boolean;
  compact?: boolean;
}) {
  const descriptionById = new Map(
    options.map((option) => [option.id, option.description]),
  );
  const selectedDescription = descriptionById.get(value);

  return (
    <label className="parameterSelect block font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-ink-lighter focus-within:text-cyan">
      {title}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as TId)}
        disabled={disabled}
        className={classNames(
          "w-full cursor-pointer appearance-none rounded-2xl border border-border bg-paper-subtle px-4 font-mono text-sm text-ink outline-none transition-refined focus:border-cyan disabled:cursor-not-allowed disabled:opacity-50",
          compact ? "mt-2 py-2.5" : "mt-3 py-3",
        )}
      >
        {options.map((option) => (
          <option key={option.id} value={option.id} className="bg-surface text-ink">
            {option.label}
          </option>
        ))}
      </select>
      {selectedDescription && (
        <span
          className={classNames(
            "block text-[11px] font-medium normal-case leading-5 tracking-normal text-ink-lighter",
            compact ? "mt-1" : "mt-1.5",
          )}
        >
          {selectedDescription}
        </span>
      )}
    </label>
  );
}
