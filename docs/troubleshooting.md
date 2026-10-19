# Troubleshooting

## PowerShell refuses to activate `.venv`

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## `py -3.12` is not found

Install Python 3.12, enable the Python launcher, reopen PowerShell, then run:

```powershell
py -0p
```

## Alembic cannot create the database

From repository root:

```powershell
New-Item -ItemType Directory -Force runtime | Out-Null
cd services\api
alembic upgrade head
cd ..\..
```

## Simulator returns `SIMULATOR_DISABLED`

Add/update these values in `.env`:

```env
ENABLE_SIMULATOR=true
SIMULATOR_API_KEY=choose-a-random-local-demo-key
```

Restart Uvicorn after changing `.env`.

## Simulator returns `INVALID_SIMULATOR_KEY`

Send the exact configured key in:

```text
X-Simulator-Key
```

## Pickup remains in VERIFY during manual testing

Normal Phase 3 behavior uses a real grace timer. Either wait at least `SCAN_GRACE_PERIOD_MS`, or use the protected demo sweep endpoint:

```text
POST /api/v1/simulator/sessions/{session_id}/reconciliation/sweep
```

with an `advance_ms` payload while simulator mode is enabled.

## Phone cannot reach laptop

1. Put laptop and Phone 2 on the same Wi-Fi/hotspot.
2. Run `ipconfig` and copy the Wi-Fi IPv4 address.
3. Run Uvicorn with `--host 0.0.0.0`.
4. Allow Python/Uvicorn on **Private** Windows networks in Defender Firewall.
5. Test `http://LAPTOP_IP:8000/health/live` from Phone 2.
