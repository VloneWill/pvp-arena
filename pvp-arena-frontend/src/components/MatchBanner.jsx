export default function MatchBanner({ status, winnerUsername, winnerId }) {
  const getBannerStyle = () => {
    if (status === "finished") {
      return {
        backgroundColor: "#2d2416",
        borderColor: "#ffc107",
        color: "#ffc107"
      };
    } else if (status === "active") {
      return {
        backgroundColor: "#1a2d3a",
        borderColor: "#0dcaf0",
        color: "#0dcaf0"
      };
    } else {
      return {
        backgroundColor: "#2d1b1b",
        borderColor: "#dc3545",
        color: "#dc3545"
      };
    }
  };

  const style = getBannerStyle();

  return (
    <div style={{
      padding: 12,
      borderRadius: 8,
      textAlign: "center",
      fontWeight: "bold",
      backgroundColor: style.backgroundColor,
      border: `2px solid ${style.borderColor}`,
      color: style.color,
    }}>
      {status === "finished" ? (
        <div>
          🏆 Match Finished! Winner: <b style={{ color: "white" }}>{winnerUsername || `Player ${winnerId}` || "Unknown"}</b>
        </div>
      ) : status === "active" ? (
        <div>⚔️ Match in Progress</div>
      ) : (
        <div>⏳ Waiting for opponent</div>
      )}
    </div>
  );
}
