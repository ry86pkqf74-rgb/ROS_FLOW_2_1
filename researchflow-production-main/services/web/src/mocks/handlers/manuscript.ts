/**
 * Manuscript Mock Handlers
 * 
 * MSW handlers for manuscript/document API endpoints
 */

import { http, HttpResponse, delay } from 'msw';

// Types
type ManuscriptStatus = 'draft' | 'in_review' | 'approved' | 'published' | 'archived';

interface ManuscriptSection {
  id: string;
  title: string;
  content: string;
  order: number;
  wordCount: number;
}

interface ManuscriptComment {
  id: string;
  sectionId: string;
  author: { id: string; name: string; avatar?: string };
  content: string;
  createdAt: string;
  resolved: boolean;
  replies: Array<{
    id: string;
    author: { id: string; name: string };
    content: string;
    createdAt: string;
  }>;
}

interface Manuscript {
  id: string;
  title: string;
  status: ManuscriptStatus;
  authors: Array<{ id: string; name: string; affiliation: string }>;
  sections: ManuscriptSection[];
  comments: ManuscriptComment[];
  createdAt: string;
  updatedAt: string;
  wordCount: number;
  targetJournal?: string;
}

// Mock data
const mockManuscripts: Manuscript[] = [
  {
    id: 'ms-001',
    title: 'Machine Learning Approaches for Early Detection of Cardiovascular Disease',
    status: 'in_review',
    authors: [
      { id: 'u1', name: 'Dr. Sarah Chen', affiliation: 'Stanford University' },
      { id: 'u2', name: 'Dr. James Wilson', affiliation: 'MIT' },
    ],
    sections: [
      { id: 's1', title: 'Abstract', content: 'Background: Cardiovascular disease remains...', order: 1, wordCount: 250 },
      { id: 's2', title: 'Introduction', content: 'The global burden of cardiovascular disease...', order: 2, wordCount: 800 },
      { id: 's3', title: 'Methods', content: 'We conducted a retrospective cohort study...', order: 3, wordCount: 1200 },
      { id: 's4', title: 'Results', content: 'A total of 15,432 patients were included...', order: 4, wordCount: 1500 },
      { id: 's5', title: 'Discussion', content: 'Our findings demonstrate that...', order: 5, wordCount: 1800 },
      { id: 's6', title: 'Conclusion', content: 'Machine learning models show promise...', order: 6, wordCount: 400 },
    ],
    comments: [
      {
        id: 'c1',
        sectionId: 's3',
        author: { id: 'r1', name: 'Reviewer 1' },
        content: 'Please clarify the inclusion/exclusion criteria.',
        createdAt: new Date(Date.now() - 86400000).toISOString(),
        resolved: false,
        replies: [
          {
            id: 'r1',
            author: { id: 'u1', name: 'Dr. Sarah Chen' },
            content: 'We have added more detail in the revised methods section.',
            createdAt: new Date(Date.now() - 43200000).toISOString(),
          },
        ],
      },
      {
        id: 'c2',
        sectionId: 's4',
        author: { id: 'r2', name: 'Reviewer 2' },
        content: 'The confidence intervals should be reported for all primary outcomes.',
        createdAt: new Date(Date.now() - 172800000).toISOString(),
        resolved: true,
        replies: [],
      },
    ],
    createdAt: new Date(Date.now() - 2592000000).toISOString(),
    updatedAt: new Date(Date.now() - 86400000).toISOString(),
    wordCount: 5950,
    targetJournal: 'JAMA Cardiology',
  },
  {
    id: 'ms-002',
    title: 'Novel Biomarkers for Alzheimer\'s Disease Progression',
    status: 'draft',
    authors: [
      { id: 'u3', name: 'Dr. Maria Garcia', affiliation: 'Johns Hopkins' },
    ],
    sections: [
      { id: 's1', title: 'Abstract', content: 'Objective: To identify...', order: 1, wordCount: 200 },
      { id: 's2', title: 'Introduction', content: 'Alzheimer\'s disease affects...', order: 2, wordCount: 600 },
    ],
    comments: [],
    createdAt: new Date(Date.now() - 604800000).toISOString(),
    updatedAt: new Date().toISOString(),
    wordCount: 800,
  },
];

export const manuscriptHandlers = [
  /**
   * List manuscripts
   */
  http.get('/api/manuscripts', async ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const forceEmpty = url.searchParams.get('_empty');
    
    await delay(200);
    
    if (forceEmpty === 'true') {
      return HttpResponse.json({ manuscripts: [], total: 0 });
    }
    
    let filtered = mockManuscripts;
    if (status) {
      filtered = mockManuscripts.filter(m => m.status === status);
    }
    
    return HttpResponse.json({
      manuscripts: filtered.map(m => ({
        id: m.id,
        title: m.title,
        status: m.status,
        authors: m.authors,
        updatedAt: m.updatedAt,
        wordCount: m.wordCount,
        targetJournal: m.targetJournal,
      })),
      total: filtered.length,
    });
  }),

  /**
   * Get manuscript by ID
   */
  http.get('/api/manuscripts/:id', async ({ params, request }) => {
    const url = new URL(request.url);
    const forceStatus = url.searchParams.get('_status') as ManuscriptStatus | null;
    
    await delay(150);
    
    const manuscript = mockManuscripts.find(m => m.id === params.id);
    
    if (!manuscript) {
      return new HttpResponse(null, { status: 404 });
    }
    
    if (forceStatus) {
      return HttpResponse.json({ ...manuscript, status: forceStatus });
    }
    
    return HttpResponse.json(manuscript);
  }),

  /**
   * Create manuscript
   */
  http.post('/api/manuscripts', async ({ request }) => {
    const body = await request.json() as { title: string; targetJournal?: string };
    
    await delay(300);
    
    const newManuscript: Manuscript = {
      id: `ms-${Date.now()}`,
      title: body.title,
      status: 'draft',
      authors: [{ id: 'current-user', name: 'Current User', affiliation: 'Institution' }],
      sections: [
        { id: 's1', title: 'Abstract', content: '', order: 1, wordCount: 0 },
      ],
      comments: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      wordCount: 0,
      targetJournal: body.targetJournal,
    };
    
    mockManuscripts.unshift(newManuscript);
    
    return HttpResponse.json(newManuscript, { status: 201 });
  }),

  /**
   * Update manuscript section
   */
  http.patch('/api/manuscripts/:id/sections/:sectionId', async ({ params, request }) => {
    const body = await request.json() as { content?: string; title?: string };
    
    await delay(200);
    
    const manuscript = mockManuscripts.find(m => m.id === params.id);
    if (!manuscript) {
      return new HttpResponse(null, { status: 404 });
    }
    
    const section = manuscript.sections.find(s => s.id === params.sectionId);
    if (!section) {
      return new HttpResponse(null, { status: 404 });
    }
    
    if (body.content !== undefined) {
      section.content = body.content;
      section.wordCount = body.content.split(/\s+/).filter(Boolean).length;
    }
    if (body.title !== undefined) {
      section.title = body.title;
    }
    
    manuscript.updatedAt = new Date().toISOString();
    manuscript.wordCount = manuscript.sections.reduce((sum, s) => sum + s.wordCount, 0);
    
    return HttpResponse.json(section);
  }),

  /**
   * Add comment
   */
  http.post('/api/manuscripts/:id/comments', async ({ params, request }) => {
    const body = await request.json() as { sectionId: string; content: string };
    
    await delay(200);
    
    const manuscript = mockManuscripts.find(m => m.id === params.id);
    if (!manuscript) {
      return new HttpResponse(null, { status: 404 });
    }
    
    const newComment: ManuscriptComment = {
      id: `c-${Date.now()}`,
      sectionId: body.sectionId,
      author: { id: 'current-user', name: 'Current User' },
      content: body.content,
      createdAt: new Date().toISOString(),
      resolved: false,
      replies: [],
    };
    
    manuscript.comments.push(newComment);
    
    return HttpResponse.json(newComment, { status: 201 });
  }),

  /**
   * Resolve comment
   */
  http.patch('/api/manuscripts/:id/comments/:commentId/resolve', async ({ params }) => {
    await delay(150);
    
    const manuscript = mockManuscripts.find(m => m.id === params.id);
    if (!manuscript) {
      return new HttpResponse(null, { status: 404 });
    }
    
    const comment = manuscript.comments.find(c => c.id === params.commentId);
    if (!comment) {
      return new HttpResponse(null, { status: 404 });
    }
    
    comment.resolved = true;
    
    return HttpResponse.json(comment);
  }),

  /**
   * Submit for review
   */
  http.post('/api/manuscripts/:id/submit', async ({ params }) => {
    await delay(300);
    
    const manuscript = mockManuscripts.find(m => m.id === params.id);
    if (!manuscript) {
      return new HttpResponse(null, { status: 404 });
    }
    
    manuscript.status = 'in_review';
    manuscript.updatedAt = new Date().toISOString();
    
    return HttpResponse.json(manuscript);
  }),
];

export default manuscriptHandlers;
