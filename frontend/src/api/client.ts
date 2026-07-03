const API_BASE = import.meta.env.VITE_API_URL || "";

export function getToken(): string | null {
  return localStorage.getItem("token");
}

export function setToken(token: string): void {
  localStorage.setItem("token", token);
}

export function clearToken(): void {
  localStorage.removeItem("token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    let message = "Request failed";
    if (typeof error.detail === "string") {
      message = error.detail;
    } else if (Array.isArray(error.detail)) {
      message = error.detail.map((e: { msg?: string }) => e.msg).filter(Boolean).join("; ");
    }
    throw new Error(message);
  }
  return response.json();
}

export interface User {
  id: number;
  email: string;
}

export interface CommandLog {
  id: number;
  interaction_id: string;
  guild_id: string | null;
  command_name: string;
  user_id: string | null;
  username: string | null;
  actions_taken: string[];
  status: string;
  created_at: string;
}

export interface GuildConfig {
  id: number;
  guild_id: string;
  guild_name: string | null;
  channel_id: string;
  mirror_webhook_url: string;
  command_rules: {
    auto_mirror: boolean;
    report_keywords: Record<string, string>;
  };
  bot_invite_url: string;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>("/api/auth/me"),
  getLogs: () => request<CommandLog[]>("/api/dashboard/logs"),
  getStats: () => request<{ total: number; by_status: Record<string, number> }>("/api/dashboard/stats"),
  getGuilds: () => request<GuildConfig[]>("/api/guilds"),
  createGuild: (data: {
    guild_id: string;
    guild_name?: string;
    channel_id: string;
    mirror_webhook_url: string;
    command_rules?: Record<string, unknown>;
  }) =>
    request<GuildConfig>("/api/guilds", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateGuild: (
    guildId: string,
    data: Partial<{
      guild_name: string;
      channel_id: string;
      mirror_webhook_url: string;
      command_rules: Record<string, unknown>;
    }>
  ) =>
    request<GuildConfig>(`/api/guilds/${guildId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  registerCommands: () =>
    request<{ registered: number; commands: string[] }>("/api/guilds/register-commands", {
      method: "POST",
    }),
  getInviteUrl: () => request<{ bot_invite_url: string }>("/api/guilds/invite-url"),
};
