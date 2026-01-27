export default function MatchHistory({ history, onRefresh }) {
  return (
    <div style={{ 
      border: "1px solid #4a5568", 
      borderRadius: 8, 
      padding: 16,
      backgroundColor: "#1e1e1e",
      marginBottom: 20
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ margin: 0, color: "white" }}>Match History</h3>
        <button 
          onClick={onRefresh} 
          style={{ 
            marginBottom: 12,
            padding: "6px 12px",
            backgroundColor: "#2d3748",
            color: "white",
            border: "1px solid #4a5568",
            borderRadius: 6,
            cursor: "pointer"
          }}
        >
          Refresh
        </button>
      </div>
      <div style={{ display: "grid", gap: 8 }}>
        {history.length === 0 ? (
          <div style={{ color: "#666" }}>No match history yet.</div>
        ) : (
          history.map((m) => (
            <div 
              key={m.id} 
              style={{ 
                padding: 12, 
                border: "1px solid #4a5568", 
                borderRadius: 8,
                backgroundColor: "#2d3748"
              }}
            >
              <div style={{ color: "white" }}><b>Match {m.id}</b> - {m.status}</div>
              <div style={{ fontSize: "0.9em", color: "#999" }}>
                Player 1: {m.player1_id} vs Player 2: {m.player2_id}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
