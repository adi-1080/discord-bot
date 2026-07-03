import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, clearToken, type CommandLog } from "../api/client";
import { CommandLogTable } from "../components/CommandLogTable";
import { useToast } from "../context/ToastContext";

export function DashboardPage() {
  const toast = useToast();
  const loadErrorShown = useRef(false);
  const [logs, setLogs] = useState<CommandLog[]>([]);
  const [stats, setStats] = useState<{ total: number; by_status: Record<string, number> } | null>(
    null
  );

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [logData, statsData] = await Promise.all([api.getLogs(), api.getStats()]);
        if (active) {
          setLogs(logData);
          setStats(statsData);
          loadErrorShown.current = false;
        }
      } catch (err) {
        if (active && !loadErrorShown.current) {
          loadErrorShown.current = true;
          toast.error(err instanceof Error ? err.message : "Failed to load dashboard");
        }
      }
    }

    load();
    const interval = setInterval(load, 5000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [toast]);

  function logout() {
    clearToken();
    window.location.href = "/login";
  }

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>Command Dashboard</h1>
          <p>Live log of slash commands and actions</p>
        </div>
        <nav>
          <Link to="/settings">Settings</Link>
          <button type="button" className="secondary" onClick={logout}>
            Log out
          </button>
        </nav>
      </header>

      {stats && (
        <div className="stats">
          <div className="stat-card">
            <span>Total commands</span>
            <strong>{stats.total}</strong>
          </div>
          {Object.entries(stats.by_status).map(([status, count]) => (
            <div className="stat-card" key={status}>
              <span>{status}</span>
              <strong>{count}</strong>
            </div>
          ))}
        </div>
      )}

      <section className="card">
        <h2>Recent commands</h2>
        <CommandLogTable logs={logs} />
      </section>
    </div>
  );
}
