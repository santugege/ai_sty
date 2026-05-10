"use client";

/* eslint-disable @next/next/no-img-element */

import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import {
  AlertCircle,
  ImagePlus,
  Loader2,
  Plus,
  Send,
  X,
} from "lucide-react";
import {
  createAgentSession,
  getAgentSession,
  listAgentSessions,
  sendAgentSessionMessage,
  type AgentEnvelope,
  type ConversationImage,
  type ConversationListItem,
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

function revokeSelectedImages(images: SelectedImage[]) {
  images.forEach((image) => URL.revokeObjectURL(image.previewUrl));
}

export function AgentImageWorkbench() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const requestSequenceRef = useRef(0);
  const isMountedRef = useRef(false);
  const selectedImagesRef = useRef<SelectedImage[]>([]);
  const [sessions, setSessions] = useState<ConversationListItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
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

  function beginRequest() {
    requestSequenceRef.current += 1;
    return requestSequenceRef.current;
  }

  function isCurrentRequest(requestId: number) {
    return isMountedRef.current && requestSequenceRef.current === requestId;
  }

  function applyEnvelope(envelope: AgentEnvelope) {
    setMessages(envelope.messages);
    setCurrentImage(envelope.currentImage ?? null);
  }

  function clearDraft(images: SelectedImage[] = selectedImages) {
    revokeSelectedImages(images);
    selectedImagesRef.current = [];
    setSelectedImages([]);
    setMessage("");
  }

  async function refreshSessions(nextActiveId?: string, requestId?: number) {
    const envelope = await listAgentSessions();
    if (requestId !== undefined && !isCurrentRequest(requestId)) {
      return;
    }
    setSessions(envelope.sessions);
    const resolvedActiveId = nextActiveId ?? envelope.sessions[0]?.id ?? null;
    setActiveSessionId(resolvedActiveId);
    if (resolvedActiveId) {
      const sessionEnvelope = await getAgentSession(resolvedActiveId);
      if (requestId === undefined || isCurrentRequest(requestId)) {
        applyEnvelope(sessionEnvelope);
      }
    }
  }

  useEffect(() => {
    isMountedRef.current = true;
    const requestId = beginRequest();
    listAgentSessions()
      .then(async (envelope) => {
        if (!isCurrentRequest(requestId)) {
          return;
        }
        setSessions(envelope.sessions);
        const firstSession = envelope.sessions[0];
        if (firstSession) {
          setActiveSessionId(firstSession.id);
          const sessionEnvelope = await getAgentSession(firstSession.id);
          if (isCurrentRequest(requestId)) {
            applyEnvelope(sessionEnvelope);
          }
        }
      })
      .catch((caught) => {
        if (isCurrentRequest(requestId)) {
          setError(caught instanceof Error ? caught.message : "加载会话失败。");
        }
      })
      .finally(() => {
        if (isCurrentRequest(requestId)) {
          setIsLoadingSessions(false);
        }
      });
    return () => {
      isMountedRef.current = false;
      requestSequenceRef.current += 1;
    };
  }, []);

  useEffect(() => {
    selectedImagesRef.current = selectedImages;
  }, [selectedImages]);

  useEffect(() => {
    return () => revokeSelectedImages(selectedImagesRef.current);
  }, []);

  function handleImages(files: FileList | null) {
    const nextImages = Array.from(files ?? []).map((file) => ({
      id: `${file.name}-${file.lastModified}-${crypto.randomUUID()}`,
      file,
      previewUrl: URL.createObjectURL(file),
    }));
    setSelectedImages((previous) => {
      const allImages = [...previous, ...nextImages];
      const keptImages = allImages.slice(0, 4);
      const droppedImages = allImages.slice(4);
      revokeSelectedImages(droppedImages);
      selectedImagesRef.current = keptImages;
      return keptImages;
    });
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
      const nextImages = previous.filter((image) => image.id !== imageId);
      selectedImagesRef.current = nextImages;
      return nextImages;
    });
  }

  async function handleSelectSession(sessionId: string) {
    const requestId = beginRequest();
    setError("");
    setActiveSessionId(sessionId);
    clearDraft();
    setIsSubmitting(true);
    try {
      const envelope = await getAgentSession(sessionId);
      if (isCurrentRequest(requestId)) {
        applyEnvelope(envelope);
      }
    } catch (caught) {
      if (isCurrentRequest(requestId)) {
        setError(caught instanceof Error ? caught.message : "加载会话失败。");
      }
    } finally {
      if (isCurrentRequest(requestId)) {
        setIsSubmitting(false);
      }
    }
  }

  function handleNewSession() {
    beginRequest();
    clearDraft();
    setActiveSessionId(null);
    setMessages([]);
    setCurrentImage(null);
    setError("");
    setIsLoadingSessions(false);
    setIsSubmitting(false);
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
    const requestId = beginRequest();

    try {
      const envelope = activeSessionId
        ? await sendAgentSessionMessage(activeSessionId, formData)
        : await createAgentSession(formData);
      if (!isCurrentRequest(requestId)) {
        return;
      }
      revokeSelectedImages(selectedImages);
      selectedImagesRef.current = [];
      setSelectedImages([]);
      setMessage("");
      applyEnvelope(envelope);
      setActiveSessionId(envelope.conversation.id);
      try {
        await refreshSessions(envelope.conversation.id, requestId);
      } catch (refreshError) {
        if (!isCurrentRequest(requestId)) {
          return;
        }
        setSessions((previous) =>
          previous.some((session) => session.id === envelope.conversation.id)
            ? previous
            : [
                {
                  id: envelope.conversation.id,
                  title: envelope.conversation.title,
                  summary: envelope.conversation.summary,
                  status: envelope.conversation.status,
                  createdAt: envelope.conversation.createdAt,
                  updatedAt: envelope.conversation.updatedAt,
                },
                ...previous,
              ],
        );
        setError(
          refreshError instanceof Error
            ? refreshError.message
            : "刷新会话列表失败。",
        );
      }
    } catch (caught) {
      if (isCurrentRequest(requestId)) {
        setError(caught instanceof Error ? caught.message : "Agent 请求失败。");
      }
    } finally {
      if (isCurrentRequest(requestId)) {
        setIsSubmitting(false);
      }
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
      <div className="grid min-h-screen lg:grid-cols-[18rem_minmax(0,1fr)]">
        <aside className="border-b border-[#deded8] bg-white px-3 py-4 lg:border-b-0 lg:border-r">
          <button
            type="button"
            onClick={handleNewSession}
            className="mb-3 flex h-10 w-full items-center justify-center gap-2 rounded-md border border-[#d2d2cc] text-sm font-medium transition hover:border-[#171717] disabled:opacity-50"
            disabled={isSubmitting}
          >
            <Plus aria-hidden="true" className="h-4 w-4" />
            新会话
          </button>
          <div className="grid gap-1">
            {sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                onClick={() => void handleSelectSession(session.id)}
                disabled={isSubmitting}
                className={`rounded-md px-3 py-2 text-left text-sm transition ${
                  activeSessionId === session.id
                    ? "bg-[#ededdf]"
                    : "hover:bg-[#f3f3ed] disabled:hover:bg-transparent"
                }`}
              >
                <span className="block truncate font-medium">
                  {session.title}
                </span>
                {session.summary && (
                  <span className="mt-1 line-clamp-2 block text-xs leading-5 text-[#6f6f68]">
                    {session.summary}
                  </span>
                )}
              </button>
            ))}
            {isLoadingSessions && (
              <p className="px-3 py-4 text-sm text-[#6f6f68]">加载会话中...</p>
            )}
            {!isLoadingSessions && sessions.length === 0 && (
              <p className="px-3 py-4 text-sm text-[#6f6f68]">暂无会话</p>
            )}
          </div>
        </aside>

        <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-4 py-4 sm:px-6">
          <header className="flex min-h-12 items-center justify-between gap-3 border-b border-[#deded8]">
            <div className="min-w-0">
              <p className="text-sm font-semibold">ChatGPT 对话</p>
              <p className="truncate text-xs text-[#6f6f68]">
                多会话持久上下文，支持图片上传与连续编辑
              </p>
            </div>
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

              <div className="flex flex-wrap items-center justify-between gap-3 px-1">
                <div className="flex min-w-0 flex-1 items-center gap-2">
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
                  <span className="min-w-0 text-xs leading-5 text-[#7d7d75]">
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
                    <Loader2
                      aria-hidden="true"
                      className="h-4 w-4 animate-spin"
                    />
                  ) : (
                    <Send aria-hidden="true" className="h-4 w-4" />
                  )}
                </button>
              </div>
            </form>
          </section>
        </div>
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
        像 ChatGPT 一样直接上传图片并输入需求；每个会话都会保存上下文和摘要。
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
