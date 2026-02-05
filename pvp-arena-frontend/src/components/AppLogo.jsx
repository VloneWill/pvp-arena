/**
 * Reusable app logo. Preserves transparency; no stretching or distortion.
 */
import logoImg from "../assets/logo/logo.png";

export default function AppLogo({ width, height, style = {} }) {
  return (
    <img
      src={logoImg}
      alt="PvP Arena"
      {...(width != null && { width })}
      {...(height != null && { height })}
      style={{
        objectFit: "contain",
        display: "block",
        ...style,
      }}
    />
  );
}
