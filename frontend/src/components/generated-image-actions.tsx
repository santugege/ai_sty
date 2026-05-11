"use client";

/* eslint-disable @next/next/no-img-element */

import { Download, ExternalLink, X } from "lucide-react";

export type GeneratedImageActionImage = {
  id?: string;
  src: string;
  mimeType?: string | null;
};

type GeneratedImageActionsProps = {
  image: GeneratedImageActionImage;
  onPreview: () => void;
  downloadName?: string;
  compact?: boolean;
  floating?: boolean;
  showPreview?: boolean;
};

type ImagePreviewDialogProps = {
  image: GeneratedImageActionImage | null;
  alt: string;
  onClose: () => void;
  downloadName?: string;
};

function classNames(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

function extensionFromMimeType(mimeType?: string | null) {
  if (mimeType?.includes("jpeg")) {
    return "jpg";
  }
  if (mimeType?.includes("webp")) {
    return "webp";
  }
  return "png";
}

function imageDownloadName(image: GeneratedImageActionImage, name?: string) {
  const baseName = name || image.id || "generated-image";
  return /\.[a-z0-9]+$/i.test(baseName)
    ? baseName
    : `${baseName}.${extensionFromMimeType(image.mimeType)}`;
}

export function GeneratedImageActions({
  image,
  onPreview,
  downloadName,
  compact = false,
  floating = true,
  showPreview = true,
}: GeneratedImageActionsProps) {
  const controlClassName =
    "inline-grid place-items-center rounded-full border border-white/75 bg-white/92 text-ink shadow-soft backdrop-blur transition-refined hover:-translate-y-0.5 hover:border-cyan hover:text-cyan focus:outline-none focus:ring-2 focus:ring-cyan/30";

  return (
    <div
      className={classNames(
        "GeneratedImageActions flex items-center gap-2",
        floating && (compact ? "absolute right-2 top-2" : "absolute right-3 top-3"),
      )}
    >
      {showPreview ? (
        <button
          type="button"
          onClick={onPreview}
          title="查看大图"
          aria-label="查看大图"
          className={classNames(controlClassName, compact ? "h-8 w-8" : "h-9 w-9")}
        >
          <ExternalLink aria-hidden="true" className="h-4 w-4" />
        </button>
      ) : null}
      <a
        href={image.src}
        download={imageDownloadName(image, downloadName)}
        title="下载图片"
        aria-label="下载图片"
        className={classNames(controlClassName, compact ? "h-8 w-8" : "h-9 w-9")}
      >
        <Download aria-hidden="true" className="h-4 w-4" />
      </a>
    </div>
  );
}

export function ImagePreviewDialog({
  image,
  alt,
  onClose,
  downloadName,
}: ImagePreviewDialogProps) {
  if (!image) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-ink/70 px-4 py-6 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="生成图片预览"
    >
      <div className="relative flex max-h-full w-full max-w-6xl flex-col overflow-hidden rounded-lg border border-white/20 bg-paper shadow-refined">
        <div className="flex items-center justify-end gap-2 border-b border-border bg-surface px-3 py-2">
          <GeneratedImageActions
            image={image}
            onPreview={() => undefined}
            downloadName={downloadName}
            floating={false}
            showPreview={false}
          />
          <button
            type="button"
            onClick={onClose}
            title="关闭预览"
            aria-label="关闭预览"
            className="grid h-9 w-9 place-items-center rounded-full border border-border bg-surface text-ink transition-refined hover:border-cyan hover:text-cyan focus:outline-none focus:ring-2 focus:ring-cyan/30"
          >
            <X aria-hidden="true" className="h-4 w-4" />
          </button>
        </div>
        <div className="grid min-h-0 flex-1 place-items-center overflow-auto bg-[#0b0f14] p-3 sm:p-5">
          <img
            src={image.src}
            alt={alt}
            className="max-h-[82vh] max-w-full rounded-md object-contain shadow-refined"
          />
        </div>
      </div>
    </div>
  );
}
