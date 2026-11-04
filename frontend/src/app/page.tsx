
"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";

type Tool = {
  name: string;
  description: string;
};

type ApiState = "checking" | "online" | "offline";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  isError?: boolean;
  toolName?: string;
};

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
).replace(/\/+$/, "");

function Mark({ small = false }: { small?: boolean }) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-xl bg-[#625CE5] text-white ${
        small ? "h-9 w-9" : "h-11 w-11"
      }`}
    >
      <svg
        viewBox="0 0 32 32"
        className={small ? "h-5 w-5" : "h-6 w-6"}
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M16 3 27 9v14l-11 6L5 23V9L16 3Z"
          stroke="currentColor"
          strokeWidth="1.6"
        />
        <path
          d="M16 9 22 22H10L16 9Z"
          stroke="currentColor"
          strokeWidth="1.6"
        />
        <path d="M16 15v7" stroke="currentColor" strokeWidth="1.6" />
      </svg>
    </div>
  );
}

function Icon({
  name,
  size = 18,
}: {
  name:
    | "plus"
    | "menu"
    | "arrow"
    | "refresh"
    | "message"
    | "close"
    | "spark"
    | "calculator"
    | "text"
    | "terminal"
    | "chevron";
  size?: number;
}) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.7,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
  };

  switch (name) {
    case "plus":
      return <svg {...common}><path d="M12 5v14M5 12h14" /></svg>;

    case "menu":
      return <svg {...common}><path d="M4 7h16M4 12h16M4 17h16" /></svg>;

    case "arrow":
      return <svg {...common}><path d="M12 19V5M5 12l7-7 7 7" /></svg>;

    case "refresh":
      return (
        <svg {...common}>
          <path d="M20 7v5h-5M4 17v-5h5" />
          <path d="M5.5 9A7 7 0 0 1 18 6l2 6M4 12l2 6a7 7 0 0 0 12.5-3" />
        </svg>
      );

    case "message":
      return (
        <svg {...common}>
          <path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8A8.5 8.5 0 0 1 8.7 3.9a8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z" />
        </svg>
      );

    case "close":
      return <svg {...common}><path d="m18 6-12 12M6 6l12 12" /></svg>;

    case "spark":
      return (
        <svg {...common}>
          <path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Z" />
          <path d="m19 14 .9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9L19 14Z" />
        </svg>
      );

    case "calculator":
      return (
        <svg {...common}>
          <rect x="5" y="3" width="14" height="18" rx="2" />
          <path d="M8 7h8M8 12h2m4 0h2M8 16h2m4 0h2" />
        </svg>
      );

    case "text":
      return (
        <svg {...common}>
          <path d="M4 6h16M4 10h16M4 14h10M4 18h8" />
        </svg>
      );

    case "terminal":
      return (
        <svg {...common}>
          <path d="m4 7 5 5-5 5M12 17h8" />
        </svg>
      );

    case "chevron":
      return <svg {...common}><path d="m9 18 6-6-6-6" /></svg>;
  }
}

function StatusIndicator({ state }: { state: ApiState }) {
  const labels: Record<ApiState, string> = {
    checking: "Connecting",
    online: "Connected",
    offline: "Offline",
  };

  return (
    <span className="inline-flex items-center gap-2 text-xs text-[#777B8C]">
      <span
        className={`h-2 w-2 rounded-full ${
          state === "online"
            ? "bg-[#25845D]"
            : state === "checking"
              ? "animate-pulse bg-[#B77926]"
              : "bg-[#C45F64]"
        }`}
      />
      {labels[state]}
    </span>
  );
}

function readMessage(payload: unknown): string {
  if (typeof payload === "string") {
    return payload;
  }

  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;

    if (record.execution && typeof record.execution === "object") {
      const execution = record.execution as Record<string, unknown>;

      if (execution.result !== undefined) {
        return readMessage(execution.result);
      }
    }

    for (const key of [
      "response",
      "result",
      "output",
      "message",
      "answer",
      "content",
      "detail",
    ]) {
      const value = record[key];

      if (typeof value === "string" && value.trim()) {
        return value;
      }

      if (value && typeof value === "object") {
        return JSON.stringify(value, null, 2);
      }
    }

    return JSON.stringify(payload, null, 2);
  }

  return "The task was completed, but the API returned no readable result.";
}

function readToolName(payload: unknown): string | undefined {
  if (!payload || typeof payload !== "object") {
    return undefined;
  }

  const record = payload as Record<string, unknown>;

  const execution = record.execution;

  if (execution && typeof execution === "object") {
    const executionRecord = execution as Record<string, unknown>;

    if (
      typeof executionRecord.tool_name === "string" &&
      executionRecord.tool_name !== "conversation"
    ) {
      return executionRecord.tool_name;
    }
  }

  if (typeof record.tool_name === "string") {
    return record.tool_name;
  }

  if (typeof record.tool === "string") {
    return record.tool;
  }

  return undefined;
}

export default function Home() {
  const [apiState, setApiState] = useState<ApiState>("checking");
  const [tools, setTools] = useState<Tool[]>([]);
  const [version, setVersion] = useState("—");
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const messageIdPrefix = useId();
  const messageCounterRef = useRef(0);

  const createMessageId = useCallback(() => {
    messageCounterRef.current += 1;
    return `${messageIdPrefix}-message-${messageCounterRef.current}`;
  }, [messageIdPrefix]);

  const checkBackend = useCallback(async () => {
    try {
      const [healthResponse, toolsResponse] = await Promise.all([
        fetch(`${API_URL}/api/health`, { cache: "no-store" }),
        fetch(`${API_URL}/api/tools`, { cache: "no-store" }),
      ]);

      if (!healthResponse.ok || !toolsResponse.ok) {
        throw new Error("Backend returned an unsuccessful response.");
      }

      const health = await healthResponse.json();
      const toolsData = await toolsResponse.json();

      const rawTools = Array.isArray(toolsData)
        ? toolsData
        : Array.isArray(toolsData?.tools)
          ? toolsData.tools
          : [];

      const normalizedTools: Tool[] = rawTools
        .filter(
          (item: unknown) =>
            item !== null &&
            typeof item === "object" &&
            typeof (item as Record<string, unknown>).name === "string",
        )
        .map((item: unknown) => {
          const record = item as Record<string, unknown>;

          return {
            name: String(record.name),
            description:
              typeof record.description === "string"
                ? record.description
                : "Registered AEGIS capability.",
          };
        });

      setTools(normalizedTools);
      setVersion(health.version || "Unknown");
      setApiState("online");
    } catch {
      setApiState("offline");
    }
  }, []);

  const handleRefresh = useCallback(() => {
    setApiState("checking");
    void checkBackend();
  }, [checkBackend]);

  useEffect(() => {
    const initialCheck = window.setTimeout(() => {
      void checkBackend();
    }, 0);

    const interval = window.setInterval(() => {
      void checkBackend();
    }, 30000);

    return () => {
      window.clearTimeout(initialCheck);
      window.clearInterval(interval);
    };
  }, [checkBackend]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  async function handleSend(text?: string) {
    const content = (text ?? draft).trim();

    if (!content || isSending) return;

    const userMessage: Message = {
      id: createMessageId(),
      role: "user",
      content,
    };

    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setIsSending(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    try {
      const response = await fetch(`${API_URL}/api/tasks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ task: content }),
      });

      const responseText = await response.text();

      let payload: unknown;

      try {
        payload = JSON.parse(responseText);
      } catch {
        payload = responseText;
      }

      if (!response.ok) {
        throw new Error(
          readMessage(payload) ||
            `Request failed with status ${response.status}.`,
        );
      }

      const assistantMessage: Message = {
        id: createMessageId(),
        role: "assistant",
        content: readMessage(payload),
        toolName: readToolName(payload),
      };

      setMessages((current) => [...current, assistantMessage]);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "An unexpected error occurred.";

      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: "assistant",
          content: errorMessage,
          isError: true,
        },
      ]);
    } finally {
      setIsSending(false);
      void checkBackend();
    }
  }

  function handleNewChat() {
    setMessages([]);
    setDraft("");
    setMobileOpen(false);
    textareaRef.current?.focus();
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  }

  const suggestions = [
    {
      title: "Perform a calculation",
      description: "Ask AEGIS to solve a mathematical task.",
      prompt: "Calculate 245 multiplied by 18.",
      icon: "calculator" as const,
    },
    {
      title: "Analyze some text",
      description: "Extract useful information and text metrics.",
      prompt:
        "Analyze this text: AEGIS is an intelligent agent that combines tools, memory and structured execution.",
      icon: "text" as const,
    },
    {
      title: "Explore capabilities",
      description: "Discover the tools currently available.",
      prompt: "What tools and capabilities are currently available to you?",
      icon: "terminal" as const,
    },
  ];

  return (
    <main className="flex h-dvh min-h-[560px] overflow-hidden bg-[#F7F8FC] text-[#242638]">
      {mobileOpen && (
        <button
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-30 bg-[#242638]/25 backdrop-blur-[2px] lg:hidden"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-[276px] shrink-0 flex-col border-r border-[#E7E9F1] bg-white transition-transform duration-200 lg:static lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-[82px] shrink-0 items-center justify-between border-b border-[#E7E9F1] px-6">
          <div className="flex items-center gap-3">
            <Mark />
            <div>
              <div className="text-[17px] font-bold tracking-[0.17em] text-[#242638]">
                AEGIS
              </div>
              <div className="mt-0.5 text-[10px] font-medium tracking-[0.04em] text-[#999CAD]">
                Intelligence workspace
              </div>
            </div>
          </div>

          <button
            onClick={() => setMobileOpen(false)}
            className="rounded-lg p-2 text-[#777B8C] transition hover:bg-[#F1F2F9] lg:hidden"
            aria-label="Close menu"
          >
            <Icon name="close" />
          </button>
        </div>

        <div className="px-5 py-5">
          <button
            onClick={handleNewChat}
            className="flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#625CE5] px-4 text-[13px] font-semibold text-white shadow-sm transition hover:bg-[#514ACB]"
          >
            <Icon name="plus" size={16} />
            New conversation
          </button>
        </div>

        <div className="px-5">
          <div className="mb-3 px-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#999CAD]">
            Workspace
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-[#EAE5FA] bg-[#F0EEFF] px-3.5 py-3 text-[13px] font-semibold text-[#514ACB]">
            <Icon name="message" size={17} />
            <span>AI assistant</span>
            <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[#625CE5]" />
          </div>
        </div>

        <div className="mt-9 min-h-0 flex-1 overflow-y-auto px-5">
          <div className="mb-3 px-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#999CAD]">
            Registered tools
          </div>

          {apiState === "online" && tools.length > 0 ? (
            <div className="space-y-1">
              {tools.map((tool) => (
                <div
                  key={tool.name}
                  title={tool.description}
                  className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-[12px] text-[#777B8C] transition hover:bg-[#F7F8FC]"
                >
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#25845D]" />
                  <span className="truncate">
                    {tool.name.replace(/_/g, " ")}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-[#E7E9F1] bg-[#FAFAFD] px-3.5 py-4">
              <p className="text-[12px] font-medium text-[#777B8C]">
                {apiState === "checking"
                  ? "Checking registered tools..."
                  : "No live tools available"}
              </p>
              <p className="mt-1.5 text-[11px] leading-5 text-[#999CAD]">
                {apiState === "offline"
                  ? "Start the local API to retrieve your registered tools."
                  : "Registered capabilities will appear here."}
              </p>
            </div>
          )}

          <div className="mt-8 border-t border-[#E7E9F1] pt-6">
            <div className="mb-3 px-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#999CAD]">
              System information
            </div>

            <div className="flex items-center justify-between gap-2 px-2 py-2.5 text-[11px]">
              <span className="text-[#777B8C]">API version</span>
              <span className="font-mono text-[10px] text-[#999CAD]">
                {version}
              </span>
            </div>

            <div className="flex items-center justify-between px-2 py-2.5 text-[11px]">
              <span className="text-[#777B8C]">Environment</span>
              <span className="text-[#777B8C]">
                {process.env.NODE_ENV === "production"
                  ? "Production"
                  : "Local"}
              </span>
            </div>
          </div>
        </div>

        <div className="shrink-0 border-t border-[#E7E9F1] px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-[#EAE5FA] bg-[#F0EEFF] text-[12px] font-semibold text-[#625CE5]">
              AY
            </div>
            <div className="min-w-0">
              <div className="text-[12px] font-semibold text-[#242638]">
                Asad Yar
              </div>
              <div className="mt-0.5 text-[10px] text-[#999CAD]">
                Personal workspace
              </div>
            </div>
          </div>
          <div className="mt-5 text-[9px] text-[#B0B2C0]">
            © 2026 AEGIS · Asad Yar
          </div>
        </div>
      </aside>

      {/* Main workspace */}
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[72px] shrink-0 items-center justify-between border-b border-[#E7E9F1] bg-white/90 px-4 sm:px-7">
          <div className="flex min-w-0 items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
              className="rounded-lg p-2 text-[#777B8C] transition hover:bg-[#F1F2F9] lg:hidden"
            >
              <Icon name="menu" />
            </button>

            <div className="min-w-0">
              <div className="text-[13px] font-semibold text-[#242638]">
                AI assistant
              </div>
              <div className="mt-0.5 text-[11px] text-[#999CAD]">
                Your intelligent workspace
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 sm:gap-5">
            <StatusIndicator state={apiState} />

            <div className="h-5 w-px bg-[#E7E9F1]" />

            <button
              onClick={handleRefresh}
              disabled={apiState === "checking"}
              title="Refresh backend connection"
              aria-label="Refresh backend connection"
              className="rounded-lg border border-[#E7E9F1] p-2.5 text-[#777B8C] transition hover:border-[#D9DCE8] hover:bg-[#F7F8FC] disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Icon name="refresh" size={16} />
            </button>
          </div>
        </header>

        {/* Conversation */}
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex-1 overflow-y-auto px-4 sm:px-8">
            <div className="mx-auto flex min-h-full w-full max-w-[900px] flex-col">
              {messages.length === 0 ? (
                <div className="flex flex-1 flex-col justify-center pb-12 pt-10">
                  <div className="mb-8 flex items-center gap-3">
                    <Mark />
                    <div>
                      <div className="text-[12px] font-semibold uppercase tracking-[0.13em] text-[#625CE5]">
                        AEGIS intelligence
                      </div>
                      <div className="mt-1 text-[11px] text-[#999CAD]">
                        Your workspace is ready
                      </div>
                    </div>
                  </div>

                  <h1 className="max-w-[700px] text-[40px] font-semibold leading-[1.12] tracking-[-0.045em] text-[#242638] sm:text-[58px]">
                    Hello, I&apos;m{" "}
                    <span className="text-[#625CE5]">AEGIS.</span>
                  </h1>

                  <p className="mt-5 max-w-[530px] text-[14px] leading-7 text-[#777B8C] sm:text-[15px]">
                    Your intelligent learning companion. Ready to think, learn
                    and assist.
                  </p>

                  <div className="mt-12">
                    <div className="mb-4 flex items-center gap-2">
                      <Icon name="spark" size={15} />
                      <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#999CAD]">
                        Start with an idea
                      </span>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-3">
                      {suggestions.map((item) => (
                        <button
                          key={item.title}
                          onClick={() => void handleSend(item.prompt)}
                          disabled={isSending}
                          className="group rounded-2xl border border-[#E7E9F1] bg-white p-5 text-left transition duration-200 hover:-translate-y-0.5 hover:border-[#CFC6F5] hover:shadow-[0_12px_32px_rgba(61,54,130,0.07)] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#F0EEFF] text-[#625CE5] transition group-hover:bg-[#EAE5FA]">
                            <Icon name={item.icon} size={18} />
                          </div>

                          <div className="mt-5 text-[13px] font-semibold text-[#242638]">
                            {item.title}
                          </div>

                          <p className="mt-2 text-[11px] leading-5 text-[#999CAD]">
                            {item.description}
                          </p>

                          <div className="mt-5 flex items-center gap-1 text-[11px] font-semibold text-[#625CE5]">
                            Try this
                            <Icon name="chevron" size={13} />
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {apiState === "offline" && (
                    <div className="mt-8 flex items-start gap-3 rounded-xl border border-[#F0DFDC] bg-[#FFF9F7] p-4">
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[#C45F64]" />
                      <div>
                        <div className="text-[12px] font-semibold text-[#9C5558]">
                          Backend is not connected
                        </div>
                        <p className="mt-1 text-[11px] leading-5 text-[#A47C7B]">
                          Start your FastAPI server in the project terminal to
                          execute tasks through AEGIS.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex-1 space-y-9 py-9">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex gap-3 sm:gap-4 ${
                        message.role === "user"
                          ? "justify-end"
                          : "justify-start"
                      }`}
                    >
                      {message.role === "assistant" && <Mark small />}

                      <div
                        className={`min-w-0 max-w-[88%] sm:max-w-[78%] ${
                          message.role === "user" ? "order-first" : ""
                        }`}
                      >
                        <div
                          className={`mb-2 text-[11px] font-semibold ${
                            message.role === "user"
                              ? "text-right text-[#999CAD]"
                              : "text-[#625CE5]"
                          }`}
                        >
                          {message.role === "user" ? "You" : "AEGIS"}
                        </div>

                        <div
                          className={`rounded-2xl px-4 py-3.5 text-[13px] leading-7 sm:px-5 ${
                            message.role === "user"
                              ? "rounded-tr-sm bg-[#EAE5FA] text-[#39345D]"
                              : message.isError
                                ? "rounded-tl-sm border border-[#F0DFDC] bg-[#FFF9F7] text-[#925D59]"
                                : "rounded-tl-sm border border-[#E7E9F1] bg-white text-[#424456]"
                          }`}
                        >
                          <div className="whitespace-pre-wrap break-words">
                            {message.content}
                          </div>
                        </div>

                        {message.toolName && (
                          <div className="mt-2 text-[10px] text-[#999CAD]">
                            Executed with {message.toolName.replace(/_/g, " ")}
                          </div>
                        )}
                      </div>

                      {message.role === "user" && (
                        <div className="mt-7 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-[#EAE5FA] bg-white text-[11px] font-semibold text-[#625CE5]">
                          AY
                        </div>
                      )}
                    </div>
                  ))}

                  {isSending && (
                    <div className="flex items-start gap-3">
                      <Mark small />
                      <div className="rounded-2xl rounded-tl-sm border border-[#E7E9F1] bg-white px-5 py-4">
                        <div className="flex items-center gap-2">
                          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#625CE5]" />
                          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#625CE5] [animation-delay:120ms]" />
                          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#625CE5] [animation-delay:240ms]" />
                          <span className="ml-2 text-[11px] text-[#999CAD]">
                            AEGIS is working
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  <div ref={bottomRef} />
                </div>
              )}
            </div>
          </div>

          {/* Composer */}
          <div className="shrink-0 border-t border-[#E7E9F1] bg-white px-4 pb-4 pt-4 sm:px-8 sm:pb-6">
            <div className="mx-auto max-w-[900px]">
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void handleSend();
                }}
                className="rounded-2xl border border-[#D9DCE8] bg-white shadow-[0_5px_24px_rgba(36,38,56,0.045)] transition focus-within:border-[#B7B0F0] focus-within:shadow-[0_5px_28px_rgba(98,92,229,0.09)]"
              >
                <textarea
                  ref={textareaRef}
                  value={draft}
                  onChange={(event) => {
                    setDraft(event.target.value);
                    event.target.style.height = "auto";
                    event.target.style.height = `${Math.min(event.target.scrollHeight, 160)}px`;
                  }}
                  onKeyDown={handleKeyDown}
                  rows={1}
                  placeholder="Ask AEGIS anything..."
                  aria-label="Message AEGIS"
                  className="block max-h-40 min-h-[58px] w-full resize-none bg-transparent px-5 pb-2 pt-4 text-[13px] leading-6 text-[#242638] outline-none placeholder:text-[#B0B2C0]"
                />

                <div className="flex items-center justify-between px-3 pb-3">
                  <div className="flex items-center gap-2 pl-2 text-[10px] text-[#999CAD]">
                    <span className="hidden sm:inline">
                      Enter to send · Shift + Enter for a new line
                    </span>
                    <span className="sm:hidden">Message AEGIS</span>
                  </div>

                  <button
                    type="submit"
                    disabled={!draft.trim() || isSending}
                    aria-label="Send message"
                    className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#625CE5] text-white transition hover:bg-[#514ACB] disabled:cursor-not-allowed disabled:bg-[#E7E9F1] disabled:text-[#999CAD]"
                  >
                    <Icon name="arrow" size={17} />
                  </button>
                </div>
              </form>

              <div className="mt-3 flex items-center justify-between gap-3 text-[10px] text-[#B0B2C0]">
                <span>AEGIS can make mistakes. Verify important results.</span>
                <span className="hidden sm:inline">
                  Powered by your configured AEGIS backend
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
