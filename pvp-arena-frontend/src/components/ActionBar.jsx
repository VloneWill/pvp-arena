export default function ActionBar({ canAct, inFlight, onAction, className, abilityCooldown }) {
  const disabled = !canAct || inFlight;
  const abilityDisabled = disabled || (abilityCooldown > 0);

  const buttonStyle = (color, isDisabled = false) => ({
    backgroundColor: (disabled || isDisabled) ? "#4a5568" : color,
    color: "white",
    border: "none",
    padding: "12px 24px",
    borderRadius: "6px",
    fontSize: "16px",
    fontWeight: "bold",
    cursor: (disabled || isDisabled) ? "not-allowed" : "pointer",
    opacity: (disabled || isDisabled) ? 0.6 : 1,
  });

  const getAbilityInfo = () => {
    if (!className) return null;
    const abilities = {
      warrior: { name: "Power Strike", action: "power_strike", emoji: "⚔️", desc: "High damage attack" },
      mage: { name: "Arcane Blast", action: "arcane_blast", emoji: "🔮", desc: "Very high damage" },
      druid: { name: "Rejuvenate", action: "rejuvenate", emoji: "🌿", desc: "Strong heal" },
    };
    return abilities[className];
  };

  const abilityInfo = getAbilityInfo();

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
        {abilityInfo && (
          <button
            onClick={() => onAction(abilityInfo.action)}
            disabled={abilityDisabled}
            style={buttonStyle("#6f42c1", abilityCooldown > 0)}
            title={abilityCooldown > 0 ? `Cooldown: ${abilityCooldown} turn(s)` : abilityInfo.desc}
          >
            {abilityInfo.emoji} {abilityInfo.name}
            {abilityCooldown > 0 && ` (CD: ${abilityCooldown})`}
          </button>
        )}
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
        <div>Attack: Deal damage based on class/level</div>
        <div>Defend: Reduce next attack by 50%</div>
        <div>Heal: Restore HP based on class/level</div>
        {abilityInfo && (
          <div>{abilityInfo.name}: {abilityInfo.desc} (3 turn cooldown)</div>
        )}
      </div>
    </div>
  );
}
