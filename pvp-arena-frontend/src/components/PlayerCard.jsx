import { getHpPercent, humanize } from "../utils/formatters";
import Tooltip from "./Tooltip";
import { buildEffectTooltipContent } from "../data/actionTooltips";
import { getClassEmoji } from "../data/classIcons";

// Health bar component
function HealthBar({ current, max, isActive, flashColor }) {
  const percentage = getHpPercent(current, max);
  let barColor = "#4caf50"; // green
  if (percentage < 30) barColor = "#f44336"; // red
  else if (percentage < 60) barColor = "#ff9800"; // yellow

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", minWidth: 0 }}>
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

// XP Bar component (100 XP per level)
function XPBar({ current, level }) {
  const xpNeeded = 100;
  const percentage = Math.min(100, (current / xpNeeded) * 100);
  
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ fontSize: "11px", color: "#999", marginBottom: 2 }}>
        Level {level} • {current} / {xpNeeded} XP to next
      </div>
      <div
        style={{
          width: "100%",
          height: 6,
          backgroundColor: "#2d3748",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${percentage}%`,
            height: "100%",
            backgroundColor: "#9c27b0",
            transition: "width 0.3s ease",
          }}
        />
      </div>
    </div>
  );
}

function formatClassName(className) {
  return humanize(className || "");
}

export default function PlayerCard({ playerId, username, health, maxHealth, isActive, isMe, flashColor, className, level, xp, activeEffects }) {
  const effects = Array.isArray(activeEffects) ? activeEffects : [];
  return (
    <div
      style={{
        minWidth: 0,
        padding: 16,
        borderRadius: 8,
        border: `2px solid ${isActive ? "#4a9eff" : "#4a5568"}`,
        backgroundColor: isActive ? "#1a2d3a" : "#1e1e1e",
        boxShadow: isActive ? "0 0 10px rgba(74, 158, 255, 0.3)" : "none",
        transition: "all 0.3s ease",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, minWidth: 0 }}>
        <div style={{ minWidth: 0, overflow: "hidden" }}>
          <div style={{ fontWeight: "bold", fontSize: "18px", color: "white", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {username || `Player ${playerId}`}
          </div>
          <div style={{ fontSize: "12px", color: "#999" }}>
            {isMe ? "You" : "Opponent"}
            {className && ` • ${getClassEmoji(className)} ${formatClassName(className)}`}
            {level && ` Lv.${level}`}
          </div>
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
      {effects.length > 0 && (
        <div style={{ marginTop: 8, fontSize: "11px", color: "#aaa", display: "flex", flexWrap: "wrap", gap: 4 }}>
          {effects.map((e, i) => {
            const name = typeof e === "object" ? e.name : e;
            const turns = typeof e === "object" ? e.turns_left : null;
            const hits = typeof e === "object" ? e.hits_left : null;
            const label = humanize(name) + (hits != null ? ` (${hits} hit${hits === 1 ? "" : "s"})` : turns != null ? ` (${turns})` : "");

            return (
              <Tooltip
                key={i}
                content={buildEffectTooltipContent(e)}
                placement="top"
              >
                <span style={{ backgroundColor: "#333", padding: "2px 6px", borderRadius: 4, cursor: "help" }}>
                  {label}
                </span>
              </Tooltip>
            );
          })}
        </div>
      )}
      {level && xp !== undefined && <XPBar current={xp} level={level} />}
    </div>
  );
}
