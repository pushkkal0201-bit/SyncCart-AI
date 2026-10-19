export type Envelope<T> = {
  data: T | null;
  meta: Record<string, unknown>;
  error: { code: string; message: string; details?: Record<string, unknown> } | null;
};

export type SessionStatus =
  | "ACTIVE"
  | "CLEAR"
  | "VERIFY"
  | "NUDGE"
  | "REVIEW"
  | "RESOLVED"
  | "CHECKOUT_BLOCKED"
  | "CHECKOUT_APPROVED"
  | "COMPLETED";

export type SessionCreated = {
  id: string;
  public_id: string;
  status: SessionStatus;
  started_at: string;
  last_activity_at: string;
  checkout_requested_at: string | null;
  completed_at: string | null;
  customer_token_expires_at: string | null;
  customer_token: string;
};

export type CartLine = {
  product_id: string;
  sku: string;
  barcode: string | null;
  name: string;
  quantity: number;
  unit_price_minor: number;
  line_total_minor: number;
  currency: string;
  confidence: number | null;
  updated_at: string;
};

export type Cart = {
  source: "DIGITAL" | "PHYSICAL" | string;
  items: CartLine[];
  distinct_items: number;
  total_quantity: number;
  totals_by_currency: Record<string, number>;
};

export type CartComparison = {
  session_id: string;
  public_id: string;
  session_status: SessionStatus;
  digital_cart: Cart;
  physical_cart: Cart;
};

export type Discrepancy = {
  id: string;
  session_id: string;
  sku: string;
  status: string;
  physical_quantity: number;
  digital_quantity: number;
  difference: number;
  risk_score: number;
  vision_confidence: number | null;
  reason_codes: string[];
  correlation_id: string;
  opened_at: string;
  updated_at: string;
  grace_expires_at: string;
  resolved_at: string | null;
};

export type Nudge = {
  id: string;
  discrepancy_id: string;
  session_id: string;
  sku: string;
  message: string;
  status: string;
  sent_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  action: string | null;
};

export type Reconciliation = {
  session_id: string;
  public_id: string;
  session_status: SessionStatus;
  cart_consistency_score: number;
  active_discrepancies: Discrepancy[];
  latest_nudges: Nudge[];
  reasons: string[];
  cart: CartComparison;
};

export type CartMutation = {
  operation: string;
  accepted: boolean;
  reason: string;
  event_id: string | null;
  sku: string;
  quantity_delta: number;
  digital_cart: Cart;
  idempotent_replay: boolean;
};

export type CustomerAction = "SCAN_NOW" | "I_RETURNED_IT" | "GET_HELP";

export type NudgeActionResult = {
  nudge_id: string;
  action: CustomerAction;
  message: string;
  reconciliation: Reconciliation;
};

export type CheckoutResult = {
  approved: boolean;
  payment_mode: "SIMULATED";
  session_status: SessionStatus;
  message: string;
  reconciliation: Reconciliation;
};

export type DomainEvent = {
  id: string;
  session_id: string | null;
  event_type: string;
  event_version: number;
  source: string;
  sku: string | null;
  quantity: number | null;
  confidence: number | null;
  correlation_id: string;
  causation_id: string | null;
  camera_id: string | null;
  zone_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

export type StoreMetrics = {
  active_sessions: number;
  synced_sessions: number;
  verifying_sessions: number;
  review_required: number;
  open_discrepancies: number;
  active_nudges: number;
  resolved_sessions: number;
};

export type StoreSessionSummary = {
  session_id: string;
  public_id: string;
  status: SessionStatus;
  started_at: string;
  last_activity_at: string;
  duration_seconds: number;
  physical_quantity: number;
  digital_quantity: number;
  discrepancy_count: number;
  consistency_score: number;
  primary_issue: string | null;
};

export type ReviewQueueItem = {
  discrepancy_id: string;
  session_id: string;
  public_id: string;
  sku: string;
  product_name: string;
  status: string;
  difference: number;
  physical_quantity: number;
  digital_quantity: number;
  risk_score: number;
  vision_confidence: number | null;
  reason_codes: string[];
  opened_at: string;
  updated_at: string;
  waiting_seconds: number;
  nudge_status: string | null;
  nudge_sent_at: string | null;
};

export type StoreOverview = {
  generated_at: string;
  metrics: StoreMetrics;
  status_counts: Record<string, number>;
  recent_sessions: StoreSessionSummary[];
  review_queue: ReviewQueueItem[];
};

export type StoreSessionDetail = {
  reconciliation: Reconciliation;
  events: DomainEvent[];
};

export type ReviewResolutionAction =
  | "FALSE_DETECTION"
  | "ITEM_RETURNED_CONFIRMED"
  | "ESCALATE_MANUAL_CHECK";

export type ReviewResolutionResult = {
  discrepancy_id: string;
  action: ReviewResolutionAction;
  resolved: boolean;
  message: string;
  reconciliation: Reconciliation;
};

export type RealtimeMessage =
  | { type: "session.snapshot"; version: 1; timestamp: string; data: Reconciliation }
  | { type: "heartbeat"; version: 1; timestamp: string; data: Record<string, string> }
  | { type: "error"; version: 1; timestamp: string; data: { code: string; message: string } };

export type StoreRealtimeMessage =
  | { type: "store.snapshot"; version: 1; timestamp: string; data: StoreOverview }
  | { type: "heartbeat"; version: 1; timestamp: string; data: { channel: string } }
  | { type: "error"; version: 1; timestamp: string; data: { code: string; message: string } };

export type ServiceState = "HEALTHY" | "DEGRADED" | "OFFLINE" | "NOT_CONFIGURED";

export type ServiceHealth = {
  name: string;
  status: ServiceState;
  detail: string;
  last_checked_at: string;
};

export type CameraTelemetry = {
  camera_id: string;
  status: ServiceState;
  source: string;
  fps: number | null;
  frame_latency_ms: number | null;
  resolution: string | null;
  stream_mode: string | null;
  last_frame_at: string | null;
  consecutive_failures: number;
  note: string;
  updated_at: string;
};

export type VisionTelemetry = {
  status: ServiceState;
  model_name: string | null;
  model_version: string | null;
  device: string | null;
  fps: number | null;
  avg_inference_ms: number | null;
  avg_confidence: number | null;
  low_confidence_rate: number | null;
  detections_by_class: Record<string, number>;
  last_inference_at: string | null;
  note: string;
  updated_at: string;
};

export type MonitoringMetrics = {
  total_sessions: number;
  active_sessions: number;
  total_events: number;
  vision_events: number;
  customer_scan_events: number;
  match_confirmed_events: number;
  open_discrepancies: number;
  event_matches: number;
  nudges_sent: number;
  reviews_required: number;
  checkouts_approved: number;
};

export type MonitoringNotice = {
  level: string;
  title: string;
  detail: string;
};

export type MonitoringOverview = {
  generated_at: string;
  services: ServiceHealth[];
  metrics: MonitoringMetrics;
  camera: CameraTelemetry;
  vision: VisionTelemetry;
  recent_events: DomainEvent[];
  notices: MonitoringNotice[];
};

export type MonitoringSessionInspector = {
  reconciliation: Reconciliation;
  events: DomainEvent[];
};

export type MonitoringRealtimeMessage =
  | { type: "monitoring.snapshot"; version: 1; timestamp: string; data: MonitoringOverview }
  | { type: "heartbeat"; version: 1; timestamp: string; data: { channel: string } }
  | { type: "error"; version: 1; timestamp: string; data: { code: string; message: string } };
