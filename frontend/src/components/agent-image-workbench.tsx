"use client";

/* eslint-disable @next/next/no-img-element */

import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import {
  AlertCircle,
  ImagePlus,
  Loader2,
  Plus,
  RefreshCcw,
  Send,
  X,
} from "lucide-react";
import {
  resetConversation,
  sendConversationMessage,
  type AgentEnvelope,
  type ConversationImage,
  type ConversationMessage,
} from "@/lib/agent-api";

const imageSizes = ["1024x1024", "1536x1024", "1024x1536"] as const;

type SelectedImage = {
  id: string;
  file: File;
  previewUrl: string;
};

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function AgentImageWorkbench() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [currentImage, setCurrentImage] = useState<ConversationImage | null>(
    null,
  );
  const [selectedImages, setSelectedImages] = useState<SelectedImage[]>([]);
  const [size, setSize] = useState<(typeof imageSizes)[number]>("1536x1024");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canSubmit =
    !isSubmitting && (message.trim().length > 0 || selectedImages.length > 0);

  function applyEnvelope(envelope: AgentEnvelope) {
    setMessages(envelope.messages);
    setCurrentImage(envelope.currentImage ?? null);
  }

  function handleImages(files: FileList | null) {
    const nextImages = Array.from(files ?? []).map((file) => ({
      id: `${file.name}-${file.lastModified}-${crypto.randomUUID()}`,
      file,
      previewUrl: URL.createObjectURL(file),
    }));
    setSelectedImages((previous) => [...previous, ...nextImages].slice(0, 4));
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function removeSelectedImage(imageId: string) {
    setSelectedImages((previous) => {
      const removed = previous.find((image) => image.id === imageId);
      if (removed) {
        URL.revokeObjectURL(removed.previewUrl);
      }
      return previous.filter((image) => image.id !== imageId);
    });
  }

  async function handleSubmit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (!canSubmit) {
      return;
    }

    const formData = new FormData();
    formData.append("message", message);
    formData.append("size", size);
    selectedImages.forEach((image) => formData.append("images", image.file));

    setError("");
    setIsSubmitting(true);

    try {
      const envelope = await sendConversationMessage(formData);
      selectedImages.forEach((image) => URL.revokeObjectURL(image.previewUrl));
      setSelectedImages([]);
      setMessage("");
      applyEnvelope(envelope);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Agent 请求失败。");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleReset() {
    setError("");
    setIsSubmitting(true);
    selectedImages.forEach((image) => URL.revokeObjectURL(image.previewUrl));
    setSelectedImages([]);
    setMessage("");

    try {
      applyEnvelope(await resetConversation());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "重置对话失败。");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <main className="min-h-screen bg-[#f7f7f4] text-[#171717]">
      <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-4 py-4 sm:px-6">
        <header className="flex min-h-12 items-center justify-between gap-3 border-b border-[#deded8]">
          <div className="min-w-0">
            <p className="text-sm font-semibold">ChatGPT 对话</p>
            <p className="truncate text-xs text-[#6f6f68]">
              单会话内存上下文，支持图片上传与连续编辑
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-[#6f6f68]">
              <span className="sr-only">输出尺寸</span>
              <select
                value={size}
                onChange={(event) =>
                  setSize(event.target.value as (typeof imageSizes)[number])
                }
                disabled={isSubmitting}
                className="h-9 rounded-md border border-[#d2d2cc] bg-white px-2 text-xs outline-none focus:border-[#171717]"
              >
                {imageSizes.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={handleReset}
              disabled={isSubmitting}
              title="重置当前对话"
              className="grid h-9 w-9 place-items-center rounded-md border border-[#d2d2cc] bg-white text-[#454540] transition hover:border-[#171717] disabled:opacity-50"
            >
              <RefreshCcw aria-hidden="true" className="h-4 w-4" />
            </button>
          </div>
        </header>

        <section className="flex min-h-0 flex-1 flex-col">
          <div className="flex-1 overflow-y-auto py-6">
            {messages.length ? (
              <div className="grid gap-6">
                {messages.map((item) => (
                  <MessageBubble key={item.id} message={item} />
                ))}
              </div>
            ) : (
              <EmptyConversation currentImage={currentImage} />
            )}
          </div>

          {currentImage && (
            <section className="mb-3 overflow-hidden rounded-lg border border-[#d2d2cc] bg-white">
              <div className="flex items-center justify-between px-3 py-2 text-xs text-[#6f6f68]">
                <span>当前图片上下文</span>
                <span>{currentImage.model}</span>
              </div>
              <div className="max-h-56 overflow-hidden bg-[#ededdf]">
                <img
                  src={currentImage.src}
                  alt="当前图片上下文"
                  className="mx-auto max-h-56 w-auto object-contain"
                />
              </div>
            </section>
          )}

          {error && (
            <div className="mb-3 flex gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              <AlertCircle
                aria-hidden="true"
                className="mt-0.5 h-4 w-4 shrink-0"
              />
              <p>{error}</p>
            </div>
          )}

          <form
            onSubmit={handleSubmit}
            className="mb-3 rounded-2xl border border-[#d2d2cc] bg-white p-2 shadow-[0_18px_50px_rgba(25,25,20,0.08)]"
          >
            {selectedImages.length > 0 && (
              <div className="mb-2 flex gap-2 overflow-x-auto px-1 pt-1">
                {selectedImages.map((image) => (
                  <div
                    key={image.id}
                    className="relative h-20 w-20 shrink-0 overflow-hidden rounded-lg border border-[#d2d2cc] bg-[#f3f3ed]"
                  >
                    <img
                      src={image.previewUrl}
                      alt={image.file.name}
                      className="h-full w-full object-cover"
                    />
                    <button
                      type="button"
                      onClick={() => removeSelectedImage(image.id)}
                      title="移除图片"
                      className="absolute right-1 top-1 grid h-6 w-6 place-items-center rounded-full bg-black/70 text-white"
                    >
                      <X aria-hidden="true" className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              rows={3}
              disabled={isSubmitting}
              placeholder="询问或描述要怎么编辑图片"
              className="max-h-40 min-h-16 w-full resize-none rounded-xl border-0 bg-transparent px-3 py-2 text-sm leading-6 text-[#171717] outline-none placeholder:text-[#8a8a82]"
            />

            <div className="flex items-center justify-between gap-3 px-1">
              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  multiple
                  disabled={isSubmitting}
                  onChange={(event) => handleImages(event.target.files)}
                  className="sr-only"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isSubmitting}
                  title="上传图片"
                  className="grid h-9 w-9 place-items-center rounded-full border border-[#d2d2cc] text-[#454540] transition hover:border-[#171717] disabled:opacity-50"
                >
                  <Plus aria-hidden="true" className="h-4 w-4" />
                </button>
                <span className="text-xs text-[#7d7d75]">
                  PNG / JPG / WebP，图片会随本轮消息发送
                </span>
              </div>
              <button
                type="submit"
                disabled={!canSubmit}
                title="发送"
                className="grid h-9 w-9 place-items-center rounded-full bg-[#171717] text-white transition hover:bg-[#0f8d7b] disabled:bg-[#c9c9c1] disabled:text-[#77776f]"
              >
                {isSubmitting ? (
                  <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
                ) : (
                  <Send aria-hidden="true" className="h-4 w-4" />
                )}
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}

function EmptyConversation({
  currentImage,
}: {
  currentImage: ConversationImage | null;
}) {
  return (
    <div className="flex min-h-[45vh] flex-col items-center justify-center text-center">
      <div className="grid h-12 w-12 place-items-center rounded-xl border border-[#d2d2cc] bg-white">
        <ImagePlus aria-hidden="true" className="h-5 w-5 text-[#0f8d7b]" />
      </div>
      <h1 className="mt-5 text-2xl font-semibold tracking-tight sm:text-3xl">
        今天要编辑哪张图片？
      </h1>
      <p className="mt-3 max-w-md text-sm leading-6 text-[#6f6f68]">
        像 ChatGPT 一样直接上传图片并输入需求；后续追问会沿用当前图片上下文。
      </p>
      {currentImage && <span className="sr-only">已有当前图片上下文</span>}
    </div>
  );
}

function MessageBubble({ message }: { message: ConversationMessage }) {
  const isUser = message.role === "user";

  return (
    <article
      className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[86%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-[#e8e8e3] text-[#171717]"
            : "border border-[#d2d2cc] bg-white text-[#20201c]"
        }`}
      >
        <div className="mb-2 flex items-center gap-2 text-[11px] text-[#77776f]">
          <span>{isUser ? "你" : "ChatGPT"}</span>
          <time dateTime={message.createdAt}>{formatTime(message.createdAt)}</time>
        </div>
        {message.attachments.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {message.attachments.map((attachment) => (
              <img
                key={attachment.id}
                src={attachment.src}
                alt={attachment.name}
                className="h-24 w-24 rounded-lg border border-[#d2d2cc] object-cover"
              />
            ))}
          </div>
        )}
        {message.content && (
          <p className="whitespace-pre-wrap text-sm leading-6 [overflow-wrap:anywhere]">
            {message.content}
          </p>
        )}
        {message.image && (
          <div className="mt-3 overflow-hidden rounded-lg border border-[#d2d2cc] bg-[#f3f3ed]">
            <img
              src={message.image.src}
              alt="ChatGPT 生成的图片"
              className="max-h-[32rem] w-full object-contain"
            />
          </div>
        )}
      </div>
    </article>
  );
}
