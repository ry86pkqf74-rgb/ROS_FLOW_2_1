/**
 * @researchflow/core Ambient Type Declarations
 * Linear Issue: ROS-59
 */

declare module '@researchflow/core' {
  export * from '@researchflow/core/types';
  export * from '@researchflow/core/policy';
  export * from '@researchflow/core/security';
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
  
  // Type exports
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
}

declare module '@researchflow/core/types' {
  export interface User { id: string; email: string; name?: string; role: string; organizationId?: string; }
  export interface Organization { id: string; name: string; slug: string; }
  export interface Project { id: string; name: string; organizationId: string; status: string; }
  export interface Artifact { id: string; projectId: string; type: string; path: string; }
  export interface Run { id: string; projectId: string; status: string; }
  export interface Stage { id: string; runId: string; name: string; status: string; }
  export interface AuditLog { id: string; action: string; userId: string; timestamp: Date; }
  export interface Approval { id: string; artifactId: string; status: string; }
  export interface Policy { id: string; name: string; rules: any; }
  export type GovernanceMode = 'demo' | 'live' | 'audit';
  export type UserRole = 'admin' | 'researcher' | 'reviewer' | 'viewer';
  export const GovernanceMode: { DEMO: 'demo'; LIVE: 'live'; AUDIT: 'audit'; };
  export const UserRole: { ADMIN: 'admin'; RESEARCHER: 'researcher'; REVIEWER: 'reviewer'; VIEWER: 'viewer'; };
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
  export const scanForPHI: (text: string) => Promise<any>;
  export const redact: (text: string, detections: any) => string;
  export const detectPHI: (data: any) => Promise<any[]>;
  export class PHIEngine {
    scan(text: string): Promise<any>;
    redact(text: string): Promise<string>;
  }
}

declare module '@researchflow/phi-engine/*' {
  const mod: any;
  export = mod;
}
