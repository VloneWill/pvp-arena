export default function AuthPanel({ mode, setMode, username, setUsername, password, setPassword, onLogin, onRegister, error }) {
  return (
    <div style={{ 
      display: "grid", 
      gap: 12, 
      maxWidth: 420, 
      margin: "0 auto",
      padding: 24,
      backgroundColor: "#1e1e1e",
      borderRadius: 8,
      border: "1px solid #333"
    }}>
      <div style={{ display: "flex", gap: 8 }}>
        <button 
          onClick={() => setMode("login")} 
          disabled={mode === "login"}
          style={{
            flex: 1,
            padding: "10px 16px",
            backgroundColor: mode === "login" ? "#4a5568" : "#2d3748",
            color: "white",
            border: "1px solid #4a5568",
            borderRadius: 6,
            cursor: mode === "login" ? "default" : "pointer",
            fontWeight: "bold"
          }}
        >
          Login
        </button>
        <button 
          onClick={() => setMode("register")} 
          disabled={mode === "register"}
          style={{
            flex: 1,
            padding: "10px 16px",
            backgroundColor: mode === "register" ? "#4a5568" : "#2d3748",
            color: "white",
            border: "1px solid #4a5568",
            borderRadius: 6,
            cursor: mode === "register" ? "default" : "pointer",
            fontWeight: "bold"
          }}
        >
          Register
        </button>
      </div>

      <label style={{ color: "white", display: "flex", flexDirection: "column", gap: 4 }}>
        Username
        <input 
          value={username} 
          onChange={(e) => setUsername(e.target.value)} 
          style={{ 
            width: "100%",
            padding: "10px",
            backgroundColor: "#2d3748",
            color: "white",
            border: "1px solid #4a5568",
            borderRadius: 6
          }} 
        />
      </label>

      <label style={{ color: "white", display: "flex", flexDirection: "column", gap: 4 }}>
        Password
        <input 
          type="password" 
          value={password} 
          onChange={(e) => setPassword(e.target.value)} 
          style={{ 
            width: "100%",
            padding: "10px",
            backgroundColor: "#2d3748",
            color: "white",
            border: "1px solid #4a5568",
            borderRadius: 6
          }} 
        />
      </label>

      {mode === "login" ? (
        <button 
          onClick={onLogin}
          style={{
            padding: "12px 24px",
            backgroundColor: "#28a745",
            color: "white",
            border: "none",
            borderRadius: 6,
            fontSize: "16px",
            fontWeight: "bold",
            cursor: "pointer"
          }}
        >
          Login
        </button>
      ) : (
        <button 
          onClick={onRegister}
          style={{
            padding: "12px 24px",
            backgroundColor: "#28a745",
            color: "white",
            border: "none",
            borderRadius: 6,
            fontSize: "16px",
            fontWeight: "bold",
            cursor: "pointer"
          }}
        >
          Register + Login
        </button>
      )}

      {error ? (
        <div style={{ 
          color: "#ff6b6b", 
          padding: 12, 
          backgroundColor: "#2d1b1b",
          borderRadius: 6,
          border: "1px solid #5a2a2a"
        }}>
          {error}
        </div>
      ) : null}
    </div>
  );
}
