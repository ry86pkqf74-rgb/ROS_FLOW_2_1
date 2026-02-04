/**
 * Impact Tracker Bridge Service
 *
 * Provides citation / impact metrics fetching for a manuscript or DOI.
 * This version is dependency-light and uses optional external APIs if configured.
 */

export interface ImpactLookupInput {
  /** DOI (preferred) */
  doi?: string;
  /** Optional title query */
  title?: string;
  /** Optional author string */
  author?: string;
  /** Optional: maximum results */
  limit?: number;
}

export interface ImpactMetric {
  source: 'crossref' | 'openalex' | 'semantic_scholar' | 'unknown';
  citations?: number;
  influentialCitations?: number;
  year?: number;
  venue?: string;
  url?: string;
  raw?: Record<string, unknown>;
}

export interface ImpactLookupResult {
  ok: boolean;
  timestamp: string;
  query: ImpactLookupInput;
  metrics: ImpactMetric[];
  summary: {
    citations?: number;
    influentialCitations?: number;
  };
}

function toInt(x: unknown): number | undefined {
  const n = typeof x === 'number' ? x : typeof x === 'string' ? Number(x) : NaN;
  return Number.isFinite(n) ? Math.trunc(n) : undefined;
}

async function fetchJson(url: string, headers?: Record<string, string>): Promise<any> {
  const res = await fetch(url, { headers });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} from ${url}${txt ? `: ${txt}` : ''}`);
  }
  return res.json();
}

async function lookupCrossrefByDoi(doi: string): Promise<ImpactMetric | null> {
  // Crossref provides metadata; not a citation count source, but we include it as context.
  const url = `https://api.crossref.org/works/${encodeURIComponent(doi)}`;
  const data = await fetchJson(url);
  const msg = data?.message;
  if (!msg) return null;
  return {
    source: 'crossref',
    year: toInt(msg?.published?.['date-parts']?.[0]?.[0]),
    venue: msg?.container-title?.[0],
    url: msg?.URL,
    raw: { crossref: msg },
  };
}

async function lookupOpenAlexByDoi(doi: string): Promise<ImpactMetric | null> {
  const url = `https://api.openalex.org/works/https://doi.org/${encodeURIComponent(doi)}`;
  const data = await fetchJson(url);
  if (!data) return null;
  return {
    source: 'openalex',
    citations: toInt(data?.cited_by_count),
    year: toInt(data?.publication_year),
    venue: data?.host_venue?.display_name,
    url: data?.id,
    raw: { openalex: data },
  };
}

async function lookupSemanticScholarByDoi(doi: string): Promise<ImpactMetric | null> {
  // Optional key. Without a key, S2 may rate-limit; keep as best-effort.
  const fields = ['citationCount', 'influentialCitationCount', 'year', 'venue', 'url'].join(',');
  const url = `https://api.semanticscholar.org/graph/v1/paper/DOI:${encodeURIComponent(doi)}?fields=${encodeURIComponent(fields)}`;
  const headers: Record<string, string> = {};
  if (process.env.SEMANTIC_SCHOLAR_API_KEY) {
    headers['x-api-key'] = process.env.SEMANTIC_SCHOLAR_API_KEY;
  }
  const data = await fetchJson(url, headers);
  if (!data) return null;
  return {
    source: 'semantic_scholar',
    citations: toInt(data?.citationCount),
    influentialCitations: toInt(data?.influentialCitationCount),
    year: toInt(data?.year),
    venue: data?.venue,
    url: data?.url,
    raw: { semanticScholar: data },
  };
}

function summarize(metrics: ImpactMetric[]): ImpactLookupResult['summary'] {
  // Prefer Semantic Scholar for citations if present, else OpenAlex.
  const s2 = metrics.find((m) => m.source === 'semantic_scholar');
  const oa = metrics.find((m) => m.source === 'openalex');
  return {
    citations: s2?.citations ?? oa?.citations,
    influentialCitations: s2?.influentialCitations,
  };
}

/**
 * Bridge method: lookup
 */
export async function lookup(input: ImpactLookupInput): Promise<ImpactLookupResult> {
  const doi = input?.doi?.trim();
  if (!doi) {
    throw new Error('doi is required for impact lookup in this implementation');
  }

  const metrics: ImpactMetric[] = [];

  // Best-effort: do not fail entirely if one provider fails.
  const providers = [
    async () => lookupCrossrefByDoi(doi),
    async () => lookupOpenAlexByDoi(doi),
    async () => lookupSemanticScholarByDoi(doi),
  ];

  for (const p of providers) {
    try {
      const m = await p();
      if (m) metrics.push(m);
    } catch (err) {
      metrics.push({
        source: 'unknown',
        raw: { error: err instanceof Error ? err.message : String(err) },
      });
    }
  }

  return {
    ok: true,
    timestamp: new Date().toISOString(),
    query: { ...input, doi },
    metrics,
    summary: summarize(metrics),
  };
}

const impactTrackerService = { lookup };
export default impactTrackerService;
