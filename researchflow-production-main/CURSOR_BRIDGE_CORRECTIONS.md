# TypeScript-Python Bridge: Plan Corrections

## Critical Fixes Required

### 1. Router Registration - WRONG LOCATION

**Problem:** The plan says to modify `services/orchestrator/routes.ts` directly, but this file is 6,400+ lines and follows a specific pattern.

**Correct Approach:**

Create a new router file following the existing pattern:

```bash
# Create new router file
touch services/orchestrator/src/routes/bridge.ts
```

**File: `services/orchestrator/src/routes/bridge.ts`**
```typescript
import { Router, Request, Response } from 'express';
import { 
  ClaudeWriterService,
  AbstractGeneratorService,
  MethodsPopulatorService 
} from '@researchflow/manuscript-engine';

const router = Router();

// Service instances (singleton pattern)
const claudeWriterService = new ClaudeWriterService();
const abstractGeneratorService = new AbstractGeneratorService();
const methodsPopulatorService = new MethodsPopulatorService();

// Service registry
const SERVICE_REGISTRY: Record<string, any> = {
  'claude-writer': claudeWriterService,
  'abstract-generator': abstractGeneratorService,
  'methods-populator': methodsPopulatorService,
};

// Health check endpoint
router.get('/health', (_req: Request, res: Response) => {
  res.json({ 
    status: 'ok', 
    services: Object.keys(SERVICE_REGISTRY),
    timestamp: new Date().toISOString()
  });
});

// Dynamic service method invocation
router.post('/:serviceName/:methodName', async (req: Request, res: Response) => {
  const { serviceName, methodName } = req.params;
  
  try {
    // Validate service exists
    const service = SERVICE_REGISTRY[serviceName];
    if (!service) {
      return res.status(404).json({ 
        success: false, 
        error: `Service '${serviceName}' not found`,
        availableServices: Object.keys(SERVICE_REGISTRY)
      });
    }
    
    // Validate method exists
    if (typeof service[methodName] !== 'function') {
      return res.status(404).json({ 
        success: false, 
        error: `Method '${methodName}' not found on service '${serviceName}'`,
        availableMethods: Object.getOwnPropertyNames(Object.getPrototypeOf(service))
          .filter(m => m !== 'constructor' && typeof service[m] === 'function')
      });
    }
    
    // Execute method
    const result = await service[methodName](req.body);
    
    res.json({ success: true, data: result });
  } catch (error: any) {
    console.error(`Bridge error: ${serviceName}/${methodName}`, error);
    res.status(500).json({ 
      success: false, 
      error: error.message,
      service: serviceName,
      method: methodName
    });
  }
});

export default router;
```

**Then add to `services/orchestrator/routes.ts`** (around line 950, after other router imports):

```typescript
// TypeScript-Python Bridge for manuscript services
import bridgeRouter from "./src/routes/bridge";

// In registerRoutes function, add:
app.use("/api/services", bridgeRouter);
```

---

### 2. IRB Generator Service - NEEDS TO BE CREATED

**Problem:** `irb-generator.service.ts` doesn't exist.

**Solution:** Create it as an orchestrator of existing services.

**File: `packages/manuscript-engine/src/services/irb-generator.service.ts`**
```typescript
import { ClaudeWriterService } from './claude-writer.service';
import { MethodsPopulatorService } from './methods-populator.service';

export interface IrbProtocolRequest {
  studyTitle: string;
  principalInvestigator: string;
  studyType: 'retrospective' | 'prospective' | 'clinical_trial';
  hypothesis: string;
  population: string;
  dataSource: string;
  variables: string[];
  analysisApproach: string;
}

export interface IrbProtocol {
  protocolNumber: string;
  title: string;
  sections: {
    background: string;
    objectives: string;
    studyDesign: string;
    population: string;
    dataCollection: string;
    dataManagement: string;
    statisticalAnalysis: string;
    ethicsConsiderations: string;
    risks: string;
    benefits: string;
    privacyProtection: string;
    consentProcess: string;
  };
  attachments: {
    consentFormDraft: string;
    dataCollectionInstruments: string[];
  };
  generatedAt: string;
}

export class IrbGeneratorService {
  private claudeWriter: ClaudeWriterService;
  private methodsPopulator: MethodsPopulatorService;

  constructor() {
    this.claudeWriter = new ClaudeWriterService();
    this.methodsPopulator = new MethodsPopulatorService();
  }

  async generateProtocol(request: IrbProtocolRequest): Promise<IrbProtocol> {
    // Generate each section using Claude
    const sections = await this.generateSections(request);
    const consentForm = await this.generateConsentForm(request);
    
    return {
      protocolNumber: `IRB-${Date.now()}`,
      title: request.studyTitle,
      sections,
      attachments: {
        consentFormDraft: consentForm,
        dataCollectionInstruments: []
      },
      generatedAt: new Date().toISOString()
    };
  }

  private async generateSections(request: IrbProtocolRequest) {
    // Use claudeWriter to generate each section
    const background = await this.claudeWriter.generateParagraph({
      topic: `Background and rationale for: ${request.studyTitle}`,
      context: request.hypothesis,
      section: 'background',
      tone: 'formal'
    });

    // Generate other sections similarly...
    return {
      background: background.paragraph,
      objectives: '',  // Generate similarly
      studyDesign: '',
      population: request.population,
      dataCollection: '',
      dataManagement: '',
      statisticalAnalysis: request.analysisApproach,
      ethicsConsiderations: '',
      risks: '',
      benefits: '',
      privacyProtection: '',
      consentProcess: ''
    };
  }

  private async generateConsentForm(request: IrbProtocolRequest): Promise<string> {
    const result = await this.claudeWriter.generateParagraph({
      topic: `Informed consent form for: ${request.studyTitle}`,
      context: `Study type: ${request.studyType}, Population: ${request.population}`,
      section: 'consent',
      tone: 'formal'
    });
    return result.paragraph;
  }
}
```

**Add to index.ts:**
```typescript
// In packages/manuscript-engine/src/services/index.ts
export { IrbGeneratorService } from './irb-generator.service';
```

---

### 3. Service Exports - NEED TO VERIFY

Check that `packages/manuscript-engine/src/services/index.ts` exports all needed services:

```typescript
// Should export:
export { ClaudeWriterService } from './claude-writer.service';
export { AbstractGeneratorService } from './abstract-generator.service';
export { MethodsPopulatorService } from './methods-populator.service';
export { IrbGeneratorService } from './irb-generator.service';  // New
```

---

### 4. Python Client - CORRECT PATH

The Python client path is correct but needs the proper directory structure:

```bash
# Create directory if it doesn't exist
mkdir -p services/worker/src/workflow_engine
touch services/worker/src/workflow_engine/bridge.py
touch services/worker/src/workflow_engine/__init__.py
```

**File: `services/worker/src/workflow_engine/bridge.py`**
```python
"""HTTP bridge client for TypeScript manuscript-engine services."""

import os
import httpx
from typing import Any, Dict, Optional
from dataclasses import dataclass

@dataclass
class BridgeConfig:
    base_url: str = "http://localhost:3000"
    timeout: float = 30.0
    
    @classmethod
    def from_env(cls) -> "BridgeConfig":
        return cls(
            base_url=os.getenv("ORCHESTRATOR_URL", "http://localhost:3000"),
            timeout=float(os.getenv("BRIDGE_TIMEOUT", "30.0"))
        )

class ManuscriptClient:
    """Async client for calling TypeScript manuscript services."""
    
    def __init__(self, config: Optional[BridgeConfig] = None):
        self.config = config or BridgeConfig.from_env()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "ManuscriptClient":
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout
        )
        return self
    
    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
    
    async def call_service(
        self, 
        service_name: str, 
        method_name: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generic method to call any service method."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with statement.")
        
        response = await self._client.post(
            f"/api/services/{service_name}/{method_name}",
            json=params
        )
        response.raise_for_status()
        result = response.json()
        
        if not result.get("success"):
            raise Exception(result.get("error", "Unknown error"))
        
        return result.get("data")
    
    # Typed convenience methods
    async def generate_paragraph(
        self,
        topic: str,
        context: str,
        section: str = "body",
        tone: str = "formal"
    ) -> Dict[str, Any]:
        """Generate a paragraph using Claude writer."""
        return await self.call_service("claude-writer", "generateParagraph", {
            "topic": topic,
            "context": context,
            "section": section,
            "tone": tone
        })
    
    async def generate_abstract(
        self,
        title: str,
        methods: str,
        results: str,
        conclusions: str
    ) -> Dict[str, Any]:
        """Generate a research abstract."""
        return await self.call_service("abstract-generator", "generateAbstract", {
            "title": title,
            "methods": methods,
            "results": results,
            "conclusions": conclusions
        })
    
    async def generate_irb_protocol(
        self,
        study_title: str,
        principal_investigator: str,
        study_type: str,
        hypothesis: str,
        population: str,
        data_source: str,
        variables: list,
        analysis_approach: str
    ) -> Dict[str, Any]:
        """Generate an IRB protocol."""
        return await self.call_service("irb-generator", "generateProtocol", {
            "studyTitle": study_title,
            "principalInvestigator": principal_investigator,
            "studyType": study_type,
            "hypothesis": hypothesis,
            "population": population,
            "dataSource": data_source,
            "variables": variables,
            "analysisApproach": analysis_approach
        })
    
    async def health_check(self) -> Dict[str, Any]:
        """Check bridge health and available services."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with statement.")
        
        response = await self._client.get("/api/services/health")
        response.raise_for_status()
        return response.json()


# Usage example:
# async with ManuscriptClient() as client:
#     result = await client.generate_abstract(
#         title="My Research",
#         methods="We analyzed...",
#         results="We found...",
#         conclusions="Therefore..."
#     )
```

---

### 5. Updated TODO Order

```
1. Create services/orchestrator/src/routes/bridge.ts (bridge router)
2. Create packages/manuscript-engine/src/services/irb-generator.service.ts
3. Update packages/manuscript-engine/src/services/index.ts (exports)
4. Add bridge router import to services/orchestrator/routes.ts
5. Create services/worker/src/workflow_engine/bridge.py (Python client)
6. Test with curl: POST http://localhost:3000/api/services/health
```

---

## Testing Commands

After implementation, test with:

```bash
# 1. Start the orchestrator
npm run dev

# 2. Health check
curl http://localhost:3000/api/services/health

# 3. Test claude-writer
curl -X POST http://localhost:3000/api/services/claude-writer/generateParagraph \
  -H "Content-Type: application/json" \
  -d '{"topic": "test", "context": "testing", "section": "methods", "tone": "formal"}'

# 4. Python client test
cd services/worker
python -c "
import asyncio
from src.workflow_engine.bridge import ManuscriptClient

async def test():
    async with ManuscriptClient() as client:
        health = await client.health_check()
        print(health)

asyncio.run(test())
"
```
