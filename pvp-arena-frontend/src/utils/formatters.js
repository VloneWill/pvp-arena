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

  if (action === "attack" || action === "double_attack") {
    const dmg = result.damage ?? 0;
    const defended = result.defended === true;
    const attackerId = result.attacker_id;
    const defenderId = result.defender_id;
    const attackerName = getDisplayName(attackerId);
    const defenderName = getDisplayName(defenderId);
    const extra = defended ? " (blocked, reduced damage)" : "";
    const attackType = action === "double_attack" ? " with a powerful double attack" : "";
    return { 
      message: `${attackerName} dealt ${dmg} damage to ${defenderName}${attackType}${extra}.`, 
      tone: "damage" 
    };
  }

  if (action === "heal") {
    const healed = result.healed ?? 0;
    const actorId = result.actor_id;
    const actorName = getDisplayName(actorId);
    return { message: `${actorName} healed for ${healed} HP.`, tone: "heal" };
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
