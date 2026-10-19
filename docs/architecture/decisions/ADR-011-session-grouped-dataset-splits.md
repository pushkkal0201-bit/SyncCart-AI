# ADR-011 — Group dataset splits by capture session

## Status

Accepted.

## Context

Phone-camera data collected as video contains many strongly correlated neighboring frames. Random per-image train/validation splitting can put nearly identical frames into both sets and make evaluation look much better than deployment behavior.

## Decision

SyncCart Phase 6 names captures with a session prefix and assigns the entire capture-session group to exactly one of train, validation, or test using a deterministic hash ordering, then assigns whole groups to split quotas. This keeps small datasets from accidentally producing an empty validation split.

The dataset validator additionally reports exact perceptual duplicates crossing split boundaries.

## Consequences

- evaluation is more conservative and more representative;
- each new capture session can be reproduced in the same split;
- very small numbers of sessions may produce uneven split sizes, so several independent capture sessions are required;
- final metrics remain *release measurements*, not proof of production performance.
