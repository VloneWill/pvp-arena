import React, { useEffect } from "react";
import { humanize } from "../utils/formatters";
import { buildActionTooltipContent } from "../data/actionTooltips";
import { log, isDebugEnabled } from "../utils/abilityModalDebug";

/**
 * Single ability-confirm modal. Rendered in a stable place (GameLayout).
 * Controlled by selectedAbilityId (string). Does not remount on poll/timer.
 * Close only on: Use, Cancel, or backdrop tap (e.target === e.currentTarget).
 */
const MODAL_STYLE = {
  position: "fixed",
  zIndex: 9999,
  padding: "6px 10px",
  backgroundColor: "#1a1a1a",
  border: "1px solid #444",
  borderRadius: 6,
  boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
  color: "#e0e0e0",
  fontSize: 11,
  lineHeight: 1.35,
  maxWidth: 260,
  minWidth: 180,
  whiteSpace: "normal",
  pointerEvents: "auto",
  maxHeight: 280,
  overflowY: "auto",
  left: "50%",
  top: "50%",
  transform: "translate(-50%, -50%)",
};

export default function AbilityConfirmModal({
  open,
  abilityId,
  actionTooltips,
  disabled,
  onConfirm,
  onClose,
}) {
  useEffect(() => {
    if (open && isDebugEnabled()) log("MODAL_MOUNT", {});
    return () => {
      if (open && isDebugEnabled()) log("MODAL_UNMOUNT", {});
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onEscape = (e) => {
      if (e.key === "Escape") {
        if (isDebugEnabled()) log("MODAL_CLOSE", { reason: "escape", abilityId, modalOpen: false });
        onClose();
      }
    };
    document.addEventListener("keydown", onEscape);
    return () => document.removeEventListener("keydown", onEscape);
  }, [open, abilityId, onClose]);

  if (!open || !abilityId) return null;

  const handleBackdrop = (e) => {
    if (e.target !== e.currentTarget) return;
    if (isDebugEnabled()) log("OUTSIDE_HANDLER_FIRED", { eventType: e.type, willClose: true, backdropTargetIsCurrentTarget: e.target === e.currentTarget });
    if (isDebugEnabled()) log("MODAL_CLOSE", { reason: "backdrop", abilityId, modalOpen: false });
    onClose();
  };

  const handleUse = (e) => {
    e.stopPropagation();
    if (isDebugEnabled()) log("MODAL_CLOSE", { reason: "use_button", abilityId, modalOpen: false });
    onConfirm();
  };

  const title = humanize(abilityId);

  return (
    <div
      role="presentation"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9998,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "rgba(0,0,0,0.4)",
        pointerEvents: "auto",
      }}
      onPointerDown={handleBackdrop}
    >
      <div
        role="dialog"
        aria-label={`Confirm ${title}`}
        style={MODAL_STYLE}
        onPointerDown={(e) => e.stopPropagation()}
      >
        {buildActionTooltipContent(abilityId, actionTooltips || {}, title)}
        <button
          type="button"
          onClick={handleUse}
          disabled={disabled}
          style={{
            marginTop: 6,
            padding: "4px 10px",
            backgroundColor: "#6f42c1",
            color: "white",
            border: "none",
            borderRadius: 4,
            cursor: disabled ? "not-allowed" : "pointer",
            fontSize: 11,
            opacity: disabled ? 0.6 : 1,
          }}
        >
          Use
        </button>
      </div>
    </div>
  );
}
