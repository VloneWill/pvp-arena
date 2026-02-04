import { getClassEmoji, getClassColor } from "../data/classIcons";

export default function MatchHistoryItem({ match }) {
  const { result, opponent } = match;

  const resultColor =
    result === "WIN" ? "#51cf66" : result === "LOSS" ? "#ff6b6b" : "#999";
  const resultBg =
    result === "WIN" ? "#1a3a1a" : result === "LOSS" ? "#3a1a1a" : "#2d3748";

  return (
    <div
      style={{
        padding: 12,
        border: "1px solid #4a5568",
        borderRadius: 8,
        backgroundColor: "#2d3748",

        display: "flex",
        alignItems: "center",
        gap: 12,

        // Robust mobile fix: allow wrapping
        flexWrap: "wrap",

        // Prevent any accidental horizontal overflow
        minWidth: 0,
        overflow: "hidden",
      }}
    >
      {/* Result badge */}
      <div
        style={{
          padding: "4px 8px",
          backgroundColor: resultBg,
          color: resultColor,
          borderRadius: 6,
          fontWeight: "bold",
          fontSize: "11px",
          textTransform: "uppercase",
          minWidth: 52,
          textAlign: "center",
          flex: "0 0 auto",
        }}
      >
        {result}
      </div>

      {/* vs text */}
      <span style={{ color: "#999", fontSize: "14px", flex: "0 0 auto" }}>
        vs
      </span>

      {/* Username (stays on first line, truncates if needed) */}
      <span
        style={{
          color: "white",
          fontWeight: "500",
          fontSize: "14px",

          // This is the "flexible" part of line 1
          flex: "1 1 auto",
          minWidth: 0,

          // Truncate instead of pushing layout wider
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {opponent.username}
      </span>

      {/* Second row container: class + level + id */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,

          // Forces this chunk onto its own row when space is tight
          flexBasis: "100%",

          // Still allow shrink/containment
          minWidth: 0,

          // A little visual separation from the top line
          marginTop: 2,
        }}
      >
        {/* Class badge */}
        {opponent.class_name && opponent.class_name !== "unknown" && (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              padding: "3px 8px",
              backgroundColor: getClassColor(opponent.class_name),
              color: "white",
              borderRadius: 8,
              fontSize: "11px",
              fontWeight: "bold",
              textTransform: "capitalize",
              whiteSpace: "nowrap",
            }}
          >
            {getClassEmoji(opponent.class_name)} {opponent.class_name}
          </span>
        )}

        {/* Level */}
        {opponent.level && (
          <span style={{ color: "#999", fontSize: "12px", whiteSpace: "nowrap" }}>
            Lv.{opponent.level}
          </span>
        )}

        {/* Match ID aligned to the right */}
        <span
          style={{
            marginLeft: "auto",
            color: "#666",
            fontSize: "11px",
            whiteSpace: "nowrap",
          }}
        >
          #{match.id}
        </span>
      </div>
    </div>
  );
}
