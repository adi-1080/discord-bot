import { type FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type GuildConfig } from "../api/client";
import { useToast } from "../context/ToastContext";

export function SettingsPage() {
  const toast = useToast();
  const [guilds, setGuilds] = useState<GuildConfig[]>([]);
  const [selectedGuildId, setSelectedGuildId] = useState<string>("");
  const [guildId, setGuildId] = useState("");
  const [guildName, setGuildName] = useState("");
  const [channelId, setChannelId] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [autoMirror, setAutoMirror] = useState(true);
  const [keywords, setKeywords] = useState("urgent:high\ncritical:high\nbug:medium\nhelp:low");
  const [inviteUrl, setInviteUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [registering, setRegistering] = useState(false);

  useEffect(() => {
    api
      .getInviteUrl()
      .then(({ bot_invite_url }) => setInviteUrl(bot_invite_url))
      .catch(() => {});

    api
      .getGuilds()
      .then((data) => {
        setGuilds(data);
        if (data.length > 0 && !selectedGuildId) {
          selectGuild(data[0]);
        }
      })
      .catch((err) =>
        toast.error(err instanceof Error ? err.message : "Failed to load guilds")
      );
  }, [toast]);

  function selectGuild(guild: GuildConfig) {
    setSelectedGuildId(guild.guild_id);
    setGuildId(guild.guild_id);
    setGuildName(guild.guild_name || "");
    setChannelId(guild.channel_id);
    setWebhookUrl("");
    setAutoMirror(guild.command_rules.auto_mirror);
    setKeywords(
      Object.entries(guild.command_rules.report_keywords || {})
        .map(([k, v]) => `${k}:${v}`)
        .join("\n")
    );
    setInviteUrl(guild.bot_invite_url);
  }

  function parseKeywords(text: string): Record<string, string> {
    const result: Record<string, string> = {};
    for (const line of text.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const [key, value] = trimmed.split(":");
      if (key && value) {
        result[key.trim()] = value.trim();
      }
    }
    return result;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (saving) return;
    setSaving(true);

    const trimmedGuildId = guildId.trim();
    const trimmedChannelId = channelId.trim();
    const trimmedWebhookUrl = webhookUrl.trim();
    const command_rules = {
      auto_mirror: autoMirror,
      report_keywords: parseKeywords(keywords),
    };

    try {
      if (selectedGuildId) {
        const payload: Record<string, unknown> = {
          guild_name: guildName.trim() || null,
          channel_id: trimmedChannelId,
          command_rules,
        };
        if (trimmedWebhookUrl) {
          payload.mirror_webhook_url = trimmedWebhookUrl;
        }
        await api.updateGuild(selectedGuildId, payload);
        toast.success("Guild configuration updated");
      } else {
        await api.createGuild({
          guild_id: trimmedGuildId,
          guild_name: guildName.trim() || undefined,
          channel_id: trimmedChannelId,
          mirror_webhook_url: trimmedWebhookUrl,
          command_rules,
        });
        setSelectedGuildId(trimmedGuildId);
        toast.success("Guild connected successfully");
      }
      const updated = await api.getGuilds();
      setGuilds(updated);
      const match = updated.find((g) => g.guild_id === trimmedGuildId) || updated[0];
      if (match) {
        selectGuild(match);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save guild configuration");
    } finally {
      setSaving(false);
    }
  }

  async function registerCommands() {
    if (registering) return;
    setRegistering(true);
    try {
      const result = await api.registerCommands();
      toast.success(`Registered commands: ${result.commands.join(", ")}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to register commands");
    } finally {
      setRegistering(false);
    }
  }

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>Bot Settings</h1>
          <p>Connect your Discord server and configure command behavior</p>
        </div>
        <nav>
          <Link to="/">Dashboard</Link>
        </nav>
      </header>

      <section className="card">
        <h2>1. Add bot to server</h2>
        <p className="help">
          Click below to add the bot to your Discord server. Do this first — you need the bot in
          your server before slash commands will work.
        </p>
        {inviteUrl ? (
          <a href={inviteUrl} target="_blank" rel="noreferrer" className="button-link">
            Invite bot to Discord server
          </a>
        ) : (
          <p className="help">Set DISCORD_APPLICATION_ID in backend/.env and restart the server.</p>
        )}
      </section>

      <section className="card">
        <h2>2. Guild configuration</h2>
        <p className="help">
          Enable <strong>Developer Mode</strong> in Discord: User Settings → Advanced → Developer
          Mode. Then right-click your server or channel and choose <strong>Copy Server ID</strong>{" "}
          or <strong>Copy Channel ID</strong>.
        </p>
        {guilds.length > 0 && (
          <label>
            Existing guilds
            <select
              value={selectedGuildId}
              onChange={(e) => {
                const guild = guilds.find((g) => g.guild_id === e.target.value);
                if (guild) selectGuild(guild);
              }}
            >
              {guilds.map((g) => (
                <option key={g.guild_id} value={g.guild_id}>
                  {g.guild_name || g.guild_id}
                </option>
              ))}
            </select>
          </label>
        )}

        <form onSubmit={handleSubmit} className="form-grid">
          <label>
            Guild ID
            <span className="field-hint">Right-click your server name → Copy Server ID</span>
            <input
              value={guildId}
              onChange={(e) => setGuildId(e.target.value)}
              required
              disabled={!!selectedGuildId}
              placeholder="e.g. 123456789012345678"
            />
          </label>
          <label>
            Guild name (optional)
            <span className="field-hint">Friendly label for the dashboard only</span>
            <input
              value={guildName}
              onChange={(e) => setGuildName(e.target.value)}
              placeholder="My Test Server"
            />
          </label>
          <label>
            Primary channel ID
            <span className="field-hint">
              Channel where /report posts appear. Bot needs Send Messages here.
            </span>
            <input
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              required
              placeholder="e.g. 987654321098765432"
            />
          </label>
          <label>
            Mirror webhook URL
            <span className="field-hint">
              Second channel: Edit Channel → Integrations → Webhooks → New Webhook → Copy URL
            </span>
            <input
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder={
                selectedGuildId
                  ? "Leave blank to keep existing"
                  : "https://discord.com/api/webhooks/1234567890/abcdef..."
              }
              required={!selectedGuildId}
            />
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={autoMirror}
              onChange={(e) => setAutoMirror(e.target.checked)}
            />
            Auto-mirror commands to webhook channel
          </label>
          <label className="full-width">
            Report keyword rules (keyword:priority, one per line)
            <textarea value={keywords} onChange={(e) => setKeywords(e.target.value)} rows={5} />
          </label>
          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : selectedGuildId ? "Update guild" : "Connect guild"}
          </button>
        </form>
      </section>

      <section className="card">
        <h2>3. Register slash commands</h2>
        <p className="help">
          After saving guild config, click below to register <code>/report</code> and{" "}
          <code>/status</code> with Discord. Commands may take up to a minute to appear in your
          server.
        </p>
        <button type="button" onClick={registerCommands} disabled={registering}>
          {registering ? "Registering…" : "Register commands"}
        </button>
      </section>
    </div>
  );
}
