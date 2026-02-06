import { useCallback, useEffect, useRef, useState } from "react";
import {
  isDebugEnabled,
  getLogs,
  clearLogs,
  subscribe,
  log,
} from "../utils/abilityModalDebug";

const DISPLAY_CAP = 20;

export default function AbilityModalDebugOverlay() {
  const [entries, setEntries] = useState([]);
  const [visible, setVisible] = useState(true);
  const listRef = useRef(null);

  const refresh = useCallback(() => {
    const all = getLogs();
    setEntries(all.slice(-DISPLAY_CAP).reverse());
  }, []);

  useEffect(() => {
    if (!isDebugEnabled()) return;
    refresh();
    const unsub = subscribe(() => refresh());
    return unsub;
  }, [refresh]);

  useEffect(() => {
    if (!isDebugEnabled()) return;
    const onResize = () => {
      log("RESIZE", {
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };
    const onViewportResize = () => {
      const vv = window.visualViewport;
      log("VISUAL_VIEWPORT_RESIZE", {
        width: vv?.width ?? window.innerWidth,
        height: vv?.height ?? window.innerHeight,
      });
    };
    window.addEventListener("resize", onResize);
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", onViewportResize);
    }
    return () => {
      window.removeEventListener("resize", onResize);
      if (window.visualViewport) {
        window.visualViewport.removeEventListener("resize", onViewportResize);
      }
    };
  }, []);

  const handleCopy = useCallback(() => {
    const raw = JSON.stringify(getLogs(), null, 2);
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(raw).catch(() => {
        copyBySelect(raw);
      });
    } else {
      copyBySelect(raw);
    }
  }, []);

  const handleClear = useCallback(() => {
    clearLogs();
    setEntries([]);
  }, []);

  if (!isDebugEnabled()) return null;

  function copyBySelect(text) {
    const el = document.createElement("textarea");
    el.value = text;
    el.style.position = "fixed";
    el.style.left = "-9999px";
    document.body.appendChild(el);
    el.select();
    try {
      document.execCommand("copy");
    } finally {
      document.body.removeChild(el);
    }
  }

  if (!visible) {
    return (
      <button
        type="button"
        onClick={() => setVisible(true)}
        style={{
          position: "fixed",
          top: 8,
          left: 8,
          zIndex: 10000,
          padding: "4px 8px",
          fontSize: 10,
          backgroundColor: "#333",
          color: "#ccc",
          border: "1px solid #555",
          borderRadius: 4,
          cursor: "pointer",
        }}
      >
        Ability Modal Debug (hidden)
      </button>
    );
  }

  return (
    <div
      ref={listRef}
      style={{
        position: "fixed",
        top: 8,
        left: 8,
        zIndex: 10000,
        maxWidth: "min(320px, calc(100vw - 16px))",
        maxHeight: "min(360px, calc(100vh - 80px))",
        overflow: "auto",
        backgroundColor: "rgba(0,0,0,0.9)",
        border: "1px solid #555",
        borderRadius: 8,
        padding: 8,
        fontSize: 10,
        fontFamily: "monospace",
        color: "#e0e0e0",
        boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
        <strong style={{ color: "#fff" }}>Ability Modal Debug</strong>
        <div style={{ display: "flex", gap: 4 }}>
          <button
            type="button"
            onClick={handleCopy}
            style={{
              padding: "2px 6px",
              fontSize: 10,
              backgroundColor: "#444",
              color: "#fff",
              border: "1px solid #666",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            Copy
          </button>
          <button
            type="button"
            onClick={handleClear}
            style={{
              padding: "2px 6px",
              fontSize: 10,
              backgroundColor: "#444",
              color: "#fff",
              border: "1px solid #666",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            Clear
          </button>
          <button
            type="button"
            onClick={() => setVisible(false)}
            style={{
              padding: "2px 6px",
              fontSize: 10,
              backgroundColor: "#444",
              color: "#fff",
              border: "1px solid #666",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            Hide
          </button>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {entries.length === 0 ? (
          <span style={{ color: "#888" }}>No events yet.</span>
        ) : (
          entries.map((e, i) => (
            <div
              key={e.ts != null ? `${e.ts}-${i}` : i}
              style={{
                padding: 4,
                backgroundColor: "rgba(255,255,255,0.05)",
                borderRadius: 4,
                borderLeft: "3px solid #666",
                wordBreak: "break-all",
              }}
            >
              <span style={{ color: "#8af" }}>{e.event}</span>
              <span style={{ color: "#888", marginLeft: 4 }}>
                {e.iso ? new Date(e.ts).toISOString().slice(11, 23) : ""}
              </span>
              {e.reason != null && <span style={{ color: "#fa8" }}> reason={e.reason}</span>}
              {e.abilityId != null && <span style={{ color: "#8f8" }}> abilityId={e.abilityId}</span>}
              {e.turn != null && <span style={{ color: "#8f8" }}> turn={e.turn}</span>}
              {e.matchId != null && <span style={{ color: "#8f8" }}> matchId={e.matchId}</span>}
              {e.eventType != null && <span style={{ color: "#f88" }}> eventType={e.eventType}</span>}
              {e.willClose != null && <span style={{ color: "#f88" }}> willClose={String(e.willClose)}</span>}
              {e.width != null && <span style={{ color: "#88f" }}> w={e.width} h={e.height}</span>}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
