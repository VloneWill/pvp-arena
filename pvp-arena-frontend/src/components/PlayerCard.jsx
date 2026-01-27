import { getHpPercent } from "../utils/formatters";

// Health bar component
function HealthBar({ current, max, isActive, flashColor }) {
  const percentage = getHpPercent(current, max);
  let barColor = "#4caf50"; // green
  if (percentage < 30) barColor = "#f44336"; // red
  else if (percentage < 60) barColor = "#ff9800"; // yellow

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <div
        style={{
          width: "100%",
          height: 24,
          backgroundColor: "#2d3748",
          borderRadius: 12,
          overflow: "hidden",
          border: "1px solid #4a5568",
        }}
      >
        <div
          style={{
            width: `${percentage}%`,
            height: "100%",
            backgroundColor: flashColor || barColor,
            transition: "width 0.5s ease, background-color 0.3s ease",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: percentage > 50 ? "#fff" : "#000",
            fontWeight: "bold",
            fontSize: "12px",
          }}
        >
          {current > 0 && `${current}`}
        </div>
      </div>
      <div style={{ marginTop: 4, fontSize: "12px", color: "#999" }}>
        {current} / {max} HP
      </div>
    </div>
  );
}

export default function PlayerCard({ playerId, username, health, maxHealth, isActive, isMe, flashColor }) {
  return (
    <div
      style={{
        flex: 1,
        padding: 16,
        borderRadius: 8,
        border: `2px solid ${isActive ? "#4a9eff" : "#4a5568"}`,
        backgroundColor: isActive ? "#1a2d3a" : "#1e1e1e",
        boxShadow: isActive ? "0 0 10px rgba(74, 158, 255, 0.3)" : "none",
        transition: "all 0.3s ease",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div>
          <div style={{ fontWeight: "bold", fontSize: "18px", color: "white" }}>{username || `Player ${playerId}`}</div>
          <div style={{ fontSize: "12px", color: "#999" }}>{isMe ? "You" : "Opponent"}</div>
        </div>
        {isActive && (
          <div style={{ 
            padding: "4px 12px", 
            backgroundColor: "#4a9eff", 
            color: "white", 
            borderRadius: 12,
            fontSize: "12px",
            fontWeight: "bold"
          }}>
            {isMe ? "Your Turn" : "Opponent's Turn"}
          </div>
        )}
      </div>
      <HealthBar current={health} max={maxHealth} isActive={isActive} flashColor={flashColor} />
    </div>
  );
}
