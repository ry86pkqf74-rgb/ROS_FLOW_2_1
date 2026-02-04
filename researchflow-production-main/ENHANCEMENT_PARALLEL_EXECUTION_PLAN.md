# ResearchFlow Enhancement - Parallel Execution Plan

## Executive Summary: Comprehensive Repository Analysis

### Current State Assessment

| Layer | Files | LOC | Completion | Key Gaps |
|-------|-------|-----|------------|----------|
| **Python Worker** | 457 | 132,033 | 85% | SHAP missing, real diagnostics mock, no AutoML |
| **Orchestrator** | 100+ routes | ~50,000 | 60% | AI integration placeholders, Pandoc incomplete |
| **Frontend** | 21 stages | ~35,000 | 75% | No Yjs collab, editor placeholders |

### Critical Findings

**Python Worker Strengths:**
- ✅ Real statistical backend (statsmodels, scipy, lifelines)
- ✅ Comprehensive LangGraph + ChromaDB RAG infrastructure
- ✅ Clinical data extraction with PHI scanning
- ✅ 20-stage pipeline fully wired

**Python Worker Gaps:**
- ❌ SHAP/Model Explainability not implemented
- ❌ Diagnostics are mock-generated even with real coefficients
- ❌ No automated variable selection algorithms
- ❌ Cross-validation framework incomplete
- ❌ Plotly underutilized (matplotlib only)

**Orchestrator Gaps:**
- ❌ AI refinement endpoints return placeholders
- ❌ Pandoc export framework incomplete
- ❌ Real-time presence (cursors) not implemented
- ❌ Audit trail query API not exposed
- ❌ Statistical explanation routes missing

**Frontend Gaps:**
- ❌ No Yjs collaborative editing integration
- ❌ Editor toolbar has placeholder handlers
- ❌ Chart preview uses callbacks (no actual Recharts)
- ❌ Statistical diagnostics visualization missing

---

## Enhancement Areas (From User Requirements)

1. **AI-Driven Statistical Analysis Selection** - AutoML, knowledge graphs, hybrid mode
2. **Automated Variable Selection** - SHAP, RAG-enhanced, collaborative tagging
3. **Live Manuscript Editing** - Git-like versioning, Yjs real-time, AI loops
4. **Figure/Table Generation** - Interactive builder, AI suggestions, versioned linking
5. **Statistical Reasoning Explanation** - Audit trails, dashboards, NL summaries

---

# PHASE 1: Statistical Intelligence & Variable Selection
*Focus: Backend AI/ML infrastructure*

---

## CODEX Prompt - Phase 1

```
You are working on ResearchFlow-Production at /Users/lhglosser/researchflow-production

TASK: Implement SHAP integration and AutoML model selection in Python worker

FILES TO CREATE/MODIFY:

1. services/worker/requirements.txt
   Add:
   ```
   shap>=0.43.0
   scikit-learn>=1.3.0
   tpot>=0.12.0
   ```

2. services/worker/src/ml/model_selector.py (NEW - 400+ lines)
   ```python
   """
   AutoML Model Selection with Multi-Model Evaluation
   
   Features:
   - TPOT/Auto-sklearn integration for automated model selection
   - Multi-model comparison (parametric vs non-parametric)
   - AIC/BIC ranking framework
   - Feature metadata-driven model scoring
   """
   
   from typing import Dict, List, Optional, Tuple
   from dataclasses import dataclass
   from enum import Enum
   import numpy as np
   import pandas as pd
   
   # Graceful imports
   try:
       from tpot import TPOTClassifier, TPOTRegressor
       TPOT_AVAILABLE = True
   except ImportError:
       TPOT_AVAILABLE = False
   
   try:
       import shap
       SHAP_AVAILABLE = True
   except ImportError:
       SHAP_AVAILABLE = False
   
   class ModelFamily(Enum):
       LINEAR = "linear"
       LOGISTIC = "logistic"
       TREE_BASED = "tree_based"
       ENSEMBLE = "ensemble"
       NONPARAMETRIC = "nonparametric"
       BAYESIAN = "bayesian"
   
   @dataclass
   class ModelCandidate:
       name: str
       family: ModelFamily
       aic: float
       bic: float
       cv_score: float
       assumptions_met: Dict[str, bool]
       recommended: bool
       rationale: str
   
   class AutoModelSelector:
       """Automated model selection with explainability."""
       
       def __init__(self, max_time_mins: int = 5, cv_folds: int = 5):
           self.max_time_mins = max_time_mins
           self.cv_folds = cv_folds
           self.candidates: List[ModelCandidate] = []
       
       def analyze_data_characteristics(self, df: pd.DataFrame, target: str) -> Dict:
           """Analyze dataset to inform model selection."""
           # Distribution analysis, sample size, feature types
           pass
       
       def evaluate_model_families(
           self, 
           X: pd.DataFrame, 
           y: pd.Series,
           problem_type: str  # "classification" or "regression"
       ) -> List[ModelCandidate]:
           """Evaluate multiple model families and rank by AIC/BIC."""
           pass
       
       def get_shap_explanations(
           self, 
           model, 
           X: pd.DataFrame
       ) -> Dict[str, np.ndarray]:
           """Generate SHAP values for model interpretability."""
           if not SHAP_AVAILABLE:
               return {"error": "SHAP not available"}
           
           explainer = shap.Explainer(model, X)
           shap_values = explainer(X)
           return {
               "values": shap_values.values,
               "base_values": shap_values.base_values,
               "feature_names": list(X.columns),
               "feature_importance": np.abs(shap_values.values).mean(0)
           }
       
       def generate_selection_rationale(self) -> str:
           """Generate human-readable model selection rationale."""
           pass
   ```

3. services/worker/src/ml/variable_selector.py (NEW - 350+ lines)
   ```python
   """
   Automated Variable Selection with Explainability
   
   Features:
   - SHAP-based feature importance ranking
   - LASSO/Elastic Net regularization selection
   - Recursive Feature Elimination (RFE)
   - VIF-based multicollinearity detection
   - Domain knowledge integration via RAG
   """
   
   class VariableSelector:
       def select_by_shap(self, model, X, threshold=0.01): pass
       def select_by_lasso(self, X, y, alpha=1.0): pass
       def select_by_rfe(self, estimator, X, y, n_features=10): pass
       def detect_multicollinearity(self, X, vif_threshold=5.0): pass
       def get_selection_explanation(self) -> Dict: pass
   ```

4. services/worker/src/workflow_engine/stages/stage_07_stats.py
   MODIFY: Integrate ModelSelector and VariableSelector
   - Add SHAP explanations to output
   - Add model selection rationale
   - Replace mock diagnostics with real computation

VERIFY: Run `pytest services/worker/tests/ml/` after implementation

COMMIT: "feat(worker): implement SHAP integration and AutoML model selection"
```

---

## CURSOR Prompt - Phase 1

```
You are working on ResearchFlow-Production at /Users/lhglosser/researchflow-production

TASK: Implement knowledge graph integration for statistical method recommendation

FILES TO CREATE/MODIFY:

1. services/worker/src/knowledge/stats_knowledge_graph.py (NEW - 500+ lines)
   ```python
   """
   Statistical Methods Knowledge Graph
   
   Links study types to recommended analyses using domain knowledge.
   Integrates with LangChain for semantic queries.
   """
   
   from typing import Dict, List, Optional
   from dataclasses import dataclass
   from enum import Enum
   
   class StudyType(Enum):
       RCT = "randomized_controlled_trial"
       COHORT = "cohort_study"
       CASE_CONTROL = "case_control"
       CROSS_SECTIONAL = "cross_sectional"
       META_ANALYSIS = "meta_analysis"
       OBSERVATIONAL = "observational"
   
   class OutcomeType(Enum):
       BINARY = "binary"
       CONTINUOUS = "continuous"
       TIME_TO_EVENT = "time_to_event"
       COUNT = "count"
       ORDINAL = "ordinal"
   
   @dataclass
   class MethodRecommendation:
       method: str
       rationale: str
       assumptions: List[str]
       alternatives: List[str]
       guidelines: List[str]  # CONSORT, STROBE, etc.
       confidence: float
   
   class StatisticalKnowledgeGraph:
       """Knowledge graph for statistical method recommendations."""
       
       # Core mappings
       STUDY_METHOD_MAP = {
           (StudyType.RCT, OutcomeType.BINARY): [
               MethodRecommendation(
                   method="logistic_regression",
                   rationale="Standard for binary outcomes in RCTs",
                   assumptions=["independence", "linearity_in_logit"],
                   alternatives=["fisher_exact", "chi_square"],
                   guidelines=["CONSORT"],
                   confidence=0.95
               ),
               # ... more recommendations
           ],
           (StudyType.RCT, OutcomeType.CONTINUOUS): [
               MethodRecommendation(
                   method="ancova",
                   rationale="Controls for baseline in continuous RCT outcomes",
                   assumptions=["normality", "homoscedasticity", "linearity"],
                   alternatives=["t_test", "mann_whitney"],
                   guidelines=["CONSORT"],
                   confidence=0.90
               ),
           ],
           (StudyType.COHORT, OutcomeType.TIME_TO_EVENT): [
               MethodRecommendation(
                   method="cox_proportional_hazards",
                   rationale="Standard for survival analysis in cohort studies",
                   assumptions=["proportional_hazards", "censoring_independence"],
                   alternatives=["kaplan_meier", "accelerated_failure_time"],
                   guidelines=["STROBE"],
                   confidence=0.92
               ),
           ],
           # ... comprehensive mappings for all combinations
       }
       
       def recommend_methods(
           self,
           study_type: StudyType,
           outcome_type: OutcomeType,
           sample_size: int,
           has_confounders: bool,
           is_clustered: bool
       ) -> List[MethodRecommendation]:
           """Get ranked method recommendations."""
           pass
       
       def explain_recommendation(
           self,
           method: str,
           context: Dict
       ) -> str:
           """Generate natural language explanation."""
           pass
       
       def get_assumption_tests(self, method: str) -> List[Dict]:
           """Get required assumption tests for a method."""
           pass
   ```

2. services/worker/src/workflow_engine/stages/stage_06_analysis.py
   MODIFY: Integrate knowledge graph for EDA recommendations
   - Query knowledge graph based on study type detection
   - Add method recommendations to output

3. services/orchestrator/src/routes/statistical-recommendations.ts (NEW)
   Create API endpoint for statistical method recommendations:
   - GET /api/analysis/recommendations
   - POST /api/analysis/explain-method

VERIFY: Run stage_06 and stage_07 tests

COMMIT: "feat(worker): implement statistical knowledge graph for method recommendations"
```

---

## COMPOSIO Prompt - Phase 1

```
You are working on ResearchFlow-Production at /Users/lhglosser/researchflow-production

TASK: Implement collaborative variable tagging and RAG-enhanced selection

FILES TO CREATE/MODIFY:

1. services/orchestrator/src/routes/variable-selection.ts (NEW - 300+ lines)
   ```typescript
   /**
    * Variable Selection API
    * 
    * Features:
    * - Collaborative variable tagging (primary/secondary/confounder)
    * - Real-time voting on variable inclusion
    * - RAG-enhanced literature-based suggestions
    * - WebSocket notifications for tag updates
    */
   
   import { Router } from 'express';
   import { z } from 'zod';
   import { requireAuth, requireRole } from '../middleware/auth';
   
   const router = Router();
   
   // Variable tag schema
   const variableTagSchema = z.object({
     variableId: z.string().uuid(),
     datasetId: z.string().uuid(),
     tag: z.enum(['primary', 'secondary', 'confounder', 'excluded', 'candidate']),
     rationale: z.string().optional(),
     votedBy: z.array(z.string().uuid()).optional(),
   });
   
   // GET /api/datasets/:datasetId/variables - List variables with tags
   router.get('/datasets/:datasetId/variables', requireAuth, async (req, res) => {
     // Return variables with collaborative tags and vote counts
   });
   
   // POST /api/datasets/:datasetId/variables/:variableId/tag - Tag a variable
   router.post('/datasets/:datasetId/variables/:variableId/tag', 
     requireAuth, requireRole(['RESEARCHER']), async (req, res) => {
     // Add/update tag with user attribution
   });
   
   // POST /api/datasets/:datasetId/variables/:variableId/vote - Vote on variable
   router.post('/datasets/:datasetId/variables/:variableId/vote',
     requireAuth, async (req, res) => {
     // Record vote for/against inclusion
   });
   
   // GET /api/datasets/:datasetId/variables/suggestions - RAG suggestions
   router.get('/datasets/:datasetId/variables/suggestions',
     requireAuth, async (req, res) => {
     // Query vector store for literature-based suggestions
   });
   
   export default router;
   ```

2. services/orchestrator/src/services/variableSelectionService.ts (NEW)
   - RAG integration for literature-based variable suggestions
   - Consensus voting logic with conflict resolution
   - Linear/Slack notification integration stubs

3. infrastructure/docker/postgres/migrations/017_variable_tags.sql (NEW)
   ```sql
   CREATE TABLE variable_tags (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     dataset_id UUID NOT NULL REFERENCES datasets(id),
     variable_name VARCHAR(255) NOT NULL,
     tag VARCHAR(50) NOT NULL CHECK (tag IN ('primary', 'secondary', 'confounder', 'excluded', 'candidate')),
     rationale TEXT,
     created_by UUID NOT NULL REFERENCES users(id),
     created_at TIMESTAMPTZ DEFAULT NOW(),
     UNIQUE(dataset_id, variable_name, created_by)
   );
   
   CREATE TABLE variable_votes (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     dataset_id UUID NOT NULL REFERENCES datasets(id),
     variable_name VARCHAR(255) NOT NULL,
     vote_type VARCHAR(20) NOT NULL CHECK (vote_type IN ('include', 'exclude', 'abstain')),
     voted_by UUID NOT NULL REFERENCES users(id),
     voted_at TIMESTAMPTZ DEFAULT NOW(),
     UNIQUE(dataset_id, variable_name, voted_by)
   );
   
   CREATE INDEX idx_variable_tags_dataset ON variable_tags(dataset_id);
   CREATE INDEX idx_variable_votes_dataset ON variable_votes(dataset_id);
   ```

4. services/orchestrator/src/index.ts
   Register variable-selection routes at /api/variables

VERIFY: Run migration and test endpoints

COMMIT: "feat(orchestrator): implement collaborative variable tagging and voting"
```

---

# PHASE 2: Manuscript Editing & Real-Time Collaboration
*Focus: Yjs integration, version control, AI editing loops*

---

## CODEX Prompt - Phase 2

```
You are working on ResearchFlow-Production at /Users/lhglosser/researchflow-production

TASK: Implement Git-like branching and AI-assisted editing loops for manuscripts

FILES TO CREATE/MODIFY:

1. services/orchestrator/src/services/manuscriptVersionService.ts (NEW - 400+ lines)
   ```typescript
   /**
    * Git-Like Manuscript Version Control
    * 
    * Features:
    * - Branch creation from any version
    * - Three-way merge with conflict detection
    * - Diff generation with semantic awareness
    * - AI-suggested improvements per branch
    */
   
   interface ManuscriptBranch {
     id: string;
     name: string;
     baseVersionId: string;
     headVersionId: string;
     createdBy: string;
     createdAt: Date;
     status: 'active' | 'merged' | 'abandoned';
   }
   
   interface MergeResult {
     success: boolean;
     conflicts: ConflictBlock[];
     mergedContent?: string;
     newVersionId?: string;
   }
   
   class ManuscriptVersionService {
     async createBranch(manuscriptId: string, name: string, fromVersionId: string): Promise<ManuscriptBranch>;
     async mergeBranch(branchId: string, targetBranch: string, strategy: 'ours' | 'theirs' | 'manual'): Promise<MergeResult>;
     async diffVersions(v1: string, v2: string): Promise<DiffResult>;
     async getVersionHistory(manuscriptId: string, branch?: string): Promise<VersionNode[]>;
     async revertToVersion(manuscriptId: string, versionId: string): Promise<string>;
   }
   ```

2. services/orchestrator/src/services/aiEditingService.ts (NEW - 350+ lines)
   ```typescript
   /**
    * AI-Assisted Editing Loops
    * 
    * Features:
    * - Iterative refinement with feedback-to-RAG loops
    * - Section-specific AI improvements
    * - Style consistency checking
    * - Citation suggestion integration
    */
   
   interface EditingSuggestion {
     sectionId: string;
     originalText: string;
     suggestedText: string;
     rationale: string;
     confidence: number;
     type: 'grammar' | 'clarity' | 'style' | 'citation' | 'content';
   }
   
   class AIEditingService {
     async generateSuggestions(manuscriptId: string, sectionId: string): Promise<EditingSuggestion[]>;
     async applyWithFeedback(suggestionId: string, feedback: 'accept' | 'reject' | 'modify'): Promise<void>;
     async runIterativeRefinement(manuscriptId: string, maxIterations: number): Promise<RefinementResult>;
   }
   ```

3. services/orchestrator/src/routes/manuscript-branches.ts
   ENHANCE existing branch routes:
   - Add POST /api/manuscripts/:id/branches/:branchId/merge
   - Add GET /api/manuscripts/:id/branches/:branchId/diff
   - Add POST /api/manuscripts/:id/ai-refine with iteration control

VERIFY: Run manuscript route tests

COMMIT: "feat(orchestrator): implement Git-like versioning and AI editing loops"
```

---

## CURSOR Prompt - Phase 2

```
You are working on ResearchFlow-Production at /Users/lhglosser/researchflow-production

TASK: Integrate Yjs for real-time collaborative manuscript editing

FILES TO CREATE/MODIFY:

1. services/web/src/components/editor/CollaborativeEditor.tsx (NEW - 600+ lines)
   ```tsx
   /**
    * Yjs-Powered Collaborative Editor
    * 
    * Features:
    * - Real-time multi-user editing with CRDT
    * - Cursor presence indicators
    * - Selection range synchronization
    * - Offline-first with IndexedDB persistence
    * - WebSocket reconnection handling
    */
   
   import React, { useEffect, useRef, useState } from 'react';
   import * as Y from 'yjs';
   import { WebsocketProvider } from 'y-websocket';
   import { IndexeddbPersistence } from 'y-indexeddb';
   import { Awareness } from 'y-protocols/awareness';
   
   interface CollaborativeEditorProps {
     manuscriptId: string;
     sectionId: string;
     userId: string;
     userName: string;
     userColor: string;
     onContentChange?: (content: string) => void;
     onPresenceChange?: (users: UserPresence[]) => void;
   }
   
   interface UserPresence {
     id: string;
     name: string;
     color: string;
     cursor?: { line: number; ch: number };
     selection?: { anchor: Position; head: Position };
   }
   
   export const CollaborativeEditor: React.FC<CollaborativeEditorProps> = ({
     manuscriptId,
     sectionId,
     userId,
     userName,
     userColor,
     onContentChange,
     onPresenceChange,
   }) => {
     const ydocRef = useRef<Y.Doc | null>(null);
     const providerRef = useRef<WebsocketProvider | null>(null);
     const [isConnected, setIsConnected] = useState(false);
     const [activeUsers, setActiveUsers] = useState<UserPresence[]>([]);
     
     useEffect(() => {
       // Initialize Yjs document
       const ydoc = new Y.Doc();
       ydocRef.current = ydoc;
       
       // Setup WebSocket provider
       const wsProvider = new WebsocketProvider(
         `${process.env.NEXT_PUBLIC_WS_URL}/collaboration`,
         `manuscript-${manuscriptId}-${sectionId}`,
         ydoc
       );
       providerRef.current = wsProvider;
       
       // Setup IndexedDB persistence for offline
       const indexeddbProvider = new IndexeddbPersistence(
         `manuscript-${manuscriptId}`,
         ydoc
       );
       
       // Setup awareness for presence
       wsProvider.awareness.setLocalStateField('user', {
         id: userId,
         name: userName,
         color: userColor,
       });
       
       // Handle awareness updates
       wsProvider.awareness.on('change', () => {
         const states = wsProvider.awareness.getStates();
         const users: UserPresence[] = [];
         states.forEach((state, clientId) => {
           if (state.user) {
             users.push({
               ...state.user,
               cursor: state.cursor,
               selection: state.selection,
             });
           }
         });
         setActiveUsers(users);
         onPresenceChange?.(users);
       });
       
       // Handle connection status
       wsProvider.on('status', ({ status }) => {
         setIsConnected(status === 'connected');
       });
       
       return () => {
         wsProvider.destroy();
         ydoc.destroy();
       };
     }, [manuscriptId, sectionId, userId]);
     
     // Render editor with presence indicators
     return (
       <div className="collaborative-editor">
         <PresenceBar users={activeUsers} />
         <ConnectionStatus connected={isConnected} />
         <EditorContent ydoc={ydocRef.current} />
       </div>
     );
   };
   ```

2. services/web/src/components/editor/PresenceIndicator.tsx (NEW)
   - User avatar badges with colors
   - Cursor position tooltips
   - Selection highlighting

3. services/web/src/hooks/use-collaborative-editing.ts (NEW)
   - Custom hook for Yjs integration
   - Offline sync management
   - Conflict resolution helpers

4. services/web/package.json
   Add dependencies:
   ```json
   "yjs": "^13.6.0",
   "y-websocket": "^1.5.0",
   "y-indexeddb": "^9.0.0",
   "y-protocols": "^1.0.0"
   ```

VERIFY: Run `npm run build` in services/web

COMMIT: "feat(web): implement Yjs collaborative editor with presence indicators"
```

---

## COMPOSIO Prompt - Phase 2

```
You are working on ResearchFlow-Production at /Users/lhglosser/researchflow-production

TASK: Enhance WebSocket server for real-time presence and implement notification hooks

FILES TO MODIFY:

1. services/orchestrator/src/collaboration/websocket-server.ts
   ENHANCE with:
   ```typescript
   /**
    * Enhanced WebSocket Collaboration Server
    * 
    * New Features:
    * - Cursor position broadcasting
    * - Selection range synchronization
    * - Typing indicators
    * - User join/leave notifications
    * - Heartbeat-based presence timeout
    */
   
   interface CursorUpdate {
     userId: string;
     line: number;
     ch: number;
     sectionId: string;
   }
   
   interface SelectionUpdate {
     userId: string;
     anchor: { line: number; ch: number };
     head: { line: number; ch: number };
     sectionId: string;
   }
   
   // Add message handlers for:
   // - 'cursor:update' - Broadcast cursor positions
   // - 'selection:update' - Broadcast selection ranges
   // - 'typing:start' / 'typing:stop' - Typing indicators
   // - 'presence:heartbeat' - Keep-alive with 30s timeout
   ```

2. services/orchestrator/src/collaboration/notification-service.ts (NEW - 250+ lines)
   ```typescript
   /**
    * Notification Service for Collaboration Events
    * 
    * Integrations:
    * - Slack webhook notifications
    * - Email digest generation
    * - Linear task creation
    * - In-app notification queue
    */
   
   class NotificationService {
     async notifySlack(channel: string, message: CollabEvent): Promise<void>;
     async sendEmailDigest(userId: string, events: CollabEvent[]): Promise<void>;
     async createLinearTask(event: HandoffEvent): Promise<string>;
     async queueInAppNotification(userId: string, notification: Notification): Promise<void>;
   }
   ```

3. services/orchestrator/src/routes/notifications.ts (NEW)
   - GET /api/notifications - List user notifications
   - POST /api/notifications/:id/read - Mark as read
   - POST /api/notifications/preferences - Update preferences

4. infrastructure/docker/postgres/migrations/018_notifications.sql
   ```sql
   CREATE TABLE notifications (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     user_id UUID NOT NULL REFERENCES users(id),
     type VARCHAR(50) NOT NULL,
     title VARCHAR(255) NOT NULL,
     body TEXT,
     link VARCHAR(500),
     read_at TIMESTAMPTZ,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   
   CREATE TABLE notification_preferences (
     user_id UUID PRIMARY KEY REFERENCES users(id),
     email_digest BOOLEAN DEFAULT true,
     slack_mentions BOOLEAN DEFAULT true,
     in_app BOOLEAN DEFAULT true
   );
   ```

VERIFY: Test WebSocket connections and notification delivery

COMMIT: "feat(orchestrator): enhance WebSocket presence and add notification service"
```

---

# PHASE 3: Visualization, Explanation & Deployment
*Focus: Interactive charts, audit dashboards, export pipelines*

---

## CODEX Prompt - Phase 3

```
You are working on ResearchFlow-Production at /Users/lhglosser/researchflow-production

TASK: Implement comprehensive statistical explanation and audit trail system

FILES TO CREATE/MODIFY:

1. services/worker/src/explanation/statistical_rationale.py (NEW - 500+ lines)
   ```python
   """
   Statistical Rationale Generator
   
   Features:
   - Auto-generated methodology sections for manuscripts
   - Decision tree documentation
   - Assumption test narratives
   - Natural language summaries via LLM
   """
   
   from dataclasses import dataclass
   from typing import Dict, List, Optional
   import logging
   
   @dataclass
   class StatisticalDecision:
       decision_type: str  # model_selection, variable_selection, test_choice
       chosen_option: str
       alternatives_considered: List[str]
       rationale: str
       evidence: Dict[str, any]  # test statistics, p-values, etc.
       timestamp: str
       user_id: Optional[str]
   
   @dataclass 
   class MethodologySection:
       title: str
       content: str
       citations: List[str]
       assumptions_stated: List[str]
       limitations_noted: List[str]
   
   class StatisticalRationaleGenerator:
       """Generates human-readable statistical methodology documentation."""
       
       def __init__(self, llm_client=None):
           self.llm = llm_client
           self.decisions: List[StatisticalDecision] = []
       
       def record_decision(self, decision: StatisticalDecision) -> None:
           """Record a statistical decision for audit trail."""
           self.decisions.append(decision)
       
       def generate_methodology_section(
           self,
           analysis_type: str,
           model_config: Dict,
           test_results: Dict
       ) -> MethodologySection:
           """Generate manuscript-ready methodology section."""
           pass
       
       def generate_decision_tree_diagram(self) -> str:
           """Generate Mermaid diagram of decision flow."""
           pass
       
       def generate_natural_language_summary(
           self,
           detail_level: str = "brief"  # brief, detailed, technical
       ) -> str:
           """Use LLM to generate readable summary."""
           pass
       
       def export_audit_trail(self, format: str = "json") -> str:
           """Export decision log for compliance."""
           pass
   ```

2. services/orchestrator/src/routes/statistical-audit.ts (NEW - 200+ lines)
   ```typescript
   /**
    * Statistical Audit Trail API
    * 
    * Endpoints:
    * - GET /api/audit/statistical/:analysisId - Get decision trail
    * - GET /api/audit/statistical/:analysisId/diagram - Get decision tree
    * - GET /api/audit/statistical/:analysisId/summary - Get NL summary
    * - POST /api/audit/statistical/:analysisId/export - Export for compliance
    */
   
   router.get('/:analysisId', requireAuth, async (req, res) => {
     // Return full decision trail
   });
   
   router.get('/:analysisId/diagram', requireAuth, async (req, res) => {
     // Return Mermaid diagram code
   });
   
   router.get('/:analysisId/summary', requireAuth, async (req, res) => {
     // Generate and return NL summary
   });
   ```

3. services/orchestrator/src/index.ts
   Register statistical-audit routes at /api/audit/statistical

VERIFY: Run audit route tests

COMMIT: "feat: implement statistical rationale generator and audit trail API"
```

---

## CURSOR Prompt - Phase 3

```
You are working on ResearchFlow-Production at /Users/lhglosser/researchflow-production

TASK: Implement interactive visualization builder with Plotly and explanation dashboard

FILES TO CREATE/MODIFY:

1. services/web/src/components/visualization/InteractiveChartBuilder.tsx (NEW - 700+ lines)
   ```tsx
   /**
    * Interactive Chart Builder with Plotly
    * 
    * Features:
    * - Drag-and-drop variable mapping
    * - Real-time preview with Plotly.js
    * - AI-suggested chart types
    * - Export to SVG/PNG/PDF
    * - Accessibility color modes
    */
   
   import React, { useState, useMemo } from 'react';
   import Plot from 'react-plotly.js';
   import { DndContext, DragEndEvent } from '@dnd-kit/core';
   
   interface ChartBuilderProps {
     datasetId: string;
     columns: DataColumn[];
     onSaveChart: (chart: ChartConfig) => Promise<void>;
     onGetAISuggestions: () => Promise<ChartSuggestion[]>;
   }
   
   const CHART_TYPES = [
     { id: 'scatter', name: 'Scatter Plot', icon: ScatterIcon },
     { id: 'line', name: 'Line Chart', icon: LineIcon },
     { id: 'bar', name: 'Bar Chart', icon: BarIcon },
     { id: 'box', name: 'Box Plot', icon: BoxIcon },
     { id: 'histogram', name: 'Histogram', icon: HistogramIcon },
     { id: 'heatmap', name: 'Heatmap', icon: HeatmapIcon },
     { id: 'violin', name: 'Violin Plot', icon: ViolinIcon },
     { id: 'kaplan_meier', name: 'Kaplan-Meier', icon: SurvivalIcon },
   ];
   
   export const InteractiveChartBuilder: React.FC<ChartBuilderProps> = (props) => {
     // State for chart configuration
     const [chartType, setChartType] = useState('scatter');
     const [xAxis, setXAxis] = useState<string | null>(null);
     const [yAxis, setYAxis] = useState<string | null>(null);
     const [colorBy, setColorBy] = useState<string | null>(null);
     const [styleOptions, setStyleOptions] = useState(DEFAULT_STYLE);
     
     // Generate Plotly config from state
     const plotlyData = useMemo(() => {
       return generatePlotlyData(chartType, xAxis, yAxis, colorBy, props.columns);
     }, [chartType, xAxis, yAxis, colorBy]);
     
     return (
       <DndContext onDragEnd={handleDragEnd}>
         <div className="chart-builder grid grid-cols-12 gap-4">
           <div className="col-span-3">
             <VariableList columns={props.columns} />
           </div>
           <div className="col-span-6">
             <Plot data={plotlyData} layout={plotlyLayout} />
           </div>
           <div className="col-span-3">
             <StylePanel options={styleOptions} onChange={setStyleOptions} />
             <ExportPanel onExport={handleExport} />
           </div>
         </div>
       </DndContext>
     );
   };
   ```

2. services/web/src/components/explanation/StatisticalExplanationDashboard.tsx (NEW - 500+ lines)
   ```tsx
   /**
    * Statistical Explanation Dashboard
    * 
    * Features:
    * - Decision tree visualization (Mermaid)
    * - Interactive reasoning viewer
    * - Audit trail timeline
    * - Export for IRB/compliance
    */
   
   interface ExplanationDashboardProps {
     analysisId: string;
   }
   
   export const StatisticalExplanationDashboard: React.FC = ({ analysisId }) => {
     // Fetch audit trail
     const { data: auditTrail } = useQuery(['audit', analysisId], fetchAuditTrail);
     
     return (
       <Tabs defaultValue="decisions">
         <TabsList>
           <TabsTrigger value="decisions">Decisions</TabsTrigger>
           <TabsTrigger value="diagram">Decision Tree</TabsTrigger>
           <TabsTrigger value="methodology">Methodology</TabsTrigger>
           <TabsTrigger value="export">Export</TabsTrigger>
         </TabsList>
         
         <TabsContent value="decisions">
           <DecisionTimeline decisions={auditTrail?.decisions} />
         </TabsContent>
         
         <TabsContent value="diagram">
           <MermaidDiagram code={auditTrail?.diagram} />
         </TabsContent>
         
         <TabsContent value="methodology">
           <MethodologyPreview content={auditTrail?.methodology} />
         </TabsContent>
         
         <TabsContent value="export">
           <ExportOptions analysisId={analysisId} />
         </TabsContent>
       </Tabs>
     );
   };
   ```

3. services/web/package.json
   Add dependencies:
   ```json
   "react-plotly.js": "^2.6.0",
   "plotly.js": "^2.27.0",
   "@dnd-kit/core": "^6.0.0",
   "mermaid": "^10.6.0"
   ```

VERIFY: Run `npm run build` in services/web

COMMIT: "feat(web): implement Plotly chart builder and explanation dashboard"
```

---

## COMPOSIO Prompt - Phase 3

```
You are working on ResearchFlow-Production at /Users/lhglosser/researchflow-production

TASK: Complete export pipeline with Pandoc and deployment verification

FILES TO CREATE/MODIFY:

1. services/worker/src/export/pandoc_export.py (NEW - 400+ lines)
   ```python
   """
   Pandoc Export Pipeline
   
   Features:
   - Multi-format export (PDF, DOCX, LaTeX, HTML)
   - Journal template support
   - Citation style application (CSL)
   - Figure/table embedding
   - PHI redaction in exports
   """
   
   import subprocess
   import tempfile
   from pathlib import Path
   from typing import Dict, List, Optional
   
   class PandocExporter:
       SUPPORTED_FORMATS = ['pdf', 'docx', 'latex', 'html', 'odt', 'epub']
       
       def __init__(self, pandoc_path: str = 'pandoc'):
           self.pandoc = pandoc_path
           self.templates_dir = Path(__file__).parent / 'templates'
       
       def export(
           self,
           content: str,
           output_format: str,
           template: Optional[str] = None,
           csl_style: Optional[str] = None,
           bibliography: Optional[str] = None,
           metadata: Optional[Dict] = None
       ) -> bytes:
           """Export markdown to target format."""
           pass
       
       def embed_figures(self, content: str, figures: List[Dict]) -> str:
           """Embed figure references in markdown."""
           pass
       
       def apply_phi_redaction(self, content: str, phi_patterns: List[str]) -> str:
           """Redact PHI before export."""
           pass
   ```

2. services/orchestrator/src/routes/export.ts
   ENHANCE existing export routes:
   - Integrate with worker Pandoc service
   - Add progress tracking via BullMQ
   - Add figure embedding endpoint

3. .github/workflows/e2e-enhanced.yml (NEW)
   ```yaml
   name: Enhanced E2E Tests
   
   on:
     push:
       branches: [main]
     pull_request:
       branches: [main]
   
   jobs:
     e2e-statistical:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - name: Setup services
           run: docker-compose -f docker-compose.test.yml up -d
         - name: Run statistical pipeline tests
           run: |
             cd services/worker
             pytest tests/integration/test_statistical_pipeline.py -v
         - name: Run visualization tests
           run: |
             cd services/web
             npx playwright test visualization.spec.ts
   
     e2e-collaboration:
       runs-on: ubuntu-latest
       steps:
         - name: Test WebSocket collaboration
           run: |
             cd services/orchestrator
             npm run test:websocket
         - name: Test Yjs sync
           run: |
             cd services/web
             npm run test:collaboration
   ```

4. scripts/verify-enhancement-deployment.sh (NEW)
   ```bash
   #!/bin/bash
   set -e
   
   echo "=== ResearchFlow Enhancement Verification ==="
   
   # 1. Statistical pipeline
   echo "Testing statistical pipeline..."
   curl -f http://localhost:3001/api/analysis/recommendations?studyType=rct
   
   # 2. Variable selection
   echo "Testing variable selection..."
   curl -f http://localhost:3001/api/variables/datasets/test/suggestions
   
   # 3. Collaboration WebSocket
   echo "Testing WebSocket..."
   wscat -c ws://localhost:3001/collaboration -x '{"type":"ping"}' --timeout 5
   
   # 4. Export pipeline
   echo "Testing export..."
   curl -f http://localhost:3001/api/export/formats
   
   # 5. Audit trail
   echo "Testing audit trail..."
   curl -f http://localhost:3001/api/audit/statistical/test/summary
   
   echo "=== All enhancement checks passed! ==="
   ```

VERIFY: Run verification script

COMMIT: "ci: complete export pipeline and enhanced E2E tests"
```

---

# Verification Checklist

## Phase 1 Verification
- [ ] SHAP integration working: `pytest tests/ml/test_shap.py`
- [ ] AutoML model selection: `pytest tests/ml/test_model_selector.py`
- [ ] Knowledge graph queries: `curl /api/analysis/recommendations`
- [ ] Variable tagging API: `curl /api/variables/datasets/test`
- [ ] Migration applied: `psql -c "SELECT * FROM variable_tags LIMIT 1"`

## Phase 2 Verification
- [ ] Yjs package installed: `npm list yjs` in services/web
- [ ] WebSocket presence working: Connect two clients, verify cursor sync
- [ ] Branch merge working: `curl -X POST /api/manuscripts/test/branches/feature/merge`
- [ ] Notifications table exists: `psql -c "SELECT * FROM notifications LIMIT 1"`

## Phase 3 Verification
- [ ] Plotly charts render: Load Stage 08, create chart
- [ ] Mermaid diagrams render: Load explanation dashboard
- [ ] Pandoc export: `curl -X POST /api/export/manuscripts/test -d '{"format":"pdf"}'`
- [ ] E2E tests pass: `npx playwright test`
- [ ] Deployment script passes: `./scripts/verify-enhancement-deployment.sh`

---

# Execution Commands Summary

```bash
# Phase 1
pip install shap scikit-learn tpot --break-system-packages
pytest services/worker/tests/ml/
npm test -- --grep "variable-selection"

# Phase 2
cd services/web && npm install yjs y-websocket y-indexeddb
npm run build
docker-compose restart orchestrator

# Phase 3
cd services/worker && pip install pypandoc --break-system-packages
cd services/web && npm install react-plotly.js plotly.js @dnd-kit/core mermaid
./scripts/verify-enhancement-deployment.sh
```

---

**Document Generated**: 2026-02-02
**Repository**: ResearchFlow-Production
**Total Estimated Work**: 25-35 hours across 3 phases
**Priority**: Phase 1 (Statistical Intelligence) → Phase 2 (Collaboration) → Phase 3 (Visualization/Export)
