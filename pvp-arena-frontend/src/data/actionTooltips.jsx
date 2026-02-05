/**
 * Single source of truth for action and effect tooltips.
 * Numeric values from backend (gameState.player1_action_tooltips / player2_action_tooltips).
 */

import React from "react";
import { TooltipStatGrid } from "../components/Tooltip";

/**
 * Get tooltip stats for an action from backend state.
 * myActionTooltips = gameState.player1_action_tooltips or player2_action_tooltips (for current player).
 */
export function getActionTooltipStats(myActionTooltips, actionId) {
  if (!myActionTooltips || typeof myActionTooltips !== "object") return null;
  return myActionTooltips[actionId] || null;
}

/**
 * Build React content for an action tooltip: compact 2-column grid + summary.
 * Uses backend stats when available (myActionTooltips from game state).
 */
export function buildActionTooltipContent(actionId, myActionTooltips, title) {
  const stats = getActionTooltipStats(myActionTooltips, actionId);
  const displayTitle = title || (actionId === "attack" ? "Attack" : actionId === "defend" ? "Defend" : actionId === "heal" ? "Heal" : actionId);
  return (
    <TooltipStatGrid
      stats={stats}
      title={displayTitle}
      summaryOnly={false}
    />
  );
}

/** Shapeshift numeric bonuses (match backend abilities.py). */
const SHAPESHIFT_BONUSES = { damage_boost_pct: 25, defense_boost_pct: 25, heal_boost_pct: 20 };

/**
 * Build React content for an effect tooltip (player card).
 * effect = { name, turns_left, value?, damage_per_tick?, reflect_pct?, avoid_pct?, damage_boost_pct?, defense_boost_pct? }
 */
export function buildEffectTooltipContent(effect) {
  if (!effect) return null;
  const name = typeof effect === "object" ? effect.name : effect;
  const turns = typeof effect === "object" ? effect.turns_left : null;
  const hits = typeof effect === "object" ? effect.hits_left : null;
  const stats = {
    summary: "",
    turns_left: turns,
    duration: turns,
    hits_left: hits,
  };
    if (typeof effect === "object") {
    if (effect.value != null) stats.shield_amount = effect.value;
    if (effect.damage_per_tick != null) stats.damage_per_tick = effect.damage_per_tick;
    if (effect.reflect_pct != null) stats.reflect_pct = Math.round((effect.reflect_pct || 0) * 100);
    if (effect.reduction_pct != null) stats.reduction_pct = Math.round((effect.reduction_pct || 0) * 100);
    if (effect.avoid_pct != null) stats.avoid_pct = Math.round((effect.avoid_pct || 0) * 100);
    if (effect.damage_boost_pct != null) stats.damage_boost_pct = Math.round((effect.damage_boost_pct || 0) * 100);
    if (effect.defense_boost_pct != null) stats.defense_boost_pct = Math.round((effect.defense_boost_pct || 0) * 100);
    if (effect.heal_boost_pct != null) stats.heal_boost_pct = Math.round((effect.heal_boost_pct || 0) * 100);
    if (effect.damage_taken_pct != null) stats.damage_taken_pct = Math.round((effect.damage_taken_pct || 0) * 100);
    if (effect.dot_bonus_per_tick != null) stats.dot_bonus_per_tick = effect.dot_bonus_per_tick;
    if (effect.dot_damage_pct != null) stats.dot_damage_pct = typeof effect.dot_damage_pct === "number" ? effect.dot_damage_pct : Math.round((effect.dot_damage_pct - 1) * 100);
    if (name === "shapeshift" && stats.damage_boost_pct == null) {
      stats.damage_boost_pct = SHAPESHIFT_BONUSES.damage_boost_pct;
      stats.defense_boost_pct = SHAPESHIFT_BONUSES.defense_boost_pct;
      stats.heal_boost_pct = SHAPESHIFT_BONUSES.heal_boost_pct;
    }
    if (effect.flat_damage_bonus != null && effect.damage_reduction_pct != null) {
      const red = Math.round((effect.damage_reduction_pct || 0) * 100);
      stats.summary = "+" + effect.flat_damage_bonus + " flat damage, +" + red + "% damage reduction until end of your next turn.";
    } else if (hits != null) {
      if (stats.reduction_pct != null && stats.reflect_pct != null) {
        const n = hits != null ? hits : 1;
        stats.summary = "Next " + n + " hit(s) reduced by " + stats.reduction_pct + "%; reflect " + stats.reflect_pct + "% of reduced amount. Does not expire if unused.";
      }
      else if (stats.avoid_pct != null) stats.summary = "Avoids " + stats.avoid_pct + "% of next hit. Does not expire if unused.";
      else if (name === "defend") stats.summary = "Reduces damage of next hit by 50%. Does not expire if unused.";
      else stats.summary = "1 hit. Does not expire if unused.";
    } else if (stats.damage_taken_pct != null) stats.summary = "Target takes " + stats.damage_taken_pct + "% more damage until end of your next turn. " + (turns != null ? turns + " turn(s) left." : "");
    else if (stats.shield_amount != null) stats.summary = "Absorbs up to " + stats.shield_amount + " damage until end of your next turn. " + (turns != null ? turns + " turn(s) left." : "");
    else if (stats.damage_per_tick != null) stats.summary = stats.damage_per_tick + " damage/turn. " + (turns != null ? turns + " turn(s) left." : "");
    else if (stats.reflect_pct != null) stats.summary = "Reflects " + stats.reflect_pct + "% damage until end of your next turn. " + (turns != null ? turns + " turn(s) left." : "");
    else if (stats.avoid_pct != null) stats.summary = "Avoids " + stats.avoid_pct + "% of next attack until end of your next turn. " + (turns != null ? turns + " turn(s) left." : "");
    else if (name === "shadowstep_buff") {
      const parts = [];
      if (stats.dot_bonus_per_tick != null) parts.push("+" + stats.dot_bonus_per_tick + " DoT per tick");
      if (stats.dot_damage_pct != null) parts.push("+" + stats.dot_damage_pct + "% DoT damage");
      stats.summary = (parts.length ? "Your DoT deals " + parts.join(" and ") + ". " : "Your DoT deals more damage. ") + (turns != null ? turns + " turn(s) left." : "");
    } else if ((stats.damage_boost_pct != null || stats.defense_boost_pct != null || stats.heal_boost_pct != null) && name === "shapeshift") {
      const parts = [];
      if (stats.damage_boost_pct != null) parts.push("+" + stats.damage_boost_pct + "% damage");
      if (stats.defense_boost_pct != null) parts.push("+" + stats.defense_boost_pct + "% reduction");
      if (stats.heal_boost_pct != null) parts.push("+" + stats.heal_boost_pct + "% healing");
      stats.summary = (parts.join(", ") || "Shapeshift") + " until end of your next turn. " + (turns != null ? turns + " turn(s) left." : "");
    } else if (stats.damage_boost_pct != null && stats.defense_boost_pct != null) {
      stats.summary = "+" + stats.damage_boost_pct + "% damage, +" + stats.defense_boost_pct + "% reduction until end of your next turn. " + (turns != null ? turns + " turn(s) left." : "");
    } else stats.summary = (turns != null ? turns + " turn(s) left." : "");
  }
  const title = name ? (name.charAt(0).toUpperCase() + name.slice(1).replace(/_/g, " ")) : "Effect";
  return (
    <TooltipStatGrid
      stats={stats}
      title={title}
      summaryOnly={false}
    />
  );
}
