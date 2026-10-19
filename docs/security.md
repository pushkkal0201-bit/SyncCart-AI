# Security Baseline and Production Gaps

## Implemented controls

- Pydantic request validation;
- environment-based configuration;
- no committed `.env` secrets;
- controlled CORS configuration;
- trusted-host middleware in production mode;
- request correlation IDs;
- security response headers;
- standardized domain errors;
- temporary customer session tokens stored as hashes;
- idempotency keys for mutating flows;
- protected simulator endpoints;
- separate store-operations key;
- separate monitoring key;
- separate Vision ingestion key;
- separate Vision control key;
- database foreign keys / constraints;
- safe Vision event arming and baseline reset.

## Local deployment authentication boundary

The local hackathon release uses separate API keys for store, monitoring, simulator, and Vision boundaries. The same service boundaries can be connected to enterprise identity systems in a retail deployment.

They are **not** a substitute for production workforce identity and authorization.

## Production requirements

Before external deployment:

1. replace static operator keys with workforce SSO / OIDC;
2. implement role-based authorization;
3. move secrets to a managed secrets service;
4. terminate TLS with managed certificates;
5. add rate limiting and abuse controls;
6. centralize audit logs and monitoring;
7. define key rotation and incident response;
8. threat-model camera and edge-device compromise;
9. validate database backup / restore and tenant/store isolation;
10. disable simulator endpoints outside approved non-production environments.

## Repository hygiene

The Git configuration excludes:

- `.env`;
- local databases;
- virtual environments;
- frontend dependencies;
- raw capture datasets;
- model weights;
- generated training output.
