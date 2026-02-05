import CharacterSprite from "./CharacterSprite";

/**
 * Battle scene: background + left/right character sprites.
 * Left sprite faces RIGHT; right sprite faces LEFT (scaleX(-1)) so they face each other.
 * leftPlayer/rightPlayer are derived in parent (opponent = left, you = right).
 */
export default function ArenaScene({ backgroundImageUrl, leftClassName, leftPose, rightClassName, rightPose }) {
  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        aspectRatio: "2 / 1",
        minHeight: 180,
        maxHeight: "min(50vh, 320px)",
        borderRadius: 8,
        overflow: "hidden",
        border: "1px solid #333",
        backgroundColor: "#1a1a1a",
      }}
    >
      {backgroundImageUrl && (
        <img
          src={backgroundImageUrl}
          alt=""
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: "center center",
          }}
        />
      )}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
        }}
      >
        <CharacterSprite
          className={leftClassName || "warrior"}
          pose={leftPose || "idle"}
          faceLeft={false}
        />
        <CharacterSprite
          className={rightClassName || "warrior"}
          pose={rightPose || "idle"}
          faceLeft
        />
      </div>
    </div>
  );
}
