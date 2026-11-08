
"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

type Tool = {
  name: string;
  description: string;
};

type ApiState = "checking" | "online" | "offline";
type ThemePreference = "light" | "dark" | "system";
type AuthMode = "signin" | "signup";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  isError?: boolean;
  toolName?: string;
};

type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
};

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "")
).replace(/\/+$/, "");

function Mark({ small = false }: { small?: boolean }) {
  return (
    <div className={`aegis-mark ${small ? "aegis-mark-small" : ""}`}>
      <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
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
    | "chevron"
    | "trash";
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
      return <svg {...common}><path d="M4 6h16M4 10h16M4 14h10M4 18h8" /></svg>;
    case "terminal":
      return <svg {...common}><path d="m4 7 5 5-5 5M12 17h8" /></svg>;
    case "chevron":
      return <svg {...common}><path d="m9 18 6-6-6-6" /></svg>;
    case "trash":
      return (
        <svg {...common}>
          <path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6" />
          <path d="M10 11v5m4-5v5" />
        </svg>
      );
  }
}

function StatusIndicator({ state }: { state: ApiState }) {
  const labels: Record<ApiState, string> = {
    checking: "Connecting",
    online: "Connected",
    offline: "Offline",
  };

  return (
    <span className={`aegis-status aegis-status-${state}`}>
      <span className="aegis-status-dot" />
      {labels[state]}
    </span>
  );
}

function readMessage(payload: unknown): string {
  if (typeof payload === "string") return payload;

  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;

    if (record.execution && typeof record.execution === "object") {
      const execution = record.execution as Record<string, unknown>;
      if (execution.result !== undefined) return readMessage(execution.result);
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

      if (typeof value === "string" && value.trim()) return value;
      if (value && typeof value === "object") {
        return JSON.stringify(value, null, 2);
      }
    }

    return JSON.stringify(payload, null, 2);
  }

  return "The task was completed, but the API returned no readable result.";
}

function readToolName(payload: unknown): string | undefined {
  if (!payload || typeof payload !== "object") return undefined;

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

  if (typeof record.tool_name === "string") return record.tool_name;
  if (typeof record.tool === "string") return record.tool;

  return undefined;
}

async function readApiPayload(response: Response): Promise<unknown> {
  const responseText = await response.text();

  try {
    return JSON.parse(responseText);
  } catch {
    return responseText;
  }
}

export default function Home() {
  const [apiState, setApiState] = useState<ApiState>("checking");
  const [tools, setTools] = useState<Tool[]>([]);
  const [version, setVersion] = useState("—");

  // Authentication state.
  const [session, setSession] = useState<Session | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authMode, setAuthMode] = useState<AuthMode>("signin");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authBusy, setAuthBusy] = useState<
    "email" | "google" | "signout" | null
  >(null);
  const [authError, setAuthError] = useState("");
  const [authNotice, setAuthNotice] = useState("");

  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [themePreference, setThemePreference] =
    useState<ThemePreference>("system");
  const [isThemeLoaded, setIsThemeLoaded] = useState(false);

  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [deletingConversationId, setDeletingConversationId] = useState<
    string | null
  >(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messageIdPrefix = useId();
  const messageCounterRef = useRef(0);

  const createMessageId = useCallback(() => {
    messageCounterRef.current += 1;
    return `${messageIdPrefix}-message-${messageCounterRef.current}`;
  }, [messageIdPrefix]);

  // --------------------------------------------------
  // Authentication and session management
  // --------------------------------------------------

  useEffect(() => {
    let mounted = true;

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      if (!mounted) return;

      setSession(nextSession);
      setAuthLoading(false);

      if (!nextSession) {
        setMessages([]);
        setConversations([]);
        setConversationId(null);
        setDraft("");
        setIsSending(false);
        setIsLoadingHistory(false);
        setDeletingConversationId(null);
      }

      setAuthError("");
    });

    void supabase.auth.getSession().then(({ data, error }) => {
      if (!mounted) return;

      if (error) {
        setAuthError(error.message);
      }

      setSession(data.session);
      setAuthLoading(false);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  // Get a fresh access token for protected backend requests.
  const getAuthHeaders = useCallback(async () => {
    const {
      data: { session: currentSession },
      error,
    } = await supabase.auth.getSession();

    if (error) {
      throw new Error(error.message);
    }

    if (!currentSession?.access_token) {
      throw new Error("Your session has expired. Please sign in again.");
    }

    return {
      Authorization: `Bearer ${currentSession.access_token}`,
    };
  }, []);

  const handleAuthSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      setAuthError("");
      setAuthNotice("");

      const email = authEmail.trim();

      if (!email || !authPassword) {
        setAuthError("Please enter your email address and password.");
        return;
      }

      setAuthBusy("email");

      try {
        if (authMode === "signup") {
          const { data, error } = await supabase.auth.signUp({
            email,
            password: authPassword,
            options: {
              emailRedirectTo: window.location.origin,
            },
          });

          if (error) throw error;

          if (data.session) {
            setAuthNotice("Your account has been created successfully.");
          } else {
            setAuthNotice(
              "Your account has been created. Please check your email and confirm your address before signing in.",
            );
          }
        } else {
          const { error } = await supabase.auth.signInWithPassword({
            email,
            password: authPassword,
          });

          if (error) throw error;
        }
      } catch (error) {
        setAuthError(
          error instanceof Error
            ? error.message
            : "Authentication failed. Please try again.",
        );
      } finally {
        setAuthBusy(null);
      }
    },
    [authEmail, authPassword, authMode],
  );

  const handleGoogleSignIn = useCallback(async () => {
    setAuthError("");
    setAuthNotice("");
    setAuthBusy("google");

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: window.location.origin,
        },
      });

      if (error) throw error;
    } catch (error) {
      setAuthError(
        error instanceof Error
          ? error.message
          : "Google sign-in failed. Please try again.",
      );
      setAuthBusy(null);
    }
  }, []);

  const handleSignOut = useCallback(async () => {
    setAuthError("");
    setAuthBusy("signout");

    try {
      const { error } = await supabase.auth.signOut();

      if (error) throw error;
    } catch (error) {
      setAuthError(
        error instanceof Error
          ? error.message
          : "Unable to sign out. Please try again.",
      );
    } finally {
      setAuthBusy(null);
    }
  }, []);

  // --------------------------------------------------
  // Theme preference
  // --------------------------------------------------

  // Load the saved theme once when the component mounts.
  useEffect(() => {
    const saved = window.localStorage.getItem("aegis-theme");

    if (saved === "light" || saved === "dark" || saved === "system") {
      setThemePreference(saved);
    }

    setIsThemeLoaded(true);
  }, []);

  // Apply theme changes only after the saved preference has loaded.
  useEffect(() => {
    if (!isThemeLoaded) return;

    const media = window.matchMedia("(prefers-color-scheme: dark)");

    const applyTheme = () => {
      const resolvedTheme =
        themePreference === "system"
          ? media.matches
            ? "dark"
            : "light"
          : themePreference;

      document.documentElement.dataset.theme = resolvedTheme;
    };

    applyTheme();

    // Persist the user's current selection.
    window.localStorage.setItem("aegis-theme", themePreference);

    // Follow operating-system changes only when System is selected.
    if (themePreference === "system") {
      media.addEventListener("change", applyTheme);

      return () => {
        media.removeEventListener("change", applyTheme);
      };
    }
  }, [themePreference, isThemeLoaded]);

  // --------------------------------------------------
  // Backend connection
  // --------------------------------------------------

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

  // --------------------------------------------------
  // Conversation history
  // --------------------------------------------------

  const loadConversations = useCallback(async () => {
    if (!session) return;

    try {
      const authHeaders = await getAuthHeaders();

      const response = await fetch(`${API_URL}/api/conversations`, {
        headers: authHeaders,
        cache: "no-store",
      });

      const payload = await readApiPayload(response);

      if (!response.ok) {
        throw new Error(readMessage(payload));
      }

      const items =
        payload &&
        typeof payload === "object" &&
        Array.isArray((payload as Record<string, unknown>).conversations)
          ? (payload as Record<string, unknown>).conversations
          : [];

      setConversations(items as Conversation[]);
    } catch (error) {
      console.error("Conversation history error:", error);
    }
  }, [session, getAuthHeaders]);

  useEffect(() => {
    if (!session || authLoading) return;

    const timer = window.setTimeout(() => {
      void loadConversations();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [session, authLoading, loadConversations]);

  const openConversation = useCallback(
    async (id: string) => {
      if (isSending || isLoadingHistory) return;

      if (id === conversationId) {
        setMobileOpen(false);
        return;
      }

      setIsLoadingHistory(true);

      try {
        const authHeaders = await getAuthHeaders();

        const response = await fetch(
          `${API_URL}/api/conversations/${id}/messages`,
          {
            headers: authHeaders,
            cache: "no-store",
          },
        );

        const payload = await readApiPayload(response);

        if (!response.ok) {
          throw new Error(readMessage(payload));
        }

        if (!payload || typeof payload !== "object") {
          throw new Error("The API returned an invalid conversation.");
        }

        const record = payload as Record<string, unknown>;
        const history = Array.isArray(record.messages)
          ? record.messages
          : [];

        const restoredMessages: Message[] = history.map((item: unknown) => {
          const message =
            item && typeof item === "object"
              ? (item as Record<string, unknown>)
              : {};

          return {
            id:
              message.id !== undefined
                ? String(message.id)
                : createMessageId(),
            role: message.role === "user" ? "user" : "assistant",
            content:
              typeof message.content === "string" ? message.content : "",
            toolName:
              typeof message.tool_name === "string"
                ? message.tool_name
                : undefined,
          };
        });

        setMessages(restoredMessages);
        setConversationId(id);
        setDraft("");
        setMobileOpen(false);
      } catch (error) {
        window.alert(
          error instanceof Error
            ? error.message
            : "Unable to open this conversation.",
        );
      } finally {
        setIsLoadingHistory(false);
      }
    },
    [
      conversationId,
      createMessageId,
      getAuthHeaders,
      isLoadingHistory,
      isSending,
    ],
  );

  const deleteConversation = useCallback(
    async (id: string) => {
      if (isSending || deletingConversationId) return;

      const confirmed = window.confirm(
        "Are you sure you want to permanently delete this conversation?",
      );

      if (!confirmed) return;

      setDeletingConversationId(id);

      try {
        const authHeaders = await getAuthHeaders();

        const response = await fetch(
          `${API_URL}/api/conversations/${id}`,
          {
            method: "DELETE",
            headers: authHeaders,
          },
        );

        const payload = await readApiPayload(response);

        if (!response.ok) {
          throw new Error(readMessage(payload));
        }

        setConversations((current) =>
          current.filter((conversation) => conversation.id !== id),
        );

        if (conversationId === id) {
          setConversationId(null);
          setMessages([]);
          setDraft("");
        }
      } catch (error) {
        window.alert(
          error instanceof Error
            ? error.message
            : "Unable to delete this conversation.",
        );
      } finally {
        setDeletingConversationId(null);
      }
    },
    [conversationId, deletingConversationId, getAuthHeaders, isSending],
  );

  // --------------------------------------------------
  // Chat behavior
  // --------------------------------------------------

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  async function handleSend(text?: string) {
    const content = (text ?? draft).trim();

    if (
      !content ||
      !session ||
      isSending ||
      isLoadingHistory
    ) {
      return;
    }

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
      const authHeaders = await getAuthHeaders();

      const response = await fetch(`${API_URL}/api/tasks`, {
        method: "POST",
        headers: {
          ...authHeaders,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          task: content,
          conversation_id: conversationId,
        }),
      });

      const payload = await readApiPayload(response);

      if (!response.ok) {
        throw new Error(
          readMessage(payload) ||
            `Request failed with status ${response.status}.`,
        );
      }

      if (
        payload &&
        typeof payload === "object" &&
        typeof (payload as Record<string, unknown>).conversation_id ===
          "string"
      ) {
        setConversationId(
          (payload as Record<string, unknown>).conversation_id as string,
        );
      }

      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: "assistant",
          content: readMessage(payload),
          toolName: readToolName(payload),
        },
      ]);

      void loadConversations();
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
    if (isSending || isLoadingHistory) return;

    setConversationId(null);
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

  // --------------------------------------------------
  // Suggested starting prompts
  // --------------------------------------------------

  const suggestions = [
    {
      title: "Perform a calculation",
      description: "Solve mathematical problems with the calculator tool.",
      prompt: "Calculate 245 multiplied by 18.",
      icon: "calculator" as const,
      number: "01",
    },
    {
      title: "Analyze some text",
      description: "Extract useful information and text metrics.",
      prompt:
        "Analyze this text: AEGIS is an intelligent agent that combines tools, memory and structured execution.",
      icon: "text" as const,
      number: "02",
    },
    {
      title: "Explore capabilities",
      description: "Discover the tools currently available to AEGIS.",
      prompt: "What tools and capabilities are currently available to you?",
      icon: "terminal" as const,
      number: "03",
    },
  ];

  // --------------------------------------------------
  // Authentication screen
  // --------------------------------------------------

  if (authLoading) {
    return (
      <main className="aegis-auth-shell">
        <div className="aegis-auth-card aegis-auth-loading">
          <Mark />
          <div className="aegis-auth-brand">AEGIS</div>
          <p>Restoring your secure session...</p>
        </div>
      </main>
    );
  }

  if (!session) {
    return (
      <main className="aegis-auth-shell">
        <div className="aegis-auth-card">
          <div className="aegis-auth-brand-lockup">
            <Mark />
            <div>
              <div className="aegis-auth-brand">AEGIS</div>
              <div className="aegis-auth-brand-caption">
                INTELLIGENCE PLATFORM
              </div>
            </div>
          </div>

          <div className="aegis-auth-heading">
            <div className="aegis-auth-eyebrow">YOUR WORKSPACE AWAITS</div>
            <h1>
              {authMode === "signin" ? "Welcome back." : "Create your account."}
            </h1>
            <p>
              {authMode === "signin"
                ? "Sign in to continue working with AEGIS."
                : "Create an account to start using your AEGIS workspace."}
            </p>
          </div>

          <button
            type="button"
            onClick={() => void handleGoogleSignIn()}
            disabled={authBusy !== null}
            className="aegis-auth-google"
          >
            <svg
              viewBox="0 0 48 48"
              width="19"
              height="19"
              aria-hidden="true"
            >
              <path
                fill="#EA4335"
                d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z"
                transform="translate(0 4)"
              />
              <path
                fill="#4285F4"
                d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.25 5.48-4.73 7.18l7.64 5.93c4.46-4.13 7.13-10.2 7.13-17.58Z"
              />
              <path
                fill="#FBBC05"
                d="M10.53 28.59A14.4 14.4 0 0 1 9.75 24c0-1.59.27-3.13.75-4.59l-7.98-6.19A23.9 23.9 0 0 0 0 24c0 3.87.93 7.52 2.56 10.78l7.97-6.19Z"
              />
              <path
                fill="#34A853"
                d="M24 48c6.48 0 11.93-2.13 15.9-5.87l-7.64-5.93c-2.12 1.42-4.84 2.27-8.26 2.27-6.26 0-11.57-4.22-13.46-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z"
              />
            </svg>
            {authBusy === "google" ? "Connecting..." : "Continue with Google"}
          </button>

          <div className="aegis-auth-divider">
            <span>OR CONTINUE WITH EMAIL</span>
          </div>

          <form onSubmit={handleAuthSubmit} className="aegis-auth-form">
            <label htmlFor="aegis-auth-email">Email address</label>
            <input
              id="aegis-auth-email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={authEmail}
              onChange={(event) => setAuthEmail(event.target.value)}
              required
              disabled={authBusy !== null}
            />

            <label htmlFor="aegis-auth-password">Password</label>
            <input
              id="aegis-auth-password"
              type="password"
              autoComplete={
                authMode === "signin" ? "current-password" : "new-password"
              }
              placeholder="Enter your password"
              value={authPassword}
              onChange={(event) => setAuthPassword(event.target.value)}
              required
              minLength={6}
              disabled={authBusy !== null}
            />

            {authError && (
              <div className="aegis-auth-error" role="alert">
                {authError}
              </div>
            )}

            {authNotice && (
              <div className="aegis-auth-notice" role="status">
                {authNotice}
              </div>
            )}

            <button
              type="submit"
              disabled={authBusy !== null}
              className="aegis-auth-submit"
            >
              {authBusy === "email"
                ? "Please wait..."
                : authMode === "signin"
                  ? "Sign in"
                  : "Create account"}
            </button>
          </form>

          <div className="aegis-auth-switch">
            {authMode === "signin" ? (
              <>
                New to AEGIS?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode("signup");
                    setAuthError("");
                    setAuthNotice("");
                  }}
                >
                  Create an account
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode("signin");
                    setAuthError("");
                    setAuthNotice("");
                  }}
                >
                  Sign in
                </button>
              </>
            )}
          </div>

          <div className="aegis-auth-footer">
            Secure authentication powered by Supabase
            <span>© 2026 AEGIS · Asad Yar</span>
          </div>
        </div>
      </main>
    );
  }

  // --------------------------------------------------
  // Authenticated user information
  // --------------------------------------------------

  const userEmail = session.user.email || "AEGIS user";

  const metadataName =
    typeof session.user.user_metadata?.full_name === "string"
      ? session.user.user_metadata.full_name
      : typeof session.user.user_metadata?.name === "string"
        ? session.user.user_metadata.name
        : "";

  const profileName =
    metadataName || userEmail.split("@")[0] || "AEGIS user";

  const profileInitials = profileName
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("") || "A";

  // --------------------------------------------------
  // Interface
  // --------------------------------------------------

  return (
    <main className="aegis-shell">
      {mobileOpen && (
        <button
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
          className="aegis-mobile-overlay"
        />
      )}

      <aside className={`aegis-sidebar ${mobileOpen ? "is-open" : ""}`}>
        <div className="aegis-brand">
          <div className="aegis-brand-lockup">
            <Mark />
            <div>
              <div className="aegis-brand-name">AEGIS</div>
              <div className="aegis-brand-caption">
                INTELLIGENCE PLATFORM
              </div>
            </div>
          </div>

          <button
            onClick={() => setMobileOpen(false)}
            className="aegis-icon-button aegis-mobile-close"
            aria-label="Close menu"
          >
            <Icon name="close" />
          </button>
        </div>

        <div className="aegis-sidebar-actions">
          <button
            onClick={handleNewChat}
            disabled={isSending || isLoadingHistory}
            className="aegis-primary-button"
          >
            <Icon name="plus" size={18} />
            <span>New conversation</span>
          </button>
        </div>

        <div className="aegis-sidebar-section">
          <div className="aegis-section-label">WORKSPACE</div>
          <div className="aegis-nav-active">
            <Icon name="message" size={18} />
            <span>AI assistant</span>
            <span className="aegis-nav-indicator" />
          </div>
        </div>

        <div className="aegis-sidebar-scroll">
          <section className="aegis-history-section">
            <div className="aegis-section-label aegis-history-heading">
              <span>RECENT CONVERSATIONS</span>
              <button
                type="button"
                onClick={() => void loadConversations()}
                disabled={isLoadingHistory}
                title="Refresh conversation history"
                aria-label="Refresh conversation history"
                className="aegis-history-refresh"
              >
                <Icon name="refresh" size={14} />
              </button>
            </div>

            {isLoadingHistory ? (
              <div className="aegis-empty-tools">
                <p>Loading conversation...</p>
              </div>
            ) : conversations.length > 0 ? (
              <div className="aegis-conversation-list">
                {conversations.map((conversation) => (
                  <div
                    key={conversation.id}
                    className={`aegis-history-item ${
                      conversation.id === conversationId ? "is-active" : ""
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => void openConversation(conversation.id)}
                      disabled={isSending || isLoadingHistory}
                      className="aegis-history-open"
                      title={conversation.title}
                    >
                      <Icon name="message" size={15} />
                      <span>{conversation.title || "New conversation"}</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => void deleteConversation(conversation.id)}
                      disabled={
                        isSending || deletingConversationId !== null
                      }
                      className="aegis-history-delete"
                      title="Delete conversation"
                      aria-label={`Delete ${conversation.title}`}
                    >
                      {deletingConversationId === conversation.id ? (
                        <span className="aegis-delete-loading">...</span>
                      ) : (
                        <Icon name="trash" size={15} />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="aegis-empty-tools">
                <p>No saved conversations yet.</p>
                <span>Your conversations will appear here.</span>
              </div>
            )}
          </section>

          <section className="aegis-sidebar-explore">
            <div className="aegis-suggestions-heading">
              <div className="aegis-suggestions-icon">
                <Icon name="spark" size={17} />
              </div>
              <div>
                <div className="aegis-suggestions-title">Explore AEGIS</div>
                <div className="aegis-suggestions-subtitle">
                  Choose a starting point for your conversation
                </div>
              </div>
            </div>

            <div className="aegis-suggestions">
              {suggestions.map((item) => (
                <button
                  key={item.title}
                  onClick={() => {
                    setMobileOpen(false);
                    void handleSend(item.prompt);
                  }}
                  disabled={isSending || isLoadingHistory}
                  className="aegis-suggestion-card"
                >
                  <div className="aegis-card-top">
                    <div className="aegis-card-icon">
                      <Icon name={item.icon} size={21} />
                    </div>
                    <span className="aegis-card-number">{item.number}</span>
                  </div>

                  <div className="aegis-card-title">{item.title}</div>
                  <p className="aegis-card-description">
                    {item.description}
                  </p>

                  <div className="aegis-card-action">
                    Explore
                    <Icon name="chevron" size={16} />
                  </div>
                </button>
              ))}
            </div>
          </section>

          <div className="aegis-section-label">REGISTERED TOOLS</div>

          {apiState === "online" && tools.length > 0 ? (
            <div className="aegis-tool-list">
              {tools.map((tool) => (
                <div
                  key={tool.name}
                  title={tool.description}
                  className="aegis-tool"
                >
                  <span className="aegis-tool-dot" />
                  <span>{tool.name.replace(/_/g, " ")}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="aegis-empty-tools">
              <p>
                {apiState === "checking"
                  ? "Checking registered tools..."
                  : "No live tools available"}
              </p>
              <span>
                {apiState === "offline"
                  ? "Start the API to retrieve your registered tools."
                  : "Your available capabilities will appear here."}
              </span>
            </div>
          )}

          <div className="aegis-system-info">
            <div className="aegis-section-label">SYSTEM INFORMATION</div>
            <div className="aegis-info-row">
              <span>API version</span>
              <span className="aegis-mono">{version}</span>
            </div>
            <div className="aegis-info-row">
              <span>Environment</span>
              <span>
                {process.env.NODE_ENV === "production"
                  ? "Production"
                  : "Local"}
              </span>
            </div>
          </div>
        </div>

        <div className="aegis-profile">
          <div className="aegis-profile-row">
            <div className="aegis-avatar">{profileInitials}</div>
            <div className="aegis-profile-details">
              <div className="aegis-profile-name">{profileName}</div>
              <div className="aegis-profile-caption" title={userEmail}>
                {userEmail}
              </div>
            </div>
            <button
              type="button"
              onClick={() => void handleSignOut()}
              disabled={authBusy !== null}
              className="aegis-signout-button"
              title="Sign out"
              aria-label="Sign out"
            >
              {authBusy === "signout" ? "..." : "Sign out"}
            </button>
          </div>
          <div className="aegis-copyright">© 2026 AEGIS · Asad Yar</div>
        </div>
      </aside>

      <section className="aegis-main">
        <header className="aegis-header">
          <div className="aegis-header-left">
            <button
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
              className="aegis-icon-button aegis-mobile-menu"
            >
              <Icon name="menu" size={21} />
            </button>

            <div>
              <div className="aegis-header-title">AI assistant</div>
              <div className="aegis-header-subtitle">
                {conversationId
                  ? "Saved conversation"
                  : "Your intelligent workspace"}
              </div>
            </div>
          </div>

          <div className="aegis-header-right">
            <select
              className="aegis-theme-select"
              value={themePreference}
              onChange={(event) =>
                setThemePreference(event.target.value as ThemePreference)
              }
              aria-label="Appearance theme"
              title="Choose appearance"
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>

            <StatusIndicator state={apiState} />
            <div className="aegis-header-divider" />
            <button
              onClick={handleRefresh}
              disabled={apiState === "checking"}
              title="Refresh backend connection"
              aria-label="Refresh backend connection"
              className="aegis-icon-button aegis-refresh-button"
            >
              <Icon name="refresh" size={18} />
            </button>
          </div>
        </header>

        <div className="aegis-conversation">
          <div className="aegis-content">
            {messages.length === 0 ? (
              <div className="aegis-welcome">
                <div className="aegis-welcome-label">
                  <Mark />
                  <div>
                    <div className="aegis-eyebrow">AEGIS INTELLIGENCE</div>
                    <div className="aegis-welcome-caption">
                      Your workspace is ready
                    </div>
                  </div>
                </div>

                <h1 className="aegis-hero-title">
                  Think beyond.
                  <br />
                  <span>Work smarter with AEGIS.</span>
                </h1>

                <p className="aegis-hero-description">
                  An intelligent agent built to reason, use tools, and help you
                  turn ideas into meaningful outcomes.
                </p>

                {apiState === "offline" && (
                  <div className="aegis-offline-notice">
                    <span className="aegis-offline-dot" />
                    <div>
                      <strong>Backend is not connected</strong>
                      <p>
                        Start your FastAPI server to execute tasks through
                        AEGIS.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="aegis-messages">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`aegis-message-row ${
                      message.role === "user"
                        ? "is-user"
                        : "is-assistant"
                    }`}
                  >
                    {message.role === "assistant" && <Mark small />}

                    <div className="aegis-message-column">
                      <div
                        className={`aegis-message-author ${
                          message.role === "user" ? "user-author" : ""
                        }`}
                      >
                        {message.role === "user" ? "YOU" : "AEGIS"}
                      </div>

                      <div
                        className={`aegis-message-bubble ${
                          message.role === "user"
                            ? "aegis-user-bubble"
                            : message.isError
                              ? "aegis-error-bubble"
                              : "aegis-assistant-bubble"
                        }`}
                      >
                        <div className="whitespace-pre-wrap wrap-break-words">
                          {message.content}
                        </div>
                      </div>

                      {message.toolName && (
                        <div className="aegis-tool-execution">
                          <span className="aegis-tool-dot" />
                          Executed with{" "}
                          {message.toolName.replace(/_/g, " ")}
                        </div>
                      )}
                    </div>

                    {message.role === "user" && (
                      <div className="aegis-avatar aegis-message-avatar">
                        {profileInitials}
                      </div>
                    )}
                  </div>
                ))}

                {isSending && (
                  <div className="aegis-message-row is-assistant">
                    <Mark small />
                    <div className="aegis-thinking">
                      <div className="aegis-thinking-dots">
                        <span />
                        <span />
                        <span />
                      </div>
                      <span>AEGIS is working</span>
                    </div>
                  </div>
                )}

                <div ref={bottomRef} />
              </div>
            )}
          </div>

          <div className="aegis-composer-area">
            <div className="aegis-composer-wrap">
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void handleSend();
                }}
                className="aegis-composer"
              >
                <textarea
                  ref={textareaRef}
                  value={draft}
                  onChange={(event) => {
                    setDraft(event.target.value);
                    event.target.style.height = "auto";
                    event.target.style.height = `${Math.min(
                      event.target.scrollHeight,
                      160,
                    )}px`;
                  }}
                  onKeyDown={handleKeyDown}
                  rows={1}
                  placeholder="Message AEGIS..."
                  aria-label="Message AEGIS"
                  className="aegis-textarea"
                />

                <div className="aegis-composer-footer">
                  <div className="aegis-composer-hint">
                    <span className="aegis-composer-spark">
                      <Icon name="spark" size={14} />
                    </span>
                    <span className="hidden sm:inline">
                      Enter to send · Shift + Enter for a new line
                    </span>
                    <span className="sm:hidden">Message AEGIS</span>
                  </div>

                  <button
                    type="submit"
                    disabled={
                      !draft.trim() || isSending || isLoadingHistory
                    }
                    aria-label="Send message"
                    className="aegis-send-button"
                  >
                    <Icon name="arrow" size={20} />
                  </button>
                </div>
              </form>

              <div className="aegis-footer-note">
                <span>
                  AEGIS can make mistakes. Verify important results.
                </span>
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
