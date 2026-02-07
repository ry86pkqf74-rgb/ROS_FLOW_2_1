import { describe, it, expect } from 'vitest';

import { __stage2TestUtils } from '@apps/api-node/src/services/workflow-stages/worker';

describe('Stage 2 DEMO pipeline helpers', () => {
  it('buildStage2ScreeningCriteria derives defaults and applies overrides', () => {
    const criteria = __stage2TestUtils.buildStage2ScreeningCriteria({
      include_keywords: ['diabetes', 'metformin'],
      exclude_keywords: ['pediatric'],
      mesh_terms: ['Diabetes Mellitus, Type 2'],
      study_types: ['randomized_controlled_trial'],
      year_range: { from: 2018, to: 2024 },
      require_abstract: true,
      criteria: {
        year_min: 2020, // override
        inclusion: ['override-term'],
      },
    });

    expect(criteria.require_abstract).toBe(true);
    expect(criteria.year_min).toBe(2020);
    expect(criteria.year_max).toBe(2024);
    expect(criteria.study_types_required).toEqual(['randomized_controlled_trial']);
    expect(criteria.inclusion).toEqual(['override-term']);
    expect(criteria.excluded_keywords).toEqual(['pediatric']);
  });

  it('buildRagDocumentsFromPapers builds docId/text and skips empty entries', () => {
    const docs = __stage2TestUtils.buildRagDocumentsFromPapers(
      [
        { pmid: '123', title: 'Title A', abstract: 'Abstract A', year: 2020, doi: '10.1/a' },
        { id: '456', title: 'Title B', abstract: '', year: 2021 },
        { pmid: null, title: 'No ID', abstract: 'Abstract' },
        { pmid: '789', title: '', abstract: '' }, // no text
      ],
      'clinical'
    );

    expect(docs.map((d) => d.docId)).toEqual(['123', '456']);
    expect(docs[0].text).toContain('Title A');
    expect(docs[0].text).toContain('Abstract A');
    expect(docs[0].metadata.domainId).toBe('clinical');
  });

  it('buildGroundingPackFromRetrieve maps chunks into both chunks[] and sources[]', () => {
    const gp = __stage2TestUtils.buildGroundingPackFromRetrieve({
      status: 'ok',
      outputs: {
        chunks: [
          { chunk_id: 'c1', doc_id: 'd1', text: 't1', score: 0.9, metadata: { docId: 'd1' } },
          { chunk_id: 'c2', doc_id: 'd2', text: 't2', score: 0.8, metadata: {} },
        ],
        retrieval_trace: { stages: ['semantic', 'bm25'] },
      },
      artifacts: ['c1', 'c2'],
    });

    expect(gp).not.toBeNull();
    expect(gp?.chunks).toHaveLength(2);
    expect(gp?.citations).toEqual(['c1', 'c2']);
    expect(gp?.sources).toHaveLength(2);
    expect(gp?.sources[0].id).toBe('c1');
    expect(gp?.retrieval_trace?.stages).toEqual(['semantic', 'bm25']);
  });

  it('deriveClaimsFromExtraction pulls key_results and dedupes', () => {
    const claims = __stage2TestUtils.deriveClaimsFromExtraction({
      status: 'ok',
      outputs: {
        extraction_table: [
          { key_results: 'Claim A' },
          { key_results: ['Claim B', 'Claim A'] },
          { key_results: '' },
        ],
      },
    });

    expect(claims).toEqual(['Claim A', 'Claim B']);
  });
});

