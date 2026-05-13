"use client";

/* eslint-disable @next/next/no-img-element */

import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
  type ClipboardEvent,
} from "react";
import {
  AlertCircle,
  Check,
  Copy,
  ImagePlus,
  Pencil,
  Plus,
  RotateCcw,
  Send,
  Square,
  X,
} from "lucide-react";
import {
  createAgentSession,
  getAgentSession,
  listAgentSessions,
  sendAgentSessionMessage,
  streamAgentSession,
  streamAgentSessionMessage,
  type AgentEnvelope,
  type AgentStreamEvent,
  type ConversationListItem,
  type ConversationImage,
  type ConversationMessage,
} from "@/lib/agent-api";
import {
  GeneratedImageActions,
  ImagePreviewDialog,
} from "@/components/generated-image-actions";
import {
  imageQualities,
  imageSizes,
  type ImageQuality,
  type ImageSize,
} from "@/lib/tools";

type AgentImageWorkbenchVariant = "full" | "compact";

type AgentImageWorkbenchProps = {
  variant?: AgentImageWorkbenchVariant;
};

type SelectedImage = {
  id: string;
  file: File;
  previewUrl: string;
};

type SubmitAgentMessageOptions = {
  event?: FormEvent<HTMLFormElement>;
  messageOverride?: string;
  imagesOverride?: SelectedImage[];
};

const agentLoadingPhrases = ["生成图片", "添加细节", "润色画面", "保存图片"] as const;
const imageQualityLabels: Record<ImageQuality, string> = {
  auto: "自动质量",
  low: "低质量",
  medium: "中等质量",
  high: "高质量",
};

function classNames(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function revokeSelectedImages(images: SelectedImage[]) {
  images.forEach((image) => URL.revokeObjectURL(image.previewUrl));
}

function createPendingUserMessage(
  content: string,
  images: SelectedImage[],
): ConversationMessage {
  const createdAt = new Date().toISOString();

  return {
    id: `pending-user-${crypto.randomUUID()}`,
    role: "user",
    content,
    attachments: images.map((image) => ({
      id: image.id,
      name: image.file.name,
      mimeType: image.file.type || "application/octet-stream",
      src: image.previewUrl,
      createdAt,
    })),
    responseId: null,
    imageVersionId: images.at(-1)?.id ?? null,
    image: null,
    images: [],
    createdAt,
  };
}

function createStreamingAssistantMessage(): ConversationMessage {
  return {
    id: `streaming-assistant-${crypto.randomUUID()}`,
    role: "assistant",
    content: "",
    attachments: [],
    responseId: null,
    imageVersionId: null,
    image: null,
    images: [],
    createdAt: new Date().toISOString(),
  };
}

function appendAssistantDelta(
  message: ConversationMessage | null,
  delta: string,
): ConversationMessage {
  const baseMessage = message ?? createStreamingAssistantMessage();
  return {
    ...baseMessage,
    content: `${baseMessage.content}${delta}`,
  };
}

export function AgentImageWorkbench({
  variant = "full",
}: AgentImageWorkbenchProps) {
  const isCompact = variant === "compact";
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const activeStreamControllerRef = useRef<AbortController | null>(null);
  const requestSequenceRef = useRef(0);
  const isMountedRef = useRef(false);
  const selectedImagesRef = useRef<SelectedImage[]>([]);
  const [sessions, setSessions] = useState<ConversationListItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [pendingUserMessage, setPendingUserMessage] =
    useState<ConversationMessage | null>(null);
  const [streamingAssistantMessage, setStreamingAssistantMessage] =
    useState<ConversationMessage | null>(null);
  const [selectedImages, setSelectedImages] = useState<SelectedImage[]>([]);
  const [size, setSize] = useState<ImageSize>("1536x1024");
  const [quality, setQuality] = useState<ImageQuality>("auto");
  const [previewImage, setPreviewImage] = useState<ConversationImage | null>(null);
  const [error, setError] = useState("");
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAwaitingAgentResponse, setIsAwaitingAgentResponse] = useState(false);
  const [loadingPhraseIndex, setLoadingPhraseIndex] = useState(0);

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
    setPendingUserMessage(null);
    setStreamingAssistantMessage(null);
    setMessages(envelope.messages);
  }

  function clearDraft(images: SelectedImage[] = selectedImages, revoke = true) {
    if (revoke) {
      revokeSelectedImages(images);
    }
    selectedImagesRef.current = [];
    setSelectedImages([]);
    setMessage("");
  }

  async function refreshSessions(nextActiveId?: string, requestId?: number) {
    const envelope = await listAgentSessions();
    if (requestId !== undefined && !isCurrentRequest(requestId)) {
      return;
    }
    setIsLoadingSessions(false);
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
      activeStreamControllerRef.current?.abort();
      activeStreamControllerRef.current = null;
    };
  }, []);

  useEffect(() => {
    selectedImagesRef.current = selectedImages;
  }, [selectedImages]);

  useEffect(() => {
    return () => revokeSelectedImages(selectedImagesRef.current);
  }, []);

  useEffect(() => {
    if (!isAwaitingAgentResponse) {
      return;
    }

    const timer = window.setInterval(() => {
      setLoadingPhraseIndex(
        (currentIndex) => (currentIndex + 1) % agentLoadingPhrases.length,
      );
    }, 1400);

    return () => window.clearInterval(timer);
  }, [isAwaitingAgentResponse]);

  function handleImages(files: FileList | File[] | null) {
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

  function handleComposerPaste(event: ClipboardEvent<HTMLTextAreaElement>) {
    const imageFiles = Array.from(event.clipboardData.files).filter((file) =>
      file.type.startsWith("image/"),
    );
    if (imageFiles.length === 0) {
      return;
    }

    event.preventDefault();
    handleImages(imageFiles);
  }

  function focusComposer() {
    window.setTimeout(() => textareaRef.current?.focus(), 0);
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
    activeStreamControllerRef.current?.abort();
    activeStreamControllerRef.current = null;
    const requestId = beginRequest();
    setError("");
    setActiveSessionId(sessionId);
    setPendingUserMessage(null);
    setStreamingAssistantMessage(null);
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
    activeStreamControllerRef.current?.abort();
    activeStreamControllerRef.current = null;
    beginRequest();
    clearDraft();
    setActiveSessionId(null);
    setPendingUserMessage(null);
    setStreamingAssistantMessage(null);
    setMessages([]);
    setError("");
    setIsLoadingSessions(false);
    setIsSubmitting(false);
    setIsAwaitingAgentResponse(false);
    setLoadingPhraseIndex(0);
  }

  async function handleCopyMessage(messageToCopy: ConversationMessage) {
    const text = messageToCopy.content.trim();
    if (!text) {
      return;
    }

    try {
      await navigator.clipboard?.writeText(text);
      setCopiedMessageId(messageToCopy.id);
      window.setTimeout(() => setCopiedMessageId(null), 1600);
    } catch {
      setError("复制失败，请手动选择文本复制。");
    }
  }

  function handleEditMessage(messageToEdit: ConversationMessage) {
    if (isSubmitting || messageToEdit.role !== "user") {
      return;
    }

    setMessage(messageToEdit.content);
    setError("");
    focusComposer();
  }

  function handleRegenerateMessage(messageToRegenerate: ConversationMessage) {
    if (isSubmitting || messageToRegenerate.role !== "assistant") {
      return;
    }

    const messageIndex = messages.findIndex(
      (item) => item.id === messageToRegenerate.id,
    );
    const priorMessages =
      messageIndex === -1 ? messages : messages.slice(0, messageIndex);
    const previousUserMessage = [...priorMessages]
      .reverse()
      .find((item) => item.role === "user");
    if (!previousUserMessage?.content.trim()) {
      setError("没有可重新发送的上一条用户消息。");
      return;
    }

    setError("");
    void submitAgentMessage({ messageOverride: previousUserMessage.content });
  }

  function handleContinueEditingImage(image: ConversationImage) {
    if (isSubmitting) {
      return;
    }

    setMessage(`基于这张图继续编辑：${image.prompt || "请描述要调整的地方"}`);
    setError("");
    focusComposer();
  }

  function handleStopGeneration() {
    activeStreamControllerRef.current?.abort();
    activeStreamControllerRef.current = null;
    beginRequest();
    setIsSubmitting(false);
    setIsAwaitingAgentResponse(false);
    setPendingUserMessage(null);
    setStreamingAssistantMessage(null);
    setError("已停止生成。");
  }

  async function submitAgentMessage({
    event,
    messageOverride,
    imagesOverride,
  }: SubmitAgentMessageOptions = {}) {
    event?.preventDefault();
    const draftMessage = messageOverride ?? message;
    const draftImages = imagesOverride ?? selectedImages;
    const canSend =
      !isSubmitting && (draftMessage.trim().length > 0 || draftImages.length > 0);
    if (!canSend) {
      return;
    }

    const formData = new FormData();
    formData.append("message", draftMessage);
    formData.append("size", size);
    formData.append("quality", quality);
    draftImages.forEach((image) => formData.append("images", image.file));

    setError("");
    setIsSubmitting(true);
    setIsAwaitingAgentResponse(true);
    setLoadingPhraseIndex(0);
    setPendingUserMessage(createPendingUserMessage(draftMessage, draftImages));
    setStreamingAssistantMessage(null);
    clearDraft(draftImages, false);
    const requestId = beginRequest();
    const streamController = new AbortController();
    activeStreamControllerRef.current = streamController;
    const { signal } = streamController;

    try {
      let envelope: AgentEnvelope | null = null;
      const handleStreamEvent = (streamEvent: AgentStreamEvent) => {
        if (!isCurrentRequest(requestId)) {
          return;
        }
        if (streamEvent.event === "session") {
          const conversation = streamEvent.data.conversation as
            | AgentEnvelope["conversation"]
            | undefined;
          if (conversation?.id) {
            setActiveSessionId(conversation.id);
          }
          return;
        }
        if (streamEvent.event === "assistant_delta") {
          const delta =
            typeof streamEvent.data.delta === "string"
              ? streamEvent.data.delta
              : "";
          setStreamingAssistantMessage((current) =>
            appendAssistantDelta(current, delta),
          );
          return;
        }
        if (
          streamEvent.event === "image_generation" ||
          streamEvent.event === "image_started"
        ) {
          setIsAwaitingAgentResponse(true);
          return;
        }
        if (streamEvent.event === "final") {
          envelope = streamEvent.data as AgentEnvelope;
        }
      };

      if (activeSessionId) {
        await streamAgentSessionMessage(activeSessionId, formData, handleStreamEvent, signal);
      } else {
        await streamAgentSession(formData, handleStreamEvent, signal);
      }
      if (!envelope) {
        envelope = activeSessionId
          ? await sendAgentSessionMessage(activeSessionId, formData)
          : await createAgentSession(formData);
      }
      if (!isCurrentRequest(requestId)) {
        return;
      }
      const finalEnvelope = envelope;
      revokeSelectedImages(draftImages);
      applyEnvelope(finalEnvelope);
      setActiveSessionId(finalEnvelope.conversation.id);
      try {
        await refreshSessions(finalEnvelope.conversation.id, requestId);
      } catch (refreshError) {
        if (!isCurrentRequest(requestId)) {
          return;
        }
        setIsLoadingSessions(false);
        setSessions((previous) =>
          previous.some((session) => session.id === finalEnvelope.conversation.id)
            ? previous
            : [
                {
                  id: finalEnvelope.conversation.id,
                  title: finalEnvelope.conversation.title,
                  summary: finalEnvelope.conversation.summary,
                  status: finalEnvelope.conversation.status,
                  createdAt: finalEnvelope.conversation.createdAt,
                  updatedAt: finalEnvelope.conversation.updatedAt,
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
        if (caught instanceof DOMException && caught.name === "AbortError") {
          setMessage(draftMessage);
          setSelectedImages(draftImages);
          setPendingUserMessage(null);
          setStreamingAssistantMessage(null);
          selectedImagesRef.current = draftImages;
          return;
        }
        setError(caught instanceof Error ? caught.message : "Agent 请求失败。");
        setMessage(draftMessage);
        setSelectedImages(draftImages);
        setPendingUserMessage(null);
        setStreamingAssistantMessage(null);
        selectedImagesRef.current = draftImages;
      }
    } finally {
      if (isCurrentRequest(requestId)) {
        if (activeStreamControllerRef.current === streamController) {
          activeStreamControllerRef.current = null;
        }
        setIsSubmitting(false);
        setIsAwaitingAgentResponse(false);
      }
    }
  }

  async function handleSubmit(event?: FormEvent<HTMLFormElement>) {
    await submitAgentMessage({ event });
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <section
      className={classNames(
        "agentWorkbenchShell min-w-0 bg-paper text-ink",
        isCompact
          ? "compactAgentWorkbench h-full min-h-0"
          : "min-h-screen px-4 py-4 sm:px-6",
      )}
    >
      <div
        className={classNames(
          "grid min-w-0 overflow-hidden border border-border bg-border shadow-refined lg:grid-cols-[18rem_minmax(0,1fr)]",
          isCompact
            ? "h-full min-h-[42rem] rounded-xl xl:min-h-0"
            : "min-h-screen rounded-xl",
        )}
      >
        <aside className="min-w-0 border-b border-border bg-surface px-3 py-4 lg:border-b-0 lg:border-r">
          <button
            type="button"
            onClick={handleNewSession}
            className="mb-3 flex h-10 w-full items-center justify-center gap-2 rounded-md border border-border text-sm font-medium transition-refined hover:border-ink disabled:opacity-50"
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
                    ? "bg-paper-dim"
                    : "hover:bg-surface-soft disabled:hover:bg-transparent"
                }`}
              >
                <span className="block truncate font-medium">
                  {session.title}
                </span>
              </button>
            ))}
            {isLoadingSessions && (
              <p className="px-3 py-4 text-sm text-ink-light">加载会话中...</p>
            )}
            {!isLoadingSessions && sessions.length === 0 && (
              <p className="px-3 py-4 text-sm text-ink-light">暂无会话</p>
            )}
          </div>
        </aside>

        <div
          className={classNames(
            "flex w-full flex-col bg-paper px-4 py-4 sm:px-6",
            isCompact ? "min-h-0" : "min-h-screen",
          )}
        >
          <header className="flex min-h-12 items-center justify-between gap-3 border-b border-border">
            <div className="min-w-0">
              <p className="text-sm font-semibold">ChatGPT 对话</p>
              <p className="truncate text-xs text-ink-light">
                多会话持久上下文，支持图片上传与连续编辑
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap justify-end gap-2">
              <label className="text-xs text-ink-light">
                <span className="sr-only">输出尺寸</span>
                <select
                  value={size}
                  onChange={(event) => setSize(event.target.value as ImageSize)}
                  disabled={isSubmitting}
                  className="h-9 rounded-md border border-border bg-surface px-2 text-xs outline-none transition-refined focus:border-ink"
                >
                  {imageSizes.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-ink-light">
                <span className="sr-only">图片质量</span>
                <select
                  value={quality}
                  onChange={(event) =>
                    setQuality(event.target.value as ImageQuality)
                  }
                  disabled={isSubmitting}
                  className="h-9 rounded-md border border-border bg-surface px-2 text-xs outline-none transition-refined focus:border-ink"
                >
                  {imageQualities.map((option) => (
                    <option key={option} value={option}>
                      {imageQualityLabels[option]}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </header>

          <section className="flex min-h-0 flex-1 flex-col">
            <div className="flex-1 overflow-y-auto py-6">
              {messages.length || pendingUserMessage ? (
                <div className="grid gap-6">
                  {messages.map((item) => (
                    <MessageBubble
                      key={item.id}
                      message={item}
                      onPreviewImage={setPreviewImage}
                      onCopyMessage={() => void handleCopyMessage(item)}
                      onEditMessage={() => handleEditMessage(item)}
                      onRegenerateMessage={() => handleRegenerateMessage(item)}
                      onContinueEditingImage={handleContinueEditingImage}
                      copied={copiedMessageId === item.id}
                    />
                  ))}
                  {pendingUserMessage && (
                    <MessageBubble
                      key={pendingUserMessage.id}
                      message={pendingUserMessage}
                      onPreviewImage={setPreviewImage}
                      onCopyMessage={() => void handleCopyMessage(pendingUserMessage)}
                      onEditMessage={() => handleEditMessage(pendingUserMessage)}
                      onRegenerateMessage={() =>
                        handleRegenerateMessage(pendingUserMessage)
                      }
                      onContinueEditingImage={handleContinueEditingImage}
                      copied={copiedMessageId === pendingUserMessage.id}
                    />
                  )}
                  {streamingAssistantMessage && (
                    <MessageBubble
                      key={streamingAssistantMessage.id}
                      message={streamingAssistantMessage}
                      onPreviewImage={setPreviewImage}
                      onCopyMessage={() =>
                        void handleCopyMessage(streamingAssistantMessage)
                      }
                      onEditMessage={() => handleEditMessage(streamingAssistantMessage)}
                      onRegenerateMessage={() =>
                        handleRegenerateMessage(streamingAssistantMessage)
                      }
                      onContinueEditingImage={handleContinueEditingImage}
                      copied={copiedMessageId === streamingAssistantMessage.id}
                    />
                  )}
                  {isAwaitingAgentResponse && (
                    <ReceivingBubble phrase={agentLoadingPhrases[loadingPhraseIndex]} />
                  )}
                </div>
              ) : (
                <>
                  <EmptyConversation />
                  {isAwaitingAgentResponse && (
                    <ReceivingBubble phrase={agentLoadingPhrases[loadingPhraseIndex]} />
                  )}
                </>
              )}
            </div>

            {error && (
              <div className="mb-3 flex gap-2 rounded-md border border-error/30 bg-red-50 px-3 py-2 text-sm text-error">
                <AlertCircle
                  aria-hidden="true"
                  className="mt-0.5 h-4 w-4 shrink-0"
                />
                <p>{error}</p>
              </div>
            )}

            <form
              onSubmit={handleSubmit}
              className="mb-3 rounded-xl border border-border bg-surface p-2 shadow-soft"
            >
              {selectedImages.length > 0 && (
                <div className="mb-2 flex gap-2 overflow-x-auto px-1 pt-1">
                  {selectedImages.map((image) => (
                    <div
                      key={image.id}
                      className="relative h-20 w-20 shrink-0 overflow-hidden rounded-lg border border-border bg-surface-soft"
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
                ref={textareaRef}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                onPaste={handleComposerPaste}
                rows={3}
                disabled={isSubmitting}
                placeholder="询问或描述要怎么编辑图片"
                className="max-h-40 min-h-16 w-full resize-none rounded-xl border-0 bg-transparent px-3 py-2 text-sm leading-6 text-ink outline-none placeholder:text-ink-lighter"
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
                    className="grid h-9 w-9 place-items-center rounded-full border border-border text-ink transition-refined hover:border-ink disabled:opacity-50"
                  >
                    <Plus aria-hidden="true" className="h-4 w-4" />
                  </button>
                  <span className="min-w-0 text-xs leading-5 text-ink-light">
                    PNG / JPG / WebP，图片会随本轮消息发送
                  </span>
                </div>
                {isSubmitting ? (
                  <button
                    type="button"
                    onClick={handleStopGeneration}
                    title="停止生成"
                    aria-label="停止生成"
                    className="grid h-9 w-9 place-items-center rounded-full bg-ink text-white transition-refined hover:bg-coral"
                  >
                    <Square aria-hidden="true" className="h-3.5 w-3.5 fill-current" />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={!canSubmit}
                    title="发送"
                    className="grid h-9 w-9 place-items-center rounded-full bg-ink text-white transition-refined hover:bg-accent disabled:bg-paper-dim disabled:text-ink-lighter"
                  >
                    <Send aria-hidden="true" className="h-4 w-4" />
                  </button>
                )}
              </div>
            </form>
          </section>
        </div>
      </div>
      <ImagePreviewDialog
        image={previewImage}
        alt="ChatGPT 生成的图片"
        onClose={() => setPreviewImage(null)}
        downloadName={previewImage?.id ? `chatgpt-image-${previewImage.id}` : "chatgpt-image"}
      />
    </section>
  );
}

function EmptyConversation() {
  return (
    <div className="flex min-h-[45vh] flex-col items-center justify-center text-center">
      <div className="grid h-12 w-12 place-items-center rounded-xl border border-border bg-surface">
        <ImagePlus aria-hidden="true" className="h-5 w-5 text-accent" />
      </div>
      <h1 className="mt-5 text-2xl font-semibold tracking-tight sm:text-3xl">
        今天要编辑哪张图片？
      </h1>
      <p className="mt-3 max-w-md text-sm leading-6 text-ink-light">
        像 ChatGPT 一样直接上传图片并输入需求；每个会话都会保存上下文和摘要。
      </p>
    </div>
  );
}

function ReceivingBubble({ phrase }: { phrase: string }) {
  return (
    <article className="flex w-full justify-start" aria-live="polite">
      <div className="rounded-2xl border border-border bg-surface px-4 py-3 text-ink">
        <div className="mb-2 flex items-center gap-2 text-[11px] text-ink-light">
          <span>ChatGPT</span>
          <span>{phrase}</span>
        </div>
        <div className="flex h-6 items-center gap-1" aria-hidden="true">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-light" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-light [animation-delay:120ms]" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-light [animation-delay:240ms]" />
        </div>
      </div>
    </article>
  );
}

function MessageBubble({
  message,
  onPreviewImage,
  onCopyMessage,
  onEditMessage,
  onRegenerateMessage,
  onContinueEditingImage,
  copied = false,
}: {
  message: ConversationMessage;
  onPreviewImage: (image: ConversationImage) => void;
  onCopyMessage: () => void;
  onEditMessage: () => void;
  onRegenerateMessage: () => void;
  onContinueEditingImage: (image: ConversationImage) => void;
  copied?: boolean;
}) {
  const isUser = message.role === "user";
  const generatedImages =
    message.images && message.images.length > 0
      ? message.images
      : message.image
        ? [message.image]
        : [];

  return (
    <article
      className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[86%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-paper-dim text-ink"
            : "border border-border bg-surface text-ink"
        }`}
      >
        <div className="mb-2 flex items-center gap-2 text-[11px] text-ink-light">
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
                className="h-24 w-24 rounded-lg border border-border object-cover"
              />
            ))}
          </div>
        )}
        {message.content && (
          <p className="whitespace-pre-wrap text-sm leading-6 [overflow-wrap:anywhere]">
            {message.content}
          </p>
        )}
        <MessageActionBar
          isUser={isUser}
          canCopy={message.content.trim().length > 0}
          copied={copied}
          onCopy={onCopyMessage}
          onEdit={onEditMessage}
          onRegenerate={onRegenerateMessage}
        />
        {generatedImages.length > 0 && (
          <div className="mt-3 grid gap-3 sm:grid-cols-[repeat(auto-fit,minmax(14rem,1fr))]">
            {generatedImages.map((generatedImage, imageIndex) => (
              <div
                key={generatedImage.id}
                className="relative overflow-hidden rounded-lg border border-border bg-surface-soft"
              >
                <button
                  type="button"
                  onClick={() => onPreviewImage(generatedImage)}
                  className="block w-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-cyan/40"
                >
                  <img
                    src={generatedImage.src}
                    alt={`ChatGPT generated image ${imageIndex + 1}`}
                    className="max-h-[32rem] w-full object-contain transition-refined hover:brightness-95"
                  />
                </button>
                <GeneratedImageActions
                  image={generatedImage}
                  onPreview={() => onPreviewImage(generatedImage)}
                  downloadName={`chatgpt-image-${generatedImage.id}`}
                  compact
                />
                <button
                  type="button"
                  onClick={() => onContinueEditingImage(generatedImage)}
                  className="flex w-full items-center justify-center gap-2 border-t border-border bg-surface px-3 py-2 text-xs font-medium text-ink-light transition-refined hover:bg-accent-soft hover:text-accent"
                >
                  <Pencil aria-hidden="true" className="h-3.5 w-3.5" />
                  继续编辑
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </article>
  );
}

function MessageActionBar({
  isUser,
  canCopy,
  copied,
  onCopy,
  onEdit,
  onRegenerate,
}: {
  isUser: boolean;
  canCopy: boolean;
  copied: boolean;
  onCopy: () => void;
  onEdit: () => void;
  onRegenerate: () => void;
}) {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-1.5 text-ink-light">
      {canCopy && (
        <button
          type="button"
          onClick={onCopy}
          className="inline-flex h-7 items-center gap-1.5 rounded-full px-2 text-xs transition-refined hover:bg-paper-dim hover:text-ink"
        >
          {copied ? (
            <Check aria-hidden="true" className="h-3.5 w-3.5" />
          ) : (
            <Copy aria-hidden="true" className="h-3.5 w-3.5" />
          )}
          {copied ? "已复制" : "复制"}
        </button>
      )}
      {isUser ? (
        <button
          type="button"
          onClick={onEdit}
          className="inline-flex h-7 items-center gap-1.5 rounded-full px-2 text-xs transition-refined hover:bg-paper-dim hover:text-ink"
        >
          <Pencil aria-hidden="true" className="h-3.5 w-3.5" />
          编辑再发
        </button>
      ) : (
        <button
          type="button"
          onClick={onRegenerate}
          className="inline-flex h-7 items-center gap-1.5 rounded-full px-2 text-xs transition-refined hover:bg-paper-dim hover:text-ink"
        >
          <RotateCcw aria-hidden="true" className="h-3.5 w-3.5" />
          重新生成
        </button>
      )}
    </div>
  );
}
