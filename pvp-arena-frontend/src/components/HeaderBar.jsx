import ProfileChip from "./ProfileChip";

export default function HeaderBar({ username, className, level, showHistory, onToggleHistory, showLeaderboard, onToggleLeaderboard, onLogout }) {
  return (
    <div style={{ display: "grid", gap: 12, margin: "0 0 20px 0" }}>
      <div style={{ 
        display: "flex", 
        justifyContent: "center",
        alignItems: "center",
        padding: "12px 20px",
        backgroundColor: "#1e1e1e",
        borderRadius: 8,
        border: "1px solid #333"
      }}>
        <ProfileChip username={username} className={className} level={level} />
      </div>
      <div style={{ 
        display: "flex", 
        justifyContent: "center",
        gap: 8,
        padding: "8px 20px",
        backgroundColor: "#1e1e1e",
        borderRadius: 8,
        border: "1px solid #333"
      }}>
        <button 
          onClick={onToggleHistory}
          style={{
            padding: "8px 16px",
            backgroundColor: showHistory ? "#4a5568" : "#2d3748",
            color: "white",
            border: "1px solid #4a5568",
            borderRadius: 6,
            cursor: "pointer",
            fontWeight: "bold",
            fontSize: "14px"
          }}
        >
          {showHistory ? "Hide" : "Show"} History
        </button>
        <button 
          onClick={onToggleLeaderboard}
          style={{
            padding: "8px 16px",
            backgroundColor: showLeaderboard ? "#4a5568" : "#2d3748",
            color: "white",
            border: "1px solid #4a5568",
            borderRadius: 6,
            cursor: "pointer",
            fontWeight: "bold",
            fontSize: "14px"
          }}
        >
          {showLeaderboard ? "Hide" : "Show"} Leaderboard
        </button>
        <button 
          onClick={onLogout}
          style={{
            padding: "8px 16px",
            backgroundColor: "#dc3545",
            color: "white",
            border: "none",
            borderRadius: 6,
            cursor: "pointer",
            fontWeight: "bold",
            fontSize: "14px"
          }}
        >
          Logout
        </button>
      </div>
    </div>
  );
}
