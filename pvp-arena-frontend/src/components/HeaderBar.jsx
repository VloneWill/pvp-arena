export default function HeaderBar({ username, showHistory, onToggleHistory, onLogout }) {
  return (
    <div style={{ 
      display: "flex", 
      justifyContent: "space-between", 
      alignItems: "center",
      padding: "16px 20px",
      backgroundColor: "#1e1e1e",
      borderRadius: 8,
      border: "1px solid #333",
      marginBottom: 20
    }}>
      <div style={{ color: "white" }}>
        Logged in as <b style={{ color: "#4a9eff" }}>{username}</b>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button 
          onClick={onToggleHistory}
          style={{
            padding: "8px 16px",
            backgroundColor: showHistory ? "#4a5568" : "#2d3748",
            color: "white",
            border: "1px solid #4a5568",
            borderRadius: 6,
            cursor: "pointer",
            fontWeight: "bold"
          }}
        >
          {showHistory ? "Hide" : "Show"} History
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
            fontWeight: "bold"
          }}
        >
          Logout
        </button>
      </div>
    </div>
  );
}
