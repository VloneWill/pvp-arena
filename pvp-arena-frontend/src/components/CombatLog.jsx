function getToneColor(tone) {
  if (tone === "damage") return "#ff6b6b";
  if (tone === "heal") return "#51cf66";
  if (tone === "defend") return "#4dabf7";
  if (tone === "buff") return "#9775fa";
  return "#e9ecef";
}

export default function CombatLog({ entries }) {
  return (
    <div style={{
      border: "1px solid #4a5568",
      borderRadius: 8,
      padding: 16,
      backgroundColor: "#1e1e1e",
      maxHeight: 200,
      overflowY: "auto",
    }}>
      <h3 style={{ marginTop: 0, color: "white" }}>Combat Log</h3>
      {entries.length === 0 ? (
        <div style={{ color: "#666", fontStyle: "italic" }}>No actions yet...</div>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {entries.map((entry, idx) => (
            <div
              key={idx}
              style={{
                padding: 8,
                borderRadius: 4,
                backgroundColor: "#2d3748",
                color: getToneColor(entry.tone),
                fontWeight: 500,
                fontSize: "14px",
              }}
            >
              {entry.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
