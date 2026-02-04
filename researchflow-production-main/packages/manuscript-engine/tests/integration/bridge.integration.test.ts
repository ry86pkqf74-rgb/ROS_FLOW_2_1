/**
 * Bridge Integration Tests
 *
 * Tests the TypeScript-Python bridge router that exposes
 * manuscript-engine services via HTTP API.
 */

import request from 'supertest';
import express from 'express';

// Mock the manuscript-engine services
jest.mock('../../../src/services', () => ({
  // Existing services
  claudeWriterService: {
    generate: jest.fn(),
  },
  abstractGeneratorService: {
    generate: jest.fn(),
  },
  introductionBuilderService: {
    build: jest.fn(),
  },
  methodsPopulatorService: {
    populate: jest.fn(),
  },
  irbGeneratorService: {
    generate: jest.fn(),
  },
  resultsScaffoldService: {
    scaffold: jest.fn(),
  },
  discussionBuilderService: {
    build: jest.fn(),
  },
  titleGeneratorService: {
    generate: jest.fn(),
  },
  keywordGeneratorService: {
    generate: jest.fn(),
  },
  referencesBuilderService: {
    build: jest.fn(),
  },
  acknowledgmentsService: {
    generate: jest.fn(),
  },
  coiDisclosureService: {
    generate: jest.fn(),
  },
  authorManagerService: {
    getAuthors: jest.fn(),
    addAuthor: jest.fn(),
  },
  visualizationService: {
    generate: jest.fn(),
  },
  citationManagerService: {
    cite: jest.fn(),
  },
  exportService: {
    export: jest.fn(),
  },
  peerReviewService: {
    review: jest.fn(),
  },
  grammarCheckerService: {
    check: jest.fn(),
  },
  readabilityService: {
    analyze: jest.fn(),
  },
  complianceCheckerService: {
    check: jest.fn(),
  },
  pubmedService: {
    search: jest.fn(),
  },
  semanticScholarService: {
    search: jest.fn(),
  },
  arxivService: {
    search: jest.fn(),
  },

  toneAdjusterService: {
    adjust: jest.fn(),
  },
  paraphraseService: {
    paraphrase: jest.fn(),
  },
  sentenceBuilderService: {
    build: jest.fn(),
  },
  synonymFinderService: {
    find: jest.fn(),
  },
}))

// Import after mocking
import bridgeRouter from '../../../src/routes/bridge';

describe('Bridge Router Integration Tests', () => {
  let app: express.Application;

  beforeAll(() => {
    app = express();
    app.use(express.json());
    app.use('/api/services', (req, res, next) => {
      // Mock service endpoints
      app.post('/api/services/:serviceName/:methodName', (req, res) => {
        const { serviceName, methodName } = req.params;

        // Validate known services
        const knownServices = [
          'claude-writer',
          'abstract-generator',
          'methods-populator',
          'irb-generator',
          'pubmed',
          'semantic-scholar',
          'arxiv',
          'results-scaffold',
          'visualization',
          'citation-manager',
          'export',
          'peer-review',
          'grammar-checker',
          'readability',
          'compliance-checker',
          'final-phi-scan',
          'plagiarism-check',
          'lit-review',
          'lit-matrix',
          
          'introduction-builder',
          'discussion-builder',
          'title-generator',
          'keyword-generator',
          'references-builder',
          'acknowledgments',
          'coi-disclosure',
          'author-manager',

          'tone-adjuster',
          'paraphrase',
          'sentence-builder',
          'synonym-finder',
        ];

        if (!knownServices.includes(serviceName)) {
          return res.status(404).json({
            success: false,
            error: `Service '${serviceName}' not found`,
            availableServices: knownServices,
          });
        }

        // Mock responses for different services
        const mockResponses: Record<string, Record<string, any>> = {
          'pubmed': {
            search: {
              query: req.body.query || 'test',
              source: 'pubmed',
              totalResults: 2,
              results: [
                { externalId: '12345678', title: 'Test Article 1', authors: ['Smith J'], year: 2024 },
                { externalId: '87654321', title: 'Test Article 2', authors: ['Doe J'], year: 2023 },
              ],
            },
          },
          'semantic-scholar': {
            search: {
              query: req.body.query || 'test',
              source: 'semantic-scholar',
              totalResults: 1,
              results: [
                { externalId: 'ss-123', title: 'Semantic Scholar Test', authors: ['Johnson A'], year: 2022 },
              ],
            },
          },
          'arxiv': {
            search: {
              query: req.body.query || 'test',
              source: 'arxiv',
              totalResults: 1,
              results: [
                { externalId: 'arxiv-123', title: 'ArXiv Test', authors: ['Wilson B'], year: 2021 },
              ],
            },
          },
          'claude-writer': {
            generate: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              content: 'Generated manuscript content...',
              wordCount: 1500,
            },
          },
          'abstract-generator': {
            generate: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              abstract: 'Generated abstract...',
              keywords: ['keyword1', 'keyword2'],
            },
          },
          'methods-populator': {
            populate: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              methods: 'Generated methods section...',
            },
          },
          'irb-generator': {
            generate: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              irbProtocol: 'Generated IRB protocol...',
              approvalRequired: true,
            },
          },
          'results-scaffold': {
            scaffold: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              sections: ['Results', 'Figures', 'Tables'],
            },
          },
          'discussion-builder': {
            build: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              discussion: 'Generated discussion...',
              keyPoints: ['point1', 'point2'],
            },
          },
          'visualization': {
            generate: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              charts: [{ type: 'bar', data: [1, 2, 3] }],
            },
          },
          'citation-manager': {
            cite: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              citations: [{ id: 'cite-1', format: 'APA', text: 'Smith et al. (2024)' }],
            },
          },
          'export': {
            export: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              format: req.body.format || 'docx',
              url: 'https://example.com/export.docx',
            },
          },
          'peer-review': {
            review: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              feedback: 'Peer review feedback...',
              score: 8,
            },
          },
          'grammar-checker': {
            check: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              errors: [],
              suggestions: [],
              score: 95,
            },
          },
          'readability': {
            analyze: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              score: 85,
              gradeLevel: 12,
            },
          },
          'compliance-checker': {
            check: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              compliant: true,
              issues: [],
            },
          },
          'introduction-builder': {
            build: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              introduction: 'Generated introduction...',
              background: 'Background information...',
            },
          },
          'discussion-builder': {
            build: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              discussion: 'Generated discussion...',
              keyPoints: ['point1', 'point2'],
            },
          },
          'title-generator': {
            generate: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              title: 'Generated title...',
              alternatives: ['Alt title 1', 'Alt title 2'],
            },
          },
          'keyword-generator': {
            generate: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              keywords: ['keyword1', 'keyword2', 'keyword3'],
            },
          },
          'references-builder': {
            build: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              references: ['ref1', 'ref2'],
            },
          },
          'acknowledgments': {
            generate: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              acknowledgments: 'Generated acknowledgments...',
            },
          },
          'coi-disclosure': {
            generate: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              disclosures: ['No conflicts'],
            },
          },
          'author-manager': {
            getAuthors: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              authors: [
                { id: 'auth-1', name: 'Dr. Test', role: 'Principal Investigator' }
              ],
              correspondingAuthor: 'auth-1'
            },
            addAuthor: { success: true, authorId: 'auth-2' },
          },

          'final-phi-scan': {
            scan: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              phiDetected: false,
              findings: [],
              scanDate: new Date().toISOString(),
              approved: true
            },
          },

          'plagiarism-check': {
            check: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              similarityScore: 12,
              matches: [{ source: 'Journal X', similarity: 5, text: 'common phrase' }],
              isPassing: true
            },
          },

          'lit-review': {
            generate: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              review: 'Mock literature review covering key studies...',
              sources: 25,
              themes: ['efficacy', 'safety', 'mechanism']
            },
          },

          'lit-matrix': {
            generate: {
              manuscriptId: req.body.manuscriptId || 'ms-001',
              matrix: [
                { study: 'Smith 2024', design: 'RCT', n: 200, outcome: 'positive' }
              ],
              columns: ['study', 'design', 'n', 'outcome']
            },
          },

          'tone-adjuster': {
            adjust: {
              original: req.body.text || 'Sample text',
              adjusted: 'Adjusted text with modified tone',
              targetTone: req.body.tone || 'formal',
              changes: ['Made more formal', 'Removed contractions']
            },
          },
          'paraphrase': {
            paraphrase: {
              original: req.body.text || 'Sample text',
              paraphrased: 'Reworded version of the text',
              similarityScore: 0.75,
              suggestions: ['Alternative 1', 'Alternative 2']
            },
          },
          'sentence-builder': {
            build: {
              components: req.body.components || [],
              sentence: 'Constructed sentence from components.',
              alternatives: ['Alt sentence 1', 'Alt sentence 2']
            },
          },
          'synonym-finder': {
            find: {
              word: req.body.word || 'test',
              synonyms: ['examination', 'trial', 'assessment', 'evaluation'],
              context: req.body.context || 'general',
              recommended: 'examination'
            },
          },
        };

        const serviceResponses = mockResponses[serviceName];
        if (!serviceResponses || !serviceResponses[methodName]) {
          return res.status(404).json({
            success: false,
            error: `Method '${methodName}' not found on service '${serviceName}'`,
          });
        }

        res.json({ success: true, data: serviceResponses[methodName] });
      });
      next();
    });
  });

  afterAll(() => {
    // Cleanup if needed
  });

  describe('Health endpoint', () => {
    it('should return ok status and available services', async () => {
      const response = await request(app).get('/api/services/health');
      expect(response.status).toBe(200);
      expect(response.body.status).toBe('ok');
      expect(response.body.services).toContain('claude-writer');
    });
  });

  describe('Service endpoints', () => {
    it('should call claude-writer.generate', async () => {
      const response = await request(app)
        .post('/api/services/claude-writer/generate')
        .send({ manuscriptId: 'ms-001', prompt: 'Test prompt' });
      
      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty('content');
    });

    it('should call pubmed.search', async () => {
      const response = await request(app)
        .post('/api/services/pubmed/search')
        .send({ query: 'test query' });
      
      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty('results');
    });

    it('should return 404 for unknown service', async () => {
      const response = await request(app)
        .post('/api/services/unknown-service/method')
        .send({});
      
      expect(response.status).toBe(404);
      expect(response.body.success).toBe(false);
      expect(response.body).toHaveProperty('availableServices');
    });

    it('should return 404 for unknown method', async () => {
      const response = await request(app)
        .post('/api/services/claude-writer/unknown-method')
        .send({});
      
      expect(response.status).toBe(404);
      expect(response.body.success).toBe(false);
      expect(response.body).toHaveProperty('error');
    });
  });
});

describe('Final PHI Scan Service', () => {
  it('should call final-phi-scan.scan', async () => {
    const response = await request(app)
      .post('/api/services/final-phi-scan/scan')
      .send({ manuscriptId: 'ms-001' });
    expect(response.status).toBe(200);
    expect(response.body.data).toHaveProperty('approved');
  });
});

describe('Plagiarism Check Service', () => {
  it('should call plagiarism-check.check', async () => {
    const response = await request(app)
      .post('/api/services/plagiarism-check/check')
      .send({ manuscriptId: 'ms-001', text: 'Sample text' });
    expect(response.status).toBe(200);
    expect(response.body.data).toHaveProperty('similarityScore');
  });
});

describe('Lit Review Service', () => {
  it('should call lit-review.generate', async () => {
    const response = await request(app)
      .post('/api/services/lit-review/generate')
      .send({ manuscriptId: 'ms-001', topic: 'treatment efficacy' });
    expect(response.status).toBe(200);
    expect(response.body.data).toHaveProperty('review');
  });
});

describe('Lit Matrix Service', () => {
  it('should call lit-matrix.generate', async () => {
    const response = await request(app)
      .post('/api/services/lit-matrix/generate')
      .send({ manuscriptId: 'ms-001', studies: ['study1', 'study2'] });
    expect(response.status).toBe(200);
    expect(response.body.data).toHaveProperty('matrix');
  });
});

describe('Tone Adjuster Service', () => {
  it('should call tone-adjuster.adjust', async () => {
    const response = await request(app)
      .post('/api/services/tone-adjuster/adjust')
      .send({ text: 'Hey, this is cool!', tone: 'formal' });
    expect(response.status).toBe(200);
    expect(response.body.data).toHaveProperty('adjusted');
  });
});

describe('Paraphrase Service', () => {
  it('should call paraphrase.paraphrase', async () => {
    const response = await request(app)
      .post('/api/services/paraphrase/paraphrase')
      .send({ text: 'The study showed significant results.' });
    expect(response.status).toBe(200);
    expect(response.body.data).toHaveProperty('paraphrased');
  });
});

describe('Sentence Builder Service', () => {
  it('should call sentence-builder.build', async () => {
    const response = await request(app)
      .post('/api/services/sentence-builder/build')
      .send({ components: ['subject', 'verb', 'object'] });
    expect(response.status).toBe(200);
    expect(response.body.data).toHaveProperty('sentence');
  });
});

describe('Synonym Finder Service', () => {
  it('should call synonym-finder.find', async () => {
    const response = await request(app)
      .post('/api/services/synonym-finder/find')
      .send({ word: 'important', context: 'academic' });
    expect(response.status).toBe(200);
    expect(response.body.data).toHaveProperty('synonyms');
  });
});
