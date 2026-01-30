/**
 * Central class icon (emoji) and color mapping. Used by Leaderboard, PlayerCard,
 * ProfileChip, MatchHistoryItem, AuthPanel, and any other class display.
 */
export const CLASS_EMOJI = {
  warrior: "⚔️",
  mage: "🔮",
  druid: "🌿",
  rogue: "🗡️",
};

export const CLASS_COLOR = {
  warrior: "#e63946",
  mage: "#457b9d",
  druid: "#2a9d8f",
  rogue: "#6a4c93",
};

export function getClassEmoji(className) {
  if (!className) return "";
  return CLASS_EMOJI[className] || "";
}

export function getClassColor(className) {
  if (!className) return "#666";
  return CLASS_COLOR[className] || "#666";
}
