/**
 * Thin fetch wrapper for the backend API. All paths are relative so this
 * works unmodified in dev (Vite proxies /api to Flask) and in production
 * (Flask serves the built frontend from the same origin as the API).
 */

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let body = null;
  try {
    body = await res.json();
  } catch {
    // no JSON body (e.g. 501 plain-text "build the frontend" message)
  }

  if (!res.ok) {
    const message = body?.error || `Request failed with status ${res.status}`;
    throw new Error(message);
  }
  return body;
}

const BASE = import.meta.env.VITE_API_BASE ?? "";

export async function runCode(code, language = "python", stdin = "") {
  const res = await fetch(`${BASE}/api/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, language, stdin }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function reviewCode(code, language = "python") {
  const apiKey = localStorage.getItem("ai_api_key") || "";
  const res = await fetch(`${BASE}/api/analyze`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "X-AI-API-Key": apiKey
    },
    body: JSON.stringify({ code, language }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function fetchHistory(limit = 50) {
  return request(`/api/history?limit=${limit}`);
}

export function fetchHistoryDetail(id) {
  return request(`/api/history/${id}`);
}

export function deleteHistoryItem(id) {
  return request(`/api/history/${id}`, { method: "DELETE" });
}

export async function chatCode(code, language = "python", messages = []) {
  const apiKey = localStorage.getItem("ai_api_key") || "";
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "X-AI-API-Key": apiKey
    },
    body: JSON.stringify({ code, language, messages }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function autocompleteCode(prefix, suffix, language = "python") {
  const apiKey = localStorage.getItem("ai_api_key") || "";
  const res = await fetch(`${BASE}/api/autocomplete`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "X-AI-API-Key": apiKey
    },
    body: JSON.stringify({ prefix, suffix, language }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
