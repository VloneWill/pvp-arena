import { getCharacterSprite } from "../data/assetMap";

/**
 * Renders one character sprite with pose (idle / attack / defend).
 * Sprites face RIGHT by default; use faceLeft=true for player 2 so they face each other.
 */
export default function CharacterSprite({ className, pose = "idle", faceLeft = false, style = {} }) {
  const src = getCharacterSprite(className, pose);
  if (!src) return null;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: faceLeft ? undefined : "20%",
        right: faceLeft ? "20%" : undefined,
        width: "38%",
        minWidth: "80px",
        maxWidth: "160px",
        height: "90%",
        minHeight: "120px",
        maxHeight: "240px",
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
