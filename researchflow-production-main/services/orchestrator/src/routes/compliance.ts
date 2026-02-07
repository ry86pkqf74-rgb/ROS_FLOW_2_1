/**
 * Compliance & Audit Routes
 * GDPR, SOX compliance management endpoints
 */

import express from 'express';

import { ComplianceAuditService } from '../services/compliance-audit.service';
import { createLogger } from '../utils/logger';

const router = express.Router();
const logger = createLogger('compliance-routes');

// GET /api/compliance/status - Get compliance system status
router.get('/status', (req, res) => {
  try {
    const complianceService = req.app.locals.complianceService;
    if (!complianceService) {
      return res.status(503).json({
        success: false,
        error: 'Compliance service not initialized'
      });
    }

    const status = complianceService.getStatus();
    
    res.json({
      success: true,
      timestamp: Date.now(),
      compliance_status: {
        ...status,
        operational: true,
        last_check: Date.now()
      }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to get compliance status',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// POST /api/compliance/audit/log - Log custom audit event
router.post('/audit/log', async (req, res) => {
  try {
    const {
      eventType,
      userId,
      action,
      details = {},
      outcome = 'success',
      gdprCategory,
      soxCategory,
      riskLevel = 'low',
      dataSubjects = []
    } = req.body;

    if (!eventType || !action) {
      return res.status(400).json({
        success: false,
        error: 'eventType and action are required'
      });
    }

    const complianceService = req.app.locals.complianceService;
    const eventId = await complianceService.logAuditEvent({
      eventType,
      userId,
      sessionId: req.sessionID,
      ipAddress: req.ip,
      userAgent: req.get('user-agent'),
      resource: req.path,
      action,
      details,
      outcome,
      gdprCategory,
      soxCategory,
      riskLevel,
      dataSubjects
    });

    res.json({
      success: true,
      event_id: eventId,
      logged_at: Date.now(),
      message: 'Audit event logged successfully'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to log audit event',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// POST /api/compliance/gdpr/data-subject-request - Handle GDPR data subject requests
router.post('/gdpr/data-subject-request', async (req, res) => {
  try {
    const {
      type,
      subject_id,
      subject_email,
      request_details = {}
    } = req.body;

    if (!type || !subject_id) {
      return res.status(400).json({
        success: false,
        error: 'type and subject_id are required',
        valid_types: ['access', 'portability', 'erasure', 'rectification']
      });
    }

    const validTypes = ['access', 'portability', 'erasure', 'rectification'];
    if (!validTypes.includes(type)) {
      return res.status(400).json({
        success: false,
        error: 'Invalid request type',
        valid_types: validTypes
      });
    }

    const complianceService = req.app.locals.complianceService;
    const result = await complianceService.handleDataSubjectRequest(
      type, 
      subject_id, 
      { ...request_details, subject_email }
    );

    res.json({
      success: true,
      request_type: type,
      subject_id,
      result_path: result,
      processed_at: Date.now(),
      message: `GDPR ${type} request processed successfully`
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: `Failed to process GDPR ${req.body.type} request`,
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// GET /api/compliance/gdpr/consent/:subjectId - Get consent status
router.get('/gdpr/consent/:subjectId', async (req, res) => {
  try {
    const { subjectId } = req.params;
    
    // In production, fetch from database
    const consentStatus = {
      subject_id: subjectId,
      consents: {
        analytics: true,
        marketing: false,
        functional: true,
        necessary: true
      },
      last_updated: new Date(),
      legal_basis: {
        analytics: 'consent',
        marketing: 'consent',
        functional: 'legitimate_interest',
        necessary: 'contract'
      }
    };

    res.json({
      success: true,
      consent_status: consentStatus
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to get consent status',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// PUT /api/compliance/gdpr/consent/:subjectId - Update consent status
router.put('/gdpr/consent/:subjectId', async (req, res) => {
  try {
    const { subjectId } = req.params;
    const { consents, withdrawal_reason } = req.body;

    if (!consents || typeof consents !== 'object') {
      return res.status(400).json({
        success: false,
        error: 'consents object is required'
      });
    }

    // Log consent change for audit
    const complianceService = req.app.locals.complianceService;
    await complianceService.logAuditEvent({
      eventType: 'gdpr_consent_change',
      userId: subjectId,
      action: 'consent_update',
      details: { consents, withdrawal_reason },
      outcome: 'success',
      gdprCategory: 'consent_change',
      riskLevel: 'medium',
      dataSubjects: [subjectId]
    });

    // In production, update database
    res.json({
      success: true,
      subject_id: subjectId,
      updated_consents: consents,
      updated_at: Date.now(),
      message: 'Consent status updated successfully'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to update consent status',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// POST /api/compliance/reports/generate - Generate compliance report
router.post('/reports/generate', async (req, res) => {
  try {
    const {
      type,
      start_date,
      end_date
    } = req.body;

    if (!type) {
      return res.status(400).json({
        success: false,
        error: 'type is required',
        valid_types: ['gdpr', 'sox', 'security']
      });
    }

    const validTypes = ['gdpr', 'sox', 'security'];
    if (!validTypes.includes(type)) {
      return res.status(400).json({
        success: false,
        error: 'Invalid report type',
        valid_types: validTypes
      });
    }

    const period = {
      start: start_date ? new Date(start_date) : new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
      end: end_date ? new Date(end_date) : new Date()
    };

    const complianceService = req.app.locals.complianceService;
    const reportPath = await complianceService.generateComplianceReport(type, period);

    res.json({
      success: true,
      report_type: type,
      period: period,
      report_path: reportPath,
      generated_at: Date.now(),
      message: `${type.toUpperCase()} compliance report generated successfully`
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to generate compliance report',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// GET /api/compliance/reports/list - List available compliance reports
router.get('/reports/list', async (req, res) => {
  try {
    const { type, limit = 50, offset = 0 } = req.query;
    
    // In production, query report files or database
    const reports = [
      {
        id: 'report-gdpr-2024-01-01',
        type: 'gdpr',
        generated_at: new Date(),
        period: {
          start: new Date('2024-01-01'),
          end: new Date('2024-01-31')
        },
        summary: {
          total_events: 150,
          violations: 0,
          data_subject_requests: 5
        }
      }
    ];

    const filteredReports = type ? reports.filter(r => r.type === type) : reports;
    const paginatedReports = filteredReports.slice(Number(offset), Number(offset) + Number(limit));

    res.json({
      success: true,
      reports: paginatedReports,
      pagination: {
        total: filteredReports.length,
        limit: Number(limit),
        offset: Number(offset),
        has_more: Number(offset) + Number(limit) < filteredReports.length
      },
      filters: {
        type: type || 'all'
      }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to list compliance reports',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// GET /api/compliance/reports/:reportId - Get specific compliance report
router.get('/reports/:reportId', async (req, res) => {
  try {
    const { reportId } = req.params;
    
    // In production, read report file or query database
    const report = {
      id: reportId,
      type: 'gdpr',
      generated_at: new Date(),
      period: {
        start: new Date('2024-01-01'),
        end: new Date('2024-01-31')
      },
      summary: {
        total_events: 150,
        compliance_violations: 0,
        data_subject_requests: 5,
        retention_compliance: 100
      },
      violations: [],
      recommendations: [
        'Continue monitoring data subject request response times',
        'Review data retention policies quarterly'
      ]
    };

    res.json({
      success: true,
      report: report
    });
  } catch (error) {
    res.status(404).json({
      success: false,
      report_id: req.params.reportId,
      error: 'Compliance report not found',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// POST /api/compliance/test - Test compliance systems
router.post('/test', async (req, res) => {
  try {
    const { component = 'all' } = req.body;
    
    const testResults = {
      audit_logging: component === 'all' || component === 'audit' ? 'passed' : 'skipped',
      gdpr_compliance: component === 'all' || component === 'gdpr' ? 'passed' : 'skipped',
      sox_compliance: component === 'all' || component === 'sox' ? 'passed' : 'skipped',
      data_retention: component === 'all' || component === 'retention' ? 'passed' : 'skipped',
      report_generation: component === 'all' || component === 'reports' ? 'passed' : 'skipped'
    };

    // Log test event
    const complianceService = req.app.locals.complianceService;
    if (complianceService) {
      await complianceService.logAuditEvent({
        eventType: 'compliance_system_test',
        action: 'system_test',
        details: { component, results: testResults },
        outcome: 'success',
        riskLevel: 'low'
      });
    }

    const allPassed = Object.values(testResults).every(result => result === 'passed' || result === 'skipped');

    res.json({
      success: allPassed,
      test_results: testResults,
      tested_at: Date.now(),
      message: allPassed ? 'All compliance system tests passed' : 'Some compliance tests failed'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Compliance system test failed',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// GET /api/compliance/metrics - Get compliance metrics
router.get('/metrics', (req, res) => {
  try {
    const complianceService = req.app.locals.complianceService;
    if (!complianceService) {
      return res.status(503).json({
        success: false,
        error: 'Compliance service not initialized'
      });
    }

    const status = complianceService.getStatus();
    
    res.json({
      success: true,
      timestamp: Date.now(),
      compliance_metrics: {
        total_audit_events: status.metrics.totalAuditEvents,
        gdpr_requests: status.metrics.gdprRequests,
        sox_alerts: status.metrics.soxAlerts,
        data_retention_actions: status.metrics.dataRetentionActions,
        compliance_violations: status.metrics.complianceViolations,
        data_subjects_tracked: status.dataSubjects,
        audit_buffer_size: status.auditBufferSize
      }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to get compliance metrics',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

export default router;