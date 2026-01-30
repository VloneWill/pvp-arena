/**
 * Builds a combat log message from an action result, using the correct perspective
 * for the logged-in user.
 * 
 * @param {Object} result - Action result from server
 * @param {number} meId - Current logged-in user's ID
 * @param {Object} usernameMap - Map of userId -> username
 * @returns {Object|null} - { message: string, tone: string } or null
 */
export function buildCombatMessage(result, meId, usernameMap) {
  if (!result) return null;

  const action = result.action;

  // Helper to get username, using "You" for the logged-in user
  const getDisplayName = (userId) => {
    if (!userId) return "Unknown";
    if (userId === meId) return "You";
    return usernameMap[userId] || `Player ${userId}`;
  };

  if (action === "attack" || action === "power_strike" || action === "arcane_blast") {
    const dmg = result.damage ?? 0;
    const defended = result.defended === true;
    const attackerId = result.attacker_id;
    // defender_id might be missing for some actions, try opponent_id as fallback
    const defenderId = result.defender_id || result.opponent_id;
    const attackerName = getDisplayName(attackerId);
    // If defenderId is still missing, try to infer from context
    const defenderName = defenderId ? getDisplayName(defenderId) : "Opponent";
    const extra = defended ? " (blocked, reduced damage)" : "";
    let attackType = "";
    if (action === "power_strike") attackType = " with Power Strike";
    else if (action === "arcane_blast") attackType = " with Arcane Blast";
    return { 
      message: `${attackerName} dealt ${dmg} damage to ${defenderName}${attackType}${extra}.`, 
      tone: "damage" 
    };
  }

  if (action === "heal" || action === "rejuvenate") {
    const healed = result.healed ?? 0;
    const actorId = result.actor_id;
    const actorName = getDisplayName(actorId);
    const abilityName = action === "rejuvenate" ? " with Rejuvenate" : "";
    return { message: `${actorName} healed for ${healed} HP${abilityName}.`, tone: "heal" };
  }

  if (action === "defend") {
    const actorId = result.actor_id;
    const actorName = getDisplayName(actorId);
    return { message: `${actorName} is blocking. Next attack will be reduced by 50%.`, tone: "defend" };
  }

  // Fallback for unknown actions
  const actorId = result.actor_id || result.attacker_id;
  const actorName = getDisplayName(actorId);
  return { message: `${actorName} used ${action}.`, tone: "neutral" };
}

/**
 * Get HP percentage (0-100)
 */
export function getHpPercent(current, max) {
  return Math.max(0, Math.min(100, (current / max) * 100));
}

/**
 * Get username from map with fallback
 */
export function getUsername(userId, usernameMap) {
  return usernameMap[userId] || `Player ${userId}`;
}

/**
 * Humanize snake_case to Title Case (single source for UI).
 * "arcane_blast" -> "Arcane Blast"
 */
export function humanize(str) {
  if (str == null || typeof str !== "string") return "";
  return str
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}
