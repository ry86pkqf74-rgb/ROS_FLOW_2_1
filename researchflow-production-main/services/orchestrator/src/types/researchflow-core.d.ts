/**
 * @researchflow/core Ambient Type Declarations
 * Linear Issue: ROS-59
 */

declare module '@researchflow/core' {
  export * from '@researchflow/core/types';
  export * from '@researchflow/core/policy';
  export * from '@researchflow/core/security';

  // ── Literature types (fixes TS2305 ×13 in arxiv.ts, pubmed.ts, semantic-scholar.ts, literature.ts) ──

  export type LiteratureProvider = 'pubmed' | 'semantic_scholar' | 'arxiv';

  export interface LiteratureAuthor {
    name: string;
    affiliation?: string;
    orcid?: string;
  }

  export interface LiteratureItem {
    id: string;
    provider: LiteratureProvider;
    title: string;
    abstract?: string;
    authors: LiteratureAuthor[];
    year?: number;
    venue?: string;
    doi?: string;
    pmid?: string;
    pmcid?: string;
    arxivId?: string;
    s2PaperId?: string;
    urls: string[];
    pdfUrl?: string;
    fetchedAt: string;
    keywords?: string[];
    citationCount?: number;
    influentialCitationCount?: number;
    relevanceScore?: number;
    meshTerms?: string[];
    publicationTypes?: string[];
  }

  export interface LiteratureSearchRequest {
    query: string;
    provider?: LiteratureProvider;
    providers?: LiteratureProvider[];
    limit?: number;
    offset?: number;
    yearStart?: number;
    yearEnd?: number;
    publicationTypes?: string[];
    useCache?: boolean;
    cacheTtlSeconds?: number;
  }

  export interface LiteratureSearchResponse {
    items: LiteratureItem[];
    total: number;
    query: string;
    providers: string[];
    cached: boolean;
    searchDurationMs?: number;
    cachedAt?: string;
    providerResults?: Record<string, {
      count: number;
      total: number;
      durationMs?: number;
      error?: string;
    }>;
  }

  // ── RBAC types (fixes TS2305 ×7 in rbac.ts) ──

  export type RoleName = 'VIEWER' | 'RESEARCHER' | 'STEWARD' | 'ADMIN';
  export type Permission = string;

  export const ROLES: {
    readonly VIEWER: 'VIEWER';
    readonly RESEARCHER: 'RESEARCHER';
    readonly STEWARD: 'STEWARD';
    readonly ADMIN: 'ADMIN';
  };

  export const ROLE_CONFIGS: Record<RoleName, {
    can: Permission[];
    level: number;
    description?: string;
  }>;

  export function hasPermission(user: { role: RoleName }, permission: Permission): boolean;
  export function hasMinimumRole(user: { role: RoleName }, requiredRole: RoleName): boolean;

  export class InsufficientPermissionsError extends Error {
    readonly required: Permission | RoleName;
    readonly actual: Permission[] | RoleName;
    readonly operation: string;
    constructor(
      required: Permission | RoleName,
      actual: Permission[] | RoleName,
      operation: string,
    );
  }

  // ── App mode types (fixes TS2305 ×3 in mode-guard.ts, mock-ai-service.ts) ──

  export enum AppMode {
    DEMO = 'DEMO',
    LIVE = 'LIVE',
    STANDBY = 'STANDBY',
  }

  export const MODE_CONFIGS: Record<AppMode, {
    mode: AppMode;
    requiresAuth: boolean;
    allowsRealAI: boolean;
    allowsRealData: boolean;
    allowsExport: boolean;
  }>;
}

declare module '@researchflow/core/schema' {
  export const users: any;
  export const organizations: any;
  export const projects: any;
  export const artifacts: any;
  export const runs: any;
  export const stages: any;
  export const sessions: any;
  export const auditLogs: any;
  export const approvals: any;
  export const policies: any;
  export const analysisPlans: any;
  export const analysisJobs: any;
  export const analysisJobEvents: any;
  export const analysisArtifacts: any;
  export const guidelines: any;
  export const chats: any;
  export const chatMessages: any;
  export const shares: any;
  export const papers: any;
  export const workflows: any;
  export const workflowVersions: any;
  export const workflowTemplates: any;
  export const workflowPolicies: any;
  export const workflowRunCheckpoints: any;

  // Additional table exports for orchestrator
  export const researchProjects: any;
  export const userRoles: any;
  export const approvalGates: any;  // separate table from approvals (both exist in schema)
  export const approvalAuditEntries: any;
  export const phiIncidents: any;
  export const handoffPacks: any;
  export const conversations: any;
  export const messages: any;
  export const artifactVersions: any;
  export const artifactComparisons: any;
  export const fileUploads: any;
  export const researchSessions: any;

  // TS2305 cluster fix (PR150): tables added after initial .d.ts authoring
  export const aiInvocations: any;
  export const aiOutputFeedback: any;
  export const artifactEmbeddings: any;
  export const artifactShares: any;
  export const claimEvidenceLinks: any;
  export const claims: any;
  export const comments: any;
  export const datasets: any;
  export const docAnchors: any;
  export const docKitItems: any;
  export const docKits: any;
  export const ethicsApprovals: any;
  export const experimentAssignments: any;
  export const experiments: any;
  export const featureFlags: any;
  export const governanceConfig: any;
  export const ideaScorecards: any;
  export const ideas: any;
  export const orgInvites: any;
  export const orgMemberships: any;
  export const orgSubscriptions: any;
  export const phiScanResults: any;
  export const rebuttalResponses: any;
  export const researchBriefs: any;
  export const reviewSessions: any;
  export const reviewerPoints: any;
  export const statisticalPlans: any;
  export const submissionPackages: any;
  export const submissionTargets: any;
  export const submissions: any;
  export const topicBriefs: any;
  export const tutorialAssets: any;
  export const userConsents: any;
  export const userOnboarding: any;
  export const venues: any;

  // TS2724 cluster fix: tables & schemas missing from initial .d.ts
  export const topics: any;
  export const analyticsEvents: any;
  export const artifactEdges: any;
  export const insertArtifactSchema: any;
  export const insertArtifactVersionSchema: any;
  export const insertArtifactComparisonSchema: any;

  // TS2305 cluster fix (PR150): const arrays / enums
  export const GOVERNANCE_MODES: readonly string[];
  export const ANALYTICS_EVENT_NAMES: readonly string[];

  // Type exports (original)
  export type Topic = any;
  export type InsertTopic = any;
  export type UpsertUser = any;
  export type Artifact = any;
  export type InsertArtifact = any;
  export type ArtifactVersion = any;
  export type InsertArtifactVersion = any;
  export type ArtifactComparison = any;
  export type InsertArtifactComparison = any;
  export type ResearchProject = any;
  export type InsertResearchProject = any;
  export type UserRoleRecord = any;
  export type InsertUserRole = any;
  export type ApprovalGateRecord = any;
  export type InsertApprovalGate = any;
  export type ApprovalAuditEntryRecord = any;
  export type InsertApprovalAuditEntry = any;
  export type AuditLog = any;
  export type InsertAuditLog = any;
  export type PhiIncident = any;
  export type InsertPhiIncident = any;
  export type HandoffPackRecord = any;
  export type InsertHandoffPack = any;
  export type Conversation = any;
  export type InsertConversation = any;
  export type Message = any;
  export type InsertMessage = any;
  export type FileUpload = any;
  export type InsertFileUpload = any;
  export type ResearchSession = any;
  export type InsertResearchSession = any;

  // TS2724 cluster fix: type exports missing from initial .d.ts
  export type OrganizationRecord = any;
  export type StatisticalPlanRecord = any;
  export type ResearchBriefRecord = any;
  export type InsertTopicBrief = any;

  // TS2305 cluster fix (PR150): type exports added after initial .d.ts authoring
  export type AnalyticsEventName = string;
  export type DocAnchor = any;
  export type DocKit = any;
  export type DocKitItem = any;
  export type Experiment = any;
  export type FeatureFlag = any;
  export type GovernanceMode = string;
  export type Idea = any;
  export type IdeaScorecard = any;
  export type InsertIdea = any;
  export type OrgMembershipRecord = any;
  export type TopicBrief = any;
  export type Venue = any;
}

declare module '@researchflow/core/types' {
  export interface User { id: string; email: string; name?: string; role: UserRole; organizationId?: string; }
  export interface Organization { id: string; name: string; slug: string; }
  export interface Project { id: string; name: string; organizationId: string; status: string; }
  export interface Artifact { id: string; projectId: string; type: string; path: string; }
  export interface Run { id: string; projectId: string; status: string; }
  export interface Stage { id: string; runId: string; name: string; status: string; }
  export interface AuditLog { id: string; action: string; userId: string; timestamp: Date; }
  export interface Approval { id: string; artifactId: string; status: string; }
  export interface Policy { id: string; name: string; rules: any; }
  export type GovernanceMode = 'demo' | 'live' | 'audit';
  export type UserRole = 'ADMIN' | 'RESEARCHER' | 'STEWARD' | 'VIEWER';
  export const GovernanceMode: { DEMO: 'demo'; LIVE: 'live'; AUDIT: 'audit'; };
  export const UserRole: { ADMIN: 'ADMIN'; RESEARCHER: 'RESEARCHER'; STEWARD: 'STEWARD'; VIEWER: 'VIEWER'; };
}

declare module '@researchflow/core/types/*' {
  const mod: any;
  export = mod;
}

declare module '@researchflow/core/policy' {
  export class PolicyEngine {
    constructor(config?: any);
    evaluate(context: any): Promise<any>;
    validate(action: string, resource: any, user: any): Promise<boolean>;
  }
  export const createPolicyEngine: (config?: any) => PolicyEngine;
}

declare module '@researchflow/core/security' {
  export const sanitizePath: (path: string) => string;
  export const validateFile: (file: any) => boolean;
  export const handleZip: (zipPath: string) => Promise<any>;
  export class SecurityError extends Error {}
  export class PathTraversalError extends SecurityError {}
}

declare module '@researchflow/core/config' {
  export const config: any;
  export const getConfig: () => any;
  export const envSchema: any;
}

declare module '@researchflow/core/events' {
  export const EventTypes: any;
  export const emitEvent: (type: string, payload: any) => void;
}

declare module '@researchflow/core/services' {
  export const insightsBus: any;
  export class InsightsBus {
    publish(event: any): Promise<void>;
    subscribe(handler: any): void;
  }
}

declare module '@packages/core' {
  export * from '@researchflow/core';
}

declare module '@packages/core/*' {
  const mod: any;
  export = mod;
}

declare module '@researchflow/phi-engine' {
  export interface PhiFinding {
    type: 'SSN' | 'MRN' | 'DOB' | 'PHONE' | 'EMAIL' | 'NAME' | 'ADDRESS'
         | 'ZIP_CODE' | 'IP_ADDRESS' | 'URL' | 'ACCOUNT' | 'HEALTH_PLAN'
         | 'LICENSE' | 'DEVICE_ID' | 'AGE_OVER_89' | 'UNKNOWN';
    value: string;
    startIndex: number;
    endIndex: number;
    confidence: number;
  }

  export interface PhiScanner {
    scan(text: string): PhiFinding[];
    redact(text: string): string;
    hasPhi(text: string): boolean;
  }

  export type RiskLevel = 'none' | 'low' | 'medium' | 'high';
  export type ScanContext = 'upload' | 'export' | 'llm';

  export type PatternDefinition = {
    type: PhiFinding['type'];
    regex: RegExp;
    description: string;
    hipaaCategory: string;
    baseConfidence: number;
  };

  export const scan: (text: string) => PhiFinding[];
  export const redact: (text: string) => string;
  export const hasPhi: (text: string) => boolean;
  export class RegexPhiScanner implements PhiScanner {
    scan(text: string): PhiFinding[];
    redact(text: string): string;
    hasPhi(text: string): boolean;
  }
  export const PHI_PATTERNS: PatternDefinition[];

  export const scrubLog: (text: string) => string;
  export const scrubObject: (obj: any) => any;
  export const containsPhi: (text: string) => boolean;
  export const getPhiStats: (text: string) => Record<string, number>;

  export type SnippetScanResult = any;
  export type BatchScanResult = any;
  export type SnippetScanOptions = any;
  export type SnippetInput = any;
  export class PhiSnippetScanner {
    scanSnippet(input: SnippetInput, options?: SnippetScanOptions): SnippetScanResult;
    scanBatch(inputs: SnippetInput[], options?: SnippetScanOptions): BatchScanResult;
  }
  export const createSnippetScanner: () => PhiSnippetScanner;

  export const createScrubbedLogger: (logger?: any, options?: any) => any;
  export const installConsoleScrubber: () => void;
  export const removeConsoleScrubber: () => void;
  export const isConsoleScrubberInstalled: () => boolean;

  export const PHI_ENGINE_VERSION: "1.0.0";

  export const phiEngine: {
    scan(text: string): Promise<{ hasPHI: boolean }>;
  };
}

declare module '@researchflow/phi-engine/*' {
  const mod: any;
  export = mod;
}
