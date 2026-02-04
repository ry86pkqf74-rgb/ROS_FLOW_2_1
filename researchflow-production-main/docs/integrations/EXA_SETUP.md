# Exa API Setup

Exa provides **real-time web search**, code context, company research, and deep research. This guide configures Exa for use by Cursor, Composio, Claude, Notion, and the ResearchFlow app.

## 1. API Key

1. Get an API key from [dashboard.exa.ai](https://dashboard.exa.ai).
2. Set it in your environment and/or config (see below).

## 2. Environment Variable

So that the orchestrator, workers, and any server-side code can use Exa:

**Option A – Root `.env` (recommended for local dev)**

```bash
# In project root .env (create from .env.example if needed)
EXA_API_KEY=your_exa_api_key_here
```

**Option B – Shell (current session only)**

```bash
export EXA_API_KEY="your_exa_api_key_here"
```

`.env.example` and `.env.integrations.example` already include `EXA_API_KEY=`; copy to `.env` and fill in the value.

## 3. Cursor MCP (so the AI assistant can use Exa)

Cursor can use Exa via the [Exa MCP server](https://docs.exa.ai/reference/exa-mcp) for web search, code context, and research inside the IDE.

### Project-level (this repo)

1. Open `.cursor/mcp.json` in this project.
2. Replace `YOUR_EXA_API_KEY` in the URL with your real Exa API key (same value as `EXA_API_KEY` in `.env`).
3. **Do not commit your real key.** If you store the key in `.cursor/mcp.json`, add `.cursor/mcp.json` to `.gitignore` so it stays local; the repo keeps the placeholder for other developers.

Example (with key redacted):

```json
{
  "mcpServers": {
    "exa": {
      "type": "http",
      "url": "https://mcp.exa.ai/mcp?exaApiKey=YOUR_ACTUAL_KEY",
      "headers": {}
    }
  }
}
```

### User-level (all projects)

To enable Exa in every Cursor project, add the same server to your user MCP config:

- **macOS/Linux:** `~/.cursor/mcp.json`
- **Windows:** `%USERPROFILE%\.cursor\mcp.json`

If the file already has an `mcpServers` object, add the `exa` entry inside it; otherwise use the same structure as above.

### MCP tools available in Cursor

- `web_search_exa` – Real-time web search  
- `get_code_context_exa` – Code snippets, docs, examples  
- `company_research_exa` – Company information and research  
- `crawling_exa` – Extract content from URLs  
- `linkedin_search_exa` – Find people on LinkedIn  
- `deep_researcher_start` – AI-powered deep research  

Docs: [Exa MCP reference](https://docs.exa.ai/reference/exa-mcp).

## 4. Composio / Claude / Notion

- **AI orchestration:** Exa is registered in `config/ai-orchestration.json` under `providers.cloud.exa`. Any service that reads this config (e.g. orchestrator, Composio-backed flows) can use the Exa endpoint and capabilities.
- **Composio:** Add Exa as a tool/action in your Composio project and configure the connection with `EXA_API_KEY` (from env or your secrets manager).
- **Claude / Notion:** Use Exa via:
  - **Cursor + Exa MCP** (above) when working in this repo, or  
  - **Your own app** using `EXA_API_KEY` and the [Exa API](https://docs.exa.ai) or [OpenAI-compatible integration](https://docs.exa.ai/reference/openai-sdk).

## 5. Usage in code (this repo)

If you add Exa to the orchestrator or worker:

**JavaScript/TypeScript (exa-js)**

```bash
pnpm add exa-js
```

```typescript
import Exa from "exa-js";

const exa = new Exa(process.env.EXA_API_KEY);

const results = await exa.search("latest developments in AI safety research", {
  type: "auto",
  num_results: 10,
  contents: { text: { max_characters: 20000 } },
});
```

**Python (OpenAI-compatible)**

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.exa.ai",
    api_key=os.environ["EXA_API_KEY"],
)
completion = client.chat.completions.create(
    model="exa",
    messages=[{"role": "user", "content": "What are the latest developments in quantum computing?"}],
    extra_body={"text": True},
)
```

## 6. Search and content settings (reference)

- **Search type:** `auto` (balanced relevance and speed) – configured in `config/ai-orchestration.json`.
- **Content:** Full text with `max_characters: 20000` for RAG/full content; use `highlights` for snippets and lower cost.
- **Categories (optional):** `news`, `research paper`, `company`, `people`, `tweet` – see [Exa category docs](https://docs.exa.ai).

## 7. Resources

- [Exa docs](https://docs.exa.ai)  
- [Exa dashboard](https://dashboard.exa.ai)  
- [Exa MCP for Cursor](https://docs.exa.ai/reference/exa-mcp)  
- [Exa OpenAI SDK](https://docs.exa.ai/reference/openai-sdk)  
- [API status](https://status.exa.ai)
