import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { humanize } from "../utils/formatters";

import { CLASS_EMOJI } from "../data/classIcons";

export default function Leaderboard({ token, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiFetch("/leaderboard?limit=10", { token })
      .then((list) => {
        if (!cancelled) setData(list);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || "Failed to load leaderboard");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [token]);

  return (
    <div
      style={{
        padding: 16,
        backgroundColor: "#1a1a1a",
        borderRadius: 8,
        border: "1px solid #333",
        maxWidth: 400,
        margin: "0 auto",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ margin: 0, color: "white" }}>🏆 Leaderboard</h3>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              color: "#999",
              cursor: "pointer",
              fontSize: 18,
            }}
            aria-label="Close"
          >
            ×
          </button>
        )}
      </div>
      {loading && <div style={{ color: "#999" }}>Loading...</div>}
      {error && <div style={{ color: "#ff6b6b" }}>{error}</div>}
      {!loading && !error && data && (
        <div style={{ display: "grid", gap: 6 }}>
          {data.length === 0 ? (
            <div style={{ color: "#666" }}>No matches played yet.</div>
          ) : (
            data.map((row) => (
              <div
                key={row.user_id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "8px 10px",
                  backgroundColor: "#252525",
                  borderRadius: 6,
                  border: "1px solid #333",
                }}
              >
                <span style={{ fontWeight: "bold", color: "#ffc107", minWidth: 24 }}>#{row.rank}</span>
                <span style={{ color: "white", fontWeight: 500 }}>{row.username}</span>
                <span style={{ color: "#999", fontSize: 12 }}>
                  {CLASS_EMOJI[row.class_name] || ""} {humanize(row.class_name)}
                </span>
                <span style={{ color: "#4caf50", fontSize: 12 }}>Lv.{row.level}</span>
                <span style={{ color: "#aaa", fontSize: 12 }}>
                  {row.wins}W {row.losses}L
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
