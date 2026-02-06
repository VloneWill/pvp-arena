import { useEffect, useRef, useState } from "react";
import Tooltip from "./Tooltip";
import { humanize } from "../utils/formatters";
import { buildActionTooltipContent } from "../data/actionTooltips";
import { log, isDebugEnabled } from "../utils/abilityModalDebug";

const ACTION_COOLDOWN_MS = 800;

const CLASS_ABILITIES = {
  warrior: [
    { id: "power_strike", emoji: "⚔️" },
    { id: "shield_wall", emoji: "🛡️" },
    { id: "execute", emoji: "⚔️" },
    { id: "battle_shout", emoji: "📢" },
  ],
  mage: [
    { id: "fireball", emoji: "🔥" },
    { id: "ice_bolt", emoji: "❄️" },
    { id: "arcane_shield", emoji: "🔮" },
    { id: "meteor", emoji: "☄️" },
  ],
  druid: [
    { id: "regrowth", emoji: "🌿" },
    { id: "thorns", emoji: "🌵" },
    { id: "shapeshift", emoji: "🐻" },
    { id: "nature_wrath", emoji: "🌲" },
  ],
  rogue: [
    { id: "backstab", emoji: "🗡️" },
    { id: "evade", emoji: "💨" },
    { id: "poison", emoji: "☠️" },
    { id: "shadowstep", emoji: "👤" },
  ],
};

export default function ActionBar({ canAct, inFlight, onAction, className, abilityCooldowns, actionTooltips, turnExpiresAt, turnNumber, matchId }) {
  const disabled = !canAct || inFlight;
  const cooldowns = abilityCooldowns || {};
  const myActionTooltips = actionTooltips || {};
  /** Which ability's confirm popup is open. Only close on user action (Use/cancel/outside); do not clear on timer or match polling. */
  const [tooltipAbilityId, setTooltipAbilityId] = useState(null);
  /** Which basic action's tooltip is open (mobile: first tap = show, second tap or Use = execute). */
  const [tooltipBasicActionId, setTooltipBasicActionId] = useState(null);
  const [turnSecondsLeft, setTurnSecondsLeft] = useState(null);
  const abilities = className ? CLASS_ABILITIES[className] : [];
  const lastActionTimeRef = useRef(0);

  useEffect(() => {
    if (!turnExpiresAt) {
      setTurnSecondsLeft(null);
      return;
    }
    const update = () => {
      const end = new Date(turnExpiresAt).getTime();
      const now = Date.now();
      setTurnSecondsLeft(Math.max(0, Math.ceil((end - now) / 1000)));
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [turnExpiresAt]);

  const buttonStyle = (color, isDisabled = false) => ({
    backgroundColor: (disabled || isDisabled) ? "#4a5568" : color,
    color: "white",
    border: "none",
    padding: "10px 16px",
    borderRadius: "6px",
    fontSize: "14px",
    fontWeight: "bold",
    cursor: (disabled || isDisabled) ? "not-allowed" : "pointer",
    opacity: (disabled || isDisabled) ? 0.6 : 1,
    touchAction: "manipulation",
    userSelect: "none",
  });

  const guardAndAction = (actionKey, handler) => {
    const now = Date.now();
    if (now - lastActionTimeRef.current < ACTION_COOLDOWN_MS) return;
    lastActionTimeRef.current = now;
    handler();
  };

  const handleAbilityClick = (ab) => {
    const cd = cooldowns[ab.id] ?? 0;
    if (disabled || cd > 0) return;
    if (isDebugEnabled()) {
      log("TRIGGER_TAP", { abilityId: ab.id, abilityName: humanize(ab.id), turn: turnNumber, matchId });
    }
    if (tooltipAbilityId === ab.id) {
      if (isDebugEnabled()) log("MODAL_CLOSE", { reason: "use_same_tap", abilityId: ab.id, modalOpen: false });
      setTooltipAbilityId(null);
      guardAndAction(ab.id, () => onAction(ab.id));
    } else {
      if (isDebugEnabled()) log("MODAL_OPEN", { reason: "trigger_tap", abilityId: ab.id, abilityName: humanize(ab.id), modalOpen: true, turn: turnNumber, matchId });
      setTooltipAbilityId(ab.id);
    }
  };

  const handleAbilityUse = (ab) => {
    if (isDebugEnabled()) log("MODAL_CLOSE", { reason: "use_button", abilityId: ab.id, modalOpen: false });
    setTooltipAbilityId(null);
    guardAndAction(ab.id, () => onAction(ab.id));
  };

  const BASIC_ACTIONS = [
    { id: "attack", emoji: "⚔️", label: "Attack", color: "#dc3545" },
    { id: "defend", emoji: "🛡️", label: "Defend", color: "#0d6efd" },
    { id: "heal", emoji: "❤️", label: "Heal", color: "#198754" },
  ];

  const handleBasicActionClick = (actionId) => {
    if (disabled) return;
    if (tooltipBasicActionId === actionId) {
      setTooltipBasicActionId(null);
      guardAndAction(actionId, () => onAction(actionId));
    } else {
      setTooltipBasicActionId(actionId);
    }
  };

  const handleBasicActionUse = (actionId) => {
    setTooltipBasicActionId(null);
    guardAndAction(actionId, () => onAction(actionId));
  };

  return (
    <div style={{
      padding: 20,
      border: "2px solid #4a5568",
      borderRadius: 8,
      backgroundColor: "#1e1e1e",
      marginTop: 4,
    }}>
      <div style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
        marginBottom: 16,
      }}>
        <h3 style={{ margin: 0, color: "white", fontSize: "18px" }}>Your Actions</h3>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          flexShrink: 0,
        }}>
          <span style={{
            color: canAct ? "#4ade80" : "#94a3b8",
            fontWeight: "bold",
            fontSize: "14px",
          }}>
            {canAct ? "Your Turn" : "Opponent's Turn"}
          </span>
          {turnSecondsLeft != null && (
            <span style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minWidth: 48,
              padding: "6px 10px",
              backgroundColor: "rgba(0,0,0,0.35)",
              color: "#f1f5f9",
              fontWeight: "bold",
              fontSize: "20px",
              borderRadius: 6,
              border: "1px solid #475569",
            }}>
              {turnSecondsLeft}s
            </span>
          )}
        </div>
      </div>
      <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
        {BASIC_ACTIONS.map((action) => {
          const tooltipContent = (
            <div>
              {buildActionTooltipContent(action.id, myActionTooltips, action.label)}
              {tooltipBasicActionId === action.id && !disabled && (
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); handleBasicActionUse(action.id); }}
                  style={{
                    marginTop: 6,
                    padding: "4px 10px",
                    backgroundColor: action.color,
                    color: "white",
                    border: "none",
                    borderRadius: 4,
                    cursor: "pointer",
                    fontSize: 11,
                  }}
                >
                  Use
                </button>
              )}
            </div>
          );
          return (
            <Tooltip
              key={action.id}
              content={tooltipContent}
              open={tooltipBasicActionId === action.id}
              onOpenChange={(open) => { if (!open) setTooltipBasicActionId(null); }}
              placement="top"
            >
              <button
                onClick={() => handleBasicActionClick(action.id)}
                onMouseEnter={() => { if (!disabled) setTooltipBasicActionId(action.id); }}
                onMouseLeave={() => setTooltipBasicActionId(null)}
                disabled={disabled}
                style={buttonStyle(action.color)}
              >
                {action.emoji} {action.label}
              </button>
            </Tooltip>
          );
        })}
        {abilities.map((ab) => {
          const cd = cooldowns[ab.id] ?? 0;
          const isDisabled = disabled || cd > 0;
          const tooltipContent = (
            <div>
              {buildActionTooltipContent(ab.id, myActionTooltips, humanize(ab.id))}
              {tooltipAbilityId === ab.id && !isDisabled && (
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); handleAbilityUse(ab); }}
                  style={{
                    marginTop: 6,
                    padding: "4px 10px",
                    backgroundColor: "#6f42c1",
                    color: "white",
                    border: "none",
                    borderRadius: 4,
                    cursor: "pointer",
                    fontSize: 11,
                  }}
                >
                  Use
                </button>
              )}
            </div>
          );
          return (
            <Tooltip
              key={ab.id}
              content={tooltipContent}
              open={tooltipAbilityId === ab.id}
              onOpenChange={(open) => {
                if (!open) {
                  if (isDebugEnabled()) log("MODAL_CLOSE", { reason: "onOpenChange", abilityId: ab.id, modalOpen: false });
                  setTooltipAbilityId(null);
                }
              }}
              placement="top"
            >
              <button
                onClick={() => handleAbilityClick(ab)}
                onMouseEnter={() => { if (!isDisabled) setTooltipAbilityId(ab.id); }}
                onMouseLeave={() => setTooltipAbilityId(null)}
                disabled={isDisabled}
                style={buttonStyle("#6f42c1", cd > 0)}
              >
                {ab.emoji} {humanize(ab.id)}
                {cd > 0 && " (" + cd + ")"}
              </button>
            </Tooltip>
          );
        })}
      </div>
      <div style={{ marginTop: 12, textAlign: "center", color: "#999", fontSize: "14px" }}>
        {inFlight ? (
          <div>Processing action...</div>
        ) : canAct ? (
          <div>It&apos;s your turn! Choose an action above.</div>
        ) : (
          <div>Waiting for opponent&apos;s turn...</div>
        )}
      </div>
    </div>
  );
}
