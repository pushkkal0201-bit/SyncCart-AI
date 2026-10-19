import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Card, Spinner, StatusPill } from "@synccart/design-system";
import { ApiError, StoreApiClient, inferApiBaseUrl } from "@synccart/api-client";
import { StoreRealtimeClient } from "@synccart/realtime-client";
import type {
  DomainEvent,
  ReviewQueueItem,
  ReviewResolutionAction,
  StoreOverview,
  StoreSessionDetail,
  StoreSessionSummary,
} from "@synccart/shared-types";

type View = "overview" | "sessions" | "reviews" | "analytics";
type Connection = "connecting" | "connected" | "disconnected";

const KEY_STORAGE = "synccart.store.key.v1";

function tone(status: string): "good" | "warn" | "danger" | "info" {
  if (["CLEAR", "RESOLVED", "CHECKOUT_APPROVED"].includes(status)) return "good";
  if (["VERIFY", "NUDGE"].includes(status)) return "warn";
  if (["REVIEW", "REVIEW_REQUIRED", "CHECKOUT_BLOCKED"].includes(status)) return "danger";
  return "info";
}

function label(status: string) {
  return status.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (match) => match.toUpperCase());
}

function duration(seconds: number) {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs.toString().padStart(2, "0")}s`;
}

function time(value: string) {
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function percent(value: number) {
  return `${Math.round(value)}%`;
}

function eventLabel(event: DomainEvent) {
  const names: Record<string, string> = {
    SESSION_STARTED: "Session started",
    VISION_PICKUP: "Product pickup detected",
    VISION_RETURN: "Product return detected",
    PRODUCT_SCANNED: "Product scanned",
    MATCH_CONFIRMED: "Physical and digital event matched",
    DISCREPANCY_OPENED: "Cart discrepancy opened",
    NUDGE_SENT: "Private customer nudge sent",
    NUDGE_ACKNOWLEDGED: "Customer acknowledged nudge",
    REVIEW_REQUIRED: "Colleague review requested",
    REVIEW_RESOLVED: "Colleague review resolved",
    DISCREPANCY_RESOLVED: "Cart discrepancy resolved",
    CHECKOUT_REQUESTED: "Checkout requested",
    CHECKOUT_APPROVED: "Exit approved",
    CHECKOUT_REJECTED: "Checkout verification required",
  };
  return names[event.event_type] ?? label(event.event_type);
}

function Login({ onLogin, busy, error }: { onLogin: (key: string) => void; busy: boolean; error: string | null }) {
  const [key, setKey] = useState("");
  return (
    <main className="retailer-login">
      <div className="login-grid" />
      <section className="login-brand">
        <div className="logo-cube">S</div>
        <div><p>TEAM SYNERGY</p><h1>SyncCart <span>AI</span></h1></div>
      </section>
      <Card className="login-card">
        <p className="eyebrow">Store operations</p>
        <h2>Colleague access</h2>
        <p>Use the local Store Operations key from your SyncCart <code>.env</code>. This key is the local store-operations access boundary and can be replaced by an enterprise identity adapter without changing store workflows.</p>
        <label>Store access key<input type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder="X-Store-Key" onKeyDown={(e) => e.key === "Enter" && key && onLogin(key)} /></label>
        <Button disabled={busy || !key.trim()} onClick={() => onLogin(key.trim())}>{busy ? <><Spinner /> Connecting…</> : "Open store operations"}</Button>
        {error ? <div className="login-error">{error}</div> : null}
      </Card>
      <footer>Operational decision support • No shopper biometric identity</footer>
    </main>
  );
}

function Metric({ icon, value, labelText, toneClass }: { icon: string; value: string | number; labelText: string; toneClass: string }) {
  return <Card className={`metric-card ${toneClass}`}><div className="metric-icon">{icon}</div><div><strong>{value}</strong><span>{labelText}</span></div></Card>;
}

function SessionRow({ item, onOpen }: { item: StoreSessionSummary; onOpen: () => void }) {
  return (
    <button className="session-row" onClick={onOpen}>
      <div><strong>{item.public_id}</strong><span>{duration(item.duration_seconds)} • {item.digital_quantity} scanned / {item.physical_quantity} physical</span></div>
      <StatusPill tone={tone(item.status)}>{label(item.status)}</StatusPill>
      <div className="session-score"><b>{percent(item.consistency_score)}</b><span>consistency</span></div>
      <div className="session-issue">{item.primary_issue ?? "No active mismatch"}</div>
      <span className="chevron">›</span>
    </button>
  );
}

function ReviewCard({ review, onOpen }: { review: ReviewQueueItem; onOpen: () => void }) {
  return (
    <Card className="review-card">
      <div className="review-head"><div><p className="eyebrow">Targeted verification</p><h3>{review.public_id}</h3></div><StatusPill tone="danger">Review required</StatusPill></div>
      <div className="review-product"><div className="product-glyph">{review.product_name.slice(0, 2).toUpperCase()}</div><div><strong>{review.product_name}</strong><span>{review.sku}</span></div><b>{review.difference > 0 ? "+" : ""}{review.difference}</b></div>
      <div className="review-grid"><div><span>Physical</span><strong>{review.physical_quantity}</strong></div><div><span>Digital</span><strong>{review.digital_quantity}</strong></div><div><span>Vision</span><strong>{review.vision_confidence === null ? "—" : percent(review.vision_confidence * 100)}</strong></div><div><span>Waiting</span><strong>{duration(review.waiting_seconds)}</strong></div></div>
      <Button onClick={onOpen}>Open evidence</Button>
    </Card>
  );
}

function CartComparison({ detail }: { detail: StoreSessionDetail }) {
  const state = detail.reconciliation;
  const physical = new Map(state.cart.physical_cart.items.map((item) => [item.sku, item]));
  const digital = new Map(state.cart.digital_cart.items.map((item) => [item.sku, item]));
  const skus = [...new Set([...physical.keys(), ...digital.keys()])];
  return (
    <div className="comparison-table">
      <div className="compare-head"><span>Product</span><span>Physical</span><span>Digital</span><span>Difference</span></div>
      {skus.length ? skus.map((sku) => {
        const p = physical.get(sku); const d = digital.get(sku); const diff = (p?.quantity ?? 0) - (d?.quantity ?? 0);
        return <div className={`compare-row ${diff ? "mismatch" : ""}`} key={sku}><div><strong>{p?.name ?? d?.name ?? sku}</strong><small>{sku}</small></div><b>{p?.quantity ?? 0}</b><b>{d?.quantity ?? 0}</b><span>{diff === 0 ? "✓" : `${diff > 0 ? "+" : ""}${diff}`}</span></div>;
      }) : <div className="compare-empty">No products in either cart yet.</div>}
    </div>
  );
}

function SessionDrawer({ detail, onClose }: { detail: StoreSessionDetail; onClose: () => void }) {
  const state = detail.reconciliation;
  const [tab, setTab] = useState<"evidence" | "timeline">("evidence");
  return (
    <div className="drawer-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <aside className="session-drawer">
        <header><div><p className="eyebrow">Live session evidence</p><h2>{state.public_id}</h2></div><button onClick={onClose}>×</button></header>
        <div className="drawer-status"><StatusPill tone={tone(state.session_status)}>{label(state.session_status)}</StatusPill><div className="score-badge"><b>{percent(state.cart_consistency_score)}</b><span>consistency</span></div></div>
        <nav className="drawer-tabs"><button className={tab === "evidence" ? "active" : ""} onClick={() => setTab("evidence")}>Evidence</button><button className={tab === "timeline" ? "active" : ""} onClick={() => setTab("timeline")}>Timeline</button></nav>
        {tab === "evidence" ? <>
          <section><h3>Physical vs digital cart</h3><CartComparison detail={detail} /></section>
          <section><h3>Why this state?</h3><div className="reason-list">{state.reasons.map((reason) => <div key={reason}><span>↳</span>{reason}</div>)}</div></section>
          {state.active_discrepancies.length ? <section><h3>Open discrepancy evidence</h3>{state.active_discrepancies.map((d) => <div className="evidence-card" key={d.id}><div><span>SKU</span><b>{d.sku}</b></div><div><span>Difference</span><b>{d.difference > 0 ? "+" : ""}{d.difference}</b></div><div><span>Vision confidence</span><b>{d.vision_confidence === null ? "—" : percent(d.vision_confidence * 100)}</b></div><div><span>Risk heuristic</span><b>{percent(d.risk_score * 100)}</b></div><p>{d.reason_codes.map(label).join(" • ")}</p></div>)}</section> : null}
        </> : <section><h3>Event timeline</h3><div className="timeline">{[...detail.events].reverse().map((event) => <article key={event.id}><i className={`event-dot ${event.source.toLowerCase()}`} /><div><strong>{eventLabel(event)}</strong><span>{time(event.created_at)} • {event.source}{event.sku ? ` • ${event.sku}` : ""}</span>{event.confidence !== null ? <small>Confidence {percent(event.confidence * 100)}</small> : null}</div></article>)}</div></section>}
      </aside>
    </div>
  );
}

function ReviewDrawer({ review, onClose, onResolve, busy }: { review: ReviewQueueItem; onClose: () => void; onResolve: (action: ReviewResolutionAction, note: string) => Promise<void>; busy: boolean }) {
  const [note, setNote] = useState("");
  return <div className="drawer-backdrop"><aside className="review-drawer"><header><div><p className="eyebrow">Review decision</p><h2>{review.product_name}</h2><span>{review.public_id} • {review.sku}</span></div><button onClick={onClose}>×</button></header>
    <Card className="review-evidence"><h3>Evidence summary</h3><div className="review-grid"><div><span>Physical</span><strong>{review.physical_quantity}</strong></div><div><span>Digital</span><strong>{review.digital_quantity}</strong></div><div><span>Vision</span><strong>{review.vision_confidence === null ? "—" : percent(review.vision_confidence * 100)}</strong></div><div><span>Risk</span><strong>{percent(review.risk_score * 100)}</strong></div></div><p>{review.reason_codes.map(label).join(" • ")}</p></Card>
    <label className="operator-note">Colleague note<textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Optional observation or reason…" /></label>
    <div className="decision-stack"><button disabled={busy} className="decision good" onClick={() => void onResolve("ITEM_RETURNED_CONFIRMED", note)}><b>Item returned — confirmed</b><span>Correct the physical projection after colleague verification.</span></button><button disabled={busy} className="decision info" onClick={() => void onResolve("FALSE_DETECTION", note)}><b>False detection</b><span>Correct the physical projection after checking the shelf.</span></button><button disabled={busy} className="decision danger" onClick={() => void onResolve("ESCALATE_MANUAL_CHECK", note)}><b>Escalate manual check</b><span>Keep this review open and record escalation.</span></button></div>
    <small className="safety-copy">Operator resolutions create immutable events. SyncCart never fabricates a customer barcode scan.</small>
  </aside></div>;
}

function Analytics({ overview }: { overview: StoreOverview }) {
  const counts = overview.status_counts;
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(([, count]) => count), 1);
  const total = Math.max(overview.metrics.active_sessions, 1);
  const syncedRatio = Math.min(100, Math.round((overview.metrics.synced_sessions / total) * 100));
  return <div className="analytics-grid"><Card className="analytics-card"><p className="eyebrow">Session distribution</p><h3>Operational states</h3><div className="bar-chart">{entries.length ? entries.map(([status, count]) => <div key={status}><span>{label(status)}</span><div><i style={{ width: `${Math.max(5, (count / max) * 100)}%` }} /></div><b>{count}</b></div>) : <p>No session data yet.</p>}</div></Card><Card className="analytics-card"><p className="eyebrow">Friction signal</p><h3>Current active-session mix</h3><div className="donut-wrap"><div className="donut" style={{ background: `conic-gradient(var(--sc-green) 0 ${syncedRatio}%, var(--sc-amber) ${syncedRatio}% 100%)` }}><div><strong>{syncedRatio}%</strong><span>synced</span></div></div><div className="donut-legend"><span><i className="green" />Synced {overview.metrics.synced_sessions}</span><span><i className="amber" />Needs attention {overview.metrics.verifying_sessions + overview.metrics.review_required}</span></div></div></Card><Card className="analytics-card wide"><p className="eyebrow">Operational interpretation</p><h3>What these metrics mean</h3><div className="insight-grid"><div><strong>{overview.metrics.active_nudges}</strong><span>private nudges currently active</span></div><div><strong>{overview.metrics.review_required}</strong><span>sessions needing colleague attention</span></div><div><strong>{overview.metrics.resolved_sessions}</strong><span>sessions presently marked resolved</span></div><div><strong>{overview.metrics.open_discrepancies}</strong><span>open item-level discrepancies</span></div></div><p className="analytics-note">These are live operational counts from the active SyncCart deployment. Business-impact KPIs are intentionally kept separate from runtime event metrics.</p></Card></div>;
}

export function App() {
  const apiBaseUrl = useMemo(() => inferApiBaseUrl(), []);
  const [storeKey, setStoreKey] = useState(() => sessionStorage.getItem(KEY_STORAGE) ?? "");
  const [authenticated, setAuthenticated] = useState(false);
  const [loginBusy, setLoginBusy] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const api = useRef<StoreApiClient | null>(null);
  const [overview, setOverview] = useState<StoreOverview | null>(null);
  const [view, setView] = useState<View>("overview");
  const [connection, setConnection] = useState<Connection>("disconnected");
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [detail, setDetail] = useState<StoreSessionDetail | null>(null);
  const [review, setReview] = useState<ReviewQueueItem | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  async function authenticate(key: string) {
    setLoginBusy(true); setLoginError(null);
    try {
      const client = new StoreApiClient({ baseUrl: apiBaseUrl, storeKey: key });
      const data = await client.getOverview();
      api.current = client; setStoreKey(key); setOverview(data); setAuthenticated(true);
      sessionStorage.setItem(KEY_STORAGE, key);
    } catch (exc) {
      setLoginError(exc instanceof ApiError ? exc.message : "Could not connect to Store Operations");
    } finally { setLoginBusy(false); }
  }

  useEffect(() => { if (storeKey && !authenticated) void authenticate(storeKey); }, []); // restore one browser session only

  useEffect(() => {
    if (!authenticated || !api.current) return;
    let active = true;
    const realtime = new StoreRealtimeClient({ apiBaseUrl, storeKey, onStatus: (status) => active && setConnection(status), onMessage: (message) => { if (active && message.type === "store.snapshot") setOverview(message.data); } });
    realtime.start();
    const poll = window.setInterval(() => { void api.current?.getOverview().then((value) => active && setOverview(value)).catch(() => undefined); }, 3500);
    return () => { active = false; realtime.stop(); window.clearInterval(poll); };
  }, [authenticated, apiBaseUrl, storeKey]);

  useEffect(() => { if (!toast) return; const timer = window.setTimeout(() => setToast(null), 2600); return () => window.clearTimeout(timer); }, [toast]);

  async function openSession(sessionId: string) {
    if (!api.current) return;
    setBusy(true); setError(null);
    try { setDetail(await api.current.getSession(sessionId)); } catch (exc) { setError(exc instanceof Error ? exc.message : "Unable to load session"); } finally { setBusy(false); }
  }

  async function resolveReview(action: ReviewResolutionAction, note: string) {
    if (!api.current || !review) return;
    setBusy(true); setError(null);
    try {
      const result = await api.current.resolveReview(review.discrepancy_id, action, note);
      setToast(result.message); setReview(null); setOverview(await api.current.getOverview());
    } catch (exc) { setError(exc instanceof Error ? exc.message : "Unable to record review decision"); } finally { setBusy(false); }
  }

  function logout() { sessionStorage.removeItem(KEY_STORAGE); setAuthenticated(false); setStoreKey(""); setOverview(null); api.current = null; }

  if (!authenticated) return <Login onLogin={authenticate} busy={loginBusy} error={loginError} />;
  if (!overview) return <main className="retailer-loading"><Spinner /> Loading store operations…</main>;

  const filtered = overview.recent_sessions.filter((item) => {
    const matchesSearch = !search || item.public_id.toLowerCase().includes(search.toLowerCase()) || (item.primary_issue ?? "").toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === "ALL" || item.status === filter;
    return matchesSearch && matchesFilter;
  });

  return <main className="ops-shell">
    <aside className="sidebar"><div className="side-brand"><div className="logo-cube small">S</div><div><b>SyncCart AI</b><span>Store Operations</span></div></div><nav>{(["overview", "sessions", "reviews", "analytics"] as View[]).map((item) => <button key={item} className={view === item ? "active" : ""} onClick={() => setView(item)}><span>{item === "overview" ? "⌂" : item === "sessions" ? "◎" : item === "reviews" ? "!" : "⌁"}</span>{label(item)}</button>)}</nav><div className="side-bottom"><div className={`live-state ${connection}`}><i />{connection === "connected" ? "Live store feed" : label(connection)}</div><button onClick={logout}>Sign out</button></div></aside>
    <section className="ops-main"><header className="ops-header"><div><p className="eyebrow">Team Synergy • Retail intelligence</p><h1>{view === "overview" ? "Store command floor" : view === "sessions" ? "Shopping sessions" : view === "reviews" ? "Review queue" : "Operational analytics"}</h1></div><div className="header-tools"><div className="store-chip"><i /> Demo Store 01</div><span className="generated">Updated {time(overview.generated_at)}</span></div></header>
      {error ? <div className="ops-error">{error}<button onClick={() => setError(null)}>×</button></div> : null}
      {view === "overview" ? <>
        <div className="metric-grid"><Metric icon="◎" value={overview.metrics.active_sessions} labelText="Active shoppers" toneClass="cyan" /><Metric icon="✓" value={overview.metrics.synced_sessions} labelText="Synced carts" toneClass="green" /><Metric icon="◌" value={overview.metrics.verifying_sessions} labelText="Verifying / nudged" toneClass="amber" /><Metric icon="!" value={overview.metrics.review_required} labelText="Review required" toneClass="danger" /></div>
        <div className="overview-grid"><section><div className="section-heading"><div><p className="eyebrow">Live floor</p><h2>Recent sessions</h2></div><button onClick={() => setView("sessions")}>View all</button></div><Card className="session-list">{overview.recent_sessions.slice(0, 8).map((item) => <SessionRow key={item.session_id} item={item} onOpen={() => void openSession(item.session_id)} />)}{!overview.recent_sessions.length ? <div className="empty">No sessions yet. Start a customer session on Phone 2.</div> : null}</Card></section><section><div className="section-heading"><div><p className="eyebrow">Needs attention</p><h2>Targeted reviews</h2></div><b>{overview.review_queue.length}</b></div><div className="review-stack">{overview.review_queue.slice(0, 3).map((item) => <ReviewCard key={item.discrepancy_id} review={item} onOpen={() => setReview(item)} />)}{!overview.review_queue.length ? <Card className="all-clear"><div>✓</div><h3>No colleague reviews</h3><p>Only persistent, high-confidence mismatches appear here.</p></Card> : null}</div></section></div>
      </> : null}
      {view === "sessions" ? <><div className="control-bar"><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search session or mismatch SKU…" /><div className="filters">{["ALL", "CLEAR", "VERIFY", "NUDGE", "REVIEW", "RESOLVED", "CHECKOUT_BLOCKED"].map((item) => <button className={filter === item ? "active" : ""} onClick={() => setFilter(item)} key={item}>{label(item)}</button>)}</div></div><Card className="session-list large">{filtered.map((item) => <SessionRow key={item.session_id} item={item} onOpen={() => void openSession(item.session_id)} />)}{!filtered.length ? <div className="empty">No sessions match the selected filter.</div> : null}</Card></> : null}
      {view === "reviews" ? <><div className="reviews-intro"><div><p className="eyebrow">Exception-only workflow</p><h2>Verify one item, not the whole trolley.</h2><p>Reviews appear after a mismatch survives the private customer-correction flow. Open evidence before making a decision.</p></div><div className="review-counter"><strong>{overview.review_queue.length}</strong><span>open reviews</span></div></div><div className="reviews-grid">{overview.review_queue.map((item) => <ReviewCard key={item.discrepancy_id} review={item} onOpen={() => setReview(item)} />)}{!overview.review_queue.length ? <Card className="all-clear wide"><div>✓</div><h3>Review queue is clear</h3><p>Customer correction and automatic matching are handling the current sessions.</p></Card> : null}</div></> : null}
      {view === "analytics" ? <Analytics overview={overview} /> : null}
    </section>
    {busy && !detail && !review ? <div className="global-busy"><Spinner /></div> : null}
    {detail ? <SessionDrawer detail={detail} onClose={() => setDetail(null)} /> : null}
    {review ? <ReviewDrawer review={review} onClose={() => setReview(null)} onResolve={resolveReview} busy={busy} /> : null}
    {toast ? <div className="ops-toast">{toast}</div> : null}
  </main>;
}
