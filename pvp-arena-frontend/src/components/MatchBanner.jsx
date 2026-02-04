import { useEffect, useState } from "react";

export default function MatchBanner({ status, winnerUsername, winnerId, turnExpiresAt }) {
  const [turnSecondsLeft, setTurnSecondsLeft] = useState(null);

  useEffect(() => {
    if (status !== "active" || !turnExpiresAt) {
      setTurnSecondsLeft(null);
      return;
    }
    const update = () => {
      const end = new Date(turnExpiresAt).getTime();
      const now = Date.now();
      const left = Math.max(0, Math.ceil((end - now) / 1000));
      setTurnSecondsLeft(left);
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [status, turnExpiresAt]);

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
        <div>
          ⚔️ Match in Progress
          {turnSecondsLeft != null && (
            <span style={{ marginLeft: 10, opacity: 0.9 }}>Turn: {turnSecondsLeft}s</span>
          )}
        </div>
      ) : (
        <div>⏳ Waiting for opponent</div>
      )}
    </div>
  );
}
