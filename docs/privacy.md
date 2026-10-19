# Privacy and Responsible AI

SyncCart AI is designed around **transaction discrepancy**, not identity classification.

## Data-minimization principle

The preferred flow is:

```text
raw frame at edge
    ↓
SKU detection / count change
    ↓
normalized event metadata
    ↓
core reconciliation
```

The transactional platform does not require raw video to understand that, for example, one `olive_oil` unit moved from shelf to physical cart.

## Normalized Vision metadata

A physical event may include:

- anonymous session ID;
- SKU;
- pickup / return direction;
- quantity;
- Vision confidence;
- camera ID;
- shelf-zone ID;
- frame ID;
- model version;
- timestamp.

## Explicitly prohibited product features

- facial recognition;
- permanent shopper identity tracking;
- race / gender / age inference;
- emotion inference;
- criminal-intent classification;
- accusation-first customer labels.

## Customer intervention principle

A discrepancy means the two cart projections disagree. It does not prove intent. The UX therefore starts with verification and a neutral private nudge.

## Raw-image handling

The repository includes capture tooling for controlled model-development sessions, but raw captures and annotated datasets are excluded from Git. A pilot should define explicit consent, access controls, storage location, retention, and deletion rules before retaining any debug imagery.

## Production governance still required

A production pilot should complete:

- data-protection review;
- documented retention policy;
- access-control review;
- camera signage / consent requirements applicable to the deployment;
- model performance and bias/error analysis at the SKU/event level;
- incident-response procedures.
