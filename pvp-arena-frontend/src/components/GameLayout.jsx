import MatchBanner from "./MatchBanner";
import PlayerCard from "./PlayerCard";
import ActionBar from "./ActionBar";
import CombatLog from "./CombatLog";
import ArenaScene from "./ArenaScene";

/**
 * Game layout: arena scene, player panels, action bar, combat log.
 * Used when a match is active or just finished.
 */
export default function GameLayout({
  gameState,
  status,
  winnerUsername,
  winnerId,
  leftPlayer,
  rightPlayer,
  canAct,
  actionInFlight,
  onAction,
  myInfo,
  myCooldowns,
  actionTooltips,
  combatLog,
  matchBackgroundUrl,
  onReturnToMatchmaking,
  onForfeit,
  error,
}) {
  return (
    <div style={{
      display: "grid",
      gap: 20,
      gridTemplateRows: "auto auto auto auto 1fr auto auto",
      flex: 1,
      minHeight: 0,
    }}>
      <MatchBanner
        status={status}
        winnerUsername={winnerUsername}
        winnerId={winnerId}
      />

      {gameState && leftPlayer && rightPlayer && (
        <div className="match-cards-row">
          <div style={{ minWidth: 0 }}>
            <PlayerCard
              playerId={leftPlayer.playerId}
              username={leftPlayer.username}
              health={leftPlayer.health}
              maxHealth={leftPlayer.maxHealth}
              isActive={leftPlayer.isActive}
              isMe={leftPlayer.isMe}
              flashColor={leftPlayer.flashColor}
              className={leftPlayer.class_name}
              level={leftPlayer.level}
              xp={leftPlayer.xp}
              activeEffects={leftPlayer.activeEffects}
            />
          </div>
          <div className="match-vs" style={{ display: "flex", alignItems: "center", justifyContent: "center", fontSize: "24px", fontWeight: "bold", color: "#666" }}>
            VS
          </div>
          <div style={{ minWidth: 0 }}>
            <PlayerCard
              playerId={rightPlayer.playerId}
              username={rightPlayer.username}
              health={rightPlayer.health}
              maxHealth={rightPlayer.maxHealth}
              isActive={rightPlayer.isActive}
              isMe={rightPlayer.isMe}
              flashColor={rightPlayer.flashColor}
              className={rightPlayer.class_name}
              level={rightPlayer.level}
              xp={rightPlayer.xp}
              activeEffects={rightPlayer.activeEffects}
            />
          </div>
        </div>
      )}

      {gameState && leftPlayer && rightPlayer && (
        <ArenaScene
          backgroundImageUrl={matchBackgroundUrl}
          leftClassName={leftPlayer.class_name}
          leftPose={leftPlayer.pose}
          rightClassName={rightPlayer.class_name}
          rightPose={rightPlayer.pose}
        />
      )}

      {status === "active" && (
        <ActionBar
          canAct={canAct}
          inFlight={actionInFlight}
          onAction={onAction}
          className={myInfo?.class_name}
          abilityCooldowns={myCooldowns}
          actionTooltips={actionTooltips}
          turnExpiresAt={gameState?.turn_expires_at}
        />
      )}

      {status === "finished" && (
        <div style={{ textAlign: "center", padding: 20 }}>
          <div style={{ fontSize: "18px", marginBottom: 12, color: "white" }}>Match Over</div>
          <button
            onClick={onReturnToMatchmaking}
            style={{
              backgroundColor: "#28a745",
              color: "white",
              border: "none",
              padding: "12px 24px",
              borderRadius: "6px",
              fontSize: "16px",
              fontWeight: "bold",
              cursor: "pointer",
            }}
          >
            Return to Matchmaking
          </button>
        </div>
      )}

      <div style={{ minHeight: 0, flex: 1, display: "flex", flexDirection: "column" }}>
        <CombatLog entries={combatLog} />
      </div>

      {status === "active" && (
        <div style={{ textAlign: "center" }}>
          <button
            onClick={onForfeit}
            style={{
              backgroundColor: "#dc3545",
              color: "white",
              border: "none",
              padding: "8px 16px",
              borderRadius: "6px",
              cursor: "pointer",
            }}
          >
            Forfeit Match
          </button>
        </div>
      )}

      {error ? (
        <div style={{
          color: "#ff6b6b",
          padding: 12,
          backgroundColor: "#2d1b1b",
          borderRadius: 8,
          border: "1px solid #5a2a2a",
        }}>
          {error}
        </div>
      ) : null}
    </div>
  );
}
