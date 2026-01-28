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

export default function ProfileChip({ username, className, level }) {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: 8,
    }}>
      <span style={{
        color: "white",
        fontWeight: "bold",
        fontSize: "16px"
      }}>
        {username}
      </span>
      {className && (
        <span style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
          padding: "4px 10px",
          backgroundColor: getClassColor(className),
          color: "white",
          borderRadius: 12,
          fontSize: "12px",
          fontWeight: "bold",
          textTransform: "capitalize"
        }}>
          {getClassEmoji(className)} {className}
        </span>
      )}
      {level && (
        <span style={{
          color: "#999",
          fontSize: "14px",
          fontWeight: "500"
        }}>
          Lv.{level}
        </span>
      )}
    </div>
  );
}
