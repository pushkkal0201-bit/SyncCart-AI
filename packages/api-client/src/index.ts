import type {
  CartComparison,
  CartMutation,
  CheckoutResult,
  CustomerAction,
  Envelope,
  NudgeActionResult,
  Reconciliation,
  ReviewQueueItem,
  ReviewResolutionAction,
  ReviewResolutionResult,
  SessionCreated,
  StoreOverview,
  StoreSessionDetail,
  StoreSessionSummary,
  MonitoringOverview,
  MonitoringSessionInspector,
  DomainEvent,
  CameraTelemetry,
  VisionTelemetry,
  ServiceState,
} from "@synccart/shared-types";

export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number) {
    super(message);
  }
}

type BaseOptions = { baseUrl: string };

async function decode<T>(response: Response): Promise<T> {
  const body = (await response.json()) as Envelope<T>;
  if (!response.ok || body.error) {
    throw new ApiError(
      body.error?.code ?? "HTTP_ERROR",
      body.error?.message ?? `Request failed with status ${response.status}`,
      response.status,
    );
  }
  if (body.data === null) throw new ApiError("EMPTY_RESPONSE", "Server returned no data", response.status);
  return body.data;
}

export type ApiClientOptions = BaseOptions & { sessionToken?: string | null };

export class SyncCartApiClient {
  private baseUrl: string;
  private sessionToken: string | null;

  constructor(options: ApiClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.sessionToken = options.sessionToken ?? null;
  }

  setSessionToken(token: string | null) {
    this.sessionToken = token;
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Content-Type", "application/json");
    if (this.sessionToken) headers.set("X-Session-Token", this.sessionToken);
    return decode<T>(await fetch(`${this.baseUrl}${path}`, { ...init, headers }));
  }

  createSession() { return this.request<SessionCreated>("/api/v1/sessions", { method: "POST" }); }
  getCart(sessionId: string) { return this.request<CartComparison>(`/api/v1/sessions/${sessionId}/cart`); }
  getReconciliation(sessionId: string) { return this.request<Reconciliation>(`/api/v1/sessions/${sessionId}/reconciliation`); }

  scan(sessionId: string, barcode: string, quantity = 1) {
    return this.request<CartMutation>(`/api/v1/sessions/${sessionId}/scan`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({ barcode, quantity }),
    });
  }

  removeItem(sessionId: string, sku: string, quantity = 1) {
    return this.request<CartMutation>(`/api/v1/sessions/${sessionId}/cart/items/${encodeURIComponent(sku)}/remove`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({ quantity }),
    });
  }

  respondToNudge(sessionId: string, nudgeId: string, action: CustomerAction) {
    return this.request<NudgeActionResult>(`/api/v1/sessions/${sessionId}/nudges/${nudgeId}/action`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({ action }),
    });
  }

  checkout(sessionId: string) {
    return this.request<CheckoutResult>(`/api/v1/sessions/${sessionId}/checkout`, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({ payment_mode: "SIMULATED" }),
    });
  }
}

export type StoreApiClientOptions = BaseOptions & { storeKey: string };

export class StoreApiClient {
  private baseUrl: string;
  private storeKey: string;

  constructor(options: StoreApiClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.storeKey = options.storeKey;
  }

  setStoreKey(key: string) { this.storeKey = key; }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Content-Type", "application/json");
    headers.set("X-Store-Key", this.storeKey);
    return decode<T>(await fetch(`${this.baseUrl}${path}`, { ...init, headers }));
  }

  getOverview() { return this.request<StoreOverview>("/api/v1/store/overview"); }
  listSessions(limit = 100) { return this.request<StoreSessionSummary[]>(`/api/v1/store/sessions?limit=${limit}`); }
  getSession(sessionId: string) { return this.request<StoreSessionDetail>(`/api/v1/store/sessions/${sessionId}`); }
  listReviews() { return this.request<ReviewQueueItem[]>("/api/v1/store/reviews"); }

  resolveReview(discrepancyId: string, action: ReviewResolutionAction, note = "") {
    return this.request<ReviewResolutionResult>(`/api/v1/store/reviews/${discrepancyId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ action, note }),
    });
  }
}

export function inferApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (configured) return configured.replace(/\/$/, "");
  return `${window.location.protocol}//${window.location.hostname}:8000`;
}


export type MonitoringApiClientOptions = BaseOptions & { monitoringKey: string };

export class MonitoringApiClient {
  private baseUrl: string;
  private monitoringKey: string;

  constructor(options: MonitoringApiClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.monitoringKey = options.monitoringKey;
  }

  setMonitoringKey(key: string) { this.monitoringKey = key; }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Content-Type", "application/json");
    headers.set("X-Monitor-Key", this.monitoringKey);
    return decode<T>(await fetch(`${this.baseUrl}${path}`, { ...init, headers }));
  }

  getOverview() { return this.request<MonitoringOverview>("/api/v1/admin/overview"); }
  listEvents(limit = 100, eventType?: string) {
    const query = new URLSearchParams({ limit: String(limit) });
    if (eventType) query.set("event_type", eventType);
    return this.request<DomainEvent[]>(`/api/v1/admin/events?${query.toString()}`);
  }
  inspectSession(sessionId: string) {
    return this.request<MonitoringSessionInspector>(`/api/v1/admin/sessions/${encodeURIComponent(sessionId)}/reconciliation`);
  }
  updateCameraTelemetry(payload: {
    camera_id: string; status: ServiceState; source?: string; fps?: number | null; frame_latency_ms?: number | null;
    resolution?: string | null; stream_mode?: string | null; last_frame_at?: string | null; consecutive_failures?: number; note?: string;
  }) {
    return this.request<CameraTelemetry>("/api/v1/admin/telemetry/camera", { method: "POST", body: JSON.stringify(payload) });
  }
  updateVisionTelemetry(payload: {
    status: ServiceState; model_name?: string | null; model_version?: string | null; device?: string | null; fps?: number | null;
    avg_inference_ms?: number | null; avg_confidence?: number | null; low_confidence_rate?: number | null;
    detections_by_class?: Record<string, number>; last_inference_at?: string | null; note?: string;
  }) {
    return this.request<VisionTelemetry>("/api/v1/admin/telemetry/vision", { method: "POST", body: JSON.stringify(payload) });
  }
  resetTelemetry() { return this.request<Record<string, CameraTelemetry | VisionTelemetry>>("/api/v1/admin/telemetry/reset", { method: "POST" }); }
}
