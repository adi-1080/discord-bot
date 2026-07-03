import type { CommandLog } from "../api/client";

interface Props {
  logs: CommandLog[];
}

export function CommandLogTable({ logs }: Props) {
  if (logs.length === 0) {
    return <p className="empty">No commands recorded yet.</p>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Command</th>
            <th>User</th>
            <th>Guild</th>
            <th>Actions</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td>{new Date(log.created_at).toLocaleString()}</td>
              <td>/{log.command_name}</td>
              <td>{log.username || log.user_id || "—"}</td>
              <td>{log.guild_id || "—"}</td>
              <td>{log.actions_taken.join(", ") || "—"}</td>
              <td>
                <span className={`badge badge-${log.status}`}>{log.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
