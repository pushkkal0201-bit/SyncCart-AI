from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]


def data(response: httpx.Response) -> dict:
    response.raise_for_status()
    body = response.json()
    return body.get("data", body)


def wait_until(predicate, *, timeout: float, interval: float = 0.25):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval)
    return last


def ensure_product(client: httpx.Client, core: str, sku: str, barcode: str) -> None:
    existing = client.get(f"{core}/api/v1/products/{sku}")
    if existing.status_code == 200:
        return
    response = client.post(
        f"{core}/api/v1/products",
        json={
            "sku": sku,
            "barcode": barcode,
            "name": "Demo Soap" if sku == "SOAP-001" else sku,
            "category": "Demo",
            "unit_price_minor": 4500,
            "currency": "INR",
            "expected_visual_class": sku.split("-")[0].lower(),
        },
    )
    response.raise_for_status()


def create_session(client: httpx.Client, core: str) -> tuple[str, str, str]:
    created = data(client.post(f"{core}/api/v1/sessions"))
    return str(created["id"]), str(created["customer_token"]), str(created["public_id"])


def reconciliation(client: httpx.Client, core: str, session_id: str, token: str) -> dict:
    return data(client.get(f"{core}/api/v1/sessions/{session_id}/reconciliation", headers={"X-Session-Token": token}))


def scan(client: httpx.Client, core: str, session_id: str, token: str, barcode: str) -> dict:
    return data(
        client.post(
            f"{core}/api/v1/sessions/{session_id}/scan",
            headers={"X-Session-Token": token, "Idempotency-Key": str(uuid4())},
            json={"barcode": barcode, "quantity": 1},
        )
    )


def simulator_flow(client: httpx.Client, args, session_id: str, token: str) -> dict:
    sim_headers = {"X-Simulator-Key": args.simulator_key, "Idempotency-Key": str(uuid4())}
    pickup = data(
        client.post(
            f"{args.core}/api/v1/simulator/sessions/{session_id}/pickup",
            headers=sim_headers,
            json={"sku": args.sku, "quantity": 1, "confidence": 0.95, "camera_id": "SIM-CAM-01", "zone_id": "ZONE-SOAP"},
        )
    )
    nudge = data(
        client.post(
            f"{args.core}/api/v1/simulator/sessions/{session_id}/reconciliation/sweep",
            headers={"X-Simulator-Key": args.simulator_key},
            json={"advance_ms": args.advance_ms},
        )
    )
    scanned = scan(client, args.core, session_id, token, args.barcode)
    final = reconciliation(client, args.core, session_id, token)
    return {"pickup": pickup, "nudge": nudge, "scan": scanned, "final": final}


def live_flow(client: httpx.Client, args, session_id: str, token: str) -> dict:
    control_headers = {args.vision_control_header: args.vision_control_key}
    client.post(f"{args.vision}/control/arm", headers=control_headers).raise_for_status()
    print("Vision event emission ARMED. Keep the shelf untouched while the baseline learns.")

    def baseline_ready():
        response = client.get(f"{args.vision}/control/status")
        if not response.is_success:
            return None
        state = response.json()
        return state if state.get("baseline_status") == "READY" else None

    baseline = wait_until(baseline_ready, timeout=args.timeout)
    if not baseline:
        raise RuntimeError("Vision baseline did not become READY before timeout")
    print(f"Baseline READY: {baseline.get('zone_counts')}")
    print(f"Now physically REMOVE one {args.sku} from the shelf.")

    def pickup_seen():
        events = data(client.get(f"{args.core}/api/v1/sessions/{session_id}/events"))
        for event in reversed(events):
            if event.get("event_type") == "VISION_PICKUP" and event.get("sku") == args.sku:
                return event
        return None

    pickup = wait_until(pickup_seen, timeout=args.timeout)
    if not pickup:
        raise RuntimeError(f"No VISION_PICKUP for {args.sku} before timeout")
    print("Real Vision pickup received. Scanning the product digitally...")
    scanned = scan(client, args.core, session_id, token, args.barcode)

    def resolved():
        state = reconciliation(client, args.core, session_id, token)
        return state if state.get("session_status") in {"RESOLVED", "CLEAR"} and not state.get("active_discrepancies") else None

    final = wait_until(resolved, timeout=8.0)
    client.post(f"{args.vision}/control/disarm", headers=control_headers).raise_for_status()
    if not final:
        raise RuntimeError("Carts did not resolve after digital scan")
    return {"baseline": baseline, "pickup": pickup, "scan": scanned, "final": final}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a reproducible SyncCart end-to-end demo")
    parser.add_argument("--mode", choices=["simulator", "live"], default="simulator")
    parser.add_argument("--core", default="http://127.0.0.1:8000")
    parser.add_argument("--vision", default="http://127.0.0.1:8100")
    parser.add_argument("--simulator-key", default="replace-with-a-random-local-demo-key")
    parser.add_argument("--vision-control-key", default="replace-with-a-random-local-vision-control-key")
    parser.add_argument("--vision-api-key", default="replace-with-a-random-local-vision-key")
    parser.add_argument("--vision-api-header", default="X-Vision-Key")
    parser.add_argument("--vision-control-header", default="X-Vision-Control-Key")
    parser.add_argument("--sku", default="SOAP-001")
    parser.add_argument("--barcode", default="8900000000036")
    parser.add_argument("--advance-ms", type=int, default=4500)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output", default=str(ROOT / "runtime" / "phase7_e2e_demo.json"))
    args = parser.parse_args()
    args.core = args.core.rstrip("/")
    args.vision = args.vision.rstrip("/")

    with httpx.Client(timeout=5.0) as client:
        ensure_product(client, args.core, args.sku, args.barcode)
        if args.mode == "live":
            preflight = client.get(
                f"{args.core}/api/v1/vision/active-session",
                headers={args.vision_api_header: args.vision_api_key},
            )
            preflight.raise_for_status()
            current = data(preflight)
            if current.get("available"):
                raise RuntimeError(
                    f"An eligible SyncCart session is already active ({current.get('public_id')}). "
                    "Finish or reset it before starting a controlled one-shopper live run."
                )
            if current.get("reason") == "MULTIPLE_ACTIVE_SESSIONS_UNSUPPORTED_IN_WATCHED_ZONE":
                raise RuntimeError("Multiple active sessions already exist; live Vision attribution is intentionally blocked.")
        session_id, token, public_id = create_session(client, args.core)
        print(f"Created anonymous shopping session {public_id} ({session_id})")
        try:
            result = simulator_flow(client, args, session_id, token) if args.mode == "simulator" else live_flow(client, args, session_id, token)
        finally:
            if args.mode == "live":
                try:
                    client.post(
                        f"{args.vision}/control/disarm",
                        headers={args.vision_control_header: args.vision_control_key},
                    )
                except Exception:
                    pass

    report = {
        "mode": args.mode,
        "session_id": session_id,
        "public_id": public_id,
        "sku": args.sku,
        "final_status": result["final"].get("session_status"),
        "active_discrepancies": result["final"].get("active_discrepancies"),
        "result": result,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Final state: {report['final_status']}; report={output}")
    return 0 if not report["active_discrepancies"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
