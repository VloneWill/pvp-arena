import { useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "./api/client";
import { getUsername, humanize } from "./utils/formatters";
import { useMatchPolling, useMatchmakingPolling } from "./hooks/useMatchPolling";
import { getRandomBackground } from "./data/assetMap";
import { getActorPose, isDefenderMitigating } from "./data/poseFromAction";
import AuthPanel from "./components/AuthPanel";
import AppLogo from "./components/AppLogo";
import HeaderBar from "./components/HeaderBar";
import GameLayout from "./components/GameLayout";
import MatchHistory from "./components/MatchHistory";
import Leaderboard from "./components/Leaderboard";
import landingPageBg from "./assets/landing_page/landing_page.png";

export default function App() {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [className, setClassName] = useState("");
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [me, setMe] = useState(null);

  const [mmStatus, setMmStatus] = useState(null);
  const [match, setMatch] = useState(null);
  const [gameState, setGameState] = useState(null);
  const [combatLog, setCombatLog] = useState([]);
  const [usernameMap, setUsernameMap] = useState({}); // Map of userId -> username
  const [userInfoMap, setUserInfoMap] = useState({}); // Map of userId -> {class_name, level, xp}
  const [healthFlash, setHealthFlash] = useState({ p1: null, p2: null });
  const [showHistory, setShowHistory] = useState(false);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [history, setHistory] = useState([]);
  const [mmInFlight, setMmInFlight] = useState(false);
  const [actionInFlight, setActionInFlight] = useState(false);
  const [prevGameState, setPrevGameState] = useState(null);
  const [matchFinishedTime, setMatchFinishedTime] = useState(null);
  const [hasRefreshedForFinish, setHasRefreshedForFinish] = useState(false);
  const [matchBackgroundUrl, setMatchBackgroundUrl] = useState(null);
  const [playerPoses, setPlayerPoses] = useState({});

  const [error, setError] = useState("");
  const [usernameError, setUsernameError] = useState("");

  const lastCombatLogLengthRef = useRef(0);
  const poseTimeoutRef = useRef({});

  const isAuthed = useMemo(() => Boolean(token), [token]);

  const POSE_DURATION_MS = 900;

  function setPlayerPose(playerId, pose) {
    if (!playerId || !["idle", "attack", "defend"].includes(pose)) return;
    setPlayerPoses((prev) => ({ ...prev, [playerId]: pose }));
    if (pose === "idle") return;
    const key = String(playerId);
    if (poseTimeoutRef.current[key]) clearTimeout(poseTimeoutRef.current[key]);
    poseTimeoutRef.current[key] = setTimeout(() => {
      setPlayerPoses((prev) => ({ ...prev, [playerId]: "idle" }));
      delete poseTimeoutRef.current[key];
    }, POSE_DURATION_MS);
  }

  async function loadMe(t = token) {
    const data = await apiFetch("/auth/me", { token: t });
    setMe(data);
    // Add to username and userInfo maps
    if (data?.id) {
      setUsernameMap(prev => ({ ...prev, [data.id]: data.username }));
      setUserInfoMap(prev => ({ ...prev, [data.id]: { 
        class_name: data.class_name, 
        level: data.level, 
        xp: data.xp 
      }}));
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
        setUserInfoMap(prev => ({ ...prev, [userId]: { 
          class_name: data.class_name, 
          level: data.level, 
          xp: data.xp 
        }}));
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

  // Random background once per match; clear when match ends
  useEffect(() => {
    if (!match) {
      setMatchBackgroundUrl(null);
      setPlayerPoses({});
      lastCombatLogLengthRef.current = 0;
      return;
    }
    setMatchBackgroundUrl((prev) => (prev ? prev : getRandomBackground()));
  }, [match]);

  // Trigger pose changes only when a new action appears in combat_log
  useEffect(() => {
    const log = gameState?.combat_log;
    if (!Array.isArray(log) || !gameState?.player1_id || !gameState?.player2_id) return;
    const len = log.length;
    if (len <= lastCombatLogLengthRef.current) return;
    lastCombatLogLengthRef.current = len;
    const lastEvent = log[len - 1];
    const actionType = lastEvent?.action_type;
    const actionKey = lastEvent?.action_key ?? actionType;
    const actorId = lastEvent?.actor_id ?? lastEvent?.attacker_id;
    if (actorId) {
      const pose = getActorPose(actionType, actionKey);
      setPlayerPose(actorId, pose);
    }
    const defenderId = lastEvent?.defender_id;
    if (defenderId && isDefenderMitigating(lastEvent)) {
      setPlayerPose(defenderId, "defend");
    }
  }, [gameState?.combat_log, gameState?.player1_id, gameState?.player2_id]);

  // Reconcile matchmaking status on load (e.g. after refresh)
  useEffect(() => {
    if (!token || !isAuthed) return;
    apiFetch("/matchmaking/status", { token })
      .then((data) => {
        if (data.in_queue) setMmStatus("waiting");
      })
      .catch(() => {});
  }, [token, isAuthed]);

  // Load usernames and update stats when match/gameState changes
  useEffect(() => {
    if (match && gameState) {
      // Load both player usernames
      loadUsername(gameState.player1_id);
      loadUsername(gameState.player2_id);
      // Load winner username if match is finished
      if (gameState.winner_id) {
        loadUsername(gameState.winner_id);
      }
      
      // Update player stats from match state (authoritative source)
      if (gameState.player1_stats) {
        setUserInfoMap(prev => ({
          ...prev,
          [gameState.player1_id]: {
            class_name: gameState.player1_stats.class_name,
            level: gameState.player1_stats.level,
            xp: gameState.player1_stats.xp
          }
        }));
      }
      if (gameState.player2_stats) {
        setUserInfoMap(prev => ({
          ...prev,
          [gameState.player2_id]: {
            class_name: gameState.player2_stats.class_name,
            level: gameState.player2_stats.level,
            xp: gameState.player2_stats.xp
          }
        }));
      }
      
      // Also update own stats from match state when match finishes
      if (gameState.status === "finished" && me) {
        const myStats = me.id === gameState.player1_id 
          ? gameState.player1_stats 
          : gameState.player2_stats;
        if (myStats) {
          setMe(prev => prev ? { ...prev, level: myStats.level, xp: myStats.xp } : prev);
        }
      }
    }
  }, [match, gameState, me]);

  async function handleRegister() {
    setError("");
    setUsernameError("");
    if (!className) {
      setError("Please select a class");
      return;
    }
    try {
      await apiFetch("/auth/register", {
        method: "POST",
        body: { username, password, class_name: className },
      });
      await handleLogin();
    } catch (e) {
      const msg = e.message || "Registration failed";
      if (msg === "Username contains disallowed language.") {
        setUsernameError(msg);
      } else {
        setError(msg);
      }
    }
  }

  async function handleLogin() {
    setError("");
    try {
      const data = await apiFetch("/auth/login", {
        method: "POST",
        body: { username, password },
      });
      const t = data.access_token;
      setToken(t);
      localStorage.setItem("token", t);
      await loadMe(t);
    } catch (e) {
      setError(e.message || "Login failed");
    }
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
    const wasActive = gameState?.status === "active";
    const isFinished = data?.status === "finished";
    setPrevGameState(gameState);
    setGameState(data);
    // If match just finished, refetch user stats immediately for both clients
    if (wasActive && isFinished) {
      loadMe().catch(() => {});
    }
    return data;
  }

  // Polling for match state (continue polling when active or just finished to detect status changes)
  // Continue polling for a few seconds after match finishes to ensure both clients detect it
  useEffect(() => {
    if (gameState?.status === "finished" && !matchFinishedTime) {
      setMatchFinishedTime(Date.now());
    } else if (gameState?.status !== "finished") {
      setMatchFinishedTime(null);
    }
  }, [gameState?.status, matchFinishedTime]);
  
  const shouldPoll = match?.id && (
    gameState?.status === "active" ||
    (gameState?.status === "finished" && matchFinishedTime && (Date.now() - matchFinishedTime < 5000))
  );

  async function pollTick(matchId) {
    if (!matchId) return;
    try {
      const data = await apiFetch(`/matches/${matchId}/tick`, { method: "POST", token });
      if (data.game_state) {
        setGameState(data.game_state);
        if (data.match) setMatch(data.match);
      } else if (data.match) {
        setMatch(data.match);
        await refreshMatchState(matchId);
      }
    } catch (_) {}
  }

  useMatchPolling(
    shouldPoll ? match.id : null,
    () => pollTick(match?.id),
    2500
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
        // Only show error if it's not a network error during normal flow
        // 422/400 errors are expected during matchmaking, don't show them
        if (e.status && e.status >= 500) {
          setError(e.message);
        }
        // Silently handle other errors during polling
      }
    },
    1000
  );

  // Sync combat log from server (authoritative source). Prefer server-rendered combat_log_display.
  useEffect(() => {
    if (!gameState || !me) return;

    const display = gameState.combat_log_display;
    if (Array.isArray(display) && display.length > 0) {
      const withTimestamp = display.map((entry, idx) => ({
        ...entry,
        message: entry.message,
        tone: entry.tone,
        isMyAction: entry.is_my_action === true || entry.isMyAction === true,
        timestamp: Date.now() - (display.length - idx) * 1000,
      }));
      setCombatLog(withTimestamp.slice().reverse());
      return;
    }

    // Fallback: build from combat_log (older API)
    const serverLog = gameState.combat_log || [];
    const myId = me.id;
    const messages = serverLog.map((event, idx) => {
      const actorId = event.actor_id || event.attacker_id;
      const isMyAction = actorId === myId;
      const actionKey = event.action_key || event.action_type;
      const label = humanize(actionKey);
      if (event.damage != null && (event.attacker_id != null || event.defender_id != null)) {
        const att = event.attacker_id === myId ? "You" : (event.attacker_username || `Player ${event.attacker_id}`);
        const def = event.defender_id === myId ? "You" : (event.defender_username || `Player ${event.defender_id}`);
        const extra = event.defended ? " (blocked, reduced damage)" : "";
        return { message: `${att} dealt ${event.damage} damage to ${def} with ${label}.${extra}`, tone: "damage", isMyAction, timestamp: Date.now() - (serverLog.length - idx) * 1000 };
      }
      if (event.healed != null && event.actor_id != null) {
        const actor = event.actor_id === myId ? "You" : (event.actor_username || `Player ${event.actor_id}`);
        return { message: `${actor} healed ${event.healed} HP with ${label}.`, tone: "heal", isMyAction, timestamp: Date.now() - (serverLog.length - idx) * 1000 };
      }
      if (event.action_type === "defend" || event.action_type === "shield_wall") {
        const actor = event.actor_id === myId ? "You" : (event.actor_username || `Player ${event.actor_id}`);
        return { message: `${actor} used ${label}. Next incoming hit will be reduced by 50%.`, tone: "defend", isMyAction, timestamp: Date.now() - (serverLog.length - idx) * 1000 };
      }
      if (event.action_type === "dot_tick") {
        const target = event.target_id === myId ? "You" : (event.target_username || `Player ${event.target_id}`);
        const effectName = humanize(event.effect || "unknown");
        const turns = event.turns_left ?? 0;
        return { message: `${target} took ${event.damage ?? 0} ${effectName} damage from ${effectName} (${turns} turn${turns !== 1 ? "s" : ""} remaining).`, tone: "damage", isMyAction: event.target_id === myId, timestamp: Date.now() - (serverLog.length - idx) * 1000 };
      }
      const actor = (event.actor_id ?? event.attacker_id) === myId ? "You" : (event.actor_username || event.attacker_username || "Unknown");
      return { message: `${actor} used ${label}.`, tone: "neutral", isMyAction, timestamp: Date.now() - (serverLog.length - idx) * 1000 };
    });
    setCombatLog(messages.slice().reverse());
  }, [gameState?.combat_log, gameState?.combat_log_display, gameState?.turn_number, me?.id]);

  // When match finishes, ensure both clients have refreshed stats
  // Stats are now included in match state, but we still refetch /auth/me as backup
  useEffect(() => {
    if (gameState && gameState.status === "finished" && !hasRefreshedForFinish) {
      // Load winner username if not already loaded
      if (gameState.winner_id) {
        loadUsername(gameState.winner_id);
      }
      // Refetch user stats to get updated XP and level (backup to match state stats)
      // This ensures both clients (winner and loser) see their updated XP
      loadMe().catch(() => {});
      setHasRefreshedForFinish(true);
    } else if (gameState && gameState.status !== "finished") {
      // Reset flag when match is no longer finished
      setHasRefreshedForFinish(false);
    }
  }, [gameState?.status, gameState?.winner_id, hasRefreshedForFinish]);

  function addToCombatLog(message, tone) {
    setCombatLog(prev => [{ message, tone, timestamp: Date.now() }, ...prev].slice(0, 50));
  }

  async function joinMatchmaking() {
    setError("");
    setMmInFlight(true);
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
        if (state) {
          loadUsername(state.player1_id);
          loadUsername(state.player2_id);
        }
      }
    } catch (e) {
      setError(e.message + (e.status ? " (HTTP " + e.status + ")" : ""));
      setMmStatus("error");
    } finally {
      setMmInFlight(false);
    }
  }

  async function leaveMatchmaking() {
    setError("");
    setMmInFlight(true);
    try {
      await apiFetch("/matchmaking/leave", { method: "POST", token });
      setMmStatus(null);
    } catch (e) {
      setError(e.message + (e.status ? " (HTTP " + e.status + ")" : ""));
    } finally {
      setMmInFlight(false);
    }
  }

  async function forfeitMatch() {
    if (!match) return;
    setError("");
    try {
      await apiFetch("/matches/" + match.id + "/forfeit", { method: "POST", token });
      await refreshMatchState(match.id);
      setMmStatus(null);
    } catch (e) {
      setError(e.message + (e.status ? " (HTTP " + e.status + ")" : ""));
    }
  }

  async function loadHistory() {
    try {
      const data = await apiFetch("/matches/history?limit=25", { token });
      setHistory(data || []);
    } catch (e) {
      setError(e.message + (e.status ? " (HTTP " + e.status + ")" : ""));
    }
  }

  async function doAction(action) {
    if (!match || !gameState || actionInFlight) return;
    
    setError("");
    setActionInFlight(true);
    
    try {
      const data = await apiFetch("/matches/" + match.id + "/action", {
        method: "POST",
        token,
        body: { action },
      });

      // Update game state immediately from response
      if (data.game_state) {
        setGameState(data.game_state);
      }

      // Flash health bar on damage/heal
      if (data.result) {
        const resultWithAction = { ...data.result, action: data.action || data.result.action };
        const isDamage = "damage" in resultWithAction && resultWithAction.damage != null;
        const isHeal = "healed" in resultWithAction && resultWithAction.healed != null;
        if (isDamage) {
          const isP1 = resultWithAction.attacker_id === gameState.player1_id;
          setHealthFlash(isP1 ? { p1: "#f44336", p2: null } : { p1: null, p2: "#f44336" });
          setTimeout(() => setHealthFlash({ p1: null, p2: null }), 300);
        } else if (isHeal) {
          const isP1 = resultWithAction.actor_id === gameState.player1_id;
          setHealthFlash(isP1 ? { p1: "#4caf50", p2: null } : { p1: null, p2: "#4caf50" });
          setTimeout(() => setHealthFlash({ p1: null, p2: null }), 300);
        }
      }

      // Always refresh match state after action to ensure sync (this will update combat log from server)
      await refreshMatchState(match.id);
      
    } catch (e) {
      setError(e.message + (e.status ? " (HTTP " + e.status + ")" : ""));
    } finally {
      setActionInFlight(false);
    }
  }

  // Helper to get max HP from server state (authoritative source)
  // Falls back to computed value only if server doesn't provide it (legacy support)
  const getMaxHp = (playerId, userInfo, gameState) => {
    // Use server-provided max_hp if available (preferred)
    if (gameState) {
      if (playerId === gameState.player1_id && gameState.player1_max_hp) {
        return gameState.player1_max_hp;
      }
      if (playerId === gameState.player2_id && gameState.player2_max_hp) {
        return gameState.player2_max_hp;
      }
    }
    // Fallback to computed value (should not happen with new backend)
    if (!userInfo || !userInfo.class_name) return 100;
    const baseHp = { warrior: 130, mage: 75, druid: 105, rogue: 90 };
    const hpPerLevel = { warrior: 14, mage: 7, druid: 11, rogue: 9 };
    return baseHp[userInfo.class_name] + (hpPerLevel[userInfo.class_name] * (userInfo.level - 1));
  };

  const myId = me?.id;
  const currentTurn = gameState?.current_turn;
  const status = gameState?.status;
  const winnerId = gameState?.winner_id;
  const canAct = Boolean(match && gameState && status === "active" && currentTurn === myId && !actionInFlight);
  const isPlayer1 = gameState && myId === gameState.player1_id;
  const p1Id = gameState?.player1_id;
  const p2Id = gameState?.player2_id;

  // Single rule: You (current user) = RIGHT, Opponent = LEFT. Same for sprites and cards.
  const leftPlayer = useMemo(() => {
    if (!gameState || !myId) return null;
    const opponentId = isPlayer1 ? p2Id : p1Id;
    const info = userInfoMap[opponentId];
    return {
      playerId: opponentId,
      username: getUsername(opponentId, usernameMap),
      health: isPlayer1 ? gameState.player2_health : gameState.player1_health,
      maxHealth: getMaxHp(opponentId, info, gameState),
      class_name: info?.class_name,
      level: info?.level,
      xp: info?.xp,
      isActive: status === "active" && currentTurn === opponentId,
      isMe: false,
      flashColor: isPlayer1 ? healthFlash.p2 : healthFlash.p1,
      activeEffects: isPlayer1 ? (gameState.player2_effects || []) : (gameState.player1_effects || []),
      pose: (playerPoses[opponentId] ?? "idle"),
    };
  }, [gameState, myId, isPlayer1, p1Id, p2Id, userInfoMap, usernameMap, status, currentTurn, healthFlash, playerPoses]);

  const rightPlayer = useMemo(() => {
    if (!gameState || !myId) return null;
    const info = userInfoMap[myId];
    return {
      playerId: myId,
      username: getUsername(myId, usernameMap) || me?.username,
      health: isPlayer1 ? gameState.player1_health : gameState.player2_health,
      maxHealth: getMaxHp(myId, info, gameState),
      class_name: info?.class_name,
      level: info?.level,
      xp: info?.xp,
      isActive: status === "active" && currentTurn === myId,
      isMe: true,
      flashColor: isPlayer1 ? healthFlash.p1 : healthFlash.p2,
      activeEffects: isPlayer1 ? (gameState.player1_effects || []) : (gameState.player2_effects || []),
      pose: (playerPoses[myId] ?? "idle"),
    };
  }, [gameState, myId, isPlayer1, userInfoMap, usernameMap, me, status, currentTurn, healthFlash, playerPoses]);

  const myInfo = userInfoMap[myId];
  const myCooldowns = isPlayer1 ? (gameState?.player1_cooldowns || {}) : (gameState?.player2_cooldowns || {});
  const myActionTooltips = isPlayer1 ? (gameState?.player1_action_tooltips || {}) : (gameState?.player2_action_tooltips || {});

  const winnerUsername = useMemo(() => {
    if (!winnerId) return null;
    return getUsername(winnerId, usernameMap);
  }, [winnerId, usernameMap]);

  return (
    <div style={{ 
      fontFamily: "system-ui, -apple-system, sans-serif", 
      width: "100%",
      minHeight: "100vh",
      boxSizing: "border-box",
      backgroundColor: "#0d0d0d",
      color: "white",
      display: "flex",
      flexDirection: "column",
      alignItems: "stretch",
    }}>
      <div className="page-container" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, paddingTop: 20, paddingBottom: 20 }}>
        {!isAuthed ? (
          <div
            style={{
              position: "fixed",
              inset: 0,
              backgroundImage: `url(${landingPageBg})`,
              backgroundSize: "cover",
              backgroundPosition: "center",
              backgroundRepeat: "no-repeat",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "flex-start",
              paddingTop: "clamp(24px, 6vw, 48px)",
              paddingLeft: 16,
              paddingRight: 16,
              paddingBottom: 24,
              overflow: "auto",
            }}
          >
            <AppLogo
              style={{
                marginBottom: 40,
                flexShrink: 0,
                width: "clamp(320px, 85vw, 480px)",
                height: "auto",
              }}
            />
            <div
              style={{
                backgroundColor: "rgba(0,0,0,0.65)",
                borderRadius: 12,
                padding: 28,
                maxWidth: 420,
                width: "100%",
                boxSizing: "border-box",
              }}
            >
              <AuthPanel
                mode={mode}
                setMode={setMode}
                username={username}
                setUsername={(val) => {
                  setUsername(val);
                  setError("");
                  setUsernameError("");
                }}
                password={password}
                setPassword={(val) => {
                  setPassword(val);
                  setError("");
                }}
                className={className}
                setClassName={setClassName}
                onLogin={handleLogin}
                onRegister={handleRegister}
                error={error}
                usernameError={usernameError}
              />
            </div>
          </div>
        ) : (
          <>
        <header style={{ textAlign: "center", marginBottom: 20, flexShrink: 0, width: "100%", boxSizing: "border-box" }}>
          <AppLogo
            style={{
              margin: "0 auto",
              width: "clamp(280px, 85vw, 500px)",
              height: "auto",
              maxWidth: "100%",
            }}
          />
        </header>
        <div style={{ display: "flex", flexDirection: "column", gap: 20, flex: 1, minHeight: 0 }}>
          <HeaderBar
            username={me?.username || "Unknown"}
            className={me?.class_name}
            level={me?.level}
            showHistory={showHistory}
            onToggleHistory={() => { 
              setShowHistory(!showHistory); 
              if (!showHistory) loadHistory(); 
            }}
            showLeaderboard={showLeaderboard}
            onToggleLeaderboard={() => setShowLeaderboard(!showLeaderboard)}
            onLogout={handleLogout}
          />

          {showHistory && (
            <MatchHistory history={history} onRefresh={loadHistory} />
          )}

          {showLeaderboard && (
            <Leaderboard token={token} onClose={() => setShowLeaderboard(false)} />
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
                  onClick={mmStatus === "waiting" ? leaveMatchmaking : joinMatchmaking}
                  disabled={mmInFlight}
                  style={{
                    backgroundColor: mmInFlight ? "#4a5568" : mmStatus === "waiting" ? "#dc3545" : "#28a745",
                    color: "white",
                    border: "none",
                    padding: "12px 24px",
                    borderRadius: "6px",
                    fontSize: "16px",
                    fontWeight: "bold",
                    cursor: mmInFlight ? "not-allowed" : "pointer",
                  }}
                >
                  {mmInFlight ? "..." : mmStatus === "waiting" ? "Leave Matchmaking" : "Join Matchmaking"}
                </button>
                {mmStatus === "waiting" && !mmInFlight && (
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
            <GameLayout
              gameState={gameState}
              status={status}
              winnerUsername={winnerUsername}
              winnerId={winnerId}
              leftPlayer={leftPlayer}
              rightPlayer={rightPlayer}
              canAct={canAct}
              actionInFlight={actionInFlight}
              onAction={doAction}
              myInfo={myInfo}
              myCooldowns={myCooldowns}
              actionTooltips={myActionTooltips}
              combatLog={combatLog}
              matchBackgroundUrl={matchBackgroundUrl}
              onReturnToMatchmaking={() => {
                setMatch(null);
                setGameState(null);
                setCombatLog([]);
                setMmStatus(null);
                setHasRefreshedForFinish(false);
              }}
              onForfeit={forfeitMatch}
              error={error}
            />
          )}
        </div>
        </>
      )}
      </div>
    </div>
  );
}
