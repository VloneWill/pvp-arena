import MatchHistoryItem from "./MatchHistoryItem";

export default function MatchHistory({ history, onRefresh }) {
  return (
    <div style={{ 
      border: "1px solid #4a5568", 
      borderRadius: 8, 
      padding: 16,
      backgroundColor: "#1e1e1e",
      marginBottom: 20,
      maxWidth: 1000,
      margin: "0 auto 20px auto"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ margin: 0, color: "white" }}>Match History</h3>
        <button 
          onClick={onRefresh} 
          style={{ 
            padding: "6px 12px",
            backgroundColor: "#2d3748",
            color: "white",
            border: "1px solid #4a5568",
            borderRadius: 6,
            cursor: "pointer",
            fontSize: "14px"
          }}
        >
          Refresh
        </button>
      </div>
      <div style={{ display: "grid", gap: 8 }}>
        {history.length === 0 ? (
          <div style={{ color: "#666", fontStyle: "italic", padding: 20, textAlign: "center" }}>
            No match history yet.
          </div>
        ) : (
          history.map((m) => (
            <MatchHistoryItem key={m.id} match={m} />
          ))
        )}
      </div>
    </div>
  );
}
