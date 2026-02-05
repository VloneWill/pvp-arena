/**
 * Centralized asset map: class → pose → image URL (Vite-processed).
 * Single source of truth for character sprites and battle backgrounds.
 */

// Backgrounds (randomly selected per match)
import arenaBg from "../assets/backgrounds/arena.png";
import forestBg from "../assets/backgrounds/forest.png";
import mountainBg from "../assets/backgrounds/mountain.png";

// Warrior
import warriorIdle from "../assets/sprites/characters/warrior/warrior_idle.png";
import warriorAttack from "../assets/sprites/characters/warrior/warrior_attack.png";
import warriorDefend from "../assets/sprites/characters/warrior/warrior_defend.png";

// Mage
import mageIdle from "../assets/sprites/characters/mage/mage_idle.png";
import mageAttack from "../assets/sprites/characters/mage/mage_attack.png";
import mageDefend from "../assets/sprites/characters/mage/mage_defend.png";

// Druid
import druidIdle from "../assets/sprites/characters/druid/druid_idle.png";
import druidAttack from "../assets/sprites/characters/druid/druid_attack.png";
import druidDefend from "../assets/sprites/characters/druid/druid_defend.png";

// Rogue
import rogueIdle from "../assets/sprites/characters/rogue/rogue_idle.png";
import rogueAttack from "../assets/sprites/characters/rogue/rogue_attack.png";
import rogueDefend from "../assets/sprites/characters/rogue/rogue_defend.png";

export const characters = {
  warrior: { idle: warriorIdle, attack: warriorAttack, defend: warriorDefend },
  mage: { idle: mageIdle, attack: mageAttack, defend: mageDefend },
  druid: { idle: druidIdle, attack: druidAttack, defend: druidDefend },
  rogue: { idle: rogueIdle, attack: rogueAttack, defend: rogueDefend },
};

export const backgrounds = [arenaBg, forestBg, mountainBg];

/** Pick a random background URL from the list. */
export function getRandomBackground() {
  return backgrounds[Math.floor(Math.random() * backgrounds.length)];
}

/** Get sprite URL for class and pose. Falls back to idle if missing. */
export function getCharacterSprite(classKey, pose) {
  const map = characters[classKey];
  if (!map) return characters.warrior?.idle || null;
  const url = map[pose] || map.idle;
  return url || null;
}
