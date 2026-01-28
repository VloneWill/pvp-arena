const API_BASE = "http://127.0.0.1:8000";

export function authHeader(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiFetch(path, { method = "GET", token, body } = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...authHeader(token),
  };

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    
    if (data && data.detail) {
      // Handle FastAPI validation errors (422) - detail is an array
      if (Array.isArray(data.detail)) {
        const messages = data.detail.map(err => {
          const field = err.loc && err.loc.length > 1 ? err.loc[err.loc.length - 1] : 'field';
          return `${field}: ${err.msg}`;
        });
        detail = messages.join('; ');
      } else if (typeof data.detail === 'string') {
        detail = data.detail;
      } else {
        detail = JSON.stringify(data.detail);
      }
    }
    
    const err = new Error(detail);
    err.status = res.status;
    err.data = data;
    throw err;
  }

  return data;
}
