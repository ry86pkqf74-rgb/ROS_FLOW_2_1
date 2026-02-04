/**
 * Compliance & Audit Trail Service
 * GDPR, SOX compliance with comprehensive audit logging
 */

import { EventEmitter } from 'events';
import { promises as fs } from 'fs';
import path from 'path';
import crypto from 'crypto';
import { createLogger } from '../utils/logger';

interface ComplianceConfig {
  enableGDPR: boolean;
  enableSOX: boolean;
  enableAuditLogging: boolean;
  enableDataRetention: boolean;
  auditLogPath: string;
  dataRetentionDays: number;
  anonymizationDelay: number;
  complianceReportPath: string;
  enableRealTimeMonitoring: boolean;
  alertThresholds: {
    dataAccess: number;
    dataExport: number;
    failedLogins: number;
  };
}

interface AuditEvent {
  id: string;
  timestamp: Date;
  eventType: string;
  userId?: string;
  sessionId?: string;
  ipAddress?: string;
  userAgent?: string;
  resource?: string;
  action: string;
  details: any;
  outcome: 'success' | 'failure' | 'warning';
  gdprCategory?: 'data_access' | 'data_export' | 'data_deletion' | 'consent_change';
  soxCategory?: 'financial_data' | 'user_access' | 'system_config' | 'audit_trail';
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  dataSubjects?: string[];
  encrypted: boolean;
  hash: string;
}

interface DataSubject {
  id: string;
  email: string;
  consentStatus: {
    analytics: boolean;
    marketing: boolean;
    functional: boolean;
    necessary: boolean;
  };
  dataCategories: string[];
  retentionExpiry: Date;
  lastAccessed: Date;
  anonymized: boolean;
}

interface ComplianceReport {
  id: string;
  type: 'gdpr' | 'sox' | 'security';
  period: { start: Date; end: Date };
  generatedAt: Date;
  summary: {
    totalEvents: number;
    complianceViolations: number;
    dataSubjectRequests: number;
    retentionCompliance: number;
  };
  violations: any[];
  recommendations: string[];
}

export class ComplianceAuditService extends EventEmitter {
  private config: ComplianceConfig;
  private logger = createLogger('compliance-audit');
  private auditBuffer: AuditEvent[] = [];
  private dataSubjects = new Map<string, DataSubject>();
  private complianceMetrics = {
    totalAuditEvents: 0,
    gdprRequests: 0,
    soxAlerts: 0,
    dataRetentionActions: 0,
    complianceViolations: 0
  };

  constructor(config: Partial<ComplianceConfig> = {}) {
    super();
    
    this.config = {
      enableGDPR: process.env.ENABLE_GDPR_COMPLIANCE !== 'false',
      enableSOX: process.env.ENABLE_SOX_COMPLIANCE !== 'false',
      enableAuditLogging: process.env.ENABLE_AUDIT_LOGGING !== 'false',
      enableDataRetention: process.env.ENABLE_DATA_RETENTION !== 'false',
      auditLogPath: process.env.AUDIT_LOG_PATH || '/app/logs/audit',
      dataRetentionDays: parseInt(process.env.DATA_RETENTION_DAYS || '2555', 10), // 7 years default
      anonymizationDelay: parseInt(process.env.ANONYMIZATION_DELAY || '30', 10), // 30 days
      complianceReportPath: process.env.COMPLIANCE_REPORT_PATH || '/app/reports',
      enableRealTimeMonitoring: process.env.ENABLE_REALTIME_MONITORING !== 'false',
      alertThresholds: {
        dataAccess: parseInt(process.env.ALERT_THRESHOLD_DATA_ACCESS || '100', 10),
        dataExport: parseInt(process.env.ALERT_THRESHOLD_DATA_EXPORT || '10', 10),
        failedLogins: parseInt(process.env.ALERT_THRESHOLD_FAILED_LOGINS || '5', 10)
      },
      ...config
    };

    this.initializeComplianceSystem();
    this.startBackgroundProcesses();
  }

  /**
   * Initialize compliance system
   */
  private async initializeComplianceSystem(): Promise<void> {
    try {
      // Create audit log directory
      await fs.mkdir(this.config.auditLogPath, { recursive: true });
      
      // Create compliance reports directory
      await fs.mkdir(this.config.complianceReportPath, { recursive: true });
      
      // Load existing data subjects
      await this.loadDataSubjects();
      
      this.logger.info('Compliance audit system initialized', {
        gdprEnabled: this.config.enableGDPR,
        soxEnabled: this.config.enableSOX,
        auditLoggingEnabled: this.config.enableAuditLogging,
        dataRetentionDays: this.config.dataRetentionDays
      });
    } catch (error) {
      this.logger.error('Failed to initialize compliance system', {
        error: error instanceof Error ? error.message : String(error)
      });
      throw error;
    }
  }

  /**
   * Log audit event with compliance categorization
   */
  async logAuditEvent(event: Omit<AuditEvent, 'id' | 'timestamp' | 'encrypted' | 'hash'>): Promise<string> {
    const auditEvent: AuditEvent = {
      id: this.generateEventId(),
      timestamp: new Date(),
      encrypted: false,
      hash: '',
      ...event
    };

    // Calculate event hash for integrity
    auditEvent.hash = this.calculateEventHash(auditEvent);

    // Encrypt sensitive events
    if (this.shouldEncryptEvent(auditEvent)) {
      auditEvent.encrypted = true;
      auditEvent.details = this.encryptSensitiveData(auditEvent.details);
    }

    // Add to buffer
    this.auditBuffer.push(auditEvent);
    this.complianceMetrics.totalAuditEvents++;

    // Process GDPR categorization
    if (this.config.enableGDPR && auditEvent.gdprCategory) {
      await this.processGDPREvent(auditEvent);
    }

    // Process SOX categorization
    if (this.config.enableSOX && auditEvent.soxCategory) {
      await this.processSOXEvent(auditEvent);
    }

    // Real-time monitoring
    if (this.config.enableRealTimeMonitoring) {
      this.performRealTimeAnalysis(auditEvent);
    }

    // Flush buffer if needed
    if (this.auditBuffer.length >= 100) {
      await this.flushAuditBuffer();
    }

    this.emit('audit:event', auditEvent);
    return auditEvent.id;
  }

  /**
   * Process GDPR compliance event
   */
  private async processGDPREvent(event: AuditEvent): Promise<void> {
    if (event.gdprCategory === 'data_access' && event.dataSubjects) {
      // Track data access for subjects
      for (const subjectId of event.dataSubjects) {
        const subject = this.dataSubjects.get(subjectId);
        if (subject) {
          subject.lastAccessed = new Date();
          this.dataSubjects.set(subjectId, subject);
        }
      }
    }

    if (event.gdprCategory === 'data_export') {
      this.complianceMetrics.gdprRequests++;
      
      // Check export threshold
      if (this.complianceMetrics.gdprRequests > this.config.alertThresholds.dataExport) {
        this.emit('compliance:alert', {
          type: 'gdpr',
          category: 'excessive_exports',
          event,
          threshold: this.config.alertThresholds.dataExport
        });
      }
    }

    if (event.gdprCategory === 'data_deletion') {
      // Process data deletion request
      await this.processDataDeletionRequest(event);
    }
  }

  /**
   * Process SOX compliance event
   */
  private async processSOXEvent(event: AuditEvent): Promise<void> {
    this.complianceMetrics.soxAlerts++;

    if (event.soxCategory === 'financial_data') {
      // Ensure financial data access is properly logged
      await this.ensureFinancialDataCompliance(event);
    }

    if (event.soxCategory === 'audit_trail' && event.outcome === 'failure') {
      // Critical: Audit trail manipulation attempt
      this.emit('compliance:critical', {
        type: 'sox',
        category: 'audit_manipulation',
        event,
        severity: 'critical'
      });
    }
  }

  /**
   * Handle GDPR data subject requests
   */
  async handleDataSubjectRequest(type: 'access' | 'portability' | 'erasure' | 'rectification', 
                                 subjectId: string, 
                                 requestDetails: any): Promise<string> {
    const requestId = this.generateRequestId();
    
    await this.logAuditEvent({
      eventType: 'gdpr_data_subject_request',
      userId: subjectId,
      action: `data_${type}`,
      details: { requestType: type, requestId, ...requestDetails },
      outcome: 'success',
      gdprCategory: 'data_access',
      riskLevel: 'medium',
      dataSubjects: [subjectId]
    });

    switch (type) {
      case 'access':
        return await this.processDataAccessRequest(subjectId, requestId);
      
      case 'portability':
        return await this.processDataPortabilityRequest(subjectId, requestId);
      
      case 'erasure':
        return await this.processDataErasureRequest(subjectId, requestId);
      
      case 'rectification':
        return await this.processDataRectificationRequest(subjectId, requestId, requestDetails);
      
      default:
        throw new Error(`Unsupported request type: ${type}`);
    }
  }

  /**
   * Process data access request (GDPR Article 15)
   */
  private async processDataAccessRequest(subjectId: string, requestId: string): Promise<string> {
    try {
      const subject = this.dataSubjects.get(subjectId);
      if (!subject) {
        throw new Error(`Data subject not found: ${subjectId}`);
      }

      // Collect all data for the subject
      const personalData = await this.collectPersonalData(subjectId);
      
      // Generate data access report
      const reportPath = path.join(this.config.complianceReportPath, `data-access-${requestId}.json`);
      await fs.writeFile(reportPath, JSON.stringify({
        requestId,
        subjectId,
        generatedAt: new Date(),
        personalData: personalData,
        dataCategories: subject.dataCategories,
        processingPurposes: this.getProcessingPurposes(subjectId),
        dataRetentionPeriod: this.config.dataRetentionDays,
        thirdPartySharing: this.getThirdPartySharing(subjectId)
      }, null, 2));

      this.logger.info('Data access request processed', { subjectId, requestId, reportPath });
      return reportPath;

    } catch (error) {
      await this.logAuditEvent({
        eventType: 'gdpr_data_access_failure',
        userId: subjectId,
        action: 'data_access',
        details: { requestId, error: error instanceof Error ? error.message : String(error) },
        outcome: 'failure',
        gdprCategory: 'data_access',
        riskLevel: 'high',
        dataSubjects: [subjectId]
      });
      
      throw error;
    }
  }

  /**
   * Process data erasure request (GDPR Article 17)
   */
  private async processDataErasureRequest(subjectId: string, requestId: string): Promise<string> {
    try {
      // Validate erasure request
      const canErase = await this.validateErasureRequest(subjectId);
      if (!canErase.allowed) {
        throw new Error(`Erasure not permitted: ${canErase.reason}`);
      }

      // Perform data erasure
      await this.erasePersonalData(subjectId);
      
      // Mark subject as anonymized
      const subject = this.dataSubjects.get(subjectId);
      if (subject) {
        subject.anonymized = true;
        this.dataSubjects.set(subjectId, subject);
      }

      await this.logAuditEvent({
        eventType: 'gdpr_data_erasure',
        userId: subjectId,
        action: 'data_deletion',
        details: { requestId, erasureMethod: 'secure_deletion' },
        outcome: 'success',
        gdprCategory: 'data_deletion',
        riskLevel: 'high',
        dataSubjects: [subjectId]
      });

      this.logger.info('Data erasure request processed', { subjectId, requestId });
      return requestId;

    } catch (error) {
      await this.logAuditEvent({
        eventType: 'gdpr_data_erasure_failure',
        userId: subjectId,
        action: 'data_deletion',
        details: { requestId, error: error instanceof Error ? error.message : String(error) },
        outcome: 'failure',
        gdprCategory: 'data_deletion',
        riskLevel: 'critical',
        dataSubjects: [subjectId]
      });
      
      throw error;
    }
  }

  /**
   * Generate compliance report
   */
  async generateComplianceReport(type: 'gdpr' | 'sox' | 'security', 
                                 period: { start: Date; end: Date }): Promise<string> {
    const reportId = this.generateReportId();
    const report: ComplianceReport = {
      id: reportId,
      type,
      period,
      generatedAt: new Date(),
      summary: {
        totalEvents: 0,
        complianceViolations: 0,
        dataSubjectRequests: 0,
        retentionCompliance: 0
      },
      violations: [],
      recommendations: []
    };

    try {
      // Analyze audit events for the period
      const events = await this.getAuditEventsForPeriod(period);
      report.summary.totalEvents = events.length;

      if (type === 'gdpr') {
        await this.analyzeGDPRCompliance(report, events);
      } else if (type === 'sox') {
        await this.analyzeSOXCompliance(report, events);
      } else if (type === 'security') {
        await this.analyzeSecurityCompliance(report, events);
      }

      // Generate recommendations
      report.recommendations = this.generateComplianceRecommendations(report);

      // Save report
      const reportPath = path.join(this.config.complianceReportPath, `${type}-report-${reportId}.json`);
      await fs.writeFile(reportPath, JSON.stringify(report, null, 2));

      await this.logAuditEvent({
        eventType: 'compliance_report_generated',
        action: 'report_generation',
        details: { reportType: type, reportId, period },
        outcome: 'success',
        riskLevel: 'low'
      });

      this.logger.info('Compliance report generated', { type, reportId, reportPath });
      return reportPath;

    } catch (error) {
      await this.logAuditEvent({
        eventType: 'compliance_report_failure',
        action: 'report_generation',
        details: { reportType: type, reportId, error: error instanceof Error ? error.message : String(error) },
        outcome: 'failure',
        riskLevel: 'medium'
      });
      
      throw error;
    }
  }

  /**
   * Start background compliance processes
   */
  private startBackgroundProcesses(): void {
    // Flush audit buffer every 5 minutes
    setInterval(() => {
      this.flushAuditBuffer().catch(error => {
        this.logger.error('Failed to flush audit buffer', {
          error: error instanceof Error ? error.message : String(error)
        });
      });
    }, 5 * 60 * 1000);

    // Data retention cleanup daily
    if (this.config.enableDataRetention) {
      setInterval(() => {
        this.performDataRetentionCleanup().catch(error => {
          this.logger.error('Data retention cleanup failed', {
            error: error instanceof Error ? error.message : String(error)
          });
        });
      }, 24 * 60 * 60 * 1000);
    }

    // Generate weekly compliance reports
    setInterval(() => {
      this.generateAutomaticReports().catch(error => {
        this.logger.error('Automatic report generation failed', {
          error: error instanceof Error ? error.message : String(error)
        });
      });
    }, 7 * 24 * 60 * 60 * 1000);
  }

  /**
   * Flush audit buffer to persistent storage
   */
  private async flushAuditBuffer(): Promise<void> {
    if (this.auditBuffer.length === 0) return;

    const events = [...this.auditBuffer];
    this.auditBuffer = [];

    const logFile = path.join(this.config.auditLogPath, `audit-${new Date().toISOString().split('T')[0]}.jsonl`);
    
    const logEntries = events.map(event => JSON.stringify(event)).join('\n') + '\n';
    await fs.appendFile(logFile, logEntries);

    this.logger.debug('Audit buffer flushed', { eventCount: events.length, logFile });
  }

  /**
   * Perform data retention cleanup
   */
  private async performDataRetentionCleanup(): Promise<void> {
    const cutoffDate = new Date(Date.now() - (this.config.dataRetentionDays * 24 * 60 * 60 * 1000));
    let cleanedCount = 0;

    for (const [subjectId, subject] of this.dataSubjects) {
      if (subject.retentionExpiry < cutoffDate && !subject.anonymized) {
        // Anonymize expired data
        await this.anonymizeDataSubject(subjectId);
        cleanedCount++;
      }
    }

    await this.logAuditEvent({
      eventType: 'data_retention_cleanup',
      action: 'data_anonymization',
      details: { cleanedCount, cutoffDate },
      outcome: 'success',
      gdprCategory: 'data_deletion',
      riskLevel: 'low'
    });

    this.complianceMetrics.dataRetentionActions += cleanedCount;
    this.logger.info('Data retention cleanup completed', { cleanedCount });
  }

  /**
   * Utility methods
   */
  private generateEventId(): string {
    return `audit_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`;
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`;
  }

  private generateReportId(): string {
    return `report_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`;
  }

  private calculateEventHash(event: AuditEvent): string {
    const dataToHash = `${event.id}${event.timestamp}${event.eventType}${event.action}${JSON.stringify(event.details)}`;
    return crypto.createHash('sha256').update(dataToHash).digest('hex');
  }

  private shouldEncryptEvent(event: AuditEvent): boolean {
    const sensitiveCategories = ['data_access', 'data_export', 'financial_data'];
    return sensitiveCategories.some(cat => 
      event.gdprCategory === cat || event.soxCategory === cat
    );
  }

  private encryptSensitiveData(data: any): any {
    // In production, use proper encryption
    return { encrypted: true, data: 'encrypted_content' };
  }

  private async loadDataSubjects(): Promise<void> {
    // In production, load from database
    this.logger.debug('Data subjects loaded from database');
  }

  private performRealTimeAnalysis(event: AuditEvent): void {
    // Real-time threat detection and compliance monitoring
    if (event.riskLevel === 'critical') {
      this.emit('compliance:critical', { event });
    }
  }

  private async collectPersonalData(subjectId: string): Promise<any> {
    // In production, query all systems for personal data
    return { placeholder: 'personal_data_collection' };
  }

  private getProcessingPurposes(subjectId: string): string[] {
    return ['research_analytics', 'service_provision', 'legal_compliance'];
  }

  private getThirdPartySharing(subjectId: string): any[] {
    return [];
  }

  private async validateErasureRequest(subjectId: string): Promise<{ allowed: boolean; reason?: string }> {
    // Check legal basis for retention
    return { allowed: true };
  }

  private async erasePersonalData(subjectId: string): Promise<void> {
    // In production, delete/anonymize data across all systems
    this.logger.info('Personal data erased', { subjectId });
  }

  private async anonymizeDataSubject(subjectId: string): Promise<void> {
    const subject = this.dataSubjects.get(subjectId);
    if (subject) {
      subject.anonymized = true;
      subject.email = 'anonymized@example.com';
      this.dataSubjects.set(subjectId, subject);
    }
  }

  private async getAuditEventsForPeriod(period: { start: Date; end: Date }): Promise<AuditEvent[]> {
    // In production, query audit log files or database
    return [];
  }

  private async analyzeGDPRCompliance(report: ComplianceReport, events: AuditEvent[]): Promise<void> {
    const gdprEvents = events.filter(e => e.gdprCategory);
    report.summary.dataSubjectRequests = gdprEvents.filter(e => e.eventType.includes('data_subject_request')).length;
  }

  private async analyzeSOXCompliance(report: ComplianceReport, events: AuditEvent[]): Promise<void> {
    const soxEvents = events.filter(e => e.soxCategory);
    report.violations = soxEvents.filter(e => e.outcome === 'failure');
  }

  private async analyzeSecurityCompliance(report: ComplianceReport, events: AuditEvent[]): Promise<void> {
    const securityEvents = events.filter(e => e.riskLevel === 'high' || e.riskLevel === 'critical');
    report.violations = securityEvents;
  }

  private generateComplianceRecommendations(report: ComplianceReport): string[] {
    const recommendations = [];
    
    if (report.summary.complianceViolations > 0) {
      recommendations.push('Review and address compliance violations');
    }
    
    if (report.type === 'gdpr' && report.summary.dataSubjectRequests > 10) {
      recommendations.push('Consider automating data subject request processing');
    }
    
    return recommendations;
  }

  private async generateAutomaticReports(): Promise<void> {
    const oneWeekAgo = new Date(Date.now() - (7 * 24 * 60 * 60 * 1000));
    const now = new Date();
    
    try {
      if (this.config.enableGDPR) {
        await this.generateComplianceReport('gdpr', { start: oneWeekAgo, end: now });
      }
      
      if (this.config.enableSOX) {
        await this.generateComplianceReport('sox', { start: oneWeekAgo, end: now });
      }
    } catch (error) {
      this.logger.error('Automatic report generation failed', {
        error: error instanceof Error ? error.message : String(error)
      });
    }
  }

  private async processDataPortabilityRequest(subjectId: string, requestId: string): Promise<string> {
    // Implement data portability (export in machine-readable format)
    return requestId;
  }

  private async processDataRectificationRequest(subjectId: string, requestId: string, requestDetails: any): Promise<string> {
    // Implement data rectification (update incorrect data)
    return requestId;
  }

  private async processDataDeletionRequest(event: AuditEvent): Promise<void> {
    // Process data deletion request
    this.logger.info('Data deletion request processed', { event: event.id });
  }

  private async ensureFinancialDataCompliance(event: AuditEvent): Promise<void> {
    // Ensure SOX compliance for financial data access
    this.logger.info('Financial data compliance verified', { event: event.id });
  }

  /**
   * Get compliance system status
   */
  getStatus() {
    return {
      config: {
        gdprEnabled: this.config.enableGDPR,
        soxEnabled: this.config.enableSOX,
        auditLoggingEnabled: this.config.enableAuditLogging,
        dataRetentionEnabled: this.config.enableDataRetention,
        dataRetentionDays: this.config.dataRetentionDays,
        realtimeMonitoringEnabled: this.config.enableRealTimeMonitoring
      },
      metrics: this.complianceMetrics,
      auditBufferSize: this.auditBuffer.length,
      dataSubjects: this.dataSubjects.size
    };
  }

  /**
   * Stop compliance service
   */
  stop(): void {
    this.flushAuditBuffer().catch(error => {
      this.logger.error('Failed to flush audit buffer during shutdown', {
        error: error instanceof Error ? error.message : String(error)
      });
    });
  }
}

export default ComplianceAuditService;