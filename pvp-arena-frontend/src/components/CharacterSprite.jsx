import { getCharacterSprite } from "../data/assetMap";

/**
 * Renders one character sprite with pose (idle / attack / defend).
 * Sprites face RIGHT by default; use faceLeft=true for player 2 so they face each other.
 */
export default function CharacterSprite({ className, pose = "idle", faceLeft = false, compact = false, style = {} }) {
  const src = getCharacterSprite(className, pose);
  if (!src) return null;

  const positionOffset = compact ? "8%" : "20%";
  const widthPct = compact ? "28%" : "38%";
  const heightPct = compact ? "80%" : "90%";
  const minW = compact ? "56px" : "80px";
  const maxW = compact ? "100px" : "160px";
  const minH = compact ? "96px" : "120px";
  const maxH = compact ? "180px" : "240px";

  return (
    <div
      style={{
        position: "absolute",
        bottom: "20%",
        left: faceLeft ? undefined : positionOffset,
        right: faceLeft ? positionOffset : undefined,
        width: widthPct,
        minWidth: minW,
        maxWidth: maxW,
        height: heightPct,
        minHeight: minH,
        maxHeight: maxH,
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "center",
        filter: "drop-shadow(0 4px 12px rgba(0,0,0,0.5))",
        ...style,
      }}
    >
      <img
        src={src}
        alt=""
        style={{
          width: "100%",
          height: "100%",
          objectFit: "contain",
          objectPosition: "bottom center",
          transform: faceLeft ? "scaleX(-1)" : "none",
        }}
      />
    </div>
  );
}
