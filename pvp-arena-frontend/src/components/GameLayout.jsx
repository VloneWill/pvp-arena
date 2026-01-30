import MatchBanner from "./MatchBanner";
import PlayerCard from "./PlayerCard";
import ActionBar from "./ActionBar";
import CombatLog from "./CombatLog";

/**
 * Game layout: player panels, center action bar, scrollable combat log.
 * Used when a match is active or just finished.
 */
export default function GameLayout({
  gameState,
  status,
  winnerUsername,
  winnerId,
  usernameMap,
  userInfoMap,
  getUsername,
  getMaxHp,
  healthFlash,
  isPlayer1,
  currentTurn,
  canAct,
  actionInFlight,
  onAction,
  myInfo,
  myCooldowns,
  actionTooltips,
  combatLog,
  onReturnToMatchmaking,
  onForfeit,
  error,
}) {
  const p1Info = userInfoMap[gameState?.player1_id];
  const p2Info = userInfoMap[gameState?.player2_id];

  return (
    <div style={{
      display: "grid",
      gap: 20,
      gridTemplateRows: "auto auto 1fr auto",
      flex: 1,
      minHeight: 0,
    }}>
      <MatchBanner
        status={status}
        winnerUsername={winnerUsername}
        winnerId={winnerId}
      />

      {gameState && (
        <div style={{ display: "grid", gap: 16, gridTemplateColumns: "1fr auto 1fr" }}>
          <PlayerCard
            playerId={gameState.player1_id}
            username={getUsername(gameState.player1_id, usernameMap)}
            health={gameState.player1_health}
            maxHealth={getMaxHp(gameState.player1_id, p1Info, gameState)}
            isActive={status === "active" && currentTurn === gameState.player1_id}
            isMe={isPlayer1}
            flashColor={healthFlash.p1}
            className={p1Info?.class_name}
            level={p1Info?.level}
            xp={p1Info?.xp}
            activeEffects={gameState.player1_effects || []}
          />
          <div style={{ display: "flex", alignItems: "center", fontSize: "24px", fontWeight: "bold", color: "#666" }}>
            VS
          </div>
          <PlayerCard
            playerId={gameState.player2_id}
            username={getUsername(gameState.player2_id, usernameMap)}
            health={gameState.player2_health}
            maxHealth={getMaxHp(gameState.player2_id, p2Info, gameState)}
            isActive={status === "active" && currentTurn === gameState.player2_id}
            isMe={!isPlayer1}
            flashColor={healthFlash.p2}
            className={p2Info?.class_name}
            level={p2Info?.level}
            xp={p2Info?.xp}
            activeEffects={gameState.player2_effects || []}
          />
        </div>
      )}

      {status === "active" && (
        <ActionBar
          canAct={canAct}
          inFlight={actionInFlight}
          onAction={onAction}
          className={myInfo?.class_name}
          abilityCooldowns={myCooldowns}
          actionTooltips={actionTooltips}
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
