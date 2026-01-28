import { useEffect, useRef } from "react";

function getToneColor(tone) {
  if (tone === "damage") return "#ff6b6b";
  if (tone === "heal") return "#51cf66";
  if (tone === "defend") return "#4dabf7";
  if (tone === "buff") return "#9775fa";
  return "#e9ecef";
}

export default function CombatLog({ entries }) {
  const scrollRef = useRef(null);
  
  // Scroll to top when entries change (newest at top)
  useEffect(() => {
    if (scrollRef.current && entries.length > 0) {
      scrollRef.current.scrollTop = 0;
    }
  }, [entries.length]);
  
  return (
    <div 
      ref={scrollRef}
      style={{
        border: "1px solid #4a5568",
        borderRadius: 8,
        padding: 16,
        backgroundColor: "#1e1e1e",
        maxHeight: 200,
        overflowY: "auto",
      }}
    >
      <h3 style={{ marginTop: 0, color: "white" }}>Combat Log</h3>
      {entries.length === 0 ? (
        <div style={{ color: "#666", fontStyle: "italic" }}>No actions yet...</div>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {entries.map((entry, idx) => {
            const isMyAction = entry.isMyAction === true;
            return (
              <div
                key={idx}
                style={{
                  padding: 8,
                  borderRadius: 4,
                  backgroundColor: isMyAction ? "#2d3a4d" : "#2d3748",
                  borderLeft: isMyAction ? "3px solid #4dabf7" : "3px solid transparent",
                  color: getToneColor(entry.tone),
                  fontWeight: 500,
                  fontSize: "14px",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                {isMyAction && (
                  <span style={{ 
                    fontSize: "12px", 
                    fontWeight: "bold", 
                    color: "#4dabf7",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px"
                  }}>
                    You
                  </span>
                )}
                {!isMyAction && (
                  <span style={{ 
                    fontSize: "12px", 
                    fontWeight: "bold", 
                    color: "#999",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px"
                  }}>
                    Opponent
                  </span>
                )}
                <span>{entry.message}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
