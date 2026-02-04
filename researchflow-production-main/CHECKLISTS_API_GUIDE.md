# Checklists API Guide - Track C (ROS-112)

## Quick Start

The Checklists API provides endpoints for managing TRIPOD+AI and CONSORT-AI reporting checklists for research documentation.

### Base URL
```
/api/checklists
```

### Authentication
Optional - endpoints work with or without authentication

---

## API Endpoints

### 1. List Available Checklists

List all available checklist types in the system.

```http
GET /api/checklists
```

**Response (200 OK)**:
```json
{
  "success": true,
  "checklists": [
    {
      "type": "tripod_ai",
      "name": "TRIPOD+AI Checklist",
      "description": "Comprehensive checklist for transparent reporting of AI/ML diagnostic and prognostic models",
      "items": 27,
      "sections": 7,
      "url": "/api/checklists/tripod_ai"
    },
    {
      "type": "consort_ai",
      "name": "CONSORT-AI Checklist",
      "description": "Extension of CONSORT 2010 guidelines with AI/ML-specific requirements for randomized controlled trials",
      "items": 12,
      "sections": 4,
      "url": "/api/checklists/consort_ai",
      "parentGuideline": "TRIPOD+AI"
    }
  ],
  "total": 2,
  "message": "Available checklists for documentation and reporting"
}
```

---

### 2. Get Specific Checklist

Retrieve a complete checklist with all items and initial completion tracking.

```http
GET /api/checklists/:type
```

**Path Parameters**:
- `type` (string, required): `tripod_ai` or `consort_ai`

**Response (200 OK)**:
```json
{
  "success": true,
  "checklist": {
    "id": "uuid",
    "type": "tripod_ai",
    "checklistId": "uuid",
    "version": "1.0",
    "title": "TRIPOD+AI Checklist for AI/ML Model Reporting in Healthcare",
    "description": "Comprehensive checklist...",
    "totalItems": 27,
    "items": [
      {
        "id": "T1",
        "category": "Title",
        "subcategory": "Title and Keywords",
        "description": "Identify the study as developing/validating a multivariable prediction model...",
        "required": true,
        "evidence_types": ["Title page", "Keywords section", "Running title"],
        "validation_rules": [
          "Must include key terms: 'model', 'prediction' or 'prognostic' or 'diagnostic'",
          "Must identify target population",
          "Must identify predicted outcome",
          "Should include AI/ML terminology if applicable"
        ],
        "guidance": "..."
      }
    ],
    "completions": [
      {
        "itemId": "T1",
        "status": "not_started",
        "evidence": [],
        "notes": "",
        "validationPassed": false,
        "validationErrors": []
      }
    ],
    "createdAt": "2026-01-30T10:00:00Z",
    "updatedAt": "2026-01-30T10:00:00Z"
  },
  "metadata": {
    "sections": 7,
    "requiredItems": 25,
    "optionalItems": 2
  }
}
```

**Error Responses**:
```json
// 400 Bad Request - Invalid checklist type
{
  "error": "Invalid checklist type",
  "code": "INVALID_CHECKLIST_TYPE",
  "validTypes": ["tripod_ai", "consort_ai"]
}
```

---

### 3. Get Item Guidance

Retrieve detailed guidance for a specific checklist item.

```http
GET /api/checklists/:type/:itemId/guidance
```

**Path Parameters**:
- `type` (string, required): `tripod_ai` or `consort_ai`
- `itemId` (string, required): Item identifier (e.g., "T1", "M7")

**Response (200 OK)**:
```json
{
  "success": true,
  "itemId": "M7",
  "category": "Methods",
  "subcategory": "Statistical Analysis and Model Development",
  "description": "Describe the type of model, all model specifications including hyperparameters...",
  "guidance": "Describe the AI/ML model in sufficient detail to allow reproduction. Include framework used (PyTorch, TensorFlow, scikit-learn, etc.) and specific implementation.",
  "evidence_types": [
    "Statistical analysis plan",
    "Model specification document",
    "Algorithm documentation",
    "Hyperparameter settings",
    "Validation strategy",
    "Code/supplementary materials"
  ],
  "validation_rules": [
    "Must specify model type (logistic, Cox, random forest, neural network, etc.)",
    "Must report all hyperparameters",
    "Must describe validation approach (k-fold, holdout, etc.)",
    "Must report regularization methods",
    "Should describe cross-validation strategy",
    "Should report random seed for reproducibility",
    "Should include algorithm-specific parameters"
  ],
  "cross_reference": {
    "consort_item": "CONSORT-AI-1",
    "rationale": "CONSORT-AI-1 extends M7 with trial-specific model specifications"
  }
}
```

**Error Responses**:
```json
// 404 Not Found - Item not found
{
  "error": "Checklist item not found",
  "code": "ITEM_NOT_FOUND",
  "itemId": "INVALID"
}
```

---

### 4. Validate Checklist Submission

Validate a checklist submission against defined rules.

```http
POST /api/checklists/:type/validate
Content-Type: application/json
```

**Path Parameters**:
- `type` (string, required): `tripod_ai` or `consort_ai`

**Request Body**:
```json
{
  "completions": [
    {
      "itemId": "T1",
      "status": "completed",
      "completedAt": "2026-01-30T10:15:00Z",
      "evidence": ["file1.pdf", "file2.docx"],
      "notes": "Title includes model type and target population",
      "validationPassed": true,
      "validationErrors": []
    },
    {
      "itemId": "A1",
      "status": "in_progress",
      "evidence": ["abstract-draft.txt"],
      "notes": "Still refining abstract"
    },
    {
      "itemId": "I1",
      "status": "not_started"
    }
  ]
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "validation": {
    "valid": false,
    "completeness": 33,
    "errors": [
      "Item I1 validation failed: Must establish clinical importance of the problem",
      "Item I2 validation failed: No evidence provided"
    ],
    "warnings": [],
    "criticalIssues": [
      "Required item I1 is not completed",
      "Required item I2 is not completed",
      "Required item I3 is not completed"
    ],
    "itemValidations": {
      "T1": {
        "passed": true,
        "errors": []
      },
      "A1": {
        "passed": false,
        "errors": ["Item must be completed, not in_progress"]
      },
      "I1": {
        "passed": false,
        "errors": ["Required item I1 (Background and Context) has no completion record"]
      }
    }
  },
  "summary": {
    "totalItems": 27,
    "completedItems": 1,
    "requiredItems": 25,
    "completedRequired": 1,
    "readyForSubmission": false
  }
}
```

**Error Responses**:
```json
// 400 Bad Request - Missing completions
{
  "error": "Invalid request body",
  "code": "MISSING_COMPLETIONS",
  "message": "completions array is required"
}
```

---

### 5. Calculate Progress

Calculate completion progress with category breakdown.

```http
POST /api/checklists/:type/progress
Content-Type: application/json
```

**Path Parameters**:
- `type` (string, required): `tripod_ai` or `consort_ai`

**Request Body**:
```json
{
  "completions": [
    {
      "itemId": "T1",
      "status": "completed"
    },
    {
      "itemId": "A1",
      "status": "completed"
    },
    {
      "itemId": "I1",
      "status": "in_progress"
    }
  ]
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "progress": {
    "checklistId": "uuid",
    "type": "tripod_ai",
    "totalItems": 27,
    "completedItems": 2,
    "inProgressItems": 1,
    "notStartedItems": 24,
    "progressPercentage": 7,
    "byCategory": {
      "Title": {
        "total": 1,
        "completed": 1,
        "percentage": 100
      },
      "Abstract": {
        "total": 1,
        "completed": 1,
        "percentage": 100
      },
      "Introduction": {
        "total": 2,
        "completed": 0,
        "percentage": 0
      },
      "Methods": {
        "total": 8,
        "completed": 0,
        "percentage": 0
      },
      "Results": {
        "total": 4,
        "completed": 0,
        "percentage": 0
      },
      "Discussion": {
        "total": 3,
        "completed": 0,
        "percentage": 0
      },
      "Other": {
        "total": 2,
        "completed": 0,
        "percentage": 0
      }
    }
  }
}
```

---

### 6. Export Checklist

Export a completed checklist in various formats.

```http
POST /api/checklists/:type/export
Content-Type: application/json
```

**Path Parameters**:
- `type` (string, required): `tripod_ai` or `consort_ai`

**Request Body**:
```json
{
  "completions": [
    {
      "itemId": "T1",
      "status": "completed",
      "evidence": ["title-page.pdf"],
      "notes": "Title includes all required elements"
    }
  ],
  "format": "json",
  "researchId": "research-123"
}
```

**Query Parameters**:
- `format` (string, optional): `json`, `yaml`, or `csv`. Default: `json`

**Response (200 OK)** - File Download:

For `format=json`:
```json
{
  "checklistType": "tripod_ai",
  "exportedAt": "2026-01-30T10:30:00Z",
  "researchId": "research-123",
  "items": [
    {
      "id": "T1",
      "category": "Title",
      "subcategory": "Title and Keywords",
      "description": "Identify the study...",
      "status": "completed",
      "evidence": ["title-page.pdf"],
      "notes": "Title includes all required elements",
      "validationPassed": true
    }
  ]
}
```

For `format=csv`:
```csv
"Item ID","Category","Subcategory","Status","Notes","Evidence Count"
"T1","Title","Title and Keywords","completed","Title includes all required elements","1"
"A1","Abstract","Abstract Summary","not_started","","0"
```

**Response Headers**:
```
Content-Type: application/json (or application/x-yaml, text/csv)
Content-Disposition: attachment; filename="tripod_ai-checklist-2026-01-30.json"
```

**Error Responses**:
```json
// 400 Bad Request - Invalid format
{
  "error": "Invalid export format",
  "code": "INVALID_FORMAT",
  "validFormats": ["json", "yaml", "csv"]
}
```

---

### 7. Compare Checklists

Compare TRIPOD+AI and CONSORT-AI checklists to see relationships.

```http
GET /api/checklists/compare/items
```

**Response (200 OK)**:
```json
{
  "success": true,
  "comparison": {
    "tripod_ai": {
      "totalItems": 27,
      "requiredItems": 25,
      "categories": ["Title", "Abstract", "Introduction", "Methods", "Results", "Discussion", "Other"]
    },
    "consort_ai": {
      "totalItems": 12,
      "requiredItems": 12,
      "categories": ["AI Model Specification", "Trial Integration", "Validation and Performance Assessment", "Interpretation and Implementation"]
    },
    "crossReferences": {
      "M7": {
        "tripodItems": ["M7"],
        "consortItems": ["CONSORT-AI-1", "CONSORT-AI-4"]
      },
      "M1": {
        "tripodItems": ["M1"],
        "consortItems": ["CONSORT-AI-2"]
      },
      "R4": {
        "tripodItems": ["R4"],
        "consortItems": ["CONSORT-AI-3", "CONSORT-AI-7"]
      }
    }
  }
}
```

---

## Data Models

### ChecklistItem
```typescript
{
  id: string;                          // Unique identifier (T1, M7, etc.)
  category: string;                    // Section (Title, Methods, etc.)
  subcategory: string;                 // Subsection
  description: string;                 // What needs to be reported
  required: boolean;                   // Is this item mandatory?
  evidence_types?: string[];           // Acceptable evidence formats
  validation_rules?: string[];         // Rules to validate completion
  guidance?: string;                   // Detailed implementation guidance
  cross_reference?: {
    tripod_item?: string;              // Cross-reference to TRIPOD+AI item
    consort_item?: string;             // Cross-reference to CONSORT-AI item
    rationale?: string;                // Why they're related
  };
}
```

### ChecklistItemCompletion
```typescript
{
  itemId: string;                      // Reference to ChecklistItem.id
  status: 'not_started' | 'in_progress' | 'completed' | 'skipped';
  completedAt?: string;                // ISO 8601 timestamp
  evidence?: string[];                 // File references or URLs
  notes?: string;                      // User notes
  validationPassed?: boolean;           // Validation status
  validationErrors?: string[];         // Specific validation errors
}
```

### ChecklistResponse
```typescript
{
  id: string;                          // Response instance ID
  type: 'tripod_ai' | 'consort_ai';    // Checklist type
  checklistId: string;                 // Configuration ID
  researchId?: string;                 // Associated research project
  version: string;                     // Checklist version (1.0)
  title: string;                       // Full title
  description: string;                 // Full description
  totalItems: number;                  // Number of items
  items: ChecklistItem[];              // All items
  completions: ChecklistItemCompletion[]; // Completion status
  createdAt: string;                   // ISO 8601 timestamp
  updatedAt: string;                   // ISO 8601 timestamp
  submittedAt?: string;                // Submission timestamp
}
```

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 404 | Not Found (item not found) |
| 500 | Server Error |

---

## Error Response Format

All error responses follow this format:

```json
{
  "error": "Human-readable error message",
  "code": "MACHINE_READABLE_CODE",
  "details": "Additional context if applicable"
}
```

### Common Error Codes

| Code | Meaning |
|------|---------|
| INVALID_CHECKLIST_TYPE | Unknown checklist type specified |
| INVALID_CHECKLIST_FORMAT | Malformed checklist configuration |
| ITEM_NOT_FOUND | Requested checklist item doesn't exist |
| MISSING_COMPLETIONS | Required field missing in request |
| INVALID_FORMAT | Export format not supported |
| VALIDATION_FAILED | Checklist validation failed |

---

## Examples

### Example 1: Start Working on a Checklist

```bash
# Get the checklist
curl http://localhost:3001/api/checklists/tripod_ai \
  -H "Accept: application/json"

# Get guidance for first item
curl http://localhost:3001/api/checklists/tripod_ai/T1/guidance
```

### Example 2: Complete Items and Validate

```bash
# Validate progress
curl -X POST http://localhost:3001/api/checklists/tripod_ai/validate \
  -H "Content-Type: application/json" \
  -d '{
    "completions": [
      {
        "itemId": "T1",
        "status": "completed",
        "evidence": ["manuscript.pdf"],
        "notes": "Title is clear"
      },
      {
        "itemId": "A1",
        "status": "completed",
        "evidence": ["abstract.txt"],
        "notes": "Structured abstract complete"
      }
    ]
  }'
```

### Example 3: Track Progress

```bash
# Get progress breakdown
curl -X POST http://localhost:3001/api/checklists/tripod_ai/progress \
  -H "Content-Type: application/json" \
  -d '{
    "completions": [...]
  }' | jq '.progress | {progressPercentage, byCategory}'
```

### Example 4: Export Completed Checklist

```bash
# Export as CSV
curl -X POST http://localhost:3001/api/checklists/tripod_ai/export \
  -H "Content-Type: application/json" \
  -d '{
    "completions": [...],
    "format": "csv",
    "researchId": "proj-123"
  }' > checklist-export.csv
```

---

## Integration Guide

### With Your Application

1. **List available checklists** on startup
2. **Load specific checklist** when user starts documentation
3. **Track completion** as user works through items
4. **Validate periodically** to provide feedback
5. **Export final checklist** for submission

### Workflow Example

```typescript
// 1. Get checklist
const response = await fetch('/api/checklists/tripod_ai');
const { checklist } = await response.json();

// 2. Track completions as user works
const completions = checklist.completions.map(c => ({
  ...c,
  status: 'not_started'
}));

// 3. Update completion for each item
completions[0].status = 'completed';
completions[0].evidence = ['file.pdf'];

// 4. Validate
const validation = await fetch('/api/checklists/tripod_ai/validate', {
  method: 'POST',
  body: JSON.stringify({ completions })
});
const { validation: result } = await validation.json();

// 5. Export when ready
if (result.valid) {
  const download = await fetch('/api/checklists/tripod_ai/export', {
    method: 'POST',
    body: JSON.stringify({ completions, format: 'pdf' })
  });
}
```

---

## Rate Limiting & Performance

- No built-in rate limiting (implement at load balancer level)
- YAML parsing happens per request (consider caching)
- Typical response times: <100ms
- Suitable for production use

---

## Support

For issues or questions about the Checklists API:
1. Check `/TRACK_C_DOCUMENTATION.md` for implementation details
2. Review test suite at `/services/orchestrator/src/routes/__tests__/checklists.test.ts`
3. Check checklist configs at `/config/*.yaml`

---

**Version**: 1.0
**Last Updated**: 2026-01-30
**API Base**: `/api/checklists`
