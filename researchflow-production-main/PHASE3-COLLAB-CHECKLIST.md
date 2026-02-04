# PHASE 3B: Collaboration Service Analysis & Deployment Checklist

**Last Updated**: 2026-01-29
**Status**: Analysis Complete, Deployment Ready
**Track**: 3B - Collaboration Service Analysis for ResearchFlow

---

## Executive Summary

This document consolidates findings from Track 3B analysis of the ResearchFlow collaboration service and provides a comprehensive deployment checklist. The collaboration infrastructure uses:

- **Yjs CRDT** for real-time conflict-free collaborative editing
- **WebSocket Server** (y-websocket) on **port 1234**
- **ProseMirror** + **y-prosemirror** for rich text editing
- **PostgreSQL** for persistent Yjs snapshots and updates
- **Redis** for pub/sub and session management (on port 6379, channel 1)
- **Kubernetes** with 2-replica collab deployment

---

## SECTION 1: FINDINGS FROM ANALYSIS

### 1.1 WebSocket Configuration

**Port Configuration**: 1234 (HTTP), 1235 (Health Check)
- Development: `ws://localhost:1234`
- Production: `wss://domain.com/collab` (nginx proxy)

**Environment Variables**:
```bash
PORT=1234                                    # Main WebSocket port
HEALTH_PORT=1235                             # Health endpoint
HOST=0.0.0.0                                 # Bind to all interfaces
NODE_ENV=production                          # Environment mode
REDIS_URL=redis://:password@redis:6379/1    # Redis channel 1
ORCHESTRATOR_URL=http://orchestrator:3001   # Orchestrator service
```

**Files**:
- `/Users/ros/researchflow-production/infrastructure/kubernetes/base/collab-deployment.yaml`
- `/Users/ros/researchflow-production/infrastructure/kubernetes/base/collab-service.yaml`
- `/Users/ros/researchflow-production/docker-compose.yml` (lines 166-200)

### 1.2 Yjs Document Provider

**Technology Stack**:
- Yjs (CRDT library) - conflict-free replicated data types
- y-websocket - WebSocket provider for Yjs
- y-prosemirror - ProseMirror binding for Yjs
- ProseMirror - Rich text editor

**Document Persistence**:
- Tables: `manuscript_yjs_updates`, `manuscript_yjs_snapshots`
- Updates stored as binary Uint8Array
- Snapshots created periodically for recovery
- Clock-based ordering for update application

**Client Configuration** (`CollaborativeEditor.tsx` lines 88-108):
```typescript
// Development: Direct connection to port 1234
const wsUrl = isDev ? 'ws://localhost:1234' : `${wsProtocol}//${host}/collab`;

// Factory: y-websocket provider
new WebsocketProvider(wsUrl, roomName, ydoc, { connect: true });

// Awareness: User presence tracking
awareness.setLocalState({ user, cursor, selection });
```

### 1.3 Real-Time Collaboration Features

**Implemented Features**:
1. **Document Editing** - Yjs CRDT sync (Tasks 76, 79)
2. **Comments & Threads** - Polymorphic anchor system (Tasks 76, 80)
3. **Presence Tracking** - Cursor position, user indicators (embedded in Awareness)
4. **Version Control** - Snapshots at each save (Task 81)
5. **Peer Review** - Rubric-based scoring with blind modes (Task 87)
6. **Task Boards** - Kanban-style task management (Task 88)
7. **Notifications** - Multi-channel delivery (Task 82)
8. **AI Moderation** - Content moderation with PHI escalation (Task 94)
9. **Collaboration Export** - Audit logs with hash chain (Task 93)

**Collaboration Model Architecture**:
```
Client (ProseMirror + Yjs)
    ↓ WebSocket
Collab Server (Yjs sync + awareness)
    ↓ Pub/Sub (Redis)
    ↓ Storage (PostgreSQL)
Audit Chain (Hash-linked events)
```

### 1.4 Kubernetes Deployment Configuration

**File**: `/Users/ros/researchflow-production/infrastructure/kubernetes/base/collab-deployment.yaml`

**Replica Configuration**:
- Replicas: 2 (high availability)
- Port: 1234 (HTTP), 1235 (Health)
- Resources: 250m CPU request, 1000m limit; 128Mi memory request, 512Mi limit
- Health checks: 10s initial delay, 30s liveness, 10s readiness
- APP_MODE: DEMO or LIVE (governance mode)

**Docker Image**: `researchflow/collab:latest`

**Service Type**: ClusterIP (internal service)

### 1.5 Linear Issues Related to Collaboration

**Found Issues**:
- **ROS-27** (Urgent, Backlog): "Infrastructure Validation" - WebSocket collab acceptance criteria
- **ROS-28** (Urgent, In Progress): "Landing Page Fact-Check" - "Real-time collaboration" needs runtime test
- **ROS-33** (High, Done): "Manuscript System" - IRB documentation with manuscript integration

**Key Requirement from ROS-27**:
```
- [ ] WebSocket collab accepts connections
```

### 1.6 Service Integration Points

**Dependencies**:
1. **Redis** - Pub/sub for awareness updates, session management
2. **Orchestrator (port 3001)** - JWT validation, artifact storage
3. **PostgreSQL** - Yjs snapshots and updates storage
4. **Nginx** - Production proxy at `/collab` path

**Clients**:
1. **Web Frontend (port 5173)** - CollaborativeEditor component
2. **Browser WebSocket** - Real-time sync

---

## SECTION 2: DEPLOYMENT CHECKLIST

### Phase 3B.1: Pre-Deployment Validation

- [ ] **Verify Collab Service Docker Build**
  - [ ] Dockerfile exists: `services/collab/Dockerfile`
  - [ ] Dependencies in package.json: `yjs`, `y-websocket`, `y-prosemirror`
  - [ ] Node.js version compatible (v18+)
  - [ ] Build succeeds: `docker build services/collab -t researchflow/collab:latest`

- [ ] **Check WebSocket Port Availability**
  - [ ] Port 1234 is not in use: `lsof -i :1234`
  - [ ] Port 1235 (health) is not in use: `lsof -i :1235`
  - [ ] Firewall allows ports 1234-1235 (both inbound and outbound for WebSocket)
  - [ ] In Kubernetes: NetworkPolicies allow ingress to collab service

- [ ] **Verify Redis Configuration**
  - [ ] Redis running and accessible: `redis-cli -p 6379 ping`
  - [ ] Redis channel 1 selected in config: `REDIS_URL=redis://...@redis:6379/1`
  - [ ] Redis memory limits set: `--maxmemory 2gb`
  - [ ] Persistence enabled: `--appendonly yes`
  - [ ] Password authentication configured (if required)

- [ ] **Database Schema Validation**
  - [ ] Tables exist: `manuscript_yjs_updates`, `manuscript_yjs_snapshots`
  - [ ] Tables have proper indexes on `manuscript_id`, `clock`, `created_at`
  - [ ] Column types verified: `update_data BYTEA`, `yjs_snapshot BYTEA`
  - [ ] Foreign keys pointing to `artifacts` table
  - [ ] Run: `psql -U $POSTGRES_USER -d researchflow_db -c "\dt manuscript_yjs*"`

- [ ] **Environment Variables Complete**
  - [ ] PORT=1234 set
  - [ ] HEALTH_PORT=1235 set
  - [ ] HOST=0.0.0.0 set
  - [ ] NODE_ENV=production set
  - [ ] REDIS_URL configured with authentication
  - [ ] ORCHESTRATOR_URL points to correct service
  - [ ] JWT_SECRET matches orchestrator
  - [ ] LOG_LEVEL set to appropriate level

- [ ] **Orchestrator Service Integration**
  - [ ] Orchestrator running on port 3001
  - [ ] Health check passing: `curl http://localhost:3001/health`
  - [ ] JWT validation endpoint accessible
  - [ ] Artifact endpoints functional

### Phase 3B.2: Network & Connectivity

- [ ] **WebSocket Connection Path**
  - [ ] Development: Direct WS to `localhost:1234` works
  - [ ] Production: Nginx proxy configured at `/collab` path
  - [ ] CORS headers configured: `Access-Control-Allow-Origin`, `Access-Control-Allow-Credentials`
  - [ ] WebSocket upgrade headers present: `Upgrade: websocket`, `Connection: Upgrade`

- [ ] **Docker Network Configuration**
  - [ ] Service on `researchflow-net` network (bridge mode)
  - [ ] Can resolve DNS names: `orchestrator`, `redis`, `postgres`
  - [ ] Inter-service connectivity tested:
    - [ ] `collab` → `orchestrator:3001`
    - [ ] `collab` → `redis:6379`
    - [ ] `collab` → `postgres:5432`

- [ ] **Kubernetes Service Configuration**
  - [ ] Service type: ClusterIP
  - [ ] Ports exposed: 1234 (http), 1235 (health)
  - [ ] Selectors match deployment labels
  - [ ] DNS resolvable: `collab.researchflow.svc.cluster.local`
  - [ ] Test: `kubectl get svc collab -n researchflow`

- [ ] **TLS/SSL Configuration (Production)**
  - [ ] Certificate installed for `domain.com`
  - [ ] Nginx configured to proxy WSS (secure WebSocket)
  - [ ] Certificate valid and not expired
  - [ ] Certificate trusted by browsers

### Phase 3B.3: Yjs Document Persistence

- [ ] **Initial Database Setup**
  - [ ] `manuscript_yjs_updates` table created and indexed
  - [ ] `manuscript_yjs_snapshots` table created (or use versioning table)
  - [ ] Constraints verified: `NOT NULL` on `update_data`
  - [ ] Cleanup triggers for old updates configured

- [ ] **Update Storage & Retrieval**
  - [ ] Test: Insert Yjs update to database
  - [ ] Test: Retrieve updates by manuscript ID
  - [ ] Test: Updates applied in clock order
  - [ ] Verify: Clock field is unique and ordered

- [ ] **Snapshot Management**
  - [ ] Snapshots created on each version save
  - [ ] Snapshots can be restored to reconstruct state
  - [ ] Snapshot file size within reasonable bounds (< 10MB)
  - [ ] Old updates pruned after snapshots created

- [ ] **Recovery Procedure**
  - [ ] Load latest snapshot on server restart
  - [ ] Apply all subsequent updates in order
  - [ ] Final state matches expected document state
  - [ ] No data loss in update stream

- [ ] **Concurrency Handling**
  - [ ] Multiple clients can edit simultaneously
  - [ ] Updates from different clients merge correctly (CRDT property)
  - [ ] No race conditions in update application
  - [ ] Ordering preserved via clock/timestamp

### Phase 3B.4: Real-Time Sync Testing

- [ ] **Basic WebSocket Connection**
  - [ ] Client can connect: `new WebSocket('ws://localhost:1234')`
  - [ ] Connection stays open (no timeouts)
  - [ ] Heartbeat/ping-pong configured (30s interval)
  - [ ] Automatic reconnection on disconnect

- [ ] **Yjs Sync Workflow**
  - [ ] Sync message sent from server on connection
  - [ ] Client receives state vector and applies updates
  - [ ] `synced` flag becomes true after initial sync
  - [ ] Client can create updates and send to server

- [ ] **Multi-Client Synchronization**
  - [ ] 2+ clients connect to same room
  - [ ] Client A makes edit → appears in Client B within 100ms
  - [ ] Client B makes concurrent edit → no conflicts
  - [ ] Both clients show identical final state
  - [ ] Offline client reconnects and syncs correctly

- [ ] **Large Document Handling**
  - [ ] Create manuscript with 50,000+ words
  - [ ] Multiple clients editing different sections
  - [ ] Sync performance acceptable (< 500ms round-trip)
  - [ ] Memory usage stays reasonable (monitor heap)

- [ ] **Network Resilience**
  - [ ] Simulate network disconnect (unplug/kill connection)
  - [ ] Client queues changes locally (buffering)
  - [ ] Connection re-established after 5 minutes
  - [ ] Buffered changes sent and synced
  - [ ] No data loss or corruption

### Phase 3B.5: Awareness & Presence

- [ ] **Presence State Broadcasting**
  - [ ] User connects → presence state published via Redis
  - [ ] Other clients receive presence update
  - [ ] User info includes: id, name, color, cursor position
  - [ ] User info updates on cursor movement

- [ ] **Cursor Position Tracking**
  - [ ] Cursor position sent from client with edits
  - [ ] Cursor position broadcast to other clients
  - [ ] Cursor visualized in correct location (with color)
  - [ ] Cursor label shows user name
  - [ ] Stale cursors removed after 60s inactivity

- [ ] **User Indicators**
  - [ ] User avatars shown in UI (name + color)
  - [ ] Avatar count matches active clients
  - [ ] Avatar removed when user disconnects
  - [ ] Hover tooltip shows user details

- [ ] **Selection Highlighting**
  - [ ] User selection range transmitted
  - [ ] Selection highlighted with user's color
  - [ ] Selection updated as user types
  - [ ] Selection cleared on deselect

### Phase 3B.6: Health Checks & Monitoring

- [ ] **Liveness Probe**
  - [ ] Endpoint: `GET /health` (port 1235)
  - [ ] Response: HTTP 200 with JSON `{"status": "ok"}`
  - [ ] Probe interval: 30 seconds
  - [ ] Failure threshold: 5 consecutive failures
  - [ ] Action: Kill container and restart

- [ ] **Readiness Probe**
  - [ ] Same endpoint as liveness
  - [ ] Probe interval: 10 seconds
  - [ ] Initial delay: 5 seconds
  - [ ] Should be false during initialization, true when ready
  - [ ] Use to route traffic only to ready pods

- [ ] **Metrics Collection**
  - [ ] Export Prometheus metrics on `/metrics` (port 1234)
  - [ ] Metrics: active_connections, documents_synced, updates_persisted
  - [ ] Monitor CPU, memory, network per pod
  - [ ] Alert on connection drops > 10% per minute

- [ ] **Logging Configuration**
  - [ ] Logs to stdout/stderr (container-friendly)
  - [ ] Log level configured: DEBUG, INFO, WARN, ERROR
  - [ ] Structured logs (JSON format recommended)
  - [ ] Log rotation configured (if file-based)
  - [ ] Logs accessible via `kubectl logs collab-xxxxx`

### Phase 3B.7: Security & Authentication

- [ ] **JWT Validation**
  - [ ] Token passed in WebSocket URL or header
  - [ ] Token validated against orchestrator `/verify-token` endpoint
  - [ ] Expired tokens rejected with 401
  - [ ] Invalid signatures rejected
  - [ ] Claims include: user_id, organization_id

- [ ] **Authorization Checks**
  - [ ] User can only edit manuscripts they have access to
  - [ ] PHI access requires correct role
  - [ ] Check organization_id matches
  - [ ] Check artifact permissions before allowing room access

- [ ] **TLS/SSL (Production)**
  - [ ] WSS (secure WebSocket) enforced in production
  - [ ] Certificate pinning if applicable
  - [ ] No unencrypted WS connections to sensitive data
  - [ ] Proxy (nginx) terminates TLS, internal communication can be WS

- [ ] **Rate Limiting**
  - [ ] Updates rate-limited per user (e.g., 100 updates/min)
  - [ ] Connection rate-limited per IP (e.g., 10 connections/min)
  - [ ] If exceeded, return 429 Too Many Requests
  - [ ] Implement token bucket algorithm

- [ ] **Input Validation**
  - [ ] Yjs updates validated as binary format
  - [ ] Malformed updates rejected
  - [ ] Update size limited (e.g., max 1MB)
  - [ ] Room name validated (no directory traversal)

### Phase 3B.8: Data Integrity

- [ ] **Hash Chain Verification**
  - [ ] Collaboration events are hash-chained
  - [ ] Hash computed: SHA-256 of deterministic JSON
  - [ ] Each event includes previousHash
  - [ ] Chain verification script passes: `npm run collab:verify-chain -- $RESEARCH_ID`
  - [ ] Broken links detected and reported

- [ ] **PHI Protection**
  - [ ] Comments scanned for PHI before storage
  - [ ] Yjs content scanned for PHI in LIVE mode
  - [ ] PHI findings block operation (PHI_FAIL)
  - [ ] Admin can override (PHI_OVERRIDE)
  - [ ] Audit log records PHI decisions

- [ ] **Audit Trail Completeness**
  - [ ] Every collaboration event recorded
  - [ ] Events include: timestamp, user_id, action, artifact_id
  - [ ] Metadata captured for context
  - [ ] No events dropped under load
  - [ ] Cleanup policy: 7-year retention for active research

- [ ] **Backup & Recovery**
  - [ ] Database backups include yjs_updates table
  - [ ] Backups tested for restoration
  - [ ] Recovery procedure documented
  - [ ] RTO < 4 hours, RPO < 1 hour

### Phase 3B.9: Performance Optimization

- [ ] **Connection Limits**
  - [ ] Max connections per pod: configured (e.g., 1000)
  - [ ] Memory per connection: < 10KB
  - [ ] Scaling: 2 pods → 2000 total connections
  - [ ] Load balancer distributes connections

- [ ] **Update Batching**
  - [ ] Updates batched for database writes
  - [ ] Batch size: 100-1000 updates
  - [ ] Write frequency: every 5 seconds or batch full
  - [ ] Reduces database load by 10x

- [ ] **Memory Management**
  - [ ] In-memory Yjs documents purged if unused > 30 minutes
  - [ ] Old updates pruned after snapshot taken
  - [ ] Awareness states cleaned up for disconnected users
  - [ ] Monitor heap size; alert if > 80%

- [ ] **Network Optimization**
  - [ ] WebSocket compression enabled
  - [ ] Update size reduction via Yjs binary format
  - [ ] Room name hashing instead of plaintext
  - [ ] Connection pooling for Redis

- [ ] **Database Optimization**
  - [ ] Index on (manuscript_id, clock) for range queries
  - [ ] Partitioning by manuscript_id if > 1B rows
  - [ ] Compression on archived updates
  - [ ] Query plans verified: < 100ms per query

### Phase 3B.10: Deployment Execution

- [ ] **Docker Build & Push**
  ```bash
  docker build -t researchflow/collab:latest services/collab/
  docker push researchflow/collab:latest
  ```

- [ ] **Kubernetes Deployment**
  ```bash
  kubectl apply -f infrastructure/kubernetes/base/collab-deployment.yaml
  kubectl apply -f infrastructure/kubernetes/base/collab-service.yaml
  kubectl rollout status deployment/collab -n researchflow
  ```

- [ ] **Verify Deployment**
  - [ ] Pods running: `kubectl get pods -l app=collab -n researchflow`
  - [ ] Both replicas healthy: `kubectl describe pod collab-xxxxx`
  - [ ] Service active: `kubectl get svc collab -n researchflow`
  - [ ] Health checks passing: `kubectl get events -n researchflow`

- [ ] **Integration Testing**
  - [ ] Frontend loads CollaborativeEditor component
  - [ ] Component attempts WebSocket connection
  - [ ] Connection succeeds (check browser DevTools → Network)
  - [ ] Real-time edits sync across clients
  - [ ] Errors logged to console (should be none)

- [ ] **Smoke Test**
  - [ ] Access ResearchFlow web app: `https://domain.com`
  - [ ] Navigate to manuscript editing
  - [ ] Create new manuscript
  - [ ] Edit text → changes sync in real-time
  - [ ] Multiple browser tabs → both sync together
  - [ ] Refresh page → content persists

- [ ] **Production Rollout**
  - [ ] Blue-green deployment: new pods alongside old
  - [ ] Health checks pass on new pods
  - [ ] Gradually shift traffic: 10% → 50% → 100%
  - [ ] Monitor error rates, latency, connections
  - [ ] Rollback plan ready (revert service selector)

### Phase 3B.11: Documentation & Runbooks

- [ ] **Operator Guides**
  - [ ] How to scale collab service (change replicas)
  - [ ] How to troubleshoot connection issues
  - [ ] How to verify data integrity
  - [ ] How to backup/restore collaboration data

- [ ] **Troubleshooting Guide**
  - [ ] "WebSocket connection failed" → check firewall, port 1234
  - [ ] "Sync conflicts" → Yjs handles; check network logs
  - [ ] "Snapshot restore failed" → verify database, disk space
  - [ ] "High memory usage" → check for memory leaks, restart pods

- [ ] **Disaster Recovery Plan**
  - [ ] Restore from database backup
  - [ ] Recreate Yjs state from updates
  - [ ] Validate hash chain integrity
  - [ ] RTO/RPO targets met

- [ ] **Related Documentation Updated**
  - [ ] docs/COLLABORATION_MODEL.md ✅ (found)
  - [ ] docs/runbooks/collaboration.md ✅ (found)
  - [ ] docs/AUDIT_CHAIN_COLLAB.md ✅ (found)
  - [ ] docs/COLLABORATION_PROVENANCE_DESIGN.md ✅ (found)

---

## SECTION 3: QUICK REFERENCE

### WebSocket Configuration Summary

| Parameter | Value | Location |
|-----------|-------|----------|
| Port | 1234 | docker-compose.yml, collab-deployment.yaml |
| Health Port | 1235 | collab-deployment.yaml |
| Dev URL | ws://localhost:1234 | services/web/src/components/editor/CollaborativeEditor.tsx |
| Prod URL | wss://domain.com/collab | nginx proxy config |
| Provider | y-websocket | services/collab/package.json |
| CRDT | Yjs | services/collab/package.json |
| Editor | ProseMirror | services/web/package.json |

### Deployment Checklist Summary

**Pre-Deployment**: 7 sections, 40+ checks
**Network**: 3 sections, 20+ checks
**Data**: 3 sections, 25+ checks
**Testing**: 4 sections, 35+ checks
**Execution**: 2 sections, 15+ checks
**Docs**: 1 section, 5+ checks

**Total**: ~140 verification points

### Key Files Reference

| Purpose | File Path |
|---------|-----------|
| Kubernetes Deployment | `/Users/ros/researchflow-production/infrastructure/kubernetes/base/collab-deployment.yaml` |
| Kubernetes Service | `/Users/ros/researchflow-production/infrastructure/kubernetes/base/collab-service.yaml` |
| Docker Compose | `/Users/ros/researchflow-production/docker-compose.yml` |
| Frontend Component | `/Users/ros/researchflow-production/services/web/src/components/editor/CollaborativeEditor.tsx` |
| Model Documentation | `/Users/ros/researchflow-production/docs/COLLABORATION_MODEL.md` |
| Runbook | `/Users/ros/researchflow-production/docs/runbooks/collaboration.md` |
| Audit Design | `/Users/ros/researchflow-production/docs/AUDIT_CHAIN_COLLAB.md` |
| Architecture Design | `/Users/ros/researchflow-production/docs/COLLABORATION_PROVENANCE_DESIGN.md` |

---

## SECTION 4: SUCCESS CRITERIA

### Deployment Success Indicators

- [ ] **Connectivity**: WebSocket connections established from browser → collab:1234
- [ ] **Sync**: Changes from one client appear in another within 100ms
- [ ] **Persistence**: Document state survives pod restart
- [ ] **Scale**: Supports 2+ concurrent clients per manuscript
- [ ] **Reliability**: 99.9% uptime over 7 days
- [ ] **Security**: JWT auth verified, PHI protected
- [ ] **Monitoring**: Prometheus metrics exposed and scraped
- [ ] **Audit**: All events hash-chained and verifiable

### Performance Benchmarks

- [ ] WebSocket latency: < 50ms (95th percentile)
- [ ] Update throughput: > 1000 updates/second per pod
- [ ] Memory per connection: < 10KB
- [ ] Database query time: < 100ms
- [ ] CPU usage: < 50% under normal load
- [ ] Network throughput: < 1MB/sec per connection

---

## NEXT STEPS

1. **Review** this checklist with DevOps/Infrastructure team
2. **Execute** Phase 3B.1-11 in sequence
3. **Record** completion status for each check
4. **Escalate** blockers immediately
5. **Update** this document as findings emerge
6. **Archive** in deployment runbook after go-live

---

**Questions?** Contact: Engineering Team Lead
**Escalation Path**: Infrastructure → Architecture → C-Suite
**Status Board**: Link to Linear ROS-27, ROS-28, ROS-33