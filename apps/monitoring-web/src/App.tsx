import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError, MonitoringApiClient, inferApiBaseUrl } from "@synccart/api-client";
import { Card, Spinner, StatusPill } from "@synccart/design-system";
import { MonitoringRealtimeClient, type ConnectionStatus } from "@synccart/realtime-client";
import type {
  DomainEvent,
  MonitoringOverview,
  MonitoringSessionInspector,
  ServiceState,
} from "@synccart/shared-types";

type View = "overview" | "camera" | "vision" | "events" | "reconciliation" | "runtime";
const STORAGE_KEY = "synccart_monitoring_key";

function label(value: string) {
  return value.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (x) => x.toUpperCase());
}

function time(value: string | null | undefined) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function tone(status: ServiceState | string): "good" | "warn" | "danger" | "info" {
  if (status === "HEALTHY") return "good";
  if (status === "DEGRADED") return "warn";
  if (status === "OFFLINE") return "danger";
  return "info";
}

function Metric({ value, labelText, detail, accent = "cyan" }: { value: string | number; labelText: string; detail?: string; accent?: string }) {
  return <Card className={`monitor-metric accent-${accent}`}><span>{labelText}</span><strong>{value}</strong>{detail ? <small>{detail}</small> : null}</Card>;
}

function Login({ onLogin, busy, error }: { onLogin: (key: string) => Promise<void>; busy: boolean; error: string | null }) {
  const [key, setKey] = useState("");
  return <main className="monitor-login"><div className="login-orb a"/><div className="login-orb b"/><Card className="monitor-login-card"><div className="ops-mark">S</div><p className="eyebrow">Team Synergy • Protected engineering surface</p><h1>AI Operations Center</h1><p>Observe platform health, camera telemetry, Vision runtime, domain events, and reconciliation evidence without mixing engineering controls into store workflows.</p><label>Monitoring access key<input type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder="X-Monitor-Key" onKeyDown={(e) => { if (e.key === "Enter" && key) void onLogin(key); }} /></label>{error ? <div className="login-error">{error}</div> : null}<button disabled={!key || busy} onClick={() => void onLogin(key)}>{busy ? <Spinner /> : "Open Operations Center"}</button><small>Local deployment access key. The authentication boundary is isolated from store and customer access.</small></Card></main>;
}

function ServiceMatrix({ overview }: { overview: MonitoringOverview }) {
  return <div className="service-grid">{overview.services.map((item) => <Card key={item.name} className="service-card"><div className="service-head"><span className={`service-light ${item.status.toLowerCase()}`} /><b>{item.name}</b><StatusPill tone={tone(item.status)}>{label(item.status)}</StatusPill></div><p>{item.detail}</p><small>Checked {time(item.last_checked_at)}</small></Card>)}</div>;
}

function EventRow({ event, onInspect }: { event: DomainEvent; onInspect?: (id: string) => void }) {
  return <button className="event-row" onClick={() => event.session_id && onInspect?.(event.session_id)}><div className="event-time">{time(event.created_at)}</div><div className="event-type"><i className={event.source.toLowerCase()} />{event.event_type}</div><div className="event-meta"><span>{event.sku ?? "system"}</span><span>{event.session_id ? event.session_id.slice(0, 8) : "global"}</span><span>{event.confidence == null ? "—" : `${Math.round(event.confidence * 100)}%`}</span></div></button>;
}

function ReconciliationInspector({ data, onClose }: { data: MonitoringSessionInspector; onClose: () => void }) {
  const state = data.reconciliation;
  return <div className="inspector-backdrop" onMouseDown={onClose}><aside className="inspector" onMouseDown={(e) => e.stopPropagation()}><div className="inspector-head"><div><p className="eyebrow">Reconciliation trace</p><h2>{state.public_id}</h2></div><button onClick={onClose}>×</button></div><div className="inspector-status"><StatusPill tone={state.session_status === "REVIEW" || state.session_status === "CHECKOUT_BLOCKED" ? "danger" : state.session_status === "VERIFY" || state.session_status === "NUDGE" ? "warn" : "good"}>{label(state.session_status)}</StatusPill><strong>{Math.round(state.cart_consistency_score * 100)}%</strong><span>cart consistency</span></div><div className="cart-compare"><Card><p className="eyebrow">Physical cart</p><strong>{state.cart.physical_cart.total_quantity}</strong><span>items observed</span>{state.cart.physical_cart.items.map((item) => <div className="line" key={item.sku}><span>{item.name}</span><b>×{item.quantity}</b></div>)}</Card><Card><p className="eyebrow">Digital cart</p><strong>{state.cart.digital_cart.total_quantity}</strong><span>items scanned</span>{state.cart.digital_cart.items.map((item) => <div className="line" key={item.sku}><span>{item.name}</span><b>×{item.quantity}</b></div>)}</Card></div><div className="reason-panel"><p className="eyebrow">Decision reasons</p>{state.reasons.length ? state.reasons.map((reason) => <span key={reason}>{label(reason)}</span>) : <span>No active inconsistency reasons.</span>}</div><h3>Immutable event trace</h3><div className="event-stream compact">{data.events.map((event) => <EventRow key={event.id} event={event} />)}</div></aside></div>;
}

export function App() {
  const apiBaseUrl = useMemo(() => inferApiBaseUrl(), []);
  const visionBaseUrl = useMemo(() => import.meta.env.VITE_VISION_BASE_URL ?? `${window.location.protocol}//${window.location.hostname}:8100`, []);
  const [key, setKey] = useState(() => sessionStorage.getItem(STORAGE_KEY) ?? "");
  const [authenticated, setAuthenticated] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [overview, setOverview] = useState<MonitoringOverview | null>(null);
  const [view, setView] = useState<View>("overview");
  const [connection, setConnection] = useState<ConnectionStatus>("disconnected");
  const [eventFilter, setEventFilter] = useState("ALL");
  const [inspector, setInspector] = useState<MonitoringSessionInspector | null>(null);
  const [sessionInput, setSessionInput] = useState("");
  const api = useRef<MonitoringApiClient | null>(null);

  async function authenticate(candidate: string) {
    setBusy(true); setLoginError(null);
    try {
      const client = new MonitoringApiClient({ baseUrl: apiBaseUrl, monitoringKey: candidate });
      const data = await client.getOverview();
      api.current = client; setOverview(data); setAuthenticated(true); setKey(candidate);
      sessionStorage.setItem(STORAGE_KEY, candidate);
    } catch (exc) {
      setLoginError(exc instanceof ApiError ? exc.message : "Could not connect to AI Operations Center");
    } finally { setBusy(false); }
  }

  useEffect(() => { if (key && !authenticated) void authenticate(key); }, []);

  useEffect(() => {
    if (!authenticated) return;
    let active = true;
    const realtime = new MonitoringRealtimeClient({ apiBaseUrl, monitoringKey: key, onStatus: (status) => active && setConnection(status), onMessage: (message) => { if (active && message.type === "monitoring.snapshot") setOverview(message.data); } });
    realtime.start();
    const poll = window.setInterval(() => { void api.current?.getOverview().then((value) => active && setOverview(value)).catch(() => undefined); }, 5000);
    return () => { active = false; realtime.stop(); window.clearInterval(poll); };
  }, [authenticated, apiBaseUrl, key]);

  async function inspect(sessionId: string) {
    if (!api.current || !sessionId) return;
    setBusy(true); setError(null);
    try { setInspector(await api.current.inspectSession(sessionId)); } catch (exc) { setError(exc instanceof Error ? exc.message : "Unable to inspect session"); } finally { setBusy(false); }
  }

  async function resetTelemetry() {
    if (!api.current) return;
    setBusy(true); setError(null);
    try { await api.current.resetTelemetry(); setOverview(await api.current.getOverview()); } catch (exc) { setError(exc instanceof Error ? exc.message : "Unable to reset telemetry"); } finally { setBusy(false); }
  }

  function logout() { sessionStorage.removeItem(STORAGE_KEY); setAuthenticated(false); setKey(""); setOverview(null); api.current = null; }

  if (!authenticated) return <Login onLogin={authenticate} busy={busy} error={loginError} />;
  if (!overview) return <main className="monitor-loading"><Spinner /> Loading operations telemetry…</main>;

  const filteredEvents = eventFilter === "ALL" ? overview.recent_events : overview.recent_events.filter((event) => event.source === eventFilter || event.event_type.startsWith(eventFilter));
  const cameraConfigured = overview.camera.status !== "NOT_CONFIGURED";
  const visionConfigured = overview.vision.status !== "NOT_CONFIGURED";
  const nav: { id: View; label: string; icon: string }[] = [
    { id: "overview", label: "Overview", icon: "⌂" },
    { id: "camera", label: "Cameras", icon: "◉" },
    { id: "vision", label: "Vision AI", icon: "◇" },
    { id: "events", label: "Event Stream", icon: "≋" },
    { id: "reconciliation", label: "Reconciliation", icon: "⇄" },
    { id: "runtime", label: "Runtime", icon: "⌘" },
  ];

  return <main className="monitor-shell"><aside className="monitor-sidebar"><div className="monitor-brand"><div className="ops-mark small">S</div><div><b>SyncCart AI</b><span>AI Operations Center</span></div></div><nav>{nav.map((item) => <button className={view === item.id ? "active" : ""} key={item.id} onClick={() => setView(item.id)}><span>{item.icon}</span>{item.label}</button>)}</nav><div className="sidebar-foot"><div className={`connection ${connection}`}><i />{connection === "connected" ? "Live telemetry" : label(connection)}</div><button onClick={logout}>Sign out</button></div></aside><section className="monitor-main"><header className="monitor-header"><div><p className="eyebrow">Team Synergy • Engineering observability</p><h1>{nav.find((item) => item.id === view)?.label}</h1></div><div className="header-right"><span className="phase-chip">Phase 4D</span><span>Updated {time(overview.generated_at)}</span></div></header>{error ? <div className="monitor-error">{error}<button onClick={() => setError(null)}>×</button></div> : null}

  {view === "overview" ? <><div className="metric-grid"><Metric value={overview.metrics.active_sessions} labelText="Active sessions" detail={`${overview.metrics.total_sessions} total`} /><Metric value={overview.metrics.total_events} labelText="Domain events" detail={`${overview.metrics.vision_events} physical`} accent="violet" /><Metric value={overview.metrics.open_discrepancies} labelText="Open discrepancies" detail={`${overview.metrics.nudges_sent} nudges`} accent="amber" /><Metric value={overview.metrics.event_matches} labelText="Confirmed matches" detail={`${overview.metrics.checkouts_approved} exits approved`} accent="green" /></div><ServiceMatrix overview={overview} />{overview.notices.length ? <div className="notice-stack">{overview.notices.map((item) => <div className={`notice ${item.level.toLowerCase()}`} key={item.title}><span>{item.level === "WARN" ? "!" : "i"}</span><div><b>{item.title}</b><p>{item.detail}</p></div></div>)}</div> : null}<div className="overview-columns"><Card className="telemetry-summary"><div className="panel-title"><div><p className="eyebrow">Edge input</p><h2>Retail edge camera</h2></div><StatusPill tone={tone(overview.camera.status)}>{label(overview.camera.status)}</StatusPill></div><div className="telemetry-hero"><strong>{overview.camera.fps == null ? "—" : overview.camera.fps.toFixed(1)}</strong><span>FPS</span></div><dl><div><dt>Source</dt><dd>{overview.camera.source}</dd></div><div><dt>Latency</dt><dd>{overview.camera.frame_latency_ms == null ? "—" : `${overview.camera.frame_latency_ms.toFixed(0)} ms`}</dd></div><div><dt>Resolution</dt><dd>{overview.camera.resolution ?? "—"}</dd></div><div><dt>Stream</dt><dd>{overview.camera.stream_mode ?? "—"}</dd></div></dl>{!cameraConfigured ? <p className="future-note">Connect the configured CCTV/NVR, IP camera, webcam, or Phone 1 demo stream to publish live telemetry.</p> : null}</Card><Card className="telemetry-summary"><div className="panel-title"><div><p className="eyebrow">Inference runtime</p><h2>Vision AI</h2></div><StatusPill tone={tone(overview.vision.status)}>{label(overview.vision.status)}</StatusPill></div><div className="telemetry-hero"><strong>{overview.vision.avg_inference_ms == null ? "—" : overview.vision.avg_inference_ms.toFixed(0)}</strong><span>ms / inference</span></div><dl><div><dt>Model</dt><dd>{overview.vision.model_name ?? "Detector"}</dd></div><div><dt>Version</dt><dd>{overview.vision.model_version ?? "—"}</dd></div><div><dt>Device</dt><dd>{overview.vision.device ?? "—"}</dd></div><div><dt>Avg confidence</dt><dd>{overview.vision.avg_confidence == null ? "—" : `${Math.round(overview.vision.avg_confidence * 100)}%`}</dd></div></dl>{!visionConfigured ? <p className="future-note">Start the Vision service to activate live detector telemetry. AUTO mode uses the fixed-zone reference detector when optional YOLO weights are absent.</p> : null}</Card></div><Card className="recent-panel"><div className="panel-title"><div><p className="eyebrow">Platform activity</p><h2>Recent domain events</h2></div><button onClick={() => setView("events")}>Open stream</button></div><div className="event-stream">{overview.recent_events.slice(0, 8).map((event) => <EventRow key={event.id} event={event} onInspect={inspect} />)}{!overview.recent_events.length ? <div className="empty">No events yet. Start a Phone 2 shopping session or use the physical-event simulator.</div> : null}</div></Card></> : null}

  {view === "camera" ? <div className="camera-page"><Card className="camera-stage"><div className="stage-head"><div><p className="eyebrow">Shelf camera • {overview.camera.camera_id}</p><h2>Live edge input</h2></div><StatusPill tone={tone(overview.camera.status)}>{label(overview.camera.status)}</StatusPill></div><div className={`camera-preview ${cameraConfigured ? "configured" : "waiting"}`}>{cameraConfigured ? <img className="camera-live-image" src={`${visionBaseUrl}/preview.mjpeg`} alt="Live SyncCart shelf camera with Vision overlays" /> : <><div className="scan-grid"/><div className="camera-center"><span>◉</span><b>Phone 1 stream not connected yet</b><p>The monitoring surface is deliberately honest: there is no fake live video.</p></div></>}<div className="camera-overlay"><span>CAM {overview.camera.camera_id}</span><span>{overview.camera.resolution ?? "NO SIGNAL"}</span></div></div></Card><div className="camera-kpis"><Metric value={overview.camera.fps?.toFixed(1) ?? "—"} labelText="Frame rate" detail="frames / second" /><Metric value={overview.camera.frame_latency_ms?.toFixed(0) ?? "—"} labelText="Frame latency" detail="milliseconds" accent="violet" /><Metric value={overview.camera.consecutive_failures} labelText="Consecutive failures" detail="runtime counter" accent={overview.camera.consecutive_failures ? "amber" : "green"} /><Metric value={time(overview.camera.last_frame_at)} labelText="Last frame" detail={overview.camera.stream_mode ?? "stream unavailable"} accent="green" /></div><Card className="contract-card"><p className="eyebrow">Telemetry contract</p><h2>What Phone 1 will publish</h2><div className="contract-grid"><span>camera_id</span><span>status</span><span>fps</span><span>frame_latency_ms</span><span>resolution</span><span>stream_mode</span><span>last_frame_at</span><span>failures</span></div><p>The Phase 5 Vision worker now publishes this contract and serves its annotated MJPEG preview directly on port 8100.</p></Card></div> : null}

  {view === "vision" ? <div className="vision-page"><div className="vision-top"><Card className="model-card"><div className="panel-title"><div><p className="eyebrow">Model runtime</p><h2>{overview.vision.model_name ?? "Vision detector"}</h2></div><StatusPill tone={tone(overview.vision.status)}>{label(overview.vision.status)}</StatusPill></div><div className="model-version">{overview.vision.model_version ?? "release-v1"}</div><div className="model-stats"><div><strong>{overview.vision.fps?.toFixed(1) ?? "—"}</strong><span>Vision FPS</span></div><div><strong>{overview.vision.avg_inference_ms?.toFixed(0) ?? "—"}</strong><span>Inference ms</span></div><div><strong>{overview.vision.avg_confidence == null ? "—" : `${Math.round(overview.vision.avg_confidence * 100)}%`}</strong><span>Avg confidence</span></div><div><strong>{overview.vision.low_confidence_rate == null ? "—" : `${Math.round(overview.vision.low_confidence_rate * 100)}%`}</strong><span>Low confidence</span></div></div><p className="future-note">{overview.vision.note}</p></Card><Card className="detections-card"><p className="eyebrow">Current class counts</p><h2>Detection distribution</h2>{Object.keys(overview.vision.detections_by_class).length ? <div className="detection-bars">{Object.entries(overview.vision.detections_by_class).map(([name, count]) => { const max = Math.max(...Object.values(overview.vision.detections_by_class), 1); return <div key={name}><span>{label(name)}</span><div><i style={{ width: `${(count / max) * 100}%` }}/></div><b>{count}</b></div>; })}</div> : <div className="empty technical">Detector counts appear here as soon as the Vision service receives the configured camera stream.</div>}</Card></div><Card className="pipeline-card"><p className="eyebrow">Inference architecture</p><h2>Shelf quantity event pipeline</h2><div className="pipeline"><span>Camera frame</span><b>→</b><span>ROI</span><b>→</b><span>Detector</span><b>→</b><span>SKU count</span><b>→</b><span>Temporal smoothing</span><b>→</b><span>Pickup / return event</span></div><p>The monitoring application observes this pipeline. It does not decide whether a shopper should be reviewed; that remains the reconciliation domain's job.</p></Card></div> : null}

  {view === "events" ? <><div className="toolbar"><div className="filter-group">{["ALL", "VISION", "CUSTOMER", "SYSTEM", "OPERATOR"].map((item) => <button className={eventFilter === item ? "active" : ""} onClick={() => setEventFilter(item)} key={item}>{item}</button>)}</div><span>{filteredEvents.length} recent events</span></div><Card className="event-console"><div className="console-head"><span>TIME</span><span>EVENT</span><span>CONTEXT</span></div><div className="event-stream">{filteredEvents.map((event) => <EventRow key={event.id} event={event} onInspect={inspect} />)}{!filteredEvents.length ? <div className="empty">No events match this filter.</div> : null}</div></Card></> : null}

  {view === "reconciliation" ? <div className="reconcile-page"><Card className="reconcile-search"><p className="eyebrow">Evidence inspector</p><h2>Trace one shopping session</h2><p>Enter an internal session UUID, or click any session-linked event in the Event Stream.</p><div><input value={sessionInput} onChange={(e) => setSessionInput(e.target.value)} placeholder="Session UUID"/><button disabled={!sessionInput || busy} onClick={() => void inspect(sessionInput)}>{busy ? <Spinner/> : "Inspect"}</button></div></Card><div className="reconcile-explainer"><Card><strong>1</strong><h3>Physical evidence</h3><p>Vision pickup and return events update the independent physical cart.</p></Card><Card><strong>2</strong><h3>Digital evidence</h3><p>Phone 2 barcode scans update the shopper-declared digital cart.</p></Card><Card><strong>3</strong><h3>Temporal matching</h3><p>SKU, quantity, session, timing, and confidence determine candidate matches.</p></Card><Card><strong>4</strong><h3>Explainable action</h3><p>Only unresolved discrepancies move through verify, nudge, and review.</p></Card></div></div> : null}

  {view === "runtime" ? <div className="runtime-page"><ServiceMatrix overview={overview}/><div className="runtime-grid"><Card><p className="eyebrow">Current deployment</p><h2>Retail edge deployment</h2><dl><div><dt>API</dt><dd>{apiBaseUrl}</dd></div><div><dt>Monitoring WS</dt><dd>/ws/admin</dd></div><div><dt>Database</dt><dd>SQLite local / PostgreSQL-ready</dd></div><div><dt>Camera</dt><dd>{overview.camera.status}</dd></div><div><dt>Vision</dt><dd>{overview.vision.status}</dd></div><div><dt>Vision service</dt><dd>{visionBaseUrl}</dd></div></dl></Card><Card><p className="eyebrow">Safety behavior</p><h2>Fail safe on uncertainty</h2><p>Camera or Vision degradation must reduce trust in automatic physical evidence. The platform should surface uncertainty instead of silently producing aggressive interventions.</p><div className="safety-flow"><span>Healthy evidence</span><b>→</b><span>Normal reconciliation</span><br/><span>Degraded evidence</span><b>→</b><span>Human verification / pause escalation</span></div></Card><Card><p className="eyebrow">Telemetry controls</p><h2>Runtime state</h2><p>Reset only clears process-local camera and Vision telemetry. It does not delete sessions, carts, events, discrepancies, or audit evidence.</p><button className="danger-outline" disabled={busy} onClick={() => void resetTelemetry()}>Reset runtime telemetry</button></Card></div></div> : null}

  </section>{inspector ? <ReconciliationInspector data={inspector} onClose={() => setInspector(null)} /> : null}{busy && !inspector ? <div className="monitor-busy"><Spinner/></div> : null}</main>;
}
