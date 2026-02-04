# Statistical Analysis API Documentation

## Overview

This document provides comprehensive API documentation for Stage 7: Statistical Analysis endpoints.

**Base URL**: `/api`

**Authentication**: All endpoints require valid JWT token in Authorization header

---

## Endpoints

### 1. Get Available Tests

Retrieves list of supported statistical tests with metadata.

**Endpoint**: `GET /statistical-tests`

**Response**: `200 OK`

```json
{
  "success": true,
  "tests": [
    {
      "type": "t-test-independent",
      "name": "Independent Samples t-test",
      "description": "Compares means between two independent groups",
      "requiredVariables": [
        {
          "role": "dependent",
          "type": ["continuous"],
          "minCount": 1,
          "maxCount": 1
        },
        {
          "role": "grouping",
          "type": ["binary", "categorical"],
          "minCount": 1,
          "maxCount": 1
        }
      ],
      "assumptions": [
        "Independence of observations",
        "Normality of distributions",
        "Homogeneity of variances"
      ],
      "useCase": "When comparing two independent groups on a continuous outcome",
      "examples": [
        "Treatment vs control group on symptom scores"
      ],
      "effectSizes": ["Cohen's d", "Hedge's g"]
    }
  ],
  "message": "Successfully retrieved test types"
}
```

---

### 2. Get Dataset Metadata

Retrieves metadata about dataset columns for variable selection.

**Endpoint**: `GET /datasets/:datasetId/metadata`

**Parameters**:
- `datasetId` (path, required): Dataset identifier

**Response**: `200 OK`

```json
{
  "success": true,
  "metadata": {
    "id": "dataset_123",
    "rowCount": 150,
    "columns": [
      {
        "name": "age",
        "type": "continuous",
        "count": 150,
        "nullCount": 0,
        "uniqueCount": 45,
        "sampleValues": [25, 30, 35, 40, 45],
        "suitable": true,
        "issues": []
      },
      {
        "name": "treatment_group",
        "type": "binary",
        "count": 150,
        "nullCount": 0,
        "uniqueCount": 2,
        "sampleValues": ["treatment", "control"],
        "suitable": true,
        "issues": []
      }
    ],
    "qualityScore": 95,
    "qualityIssues": []
  }
}
```

**Error Responses**:
- `404 Not Found`: Dataset not found
- `403 Forbidden`: No access to dataset

---

### 3. Validate Analysis Configuration

Validates statistical test configuration before execution.

**Endpoint**: `POST /statistical-analysis/validate`

**Request Body**:

```json
{
  "testType": "t-test-independent",
  "variables": [
    {
      "name": "blood_pressure",
      "type": "continuous",
      "role": "dependent",
      "label": "Blood Pressure (mmHg)"
    },
    {
      "name": "treatment_group",
      "type": "binary",
      "role": "grouping",
      "label": "Treatment Group"
    }
  ],
  "confidenceLevel": 0.95,
  "alpha": 0.05,
  "multipleComparisonCorrection": "none",
  "options": {
    "tails": "two",
    "equalVariance": true
  }
}
```

**Response**: `200 OK`

```json
{
  "success": true,
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": [
      {
        "field": "options.equalVariance",
        "message": "Equal variances assumed - will be tested automatically",
        "severity": "warning",
        "suggestion": "Consider using Welch's correction if variances differ"
      }
    ]
  }
}
```

**Validation Failure**: `200 OK` (with validation errors)

```json
{
  "success": true,
  "validation": {
    "valid": false,
    "errors": [
      {
        "field": "variables",
        "message": "Test requires exactly 1 dependent variable",
        "severity": "error",
        "suggestion": "Select a single continuous outcome variable"
      }
    ],
    "warnings": []
  }
}
```

---

### 4. Execute Statistical Analysis

Runs statistical analysis and returns results.

**Endpoint**: `POST /research/:researchId/stage/7/execute`

**Parameters**:
- `researchId` (path, required): Research project identifier

**Request Body**:

```json
{
  "config": {
    "testType": "t-test-independent",
    "variables": [
      {
        "name": "blood_pressure",
        "type": "continuous",
        "role": "dependent"
      },
      {
        "name": "treatment_group",
        "type": "binary",
        "role": "grouping"
      }
    ],
    "confidenceLevel": 0.95,
    "alpha": 0.05,
    "multipleComparisonCorrection": "none",
    "options": {
      "tails": "two",
      "equalVariance": true
    }
  },
  "datasetId": "dataset_123",
  "includeVisualizations": true
}
```

**Response**: `200 OK`

```json
{
  "success": true,
  "result": {
    "id": "analysis_789",
    "researchId": "research_456",
    "config": { /* same as request */ },
    "descriptiveStats": [
      {
        "variable": "blood_pressure",
        "n": 50,
        "mean": 128.4,
        "sd": 12.3,
        "se": 1.74,
        "min": 105.0,
        "max": 158.0,
        "median": 127.0,
        "iqr": 15.5,
        "q1": 120.25,
        "q3": 135.75,
        "skewness": 0.15,
        "kurtosis": -0.42,
        "ci95": [124.9, 131.9]
      }
    ],
    "hypothesisTest": {
      "statistic": -2.85,
      "statisticName": "t",
      "pValue": 0.005,
      "degreesOfFreedom": 96,
      "significant": true,
      "confidenceInterval": [-12.4, -2.2],
      "effectSize": {
        "name": "Cohen's d",
        "value": 0.56,
        "confidenceInterval": [0.17, 0.95],
        "interpretation": "medium",
        "guidelines": "Cohen's conventions"
      }
    },
    "assumptions": [
      {
        "name": "Normality",
        "description": "Data should follow normal distribution",
        "passed": true,
        "statistic": 0.976,
        "pValue": 0.234,
        "interpretation": "Data appears normally distributed (Shapiro-Wilk p > .05)",
        "severity": "none"
      },
      {
        "name": "Homogeneity of Variances",
        "description": "Groups should have equal variances",
        "passed": true,
        "statistic": 1.82,
        "pValue": 0.180,
        "interpretation": "Variances are approximately equal (Levene's p > .05)",
        "severity": "none"
      }
    ],
    "visualizations": [
      {
        "type": "boxplot",
        "title": "Blood Pressure by Treatment Group",
        "data": { /* chart data */ },
        "config": {}
      }
    ],
    "apaFormatted": [
      {
        "section": "inferential",
        "text": "An independent-samples t-test was conducted...",
        "includeInManuscript": true
      }
    ],
    "interpretation": "The treatment group had significantly lower blood pressure...",
    "recommendations": [
      "Report effect size in addition to p-value",
      "Consider clinical significance of 7.3 mmHg difference"
    ],
    "warnings": [],
    "createdAt": "2024-01-15T10:30:00Z",
    "duration": 1243
  },
  "message": "Analysis completed successfully"
}
```

**Error Responses**:

`400 Bad Request` - Invalid configuration

```json
{
  "success": false,
  "error": {
    "message": "Invalid test configuration",
    "code": "INVALID_CONFIG",
    "severity": "ERROR",
    "details": {
      "field": "variables",
      "reason": "Missing required dependent variable"
    }
  }
}
```

`404 Not Found` - Research project not found

`500 Internal Server Error` - Analysis execution failed

---

### 5. Get Analysis Results

Retrieves previously computed analysis results.

**Endpoint**: `GET /research/:researchId/stage/7/results/:analysisId`

**Parameters**:
- `researchId` (path, required): Research project identifier
- `analysisId` (path, required): Analysis identifier

**Response**: `200 OK`

```json
{
  "id": "analysis_789",
  "researchId": "research_456",
  "config": { /* configuration */ },
  "descriptiveStats": [ /* stats */ ],
  "hypothesisTest": { /* results */ },
  "assumptions": [ /* checks */ ],
  "visualizations": [ /* charts */ ],
  "apaFormatted": [ /* text */ ],
  "interpretation": "...",
  "recommendations": [],
  "warnings": [],
  "createdAt": "2024-01-15T10:30:00Z",
  "duration": 1243
}
```

---

### 6. List All Analyses

Lists all analyses for a research project.

**Endpoint**: `GET /research/:researchId/stage/7/analyses`

**Parameters**:
- `researchId` (path, required): Research project identifier

**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `pageSize` (optional): Results per page (default: 20)
- `sortBy` (optional): Sort field (createdAt, duration)
- `sortOrder` (optional): asc or desc (default: desc)

**Response**: `200 OK`

```json
{
  "analyses": [
    {
      "id": "analysis_789",
      "researchId": "research_456",
      "config": {
        "testType": "t-test-independent"
      },
      "createdAt": "2024-01-15T10:30:00Z",
      "duration": 1243,
      "significant": true
    }
  ],
  "total": 5,
  "page": 1,
  "pageSize": 20
}
```

---

(Continued in STATISTICAL_ANALYSIS_API_PART2.md)
