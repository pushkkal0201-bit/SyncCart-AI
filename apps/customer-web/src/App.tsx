import { useEffect, useMemo, useRef, useState } from "react";
import { AppShell, Button, Card, SectionTitle, Spinner, StatusPill } from "@synccart/design-system";
import { SyncCartApiClient, inferApiBaseUrl } from "@synccart/api-client";
import { CustomerRealtimeClient } from "@synccart/realtime-client";
import type { CheckoutResult, CustomerAction, Reconciliation, SessionCreated } from "@synccart/shared-types";
import { BarcodeScanner } from "./features/scanner/BarcodeScanner";
import { CartList, CartTotal } from "./components/CartList";

type View = "home" | "scan" | "cart" | "checkout" | "exit";
type StoredSession = Pick<SessionCreated, "id" | "public_id" | "customer_token">;

const STORAGE_KEY = "synccart.customer.session.v1";

function statusTone(status?: string): "good" | "warn" | "danger" | "info" {
  if (["CLEAR", "RESOLVED", "CHECKOUT_APPROVED"].includes(status ?? "")) return "good";
  if (["VERIFY", "NUDGE"].includes(status ?? "")) return "warn";
  if (["REVIEW", "CHECKOUT_BLOCKED"].includes(status ?? "")) return "danger";
  return "info";
}

function friendlyStatus(status?: string) {
  const map: Record<string, string> = {
    ACTIVE: "Session active",
    CLEAR: "Cart synced",
    VERIFY: "Checking cart",
    NUDGE: "Action needed",
    REVIEW: "Assistance needed",
    RESOLVED: "Cart resynced",
    CHECKOUT_BLOCKED: "Verification needed",
    CHECKOUT_APPROVED: "Clear to exit",
    COMPLETED: "Session complete",
  };
  return map[status ?? ""] ?? "Connecting";
}

function loadStoredSession(): StoredSession | null {
  try {
    const value = sessionStorage.getItem(STORAGE_KEY);
    return value ? (JSON.parse(value) as StoredSession) : null;
  } catch {
    return null;
  }
}

export function App() {
  const apiBaseUrl = useMemo(() => inferApiBaseUrl(), []);
  const api = useRef(new SyncCartApiClient({ baseUrl: apiBaseUrl }));
  const [session, setSession] = useState<StoredSession | null>(() => loadStoredSession());
  const [reconciliation, setReconciliation] = useState<Reconciliation | null>(null);
  const [view, setView] = useState<View>(() => (loadStoredSession() ? "home" : "home"));
  const [busy, setBusy] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);
  const [connection, setConnection] = useState<"connecting" | "connected" | "disconnected">("disconnected");
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [checkout, setCheckout] = useState<CheckoutResult | null>(null);

  const digitalCart = reconciliation?.cart.digital_cart;
  const activeNudge = reconciliation?.latest_nudges.find((n) => n.status === "SENT") ?? null;

  useEffect(() => {
    if (!session) return;
    api.current.setSessionToken(session.customer_token);
    let active = true;
    const realtime = new CustomerRealtimeClient({
      apiBaseUrl,
      sessionId: session.id,
      token: session.customer_token,
      onStatus: (status) => active && setConnection(status),
      onMessage: (message) => {
        if (!active) return;
        if (message.type === "session.snapshot") setReconciliation(message.data);
      },
    });
    realtime.start();

    const refresh = async () => {
      try {
        const state = await api.current.getReconciliation(session.id);
        if (active) setReconciliation(state);
      } catch (exc) {
        if (active) setError(exc instanceof Error ? exc.message : "Unable to refresh session");
      }
    };
    void refresh();
    const fallbackPoll = window.setInterval(() => {
      void refresh();
    }, 2500);
    return () => {
      active = false;
      realtime.stop();
      window.clearInterval(fallbackPoll);
    };
  }, [session, apiBaseUrl]);

  useEffect(() => {
    if (!toast) return;
    const id = window.setTimeout(() => setToast(null), 2600);
    return () => window.clearTimeout(id);
  }, [toast]);

  async function startShopping() {
    setBusy(true); setError(null);
    try {
      const created = await api.current.createSession();
      const stored: StoredSession = { id: created.id, public_id: created.public_id, customer_token: created.customer_token };
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
      api.current.setSessionToken(created.customer_token);
      setSession(stored);
      setReconciliation(await api.current.getReconciliation(created.id));
      setToast("Shopping session started");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not start shopping session");
    } finally { setBusy(false); }
  }

  async function scanBarcode(barcode: string) {
    if (!session) return;
    setBusy(true); setError(null);
    try {
      const result = await api.current.scan(session.id, barcode, 1);
      if (!result.accepted && result.reason === "DUPLICATE_SCAN_SUPPRESSED") setToast("Duplicate scan ignored");
      else setToast("Product added to cart");
      setReconciliation(await api.current.getReconciliation(session.id));
      setView("cart");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Barcode could not be added");
      throw exc;
    } finally { setBusy(false); }
  }

  async function removeItem(sku: string) {
    if (!session) return;
    setRemoving(sku); setError(null);
    try {
      await api.current.removeItem(session.id, sku, 1);
      setReconciliation(await api.current.getReconciliation(session.id));
      setToast("Item removed from digital cart");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not remove item");
    } finally { setRemoving(null); }
  }

  async function nudgeAction(action: CustomerAction) {
    if (!session || !activeNudge) return;
    setBusy(true); setError(null);
    try {
      const result = await api.current.respondToNudge(session.id, activeNudge.id, action);
      setReconciliation(result.reconciliation);
      if (action === "SCAN_NOW") setView("scan");
      if (action === "I_RETURNED_IT") setToast("Return noted. Place the item back; SyncCart is checking the shelf.");
      if (action === "GET_HELP") setToast("A store colleague has been requested.");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not submit your response");
    } finally { setBusy(false); }
  }

  async function requestCheckout() {
    if (!session) return;
    setBusy(true); setError(null);
    try {
      const result = await api.current.checkout(session.id);
      setCheckout(result);
      setReconciliation(result.reconciliation);
      setView("exit");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Checkout could not be completed");
    } finally { setBusy(false); }
  }

  function endLocalSession() {
    sessionStorage.removeItem(STORAGE_KEY);
    api.current.setSessionToken(null);
    setSession(null); setReconciliation(null); setCheckout(null); setView("home");
  }

  if (!session) {
    return (
      <AppShell>
        <div className="welcome-page">
          <div className="ambient-grid" />
          <section className="brand-lockup"><div className="brand-orbit">S</div><div><p>TEAM SYNERGY</p><h1>SyncCart <span>AI</span></h1></div></section>
          <div className="welcome-copy"><p className="eyebrow">Frictionless retail intelligence</p><h2>Shop freely.<br />Scan as you go.</h2><p>SyncCart quietly keeps your digital cart aligned with what you take from the shelf. If something looks missed, you get a private chance to fix it first.</p></div>
          <Card className="welcome-card"><div className="trust-line"><span>◎</span><div><strong>Privacy by design</strong><small>No face recognition. Temporary session only.</small></div></div><div className="trust-line"><span>↯</span><div><strong>Fast checkout</strong><small>Only mismatches trigger action.</small></div></div><Button onClick={startShopping} disabled={busy}>{busy ? <><Spinner /> Starting…</> : "Start shopping"}</Button></Card>
          {error ? <div className="error-banner">{error}</div> : null}
          <footer className="welcome-footer">Powered by SyncCart Core • Team Synergy</footer>
        </div>
      </AppShell>
    );
  }

  if (view === "scan") return <AppShell><div className="mobile-app"><BarcodeScanner busy={busy} onDetected={scanBarcode} onClose={() => setView("home")} />{error ? <div className="error-banner sticky-error">{error}</div> : null}</div></AppShell>;

  if (view === "exit") {
    const approved = checkout?.approved ?? reconciliation?.session_status === "CHECKOUT_APPROVED";
    return <AppShell><div className="mobile-app exit-page"><div className={`exit-orb ${approved ? "approved" : "blocked"}`}>{approved ? "✓" : "!"}</div><p className="eyebrow">Final cart check</p><h1>{approved ? "Clear to exit" : "Verification needed"}</h1><p>{checkout?.message ?? (approved ? "Everything matches. You're good to go." : "A store colleague will verify only the unmatched item.")}</p><Card className="exit-summary"><div><span>Physical cart</span><strong>{reconciliation?.cart.physical_cart.total_quantity ?? 0} items</strong></div><div><span>Digital cart</span><strong>{reconciliation?.cart.digital_cart.total_quantity ?? 0} items</strong></div><div><span>Consistency</span><strong>{reconciliation?.cart_consistency_score.toFixed(0) ?? "0"}%</strong></div><div><span>Payment</span><strong>{checkout?.payment_mode === "SIMULATED" ? "Demo approved" : "Simulation"}</strong></div></Card><Button onClick={approved ? endLocalSession : () => setView("home")}>{approved ? "Finish session" : "Back to cart"}</Button><p className="demo-note">Demo checkout confirmation is isolated from external payment rails; cart reconciliation remains the exit-control decision.</p></div></AppShell>;
  }

  return (
    <AppShell>
      <div className="mobile-app">
        <header className="customer-header"><div className="mini-logo">S</div><div><p>SyncCart AI</p><strong>{session.public_id}</strong></div><div className={`connection-dot ${connection}`}><span />{connection === "connected" ? "Live" : connection}</div></header>
        {error ? <div className="error-banner">{error}<button onClick={() => setError(null)}>×</button></div> : null}
        {toast ? <div className="toast">✓ {toast}</div> : null}

        {activeNudge ? <NudgePanel message={activeNudge.message} busy={busy} onAction={nudgeAction} /> : null}

        {view === "home" ? <>
          <section className="hero-status"><div><p className="eyebrow">Live cart intelligence</p><h1>{friendlyStatus(reconciliation?.session_status)}</h1><p>{reconciliation?.session_status === "CLEAR" || reconciliation?.session_status === "RESOLVED" ? "Physical and digital carts are aligned." : reconciliation?.reasons[0] ?? "SyncCart is watching for cart consistency."}</p></div><div className={`score-ring tone-${statusTone(reconciliation?.session_status)}`}><strong>{Math.round(reconciliation?.cart_consistency_score ?? 100)}</strong><span>sync</span></div></section>
          <section className="quick-metrics"><div><span>Items</span><strong>{digitalCart?.total_quantity ?? 0}</strong></div><div><span>Status</span><StatusPill tone={statusTone(reconciliation?.session_status)}>{friendlyStatus(reconciliation?.session_status)}</StatusPill></div><div><span>Network</span><strong>{connection === "connected" ? "Realtime" : "Fallback"}</strong></div></section>
          <Card className="scan-cta"><div><p className="eyebrow">Add product</p><h2>Ready for your next item?</h2><p>Use your phone camera or enter a barcode manually.</p></div><button className="scan-fab" onClick={() => setView("scan")}>⌗</button></Card>
          <section className="home-cart"><SectionTitle eyebrow="Digital cart" title="Your basket" action={<button className="text-button" onClick={() => setView("cart")}>View all →</button>} />{digitalCart ? <CartList cart={{...digitalCart, items:digitalCart.items.slice(0,2)}} onRemove={removeItem} removing={removing} /> : <div className="loading-line"><Spinner /> Loading cart</div>}</section>
        </> : null}

        {view === "cart" && digitalCart ? <section className="cart-page"><SectionTitle eyebrow="Session cart" title="Your basket" action={<StatusPill tone={statusTone(reconciliation?.session_status)}>{friendlyStatus(reconciliation?.session_status)}</StatusPill>} /><CartList cart={digitalCart} onRemove={removeItem} removing={removing} /><CartTotal cart={digitalCart} /><div className="cart-footer-actions"><Button onClick={() => setView("scan")}>Scan another item</Button><button className="secondary-action" onClick={() => setView("checkout")} disabled={!digitalCart.total_quantity}>Review checkout</button></div></section> : null}

        {view === "checkout" && digitalCart ? <section className="checkout-page"><SectionTitle eyebrow="Final review" title="Pay & exit" /><Card className="checkout-card"><div className="checkout-state"><span className="pulse-dot" /><div><strong>Final reconciliation will run now</strong><small>SyncCart compares the physical cart with your scanned cart before exit.</small></div></div><CartList cart={digitalCart} onRemove={removeItem} removing={removing} /><CartTotal cart={digitalCart} /></Card><Button onClick={requestCheckout} disabled={busy || !digitalCart.total_quantity}>{busy ? "Checking cart…" : "Simulate payment & request exit"}</Button><p className="demo-note">Demo checkout confirmation. Exit approval is based on cart consistency.</p></section> : null}

        <nav className="bottom-nav"><button className={view === "home" ? "active" : ""} onClick={() => setView("home")}><span>⌂</span>Home</button><button className="nav-scan" onClick={() => setView("scan")}><span>⌗</span>Scan</button><button className={view === "cart" || view === "checkout" ? "active" : ""} onClick={() => setView("cart")}><span>▣</span>Cart <b>{digitalCart?.total_quantity ?? 0}</b></button></nav>
      </div>
    </AppShell>
  );
}

function NudgePanel({ message, busy, onAction }: { message: string; busy: boolean; onAction: (action: CustomerAction) => void }) {
  return <div className="nudge-backdrop"><Card className="nudge-panel"><div className="nudge-icon">!</div><p className="eyebrow">Quick cart check</p><h2>{message}</h2><p>We noticed an item may not be in your digital cart. You can fix this privately before any store review.</p><div className="nudge-actions"><Button disabled={busy} onClick={() => onAction("SCAN_NOW")}>Scan now</Button><button disabled={busy} className="secondary-action" onClick={() => onAction("I_RETURNED_IT")}>I returned it</button><button disabled={busy} className="link-action" onClick={() => onAction("GET_HELP")}>Get help</button></div><small>No staff intervention is triggered by this reminder alone.</small></Card></div>;
}
