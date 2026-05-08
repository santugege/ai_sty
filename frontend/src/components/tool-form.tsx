"use client";

import Image from "next/image";
import { useMemo, useRef, useState } from "react";
import { AlertCircle, ImageIcon, Loader2, Upload } from "lucide-react";
import type { ImageSize, ImageTool } from "@/lib/tools";
import {
  genericErrorMessage,
  getImageDimensions,
  submitImageGenerationForm,
  type GeneratedImage,
} from "@/lib/image-api";

type ToolFormProps = {
  tool: ImageTool;
};

export function ToolForm({ tool }: ToolFormProps) {
  const [prompt, setPrompt] = useState("");
  const [size, setSize] = useState<ImageSize>(tool.defaultSize);
  const [resultSize, setResultSize] = useState<ImageSize>(tool.defaultSize);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<GeneratedImage | null>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submitLockRef = useRef(false);

  const promptId = `${tool.id}-prompt`;
  const imageInputId = `${tool.id}-image`;
  const sizeId = `${tool.id}-size`;

  const fileLabel = useMemo(() => {
    if (!file) {
      return tool.imageRequired ? "请选择图片文件" : "可选上传参考图";
    }

    return file.name;
  }, [file, tool.imageRequired]);

  const previewDimensions = useMemo(
    () => getImageDimensions(resultSize),
    [resultSize],
  );

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
    formData.append("prompt", prompt);
    formData.append("size", size);

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
    <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <form
        onSubmit={handleSubmit}
        className="rounded-lg border border-stone-300 bg-white/80 p-5 shadow-sm"
      >
        <label
          htmlFor={promptId}
          className="block text-sm font-semibold text-stone-900"
        >
          {tool.promptLabel}
        </label>
        <textarea
          id={promptId}
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder={tool.promptPlaceholder}
          required={tool.promptRequired}
          disabled={isSubmitting}
          rows={7}
          className="mt-3 w-full resize-none rounded-md border border-stone-300 bg-white px-4 py-3 text-base leading-7 text-stone-950 outline-none transition focus:border-stone-950 disabled:cursor-not-allowed disabled:bg-stone-100 disabled:text-stone-500"
        />

        {(tool.imageRequired || tool.mode === "edit") && (
          <label
            htmlFor={imageInputId}
            className={`group mt-5 block ${isSubmitting ? "cursor-not-allowed opacity-70" : ""}`}
          >
            <span className="text-sm font-semibold text-stone-900">
              {tool.imageLabel}
            </span>
            <span className="mt-3 flex min-h-28 items-center gap-3 rounded-md border border-dashed border-stone-400 bg-stone-50 px-4 py-4 text-stone-600 transition group-focus-within:border-stone-950 group-focus-within:ring-2 group-focus-within:ring-stone-950/20 group-hover:border-stone-950">
              <Upload aria-hidden="true" className="h-5 w-5 shrink-0" />
              <span className="min-w-0 truncate">{fileLabel}</span>
            </span>
            <input
              id={imageInputId}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              required={tool.imageRequired}
              disabled={isSubmitting}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="sr-only"
            />
          </label>
        )}

        <label
          htmlFor={sizeId}
          className="mt-5 block text-sm font-semibold text-stone-900"
        >
          输出尺寸
        </label>
        <select
          id={sizeId}
          value={size}
          onChange={(event) => setSize(event.target.value as ImageSize)}
          disabled={isSubmitting}
          className="mt-3 w-full rounded-md border border-stone-300 bg-white px-4 py-3 text-stone-950 outline-none transition focus:border-stone-950 disabled:cursor-not-allowed disabled:bg-stone-100 disabled:text-stone-500"
        >
          {tool.sizeOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>

        {error && (
          <div className="mt-5 flex gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-800">
            <AlertCircle aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
            <p className="min-w-0 break-words [overflow-wrap:anywhere]">
              {error}
            </p>
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-6 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-md bg-stone-950 px-5 py-3 text-base font-semibold text-white transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:bg-stone-500"
        >
          {isSubmitting ? (
            <Loader2 aria-hidden="true" className="h-5 w-5 animate-spin" />
          ) : (
            <ImageIcon aria-hidden="true" className="h-5 w-5" />
          )}
          {isSubmitting ? "生成中" : "生成图片"}
        </button>
      </form>

      <section className="grid min-h-[34rem] place-items-center rounded-lg border border-stone-300 bg-stone-950 p-4 text-white shadow-sm">
        {result ? (
          <div className="w-full">
            <Image
              unoptimized
              src={result.src}
              alt={`${tool.title}生成结果`}
              width={previewDimensions.width}
              height={previewDimensions.height}
              className="mx-auto h-auto max-h-[32rem] w-auto max-w-full rounded-md object-contain"
            />
            {result.revisedPrompt && (
              <p className="mt-4 break-words text-sm leading-6 text-stone-300 [overflow-wrap:anywhere]">
                {result.revisedPrompt}
              </p>
            )}
          </div>
        ) : (
          <div className="max-w-sm text-center">
            <ImageIcon aria-hidden="true" className="mx-auto h-10 w-10 text-stone-400" />
            <p className="mt-4 text-xl font-semibold">结果会显示在这里</p>
            <p className="mt-3 text-sm leading-6 text-stone-400">
              提交后请等待图片模型完成生成，复杂图片可能需要较长时间。
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
