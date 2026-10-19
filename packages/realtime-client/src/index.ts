import type { MonitoringRealtimeMessage, RealtimeMessage, StoreRealtimeMessage } from "@synccart/shared-types";

export type ConnectionStatus = "connecting" | "connected" | "disconnected";

function websocketBase(apiBaseUrl: string): string {
  const url = new URL(apiBaseUrl);
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${url.host}`;
}

export type RealtimeClientOptions = {
  apiBaseUrl: string;
  sessionId: string;
  token: string;
  onMessage: (message: RealtimeMessage) => void;
  onStatus?: (status: ConnectionStatus) => void;
};

export class CustomerRealtimeClient {
  private socket: WebSocket | null = null;
  private stopped = false;
  private retry = 0;
  constructor(private options: RealtimeClientOptions) {}
  start() { this.stopped = false; this.connect(); }
  stop() { this.stopped = true; this.socket?.close(); this.socket = null; }
  private connect() {
    if (this.stopped) return;
    this.options.onStatus?.("connecting");
    const socketUrl = `${websocketBase(this.options.apiBaseUrl)}/ws/customer/${encodeURIComponent(this.options.sessionId)}?token=${encodeURIComponent(this.options.token)}`;
    const ws = new WebSocket(socketUrl);
    this.socket = ws;
    ws.onopen = () => { this.retry = 0; this.options.onStatus?.("connected"); };
    ws.onmessage = (event) => { try { this.options.onMessage(JSON.parse(event.data) as RealtimeMessage); } catch { /* server schema authoritative */ } };
    ws.onerror = () => ws.close();
    ws.onclose = () => {
      this.options.onStatus?.("disconnected");
      if (this.stopped) return;
      const delay = Math.min(8000, 500 * 2 ** this.retry++);
      window.setTimeout(() => this.connect(), delay);
    };
  }
}

export type StoreRealtimeClientOptions = {
  apiBaseUrl: string;
  storeKey: string;
  onMessage: (message: StoreRealtimeMessage) => void;
  onStatus?: (status: ConnectionStatus) => void;
};

export class StoreRealtimeClient {
  private socket: WebSocket | null = null;
  private stopped = false;
  private retry = 0;
  constructor(private options: StoreRealtimeClientOptions) {}
  start() { this.stopped = false; this.connect(); }
  stop() { this.stopped = true; this.socket?.close(); this.socket = null; }
  private connect() {
    if (this.stopped) return;
    this.options.onStatus?.("connecting");
    const socketUrl = `${websocketBase(this.options.apiBaseUrl)}/ws/store?key=${encodeURIComponent(this.options.storeKey)}`;
    const ws = new WebSocket(socketUrl);
    this.socket = ws;
    ws.onopen = () => { this.retry = 0; this.options.onStatus?.("connected"); };
    ws.onmessage = (event) => { try { this.options.onMessage(JSON.parse(event.data) as StoreRealtimeMessage); } catch { /* server schema authoritative */ } };
    ws.onerror = () => ws.close();
    ws.onclose = () => {
      this.options.onStatus?.("disconnected");
      if (this.stopped) return;
      const delay = Math.min(8000, 500 * 2 ** this.retry++);
      window.setTimeout(() => this.connect(), delay);
    };
  }
}


export type MonitoringRealtimeClientOptions = {
  apiBaseUrl: string;
  monitoringKey: string;
  onMessage: (message: MonitoringRealtimeMessage) => void;
  onStatus?: (status: ConnectionStatus) => void;
};

export class MonitoringRealtimeClient {
  private socket: WebSocket | null = null;
  private stopped = false;
  private retry = 0;
  constructor(private options: MonitoringRealtimeClientOptions) {}
  start() { this.stopped = false; this.connect(); }
  stop() { this.stopped = true; this.socket?.close(); this.socket = null; }
  private connect() {
    if (this.stopped) return;
    this.options.onStatus?.("connecting");
    const socketUrl = `${websocketBase(this.options.apiBaseUrl)}/ws/admin?key=${encodeURIComponent(this.options.monitoringKey)}`;
    const ws = new WebSocket(socketUrl);
    this.socket = ws;
    ws.onopen = () => { this.retry = 0; this.options.onStatus?.("connected"); };
    ws.onmessage = (event) => { try { this.options.onMessage(JSON.parse(event.data) as MonitoringRealtimeMessage); } catch { /* server schema authoritative */ } };
    ws.onerror = () => ws.close();
    ws.onclose = () => {
      this.options.onStatus?.("disconnected");
      if (this.stopped) return;
      const delay = Math.min(8000, 500 * 2 ** this.retry++);
      window.setTimeout(() => this.connect(), delay);
    };
  }
}
