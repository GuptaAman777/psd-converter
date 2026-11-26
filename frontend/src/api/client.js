const BASE = "";

export function previewUrl(filePath, maxSize = 420, cacheKey = "") {
  if (!filePath) return "";
  const v = cacheKey ? `&v=${encodeURIComponent(String(cacheKey))}` : "";
  return `${BASE}/api/preview?path=${encodeURIComponent(filePath)}&max_size=${maxSize}${v}`;
}

export async function apiGet(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function apiPost(path, body = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      msg = j.detail || msg;
    } catch {
      msg = await res.text();
    }
    throw new Error(msg);
  }
  return res.json();
}

export async function apiDelete(path) {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      msg = j.detail || msg;
    } catch {
      msg = await res.text();
    }
    throw new Error(msg);
  }
  return res.json();
}

export async function nativeBrowseFiles(allowedExts) {
  if (window.pywebview?.api?.browse_files) {
    return await window.pywebview.api.browse_files(allowedExts);
  }
  // Browser dev fallback returns [] gracefully or uses input file dialog if needed
  return [];
}

export async function nativeBrowseFolder() {
  if (window.pywebview?.api?.browse_folder) {
    return await window.pywebview.api.browse_folder();
  }
  return "";
}

export async function openFolderInOS(folderPath) {
  if (window.pywebview?.api?.open_folder) {
    return await window.pywebview.api.open_folder(folderPath);
  }
  return apiPost("/api/open-folder", { path: folderPath });
}

export async function openExternalUrl(url) {
  return apiPost("/api/open-url", { path: url });
}

export function subscribeEvents(onMessage) {
  let ws = null;
  let closed = false;
  let timer = null;

  function connect() {
    if (closed) return;
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    ws = new WebSocket(`${proto}//${host}/ws/events`);
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        onMessage(msg);
      } catch {
        // ignore parse noise
      }
    };
    ws.onclose = () => {
      if (!closed) {
        timer = setTimeout(connect, 1200);
      }
    };
    ws.onerror = () => {
      try {
        ws.close();
      } catch {
        // ignore
      }
    };
  }

  connect();
  return () => {
    closed = true;
    if (timer) clearTimeout(timer);
    if (ws) {
      try {
        ws.close();
      } catch {
        // ignore
      }
    }
  };
}
