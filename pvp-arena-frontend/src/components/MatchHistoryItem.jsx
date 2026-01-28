function getClassEmoji(className) {
  if (!className) return "";
  const emojis = { warrior: "⚔️", mage: "🔮", druid: "🌿" };
  return emojis[className] || "";
}

function getClassColor(className) {
  if (!className) return "#666";
  const colors = { 
    warrior: "#e63946", 
    mage: "#457b9d", 
    druid: "#2a9d8f" 
  };
  return colors[className] || "#666";
}

export default function MatchHistoryItem({ match }) {
  const { result, opponent } = match;
  
  const resultColor = result === "WIN" ? "#51cf66" : result === "LOSS" ? "#ff6b6b" : "#999";
  const resultBg = result === "WIN" ? "#1a3a1a" : result === "LOSS" ? "#3a1a1a" : "#2d3748";
  
  return (
    <div style={{ 
      padding: 12, 
      border: "1px solid #4a5568", 
      borderRadius: 8,
      backgroundColor: "#2d3748",
      display: "flex",
      alignItems: "center",
      gap: 12
    }}>
      {/* Result badge */}
      <div style={{
        padding: "6px 12px",
        backgroundColor: resultBg,
        color: resultColor,
        borderRadius: 6,
        fontWeight: "bold",
        fontSize: "12px",
        textTransform: "uppercase",
        minWidth: 70,
        textAlign: "center"
      }}>
        {result}
      </div>
      
      {/* vs text */}
      <span style={{ color: "#999", fontSize: "14px" }}>vs</span>
      
      {/* Opponent info */}
      <div style={{ 
        display: "flex", 
        alignItems: "center", 
        gap: 8,
        flex: 1
      }}>
        <span style={{ 
          color: "white", 
          fontWeight: "500",
          fontSize: "14px"
        }}>
          {opponent.username}
        </span>
        
        {/* Class badge */}
        {opponent.class_name && opponent.class_name !== "unknown" && (
          <span style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
            padding: "3px 8px",
            backgroundColor: getClassColor(opponent.class_name),
            color: "white",
            borderRadius: 8,
            fontSize: "11px",
            fontWeight: "bold",
            textTransform: "capitalize"
          }}>
            {getClassEmoji(opponent.class_name)} {opponent.class_name}
          </span>
        )}
        
        {/* Level if available */}
        {opponent.level && (
          <span style={{
            color: "#999",
            fontSize: "12px"
          }}>
            Lv.{opponent.level}
          </span>
        )}
      </div>
      
      {/* Match ID (subtle) */}
      <div style={{
        color: "#666",
        fontSize: "11px"
      }}>
        #{match.id}
      </div>
    </div>
  );
}
