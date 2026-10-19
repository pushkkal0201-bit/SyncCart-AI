# Event Flow

All domain events are immutable, use UUID identifiers, and are timestamped in UTC.

## Normal matched purchase

```mermaid
sequenceDiagram
    participant Vision as Vision / simulator event source
    participant API
    participant Recon as Reconciliation Engine
    participant DB
    participant Customer as Phone 2

    Vision->>API: VISION_PICKUP(COKE, 1)
    API->>DB: Physical cart COKE += 1
    API->>Recon: reconcile(session)
    Recon->>DB: DISCREPANCY_OPENED (VERIFYING)
    Customer->>API: PRODUCT_SCANNED(COKE, 1)
    API->>DB: Digital cart COKE += 1
    API->>Recon: reconcile(session)
    Recon->>DB: MATCH_CONFIRMED
    Recon->>DB: DISCREPANCY_RESOLVED
    Recon-->>Customer: session RESOLVED / aligned
```

## Missed scan

```mermaid
sequenceDiagram
    participant Vision as Vision / simulator event source
    participant Recon as Reconciliation Engine
    participant Worker as Reconciliation Worker
    participant DB
    participant Customer as Phone 2

    Vision->>Recon: VISION_PICKUP(SOAP, 1)
    Recon->>DB: DISCREPANCY_OPENED
    Note over Recon,DB: Session state VERIFY
    Worker->>Recon: sweep after grace period
    Recon->>DB: MATCH_EXPIRED
    Recon->>DB: NUDGE_SENT
    Note over Recon,DB: Session state NUDGE
    Customer->>Recon: PRODUCT_SCANNED(SOAP, 1)
    Recon->>DB: MATCH_CONFIRMED
    Recon->>DB: DISCREPANCY_RESOLVED
    Note over Recon,DB: Session state RESOLVED
```

## State progression

```text
Aligned cart
    |
    v
  CLEAR

Mismatch appears
    |
    v
  VERIFY
    |
    | grace expires
    v
  NUDGE       (physical quantity ahead of digital)
    |
    | remains unresolved
    v
  REVIEW

Any point where cart becomes aligned
    |
    v
  RESOLVED
```

A digital-ahead mismatch is treated conservatively. It enters `VERIFY`, but after the grace period it escalates to `REVIEW` rather than accusing the shopper or sending an inappropriate missed-scan nudge.
