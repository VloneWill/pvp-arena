/**
 * Maps combat log action_type / action_key to pose: "attack" | "defend".
 * Used so character sprites show the correct pose (attack vs defend) per ability type.
 * - Attack: basic attack, damage-dealing abilities/spells
 * - Defend: defend, heal, buffs, shields, blocks, evasion, mitigation
 */

const ATTACK_ACTION_KEYS = new Set([
  "attack",
  "power_strike",
  "execute",
  "fireball",
  "ice_bolt",
  "meteor",
  "nature_wrath",
  "backstab",
  "shadowstep",
  "poison", // DoT on enemy = offensive
]);

const DEFEND_ACTION_KEYS = new Set([
  "defend",
  "heal",
  "shield_wall",
  "battle_shout",
  "arcane_shield",
  "regrowth",
  "thorns",
  "shapeshift",
  "evade",
]);

/**
 * Get pose for the actor who performed the action.
 * @param {string} actionType - e.g. "attack", "defend", "heal", "effect_applied", or ability id
 * @param {string} [actionKey] - canonical key e.g. "power_strike", "shield_wall"
 * @returns {"attack"|"defend"}
 */
export function getActorPose(actionType, actionKey) {
  const key = actionKey || actionType;
  if (ATTACK_ACTION_KEYS.has(key)) return "attack";
  if (DEFEND_ACTION_KEYS.has(key)) return "defend";
  if (actionType === "attack" || (actionType && key && key !== "effect_applied")) {
    // Ability id that deals damage is usually stored as action_type
    if (actionType === "heal" || actionType === "defend") return "defend";
    return "attack";
  }
  if (actionType === "defend" || actionType === "heal") return "defend";
  if (actionType === "effect_applied" || actionType === "effect") return "defend";
  return "defend";
}

/**
 * Whether the defender in a damage event used mitigation (block/evade/absorb).
 * Used to show defend pose on the defending player.
 */
export function isDefenderMitigating(event) {
  if (event.defended === true) return true;
  const t = event.action_type;
  return t === "damage_absorbed" || t === "evade_avoided" || t === "damage_reflected";
}
