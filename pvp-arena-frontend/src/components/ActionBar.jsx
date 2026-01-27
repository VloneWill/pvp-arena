export default function ActionBar({ canAct, inFlight, onAction }) {
  const disabled = !canAct || inFlight;

  const buttonStyle = (color) => ({
    backgroundColor: disabled ? "#4a5568" : color,
    color: "white",
    border: "none",
    padding: "12px 24px",
    borderRadius: "6px",
    fontSize: "16px",
    fontWeight: "bold",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.6 : 1,
  });

  return (
    <div style={{
      padding: 20,
      border: "2px solid #4a5568",
      borderRadius: 8,
      backgroundColor: "#1e1e1e",
    }}>
      <h3 style={{ marginTop: 0, textAlign: "center", color: "white" }}>Your Actions</h3>
      <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
        <button
          onClick={() => onAction("attack")}
          disabled={disabled}
          style={buttonStyle("#dc3545")}
        >
          ⚔️ Attack
        </button>
        <button
          onClick={() => onAction("defend")}
          disabled={disabled}
          style={buttonStyle("#0d6efd")}
        >
          🛡️ Defend
        </button>
        <button
          onClick={() => onAction("heal")}
          disabled={disabled}
          style={buttonStyle("#198754")}
        >
          ❤️ Heal
        </button>
        <button
          onClick={() => onAction("double_attack")}
          disabled={disabled}
          style={buttonStyle("#6f42c1")}
        >
          ⚡ Double Attack
        </button>
      </div>
      <div style={{ marginTop: 12, textAlign: "center", color: "#999", fontSize: "14px" }}>
        {inFlight ? (
          <div>Processing action...</div>
        ) : canAct ? (
          <div>It's your turn! Choose an action above.</div>
        ) : (
          <div>Waiting for opponent's turn...</div>
        )}
      </div>
      <div style={{ marginTop: 8, textAlign: "center", fontSize: "12px", color: "#666" }}>
        <div>Attack: Deal 10-20 damage</div>
        <div>Defend: Reduce next attack by 50%</div>
        <div>Heal: Restore 15 HP</div>
        <div>Double Attack: Deal 20-40 damage</div>
      </div>
    </div>
  );
}
