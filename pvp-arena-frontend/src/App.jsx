import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "./api/client";
import { buildCombatMessage, getUsername } from "./utils/formatters";
import { useMatchPolling, useMatchmakingPolling } from "./hooks/useMatchPolling";
import AuthPanel from "./components/AuthPanel";
import HeaderBar from "./components/HeaderBar";
import MatchBanner from "./components/MatchBanner";
import PlayerCard from "./components/PlayerCard";
import ActionBar from "./components/ActionBar";
import CombatLog from "./components/CombatLog";
import MatchHistory from "./components/MatchHistory";

export default function App() {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("user1");
  const [password, setPassword] = useState("password123");
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [me, setMe] = useState(null);

  const [mmStatus, setMmStatus] = useState(null);
  const [match, setMatch] = useState(null);
  const [gameState, setGameState] = useState(null);
  const [combatLog, setCombatLog] = useState([]);
  const [usernameMap, setUsernameMap] = useState({}); // Map of userId -> username
  const [healthFlash, setHealthFlash] = useState({ p1: null, p2: null });
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState([]);
  const [actionInFlight, setActionInFlight] = useState(false);

  const [error, setError] = useState("");

  const isAuthed = useMemo(() => Boolean(token), [token]);

  async function loadMe(t = token) {
    const data = await apiFetch("/auth/me", { token: t });
    setMe(data);
    // Add to username map
    if (data?.id) {
      setUsernameMap(prev => ({ ...prev, [data.id]: data.username }));
    }
    return data;
  }

  async function loadUsername(userId) {
    if (!userId) return null;
    // Check if already in map
    if (usernameMap[userId]) return usernameMap[userId];
    
    try {
      const data = await apiFetch(`/auth/user/${userId}`, { token });
      if (data?.username) {
        setUsernameMap(prev => ({ ...prev, [userId]: data.username }));
        return data.username;
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  // Load current user on token change
  useEffect(() => {
    setError("");
    if (!token) {
      setMe(null);
      return;
    }
    loadMe().catch((e) => {
      setError(e.message);
      setToken("");
      localStorage.removeItem("token");
    });
    //eslint-disable-next-line
  }, [token]);

  // Load usernames when match/gameState changes
  useEffect(() => {
    if (match && gameState) {
      // Load both player usernames
      loadUsername(gameState.player1_id);
      loadUsername(gameState.player2_id);
      // Load winner username if match is finished
      if (gameState.winner_id) {
        loadUsername(gameState.winner_id);
      }
    }
  }, [match, gameState]);

  async function handleRegister() {
    setError("");
    await apiFetch("/auth/register", {
      method: "POST",
      body: { username, password },
    });
    await handleLogin();
  }

  async function handleLogin() {
    setError("");
    const data = await apiFetch("/auth/login", {
      method: "POST",
      body: { username, password },
    });
    const t = data.access_token;
    setToken(t);
    localStorage.setItem("token", t);
    await loadMe(t);
  }

  function handleLogout() {
    setError("");
    setToken("");
    localStorage.removeItem("token");
    setMe(null);
    setMmStatus(null);
    setMatch(null);
    setGameState(null);
    setCombatLog([]);
    setUsernameMap({});
  }

  async function refreshMatchState(matchId) {
    if (!matchId) return;
    const data = await apiFetch(`/matches/${matchId}/state`, { token });
    setGameState(data);
    return data;
  }

  // Polling for match state (only when in a match)
  useMatchPolling(
    match?.id && gameState?.status === "active" ? match.id : null,
    () => {
      if (match?.id) {
        refreshMatchState(match.id).catch(() => {});
      }
    },
    1000
  );

  // Polling for matchmaking (only when waiting)
  useMatchmakingPolling(
    mmStatus === "waiting",
    async () => {
      setError("");
      try {
        const data = await apiFetch("/matchmaking/join", {
          method: "POST",
          token,
        });
        setMmStatus(data.status);
        if (data.status === "matched" && data.match) {
          setMatch(data.match);
          const state = await refreshMatchState(data.match.id);
          // Load usernames immediately
          if (state) {
            loadUsername(state.player1_id);
            loadUsername(state.player2_id);
          }
        }
      } catch (e) {
        setError(e.message);
      }
    },
    1000
  );

  // Stop polling when match finishes
  useEffect(() => {
    if (gameState && gameState.status === "finished") {
      // Load winner username if not already loaded
      if (gameState.winner_id) {
        loadUsername(gameState.winner_id);
      }
    }
  }, [gameState?.status, gameState?.winner_id]);

  function addToCombatLog(message, tone) {
    setCombatLog(prev => [{ message, tone, timestamp: Date.now() }, ...prev].slice(0, 50));
  }

  async function joinMatchmaking() {
    setError("");
    setMmStatus(null);
    setMatch(null);
    setGameState(null);
    setCombatLog([]);

    try {
      const data = await apiFetch("/matchmaking/join", {
        method: "POST",
        token,
      });

      setMmStatus(data.status);

      if (data.status === "matched" && data.match) {
        setMatch(data.match);
        const state = await refreshMatchState(data.match.id);
        // Load usernames immediately
        if (state) {
          loadUsername(state.player1_id);
          loadUsername(state.player2_id);
        }
      }
    } catch (e) {
      setError(`${e.message}${e.status ? ` (HTTP ${e.status})` : ""}`);
      setMmStatus("error");
    }
  }

  async function leaveMatchmaking() {
    setError("");
    try {
      await apiFetch("/matchmaking/leave", { method: "POST", token });
      setMmStatus(null);
    } catch (e) {
      setError(`${e.message}${e.status ? ` (HTTP ${e.status})` : ""}`);
    }
  }

  async function toggleMatchmaking() {
    if (mmStatus === "waiting") {
      await leaveMatchmaking();
    } else {
      await joinMatchmaking();
    }
  }

  async function forfeitMatch() {
    if (!match) return;
    setError("");
    try {
      await apiFetch(`/matches/${match.id}/forfeit`, { method: "POST", token });
      setMatch(null);
      setGameState(null);
      setCombatLog([]);
      setMmStatus(null);
    } catch (e) {
      setError(`${e.message}${e.status ? ` (HTTP ${e.status})` : ""}`);
    }
  }

  async function loadHistory() {
    try {
      const data = await apiFetch("/matches/history?limit=25", { token });
      setHistory(data || []);
    } catch (e) {
      setError(`${e.message}${e.status ? ` (HTTP ${e.status})` : ""}`);
    }
  }

  async function doAction(action) {
    if (!match || !gameState || actionInFlight) return;
    
    setError("");
    setActionInFlight(true);
    
    try {
      const data = await apiFetch(`/matches/${match.id}/action`, {
        method: "POST",
        token,
        body: { action },
      });

      // Update game state immediately from response
      if (data.game_state) {
        setGameState(data.game_state);
      }

      // Build and add combat log message
      if (data.result) {
        const resultWithAction = { ...data.result, action: data.action || data.result.action };
        const combatMsg = buildCombatMessage(resultWithAction, me?.id, usernameMap);
        if (combatMsg) {
          addToCombatLog(combatMsg.message, combatMsg.tone);
        }

        // Flash health bar on damage/heal
        if (action === "attack" || action === "double_attack") {
          const isP1 = resultWithAction.attacker_id === gameState.player1_id;
          setHealthFlash(isP1 ? { p1: "#f44336", p2: null } : { p1: null, p2: "#f44336" });
          setTimeout(() => setHealthFlash({ p1: null, p2: null }), 300);
        } else if (action === "heal") {
          const isP1 = resultWithAction.actor_id === gameState.player1_id;
          setHealthFlash(isP1 ? { p1: "#4caf50", p2: null } : { p1: null, p2: "#4caf50" });
          setTimeout(() => setHealthFlash({ p1: null, p2: null }), 300);
        }
      }

      // Always refresh match state after action to ensure sync
      await refreshMatchState(match.id);
      
    } catch (e) {
      setError(`${e.message}${e.status ? ` (HTTP ${e.status})` : ""}`);
    } finally {
      setActionInFlight(false);
    }
  }

  const myId = me?.id;
  const currentTurn = gameState?.current_turn;
  const status = gameState?.status;
  const winnerId = gameState?.winner_id;
  const canAct = Boolean(match && gameState && status === "active" && currentTurn === myId && !actionInFlight);
  const isPlayer1 = gameState && myId === gameState.player1_id;

  // Get winner username from map
  const winnerUsername = useMemo(() => {
    if (!winnerId) return null;
    return getUsername(winnerId, usernameMap);
  }, [winnerId, usernameMap]);

  return (
    <div style={{ 
      fontFamily: "system-ui, -apple-system, sans-serif", 
      padding: 20, 
      maxWidth: 1000, 
      margin: "0 auto",
      backgroundColor: "#121212",
      minHeight: "100vh",
      color: "white"
    }}>
      <h1 style={{ textAlign: "center", marginBottom: 24, color: "white" }}>⚔️ PvP Arena</h1>

      {!isAuthed ? (
        <AuthPanel
          mode={mode}
          setMode={setMode}
          username={username}
          setUsername={setUsername}
          password={password}
          setPassword={setPassword}
          onLogin={handleLogin}
          onRegister={handleRegister}
          error={error}
        />
      ) : (
        <div style={{ display: "grid", gap: 20 }}>
          <HeaderBar
            username={me?.username || "Unknown"}
            showHistory={showHistory}
            onToggleHistory={() => { 
              setShowHistory(!showHistory); 
              if (!showHistory) loadHistory(); 
            }}
            onLogout={handleLogout}
          />

          {showHistory && (
            <MatchHistory history={history} onRefresh={loadHistory} />
          )}

          {!match ? (
            <>
              <div style={{ 
                padding: 20, 
                border: "2px solid #4a5568", 
                borderRadius: 8, 
                textAlign: "center",
                backgroundColor: "#1e1e1e"
              }}>
                <h2 style={{ marginTop: 0, color: "white" }}>Matchmaking</h2>
                <button
                  onClick={toggleMatchmaking}
                  disabled={mmStatus === "waiting"}
                  style={{
                    backgroundColor: mmStatus === "waiting" ? "#4a5568" : "#28a745",
                    color: "white",
                    border: "none",
                    padding: "12px 24px",
                    borderRadius: "6px",
                    fontSize: "16px",
                    fontWeight: "bold",
                    cursor: mmStatus === "waiting" ? "not-allowed" : "pointer",
                  }}
                >
                  {mmStatus === "waiting" ? "Searching for opponent..." : "Join Matchmaking"}
                </button>
                {mmStatus === "waiting" && (
                  <div style={{ marginTop: 12, color: "#999" }}>
                    <div>⏳ Waiting for opponent...</div>
                  </div>
                )}
              </div>
              {error ? (
                <div style={{ 
                  color: "#ff6b6b", 
                  padding: 12, 
                  backgroundColor: "#2d1b1b", 
                  borderRadius: 8,
                  border: "1px solid #5a2a2a"
                }}>
                  {error}
                </div>
              ) : null}
            </>
          ) : (
            <div style={{ display: "grid", gap: 20 }}>
              <MatchBanner 
                status={status} 
                winnerUsername={winnerUsername}
                winnerId={winnerId}
              />

              {/* Player Panels */}
              {gameState && (
                <div style={{ display: "flex", gap: 16 }}>
                  <PlayerCard
                    playerId={gameState.player1_id}
                    username={getUsername(gameState.player1_id, usernameMap)}
                    health={gameState.player1_health}
                    maxHealth={100}
                    isActive={status === "active" && currentTurn === gameState.player1_id}
                    isMe={isPlayer1}
                    flashColor={healthFlash.p1}
                  />
                  <div style={{ display: "flex", alignItems: "center", fontSize: "24px", fontWeight: "bold", color: "#666" }}>
                    VS
                  </div>
                  <PlayerCard
                    playerId={gameState.player2_id}
                    username={getUsername(gameState.player2_id, usernameMap)}
                    health={gameState.player2_health}
                    maxHealth={100}
                    isActive={status === "active" && currentTurn === gameState.player2_id}
                    isMe={!isPlayer1}
                    flashColor={healthFlash.p2}
                  />
                </div>
              )}

              {/* Action Buttons */}
              {status === "active" && (
                <ActionBar 
                  canAct={canAct}
                  inFlight={actionInFlight}
                  onAction={doAction}
                />
              )}

              {status === "finished" && (
                <div style={{ textAlign: "center", padding: 20 }}>
                  <div style={{ fontSize: "18px", marginBottom: 12, color: "white" }}>
                    Match Over
                  </div>
                  <button
                    onClick={() => {
                      setMatch(null);
                      setGameState(null);
                      setCombatLog([]);
                      setMmStatus(null);
                    }}
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

              {/* Combat Log */}
              <CombatLog entries={combatLog} />

              {status === "active" && (
                <div style={{ textAlign: "center" }}>
                  <button
                    onClick={forfeitMatch}
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
                  border: "1px solid #5a2a2a"
                }}>
                  {error}
                </div>
              ) : null}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
