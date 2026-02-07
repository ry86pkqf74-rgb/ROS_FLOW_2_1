/**
 * Checklists API Routes (ROS-112 - Track C)
 *
 * API endpoints for checklist management, including:
 * - TRIPOD+AI checklist for AI/ML model reporting
 * - CONSORT-AI checklist for AI-integrated trials
 *
 * Provides validation, progress tracking, and export functionality
 */

import fs from 'fs';
import path from 'path';

import { Router, Request, Response } from 'express';
import yaml from 'js-yaml';
import { v4 as uuid } from 'uuid';

// Types for checklist management
interface ChecklistItem {
  id: string;
  category: string;
  subcategory: string;
  description: string;
  required: boolean;
  evidence_types?: string[];
  validation_rules?: string[];
  guidance?: string;
  cross_reference?: {
    tripod_item?: string;
    consort_item?: string;
    rationale?: string;
  };
}

interface ChecklistItemCompletion {
  itemId: string;
  status: 'not_started' | 'in_progress' | 'completed' | 'skipped';
  completedAt?: string;
  evidence?: string[];
  notes?: string;
  validationPassed?: boolean;
  validationErrors?: string[];
}

interface ChecklistResponse {
  id: string;
  type: 'tripod_ai' | 'consort_ai';
  checklistId: string;
  researchId?: string;
  version: string;
  title: string;
  description: string;
  totalItems: number;
  items: ChecklistItem[];
  completions: ChecklistItemCompletion[];
  createdAt: string;
  updatedAt: string;
  submittedAt?: string;
}

interface ChecklistProgressResponse {
  checklistId: string;
  type: 'tripod_ai' | 'consort_ai';
  totalItems: number;
  completedItems: number;
  inProgressItems: number;
  notStartedItems: number;
  progressPercentage: number;
  byCategory: Record<string, {
    total: number;
    completed: number;
    percentage: number;
  }>;
}

interface ChecklistValidationResponse {
  valid: boolean;
  completeness: number;
  errors: string[];
  warnings: string[];
  criticalIssues: string[];
  itemValidations: Record<string, {
    passed: boolean;
    errors: string[];
  }>;
}

// Helper function to load checklist YAML files
function loadChecklist(checklistType: 'tripod_ai' | 'consort_ai'): any {
  try {
    const filename = checklistType === 'tripod_ai'
      ? 'tripod-ai-checklist.yaml'
      : 'consort-ai-checklist.yaml';

    const filePath = path.join(process.cwd(), 'config', filename);

    if (!fs.existsSync(filePath)) {
      throw new Error(`Checklist file not found: ${filename}`);
    }

    const fileContent = fs.readFileSync(filePath, 'utf-8');
    const checklist = yaml.load(fileContent) as any;

    return checklist;
  } catch (error) {
    throw new Error(`Failed to load checklist: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

// Helper function to extract items from loaded checklist
function extractChecklistItems(checklistData: any, checklistType: 'tripod_ai' | 'consort_ai'): ChecklistItem[] {
  const rootKey = checklistType === 'tripod_ai' ? 'tripod_ai_checklist' : 'consort_ai_checklist';
  const checklist = checklistData[rootKey];

  if (!checklist) {
    throw new Error(`Invalid checklist structure: missing ${rootKey}`);
  }

  const items: ChecklistItem[] = [];

  if (Array.isArray(checklist.items)) {
    items.push(...checklist.items);
  }

  // For CONSORT-AI, also extract items from sections
  if (checklistType === 'consort_ai' && Array.isArray(checklist.sections)) {
    checklist.sections.forEach((section: any) => {
      if (Array.isArray(section.items)) {
        items.push(...section.items);
      }
    });
  }

  return items;
}

// Helper function to validate checklist item against rules
function validateChecklistItem(
  item: ChecklistItem,
  completion: ChecklistItemCompletion
): { passed: boolean; errors: string[] } {
  const errors: string[] = [];

  // Check if required item is completed
  if (item.required && completion.status !== 'completed') {
    errors.push(`Required item ${item.id} is not completed`);
  }

  // Validate against rules if provided
  if (completion.status === 'completed' && item.validation_rules) {
    item.validation_rules.forEach((rule: string) => {
      // Parse common validation patterns
      if (rule.includes('Must') && !completion.evidence?.length) {
        errors.push(`Item ${item.id}: ${rule} - No evidence provided`);
      }
    });
  }

  return {
    passed: errors.length === 0,
    errors
  };
}

const router = Router();

/**
 * List available checklists
 * GET /api/checklists
 */
router.get('/', (req: Request, res: Response) => {
  try {
    const checklists = [
      {
        type: 'tripod_ai',
        name: 'TRIPOD+AI Checklist',
        description: 'Comprehensive checklist for transparent reporting of AI/ML diagnostic and prognostic models',
        items: 27,
        sections: 7,
        url: '/api/checklists/tripod_ai'
      },
      {
        type: 'consort_ai',
        name: 'CONSORT-AI Checklist',
        description: 'Extension of CONSORT 2010 guidelines with AI/ML-specific requirements for randomized controlled trials',
        items: 12,
        sections: 4,
        url: '/api/checklists/consort_ai',
        parentGuideline: 'TRIPOD+AI'
      }
    ];

    res.json({
      success: true,
      checklists,
      total: checklists.length,
      message: 'Available checklists for documentation and reporting'
    });
  } catch (error) {
    console.error('Error listing checklists:', error);
    res.status(500).json({
      error: 'Failed to list checklists',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * Get specific checklist with all items
 * GET /api/checklists/:type
 */
router.get('/:type', (req: Request, res: Response) => {
  try {
    const { type } = req.params;

    if (type !== 'tripod_ai' && type !== 'consort_ai') {
      return res.status(400).json({
        error: 'Invalid checklist type',
        code: 'INVALID_CHECKLIST_TYPE',
        validTypes: ['tripod_ai', 'consort_ai']
      });
    }

    const checklistData = loadChecklist(type);
    const rootKey = type === 'tripod_ai' ? 'tripod_ai_checklist' : 'consort_ai_checklist';
    const checklist = checklistData[rootKey];

    const items = extractChecklistItems(checklistData, type);

    const response: Partial<ChecklistResponse> = {
      id: uuid(),
      type: type,
      checklistId: checklist.id || uuid(),
      version: checklist.version || '1.0',
      title: checklist.title,
      description: checklist.description,
      totalItems: items.length,
      items: items,
      completions: items.map(item => ({
        itemId: item.id,
        status: 'not_started',
        evidence: [],
        notes: '',
        validationPassed: false,
        validationErrors: []
      })),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    res.json({
      success: true,
      checklist: response,
      metadata: {
        sections: checklist.sections?.length || 0,
        requiredItems: items.filter(i => i.required).length,
        optionalItems: items.filter(i => !i.required).length
      }
    });
  } catch (error) {
    console.error('Error fetching checklist:', error);
    res.status(500).json({
      error: 'Failed to fetch checklist',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * Get checklist guidance for specific item
 * GET /api/checklists/:type/:itemId/guidance
 */
router.get('/:type/:itemId/guidance', (req: Request, res: Response) => {
  try {
    const { type, itemId } = req.params;

    if (type !== 'tripod_ai' && type !== 'consort_ai') {
      return res.status(400).json({
        error: 'Invalid checklist type',
        code: 'INVALID_CHECKLIST_TYPE'
      });
    }

    const checklistData = loadChecklist(type);
    const items = extractChecklistItems(checklistData, type);

    const item = items.find(i => i.id === itemId);
    if (!item) {
      return res.status(404).json({
        error: 'Checklist item not found',
        code: 'ITEM_NOT_FOUND',
        itemId
      });
    }

    res.json({
      success: true,
      itemId: item.id,
      category: item.category,
      subcategory: item.subcategory,
      description: item.description,
      guidance: item.guidance || 'No specific guidance available',
      evidence_types: item.evidence_types || [],
      validation_rules: item.validation_rules || [],
      cross_reference: item.cross_reference || null
    });
  } catch (error) {
    console.error('Error fetching item guidance:', error);
    res.status(500).json({
      error: 'Failed to fetch item guidance',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * Validate checklist submission
 * POST /api/checklists/:type/validate
 */
router.post('/:type/validate', (req: Request, res: Response) => {
  try {
    const { type } = req.params;
    const { completions } = req.body as { completions: ChecklistItemCompletion[] };

    if (type !== 'tripod_ai' && type !== 'consort_ai') {
      return res.status(400).json({
        error: 'Invalid checklist type',
        code: 'INVALID_CHECKLIST_TYPE'
      });
    }

    if (!completions || !Array.isArray(completions)) {
      return res.status(400).json({
        error: 'Invalid request body',
        code: 'MISSING_COMPLETIONS',
        message: 'completions array is required'
      });
    }

    const checklistData = loadChecklist(type);
    const items = extractChecklistItems(checklistData, type);

    const errors: string[] = [];
    const warnings: string[] = [];
    const criticalIssues: string[] = [];
    const itemValidations: Record<string, { passed: boolean; errors: string[] }> = {};

    let completedCount = 0;

    // Validate each item
    items.forEach(item => {
      const completion = completions.find(c => c.itemId === item.id);

      if (!completion) {
        if (item.required) {
          criticalIssues.push(`Required item ${item.id} (${item.subcategory}) has no completion record`);
        } else {
          warnings.push(`Optional item ${item.id} (${item.subcategory}) has no completion record`);
        }
        itemValidations[item.id] = { passed: false, errors: ['No completion record'] };
        return;
      }

      const validation = validateChecklistItem(item, completion);
      itemValidations[item.id] = validation;

      if (validation.passed && completion.status === 'completed') {
        completedCount++;
      } else if (validation.passed === false) {
        if (item.required) {
          criticalIssues.push(...validation.errors);
        } else {
          warnings.push(...validation.errors);
        }
      }
    });

    // Calculate completeness
    const requiredItems = items.filter(i => i.required);
    const completedRequired = requiredItems.filter(
      item => itemValidations[item.id]?.passed
    ).length;
    const requiredCompleteness = requiredItems.length > 0
      ? (completedRequired / requiredItems.length) * 100
      : 0;

    const allCompleteness = items.length > 0
      ? (completedCount / items.length) * 100
      : 0;

    const isValid = requiredCompleteness === 100 && criticalIssues.length === 0;

    const response: ChecklistValidationResponse = {
      valid: isValid,
      completeness: Math.round(allCompleteness),
      errors,
      warnings,
      criticalIssues,
      itemValidations
    };

    res.json({
      success: true,
      validation: response,
      summary: {
        totalItems: items.length,
        completedItems: completedCount,
        requiredItems: requiredItems.length,
        completedRequired: completedRequired,
        readyForSubmission: isValid
      }
    });
  } catch (error) {
    console.error('Error validating checklist:', error);
    res.status(500).json({
      error: 'Failed to validate checklist',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * Get checklist progress
 * POST /api/checklists/:type/progress
 */
router.post('/:type/progress', (req: Request, res: Response) => {
  try {
    const { type } = req.params;
    const { completions } = req.body as { completions: ChecklistItemCompletion[] };

    if (type !== 'tripod_ai' && type !== 'consort_ai') {
      return res.status(400).json({
        error: 'Invalid checklist type',
        code: 'INVALID_CHECKLIST_TYPE'
      });
    }

    const checklistData = loadChecklist(type);
    const items = extractChecklistItems(checklistData, type);

    let completed = 0;
    let inProgress = 0;
    let notStarted = 0;

    const byCategory: Record<string, {
      total: number;
      completed: number;
      percentage: number;
    }> = {};

    items.forEach(item => {
      // Initialize category
      if (!byCategory[item.category]) {
        byCategory[item.category] = { total: 0, completed: 0, percentage: 0 };
      }
      byCategory[item.category].total++;

      const completion = completions?.find(c => c.itemId === item.id);

      if (!completion) {
        notStarted++;
      } else {
        switch (completion.status) {
          case 'completed':
            completed++;
            byCategory[item.category].completed++;
            break;
          case 'in_progress':
            inProgress++;
            break;
          case 'not_started':
          case 'skipped':
            notStarted++;
            break;
        }
      }
    });

    // Calculate percentages by category
    Object.keys(byCategory).forEach(category => {
      byCategory[category].percentage = Math.round(
        (byCategory[category].completed / byCategory[category].total) * 100
      );
    });

    const totalItems = items.length;
    const progressPercentage = Math.round((completed / totalItems) * 100);

    const response: ChecklistProgressResponse = {
      checklistId: uuid(),
      type,
      totalItems,
      completedItems: completed,
      inProgressItems: inProgress,
      notStartedItems: notStarted,
      progressPercentage,
      byCategory
    };

    res.json({
      success: true,
      progress: response
    });
  } catch (error) {
    console.error('Error calculating progress:', error);
    res.status(500).json({
      error: 'Failed to calculate progress',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * Export completed checklist
 * POST /api/checklists/:type/export
 *
 * Supported formats: json, yaml, pdf, csv
 */
router.post('/:type/export', (req: Request, res: Response) => {
  try {
    const { type } = req.params;
    const { completions, format = 'json', researchId } = req.body as {
      completions: ChecklistItemCompletion[];
      format?: 'json' | 'yaml' | 'csv';
      researchId?: string;
    };

    if (type !== 'tripod_ai' && type !== 'consort_ai') {
      return res.status(400).json({
        error: 'Invalid checklist type',
        code: 'INVALID_CHECKLIST_TYPE'
      });
    }

    if (!completions || !Array.isArray(completions)) {
      return res.status(400).json({
        error: 'Invalid request body',
        code: 'MISSING_COMPLETIONS',
        message: 'completions array is required'
      });
    }

    if (!['json', 'yaml', 'csv'].includes(format)) {
      return res.status(400).json({
        error: 'Invalid export format',
        code: 'INVALID_FORMAT',
        validFormats: ['json', 'yaml', 'csv']
      });
    }

    const checklistData = loadChecklist(type);
    const items = extractChecklistItems(checklistData, type);

    let exportContent: string;
    let mimeType: string;
    let filename: string;

    const timestamp = new Date().toISOString().split('T')[0];
    const baseFilename = `${type}-checklist-${timestamp}`;

    if (format === 'json') {
      const exportData = {
        checklistType: type,
        exportedAt: new Date().toISOString(),
        researchId,
        items: items.map(item => {
          const completion = completions.find(c => c.itemId === item.id);
          return {
            id: item.id,
            category: item.category,
            subcategory: item.subcategory,
            description: item.description,
            status: completion?.status || 'not_started',
            evidence: completion?.evidence || [],
            notes: completion?.notes || '',
            validationPassed: completion?.validationPassed || false
          };
        })
      };
      exportContent = JSON.stringify(exportData, null, 2);
      mimeType = 'application/json';
      filename = `${baseFilename}.json`;
    } else if (format === 'yaml') {
      const exportData = {
        checklistType: type,
        exportedAt: new Date().toISOString(),
        researchId,
        items: items.map(item => {
          const completion = completions.find(c => c.itemId === item.id);
          return {
            id: item.id,
            category: item.category,
            subcategory: item.subcategory,
            status: completion?.status || 'not_started',
            evidence: completion?.evidence || [],
            notes: completion?.notes || ''
          };
        })
      };
      exportContent = yaml.dump(exportData);
      mimeType = 'application/x-yaml';
      filename = `${baseFilename}.yaml`;
    } else {
      // CSV format
      const headers = ['Item ID', 'Category', 'Subcategory', 'Status', 'Notes', 'Evidence Count'];
      const rows = items.map(item => {
        const completion = completions.find(c => c.itemId === item.id);
        return [
          item.id,
          item.category,
          item.subcategory,
          completion?.status || 'not_started',
          (completion?.notes || '').replace(/"/g, '""'),
          (completion?.evidence?.length || 0).toString()
        ];
      });

      const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
      ].join('\n');

      exportContent = csvContent;
      mimeType = 'text/csv';
      filename = `${baseFilename}.csv`;
    }

    res.setHeader('Content-Type', mimeType);
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.send(exportContent);
  } catch (error) {
    console.error('Error exporting checklist:', error);
    res.status(500).json({
      error: 'Failed to export checklist',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * Get checklist comparison (e.g., TRIPOD+AI vs CONSORT-AI)
 * GET /api/checklists/compare
 */
router.get('/compare/items', (req: Request, res: Response) => {
  try {
    const tripodData = loadChecklist('tripod_ai');
    const consortData = loadChecklist('consort_ai');

    const tripodItems = extractChecklistItems(tripodData, 'tripod_ai');
    const consortItems = extractChecklistItems(consortData, 'consort_ai');

    // Build mapping of cross-references
    const crossReferences: Record<string, {
      tripodItems: string[];
      consortItems: string[];
    }> = {};

    consortItems.forEach(item => {
      if (item.cross_reference?.tripod_item) {
        const tripodId = item.cross_reference.tripod_item;
        if (!crossReferences[tripodId]) {
          crossReferences[tripodId] = { tripodItems: [tripodId], consortItems: [] };
        }
        crossReferences[tripodId].consortItems.push(item.id);
      }
    });

    res.json({
      success: true,
      comparison: {
        tripod_ai: {
          totalItems: tripodItems.length,
          requiredItems: tripodItems.filter(i => i.required).length,
          categories: [...new Set(tripodItems.map(i => i.category))]
        },
        consort_ai: {
          totalItems: consortItems.length,
          requiredItems: consortItems.filter(i => i.required).length,
          categories: [...new Set(consortItems.map(i => i.category))]
        },
        crossReferences
      }
    });
  } catch (error) {
    console.error('Error comparing checklists:', error);
    res.status(500).json({
      error: 'Failed to compare checklists',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

export default router;
