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
  export const topics: any;
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
  export type Topic = any;
  export type InsertTopic = any;
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
  export class RegexPhiScanner {
    scan(text: string): any;
    redact(text: string): string;
    hasPhi(text: string): boolean;
  }
}

declare module '@researchflow/phi-engine/*' {
  const mod: any;
  export = mod;
}
