import React, { useEffect, useRef, useState } from "react";
import { log, isDebugEnabled } from "../utils/abilityModalDebug";

const MARGIN = 10;

/**
 * Dark custom tooltip. Viewport-aware: prefers top, then bottom, left, right; clamps inside viewport.
 * Desktop: hover shows. Mobile: first tap opens, second tap or "Use" triggers action.
 */
const TOOLTIP_STYLE = {
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
  /* px to avoid iOS viewport thrash when address bar shows/hides (was 40vh) */
  maxHeight: 280,
  overflowY: "auto",
};

function computeTooltipPosition(triggerRect, tooltipRect, preferredPlacement) {
  const w = window.innerWidth;
  const h = window.innerHeight;
  const tw = tooltipRect?.width ?? 200;
  const th = tooltipRect?.height ?? 80;
  const order = preferredPlacement === "top" ? ["top", "bottom", "left", "right"] : preferredPlacement === "bottom" ? ["bottom", "top", "left", "right"] : preferredPlacement === "left" ? ["left", "right", "top", "bottom"] : ["right", "left", "top", "bottom"];
  const cx = triggerRect.left + triggerRect.width / 2;
  const cy = triggerRect.top + triggerRect.height / 2;
  const gap = 6;

  for (const side of order) {
    let left, top;
    if (side === "top") {
      left = cx - tw / 2;
      top = triggerRect.top - th - gap;
    } else if (side === "bottom") {
      left = cx - tw / 2;
      top = triggerRect.bottom + gap;
    } else if (side === "left") {
      left = triggerRect.left - tw - gap;
      top = cy - th / 2;
    } else {
      left = triggerRect.right + gap;
      top = cy - th / 2;
    }
    const right = left + tw;
    const bottom = top + th;
    if (left >= MARGIN && right <= w - MARGIN && top >= MARGIN && bottom <= h - MARGIN) {
      return { left, top, side };
    }
  }
  let left = cx - tw / 2;
  let top = cy - th / 2;
  left = Math.max(MARGIN, Math.min(w - tw - MARGIN, left));
  top = Math.max(MARGIN, Math.min(h - th - MARGIN, top));
  return { left, top, side: "top" };
}

export default function Tooltip({
  content,
  children,
  open: controlledOpen,
  onOpenChange,
  disabled = false,
  placement = "top",
}) {
  const [internalOpen, setInternalOpen] = useState(false);
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : internalOpen;
  const setOpen = (v) => {
    if (!isControlled) setInternalOpen(v);
    onOpenChange?.(v);
  };
  const containerRef = useRef(null);
  const tooltipRef = useRef(null);
  const [position, setPosition] = useState(null);
  /** Ignore outside pointer events for this long after open (prevents iOS same-tap close) */
  const openedAtRef = useRef(0);

  useEffect(() => {
    if (open && isDebugEnabled()) log("MODAL_MOUNT", {});
    return () => {
      if (open && isDebugEnabled()) log("MODAL_UNMOUNT", {});
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    openedAtRef.current = Date.now();
    const onEscape = (e) => {
      if (e.key === "Escape") {
        if (isDebugEnabled()) log("MODAL_CLOSE", { reason: "escape" });
        setOpen(false);
      }
    };
    const onPointerDownOutside = (e) => {
      const now = Date.now();
      if (now - openedAtRef.current < 350) return;
      const isOutside =
        containerRef.current && !containerRef.current.contains(e.target) &&
        tooltipRef.current && !tooltipRef.current.contains(e.target);
      if (isOutside) {
        if (isDebugEnabled()) {
          log("OUTSIDE_HANDLER_FIRED", { eventType: e.type, willClose: true, targetTag: e.target?.tagName, targetClass: e.target?.className ?? "" });
        }
        setOpen(false);
      }
    };
    document.addEventListener("keydown", onEscape);
    document.addEventListener("pointerdown", onPointerDownOutside);
    return () => {
      document.removeEventListener("keydown", onEscape);
      document.removeEventListener("pointerdown", onPointerDownOutside);
    };
  }, [open]);

  useEffect(() => {
    if (!open || !content) {
      setPosition(null);
      return;
    }
    const update = () => {
      const trigger = containerRef.current;
      const tooltip = tooltipRef.current;
      if (!trigger) return;
      const triggerRect = trigger.getBoundingClientRect();
      const tooltipRect = tooltip ? tooltip.getBoundingClientRect() : { width: 200, height: 80 };
      const pos = computeTooltipPosition(triggerRect, tooltipRect, placement);
      setPosition(pos);
    };
    const raf = requestAnimationFrame(() => requestAnimationFrame(update));
    const resize = () => requestAnimationFrame(update);
    window.addEventListener("resize", resize);
    window.addEventListener("orientationchange", resize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("orientationchange", resize);
    };
  }, [open, content, placement]);

  const showTooltip = () => {
    if (!disabled) setOpen(true);
  };
  const hideTooltip = () => {
    setOpen(false);
  };

  const posStyle = position
    ? { left: position.left, top: position.top }
    : { left: -9999, top: -9999 };

  return (
    <span
      ref={containerRef}
      style={{ position: "relative", display: "inline-flex" }}
      onMouseEnter={showTooltip}
      onMouseLeave={hideTooltip}
      onPointerDown={(e) => e.stopPropagation()}
    >
      {typeof children === "function"
        ? children({ open, showTooltip, hideTooltip })
        : children}
      {open && content && (
        <span
          ref={tooltipRef}
          role="tooltip"
          style={{
            ...TOOLTIP_STYLE,
            ...posStyle,
          }}
          onPointerDown={(e) => e.stopPropagation()}
        >
          {content}
        </span>
      )}
    </span>
  );
}

/**
 * Renders a compact 2-column stat grid for action/effect tooltips.
 * stats: { damage_min, damage_max, heal_amount, shield_amount, duration, cooldown_remaining, summary, ... }
 */
export function TooltipStatGrid({ stats, title, summaryOnly }) {
  const s = stats || {};
  if (!title && !s.summary && Object.keys(s).length === 0) return null;
  const rows = [];
  if (s.damage_min != null && s.damage_max != null) {
    rows.push({ label: "Damage", value: s.damage_min === s.damage_max ? `${s.damage_max}` : `${s.damage_min}–${s.damage_max}` });
  }
  if (s.heal_amount != null) rows.push({ label: "Heal", value: `${s.heal_amount} HP` });
  if (s.shield_amount != null) rows.push({ label: "Shield", value: `${s.shield_amount}` });
  if (s.reduction_pct != null) rows.push({ label: "Reduction", value: `${s.reduction_pct}%` });
  if (s.reflect_pct != null) rows.push({ label: "Reflect", value: `${s.reflect_pct}%` });
  if (s.avoid_pct != null) rows.push({ label: "Avoid", value: `${s.avoid_pct}%` });
  if (s.damage_taken_pct != null) rows.push({ label: "Damage taken +", value: `${s.damage_taken_pct}%` });
  if (s.damage_per_tick != null) rows.push({ label: "DoT/turn", value: `${s.damage_per_tick}` });
  if (s.damage_boost_pct != null) rows.push({ label: "Damage +", value: `${s.damage_boost_pct}%` });
  if (s.defense_boost_pct != null) rows.push({ label: "Defense +", value: `${s.defense_boost_pct}%` });
  if (s.heal_boost_pct != null) rows.push({ label: "Healing +", value: `${s.heal_boost_pct}%` });
  if (s.hits_left != null) rows.push({ label: "Hits", value: `${s.hits_left} hit(s)` });
  if (s.duration != null) rows.push({ label: "Duration", value: `${s.duration} turn(s)` });
  if (s.cooldown_total != null && s.cooldown_total > 0) {
    rows.push({ label: "Cooldown", value: s.cooldown_remaining != null ? `${s.cooldown_remaining}/${s.cooldown_total}` : `${s.cooldown_total}` });
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {title && <div style={{ fontWeight: "bold", color: "#fff", fontSize: 12 }}>{title}</div>}
      {s.summary && <div style={{ color: "#b0b0b0", marginBottom: rows.length ? 4 : 0 }}>{s.summary}</div>}
      {!summaryOnly && rows.length > 0 && (
        <div style={{
          display: "grid",
          gridTemplateColumns: "auto 1fr",
          gap: "2px 12px",
          fontSize: 11,
          color: "#c0c0c0",
        }}>
          {rows.map((r, i) => (
            <React.Fragment key={i}>
              <span style={{ color: "#888" }}>{r.label}:</span>
              <span>{r.value}</span>
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
}
