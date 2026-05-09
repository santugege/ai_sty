"use client";

import { useState } from "react";
import {
  AlertCircle,
  History,
  ImagePlus,
  Loader2,
  MessageSquareText,
  RotateCcw,
  Send,
} from "lucide-react";
import {
  createAgentSession,
  restoreAgentVersion,
  sendAgentMessage,
  type AgentEnvelope,
  type AgentImageVersion,
  type AgentMessage,
} from "@/lib/agent-api";

type AgentSession = AgentEnvelope["session"];

const imageSizes = ["1024x1024", "1536x1024", "1024x1536"] as const;

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function applyEnvelope(
  envelope: AgentEnvelope,
  setters: {
    setSession: (session: AgentSession) => void;
    setMessages: (messages: AgentMessage[]) => void;
    setCurrentImage: (image: AgentImageVersion | null) => void;
    setVersions: (versions: AgentImageVersion[]) => void;
  },
) {
  setters.setSession(envelope.session);
  setters.setMessages(envelope.messages);
  setters.setCurrentImage(envelope.currentImage ?? null);
  setters.setVersions(envelope.versions);
}

export function AgentImageWorkbench() {
  const [file, setFile] = useState<File | null>(null);
  const [instruction, setInstruction] = useState("");
  const [session, setSession] = useState<AgentSession | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [currentImage, setCurrentImage] = useState<AgentImageVersion | null>(
    null,
  );
  const [versions, setVersions] = useState<AgentImageVersion[]>([]);
  const [size, setSize] = useState<(typeof imageSizes)[number]>("1536x1024");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fileLabel = file?.name || "上传初始商品图";
  const canSubmit = instruction.trim() && (session || file) && !isSubmitting;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!instruction.trim()) {
      setError("请输入编辑指令。");
      return;
    }

    if (!session && !file) {
      setError("请先上传一张初始商品图。");
      return;
    }

    setError("");
    setIsSubmitting(true);

    try {
      const envelope = session
        ? await sendAgentMessage(session.id, instruction, size)
        : await createInitialSession();

      applyEnvelope(envelope, {
        setSession,
        setMessages,
        setCurrentImage,
        setVersions,
      });
      setInstruction("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Agent 请求失败。");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function createInitialSession() {
    const formData = new FormData();
    formData.append("instruction", instruction);
    formData.append("size", size);

    if (file) {
      formData.append("image", file);
    }

    return createAgentSession(formData);
  }

  async function handleRestore(version: AgentImageVersion) {
    if (!session || isSubmitting) {
      return;
    }

    setError("");
    setIsSubmitting(true);

    try {
      const envelope = await restoreAgentVersion(session.id, version.id);

      applyEnvelope(envelope, {
        setSession,
        setMessages,
        setCurrentImage,
        setVersions,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "版本恢复失败。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto grid min-h-screen w-full max-w-7xl gap-5 px-5 py-6 sm:px-8 lg:px-10 xl:grid-cols-[20rem_minmax(0,1fr)_23rem]">
      <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-md bg-zinc-950 text-white">
            <ImagePlus aria-hidden="true" className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500">
              Agent session
            </p>
            <h1 className="text-xl font-semibold text-zinc-950">
              多轮商品图编辑
            </h1>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 grid gap-4">
          <label className="block text-sm font-semibold text-zinc-900">
            初始图片
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              disabled={Boolean(session) || isSubmitting}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="peer sr-only"
            />
            <span className="mt-2 flex min-h-28 items-center gap-3 rounded-md border border-dashed border-zinc-300 bg-zinc-50 px-4 py-4 text-sm text-zinc-600 transition hover:border-zinc-950 peer-focus-visible:ring-2 peer-focus-visible:ring-zinc-950 peer-focus-visible:ring-offset-2">
              <ImagePlus aria-hidden="true" className="h-5 w-5 shrink-0" />
              <span className="min-w-0 truncate">{fileLabel}</span>
            </span>
          </label>

          <label className="block text-sm font-semibold text-zinc-900">
            输出尺寸
            <select
              value={size}
              onChange={(event) =>
                setSize(event.target.value as (typeof imageSizes)[number])
              }
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

          <label className="block text-sm font-semibold text-zinc-900">
            编辑指令
            <textarea
              value={instruction}
              onChange={(event) => setInstruction(event.target.value)}
              rows={6}
              disabled={isSubmitting}
              placeholder="例如：保留包装结构，换成白底主图并加强金属质感。"
              className="mt-2 w-full resize-none rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm leading-6 text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            />
          </label>

          {error && (
            <div className="flex gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm leading-6 text-red-800">
              <AlertCircle
                aria-hidden="true"
                className="mt-0.5 h-4 w-4 shrink-0"
              />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={!canSubmit}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-zinc-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:bg-zinc-300 disabled:text-zinc-500"
          >
            {isSubmitting ? (
              <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
            ) : (
              <Send aria-hidden="true" className="h-4 w-4" />
            )}
            {session ? "发送追问" : "创建会话"}
          </button>
        </form>

        {session && (
          <div className="mt-5 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-xs leading-5 text-zinc-600">
            <div className="font-semibold text-zinc-900">{session.title}</div>
            <div className="mt-1">状态：{session.status}</div>
          </div>
        )}
      </section>

      <section className="grid min-h-[32rem] overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-zinc-200 px-5 py-3">
          <div>
            <h2 className="text-sm font-semibold text-zinc-950">当前画布</h2>
            <p className="text-xs text-zinc-500">
              {currentImage ? currentImage.model : "等待 Agent 生成图片"}
            </p>
          </div>
          {currentImage?.width && currentImage?.height && (
            <span className="rounded border border-zinc-200 bg-zinc-50 px-2 py-1 text-xs text-zinc-600">
              {currentImage.width} x {currentImage.height}
            </span>
          )}
        </div>

        <div className="grid min-h-[28rem] place-items-center bg-zinc-100 p-4">
          {currentImage ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={currentImage.src}
              alt="当前 Agent 编辑结果"
              className="max-h-[70vh] max-w-full rounded-md border border-zinc-200 bg-white object-contain shadow-sm"
            />
          ) : (
            <div className="grid w-full max-w-md place-items-center rounded-lg border border-dashed border-zinc-300 bg-white px-6 py-14 text-center">
              <ImagePlus aria-hidden="true" className="h-8 w-8 text-zinc-400" />
              <p className="mt-3 text-sm font-semibold text-zinc-900">
                上传图片并发送第一条编辑指令
              </p>
              <p className="mt-1 text-sm leading-6 text-zinc-500">
                生成结果会固定显示在这里，后续指令会沿用当前版本。
              </p>
            </div>
          )}
        </div>
      </section>

      <aside className="grid gap-5">
        <section className="rounded-lg border border-zinc-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 border-b border-zinc-200 px-4 py-3 text-sm font-semibold text-zinc-950">
            <MessageSquareText aria-hidden="true" className="h-4 w-4" />
            对话
          </div>
          <div className="grid max-h-[23rem] gap-3 overflow-y-auto p-4">
            {messages.length ? (
              messages.map((message) => (
                <article
                  key={message.id}
                  className="rounded-md border border-zinc-200 bg-zinc-50 p-3"
                >
                  <div className="flex items-center justify-between gap-2 text-xs text-zinc-500">
                    <span className="font-semibold uppercase text-zinc-700">
                      {message.role}
                    </span>
                    <time dateTime={message.createdAt}>
                      {formatTime(message.createdAt)}
                    </time>
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-zinc-800">
                    {message.content}
                  </p>
                </article>
              ))
            ) : (
              <p className="rounded-md border border-dashed border-zinc-300 bg-zinc-50 p-4 text-sm leading-6 text-zinc-500">
                会话消息会显示在这里。
              </p>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-zinc-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 border-b border-zinc-200 px-4 py-3 text-sm font-semibold text-zinc-950">
            <History aria-hidden="true" className="h-4 w-4" />
            版本
          </div>
          <div className="grid max-h-[25rem] gap-3 overflow-y-auto p-4">
            {versions.length ? (
              versions.map((version, index) => (
                <article
                  key={version.id}
                  className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-3 rounded-md border border-zinc-200 bg-zinc-50 p-2"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={version.src}
                    alt={`版本 ${index + 1}`}
                    className="h-20 w-20 rounded border border-zinc-200 bg-white object-cover"
                  />
                  <div className="min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-zinc-900">
                        Version {index + 1}
                      </span>
                      <span className="text-[11px] text-zinc-500">
                        {formatTime(version.createdAt)}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs leading-5 text-zinc-600">
                      {version.prompt}
                    </p>
                    <button
                      type="button"
                      disabled={
                        !session ||
                        isSubmitting ||
                        session.currentVersionId === version.id
                      }
                      onClick={() => handleRestore(version)}
                      className="mt-2 inline-flex items-center gap-1.5 rounded border border-zinc-300 bg-white px-2 py-1 text-xs font-semibold text-zinc-800 transition hover:border-zinc-950 disabled:text-zinc-400"
                    >
                      <RotateCcw aria-hidden="true" className="h-3.5 w-3.5" />
                      恢复
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <p className="rounded-md border border-dashed border-zinc-300 bg-zinc-50 p-4 text-sm leading-6 text-zinc-500">
                生成和恢复过的图片版本会显示在这里。
              </p>
            )}
          </div>
        </section>
      </aside>
    </main>
  );
}
