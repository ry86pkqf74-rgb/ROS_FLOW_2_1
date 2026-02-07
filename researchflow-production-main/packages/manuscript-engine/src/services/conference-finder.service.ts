/**
 * Conference Finder Service
 *
 * Discovers relevant academic conferences for manuscript submission
 * and conference presentation opportunities.
 */

export interface Conference {
  id: string;
  name: string;
  acronym: string;
  url: string;
  abstractDeadline: Date | null;
  fullPaperDeadline: Date | null;
  conferenceDate: Date;
  location: string;
  topics: string[];
  impactScore: number; // 1-10 ranking
}

export interface ConferenceSearchInput {
  keywords: string[];
  field?: string; // e.g., "oncology", "cardiology", "AI/ML"
  startDate?: Date;
  endDate?: Date;
  maxResults?: number;
}

export class ConferenceFinderService {
  private staticConferences: Conference[] = [
    // Major medical conferences with typical deadline months
    {
      id: 'asco-annual',
      name: 'ASCO Annual Meeting',
      acronym: 'ASCO',
      url: 'https://conferences.asco.org/am',
      abstractDeadline: new Date('2026-02-15'), // Typically February
      fullPaperDeadline: null,
      conferenceDate: new Date('2026-06-01'), // Typically early June
      location: 'Chicago, IL',
      topics: ['oncology', 'cancer', 'immunotherapy', 'clinical trials'],
      impactScore: 10,
    },
    {
      id: 'acc-annual',
      name: 'ACC Annual Scientific Session',
      acronym: 'ACC',
      url: 'https://accscientificsession.acc.org',
      abstractDeadline: new Date('2025-10-15'), // Typically October
      fullPaperDeadline: null,
      conferenceDate: new Date('2026-03-15'),
      location: 'New Orleans, LA',
      topics: ['cardiology', 'heart failure', 'interventional', 'electrophysiology'],
      impactScore: 9,
    },
    {
      id: 'aha-sessions',
      name: 'AHA Scientific Sessions',
      acronym: 'AHA',
      url: 'https://professional.heart.org/sessions',
      abstractDeadline: new Date('2026-06-01'),
      fullPaperDeadline: null,
      conferenceDate: new Date('2026-11-15'),
      location: 'Chicago, IL',
      topics: ['cardiology', 'stroke', 'vascular', 'hypertension'],
      impactScore: 9,
    },
    {
      id: 'aacr-annual',
      name: 'AACR Annual Meeting',
      acronym: 'AACR',
      url: 'https://www.aacr.org/meeting/aacr-annual-meeting',
      abstractDeadline: new Date('2025-11-15'),
      fullPaperDeadline: null,
      conferenceDate: new Date('2026-04-10'),
      location: 'San Diego, CA',
      topics: ['cancer research', 'oncology', 'molecular biology', 'immunology'],
      impactScore: 9,
    },
    {
      id: 'esmo-congress',
      name: 'ESMO Congress',
      acronym: 'ESMO',
      url: 'https://www.esmo.org/meetings/esmo-congress',
      abstractDeadline: new Date('2026-05-01'),
      fullPaperDeadline: null,
      conferenceDate: new Date('2026-09-20'),
      location: 'Barcelona, Spain',
      topics: ['oncology', 'cancer', 'clinical trials', 'translational research'],
      impactScore: 9,
    },
    {
      id: 'ats-conference',
      name: 'ATS International Conference',
      acronym: 'ATS',
      url: 'https://conference.thoracic.org',
      abstractDeadline: new Date('2026-01-15'),
      fullPaperDeadline: null,
      conferenceDate: new Date('2026-05-17'),
      location: 'San Francisco, CA',
      topics: ['pulmonology', 'respiratory', 'critical care', 'sleep medicine'],
      impactScore: 8,
    },
    {
      id: 'easd-meeting',
      name: 'EASD Annual Meeting',
      acronym: 'EASD',
      url: 'https://www.easd.org/annual-meeting',
      abstractDeadline: new Date('2026-04-15'),
      fullPaperDeadline: null,
      conferenceDate: new Date('2026-09-15'),
      location: 'Madrid, Spain',
      topics: ['diabetes', 'endocrinology', 'metabolism', 'obesity'],
      impactScore: 8,
    },
    {
      id: 'ada-sessions',
      name: 'ADA Scientific Sessions',
      acronym: 'ADA',
      url: 'https://professional.diabetes.org/scientific-sessions',
      abstractDeadline: new Date('2026-01-10'),
      fullPaperDeadline: null,
      conferenceDate: new Date('2026-06-20'),
      location: 'New Orleans, LA',
      topics: ['diabetes', 'endocrinology', 'metabolism', 'insulin'],
      impactScore: 8,
    },
    {
      id: 'ash-annual',
      name: 'ASH Annual Meeting',
      acronym: 'ASH',
      url: 'https://www.hematology.org/meetings/annual-meeting',
      abstractDeadline: new Date('2026-08-01'),
      fullPaperDeadline: null,
      conferenceDate: new Date('2026-12-05'),
      location: 'San Diego, CA',
      topics: ['hematology', 'blood disorders', 'leukemia', 'lymphoma'],
      impactScore: 9,
    },
    {
      id: 'acr-convergence',
      name: 'ACR Convergence',
      acronym: 'ACR',
      url: 'https://www.rheumatology.org/annual-meeting',
      abstractDeadline: new Date('2026-06-01'),
      fullPaperDeadline: null,
      conferenceDate: new Date('2026-11-10'),
      location: 'Washington, DC',
      topics: ['rheumatology', 'autoimmune', 'arthritis', 'lupus'],
      impactScore: 8,
    },
  ];

  /**
   * Search for conferences matching the given criteria
   */
  async searchConferences(input: ConferenceSearchInput): Promise<Conference[]> {
    const { keywords, field, startDate, endDate, maxResults = 10 } = input;

    const results = this.staticConferences.filter(conf => {
      // Filter by date range
      if (startDate && conf.conferenceDate < startDate) return false;
      if (endDate && conf.conferenceDate > endDate) return false;

      // Filter by field/keywords match
      const searchTerms = [...keywords, field].filter(Boolean).map(k => k!.toLowerCase());
      if (searchTerms.length === 0) return true;

      const confTopics = conf.topics.map(t => t.toLowerCase());
      const confName = conf.name.toLowerCase();

      return searchTerms.some(term =>
        confTopics.some(topic => topic.includes(term) || term.includes(topic)) ||
        confName.includes(term)
      );
    });

    // Sort by impact score and deadline proximity
    results.sort((a, b) => {
      // Higher impact score first
      if (b.impactScore !== a.impactScore) {
        return b.impactScore - a.impactScore;
      }
      // Earlier deadline first (for upcoming deadlines)
      const now = new Date();
      const aDeadline = a.abstractDeadline?.getTime() || Infinity;
      const bDeadline = b.abstractDeadline?.getTime() || Infinity;
      if (aDeadline > now.getTime() && bDeadline > now.getTime()) {
        return aDeadline - bDeadline;
      }
      return 0;
    });

    return results.slice(0, maxResults);
  }

  /**
   * Get details for a specific conference by ID
   */
  async getConferenceDetails(conferenceId: string): Promise<Conference | null> {
    return this.staticConferences.find(c => c.id === conferenceId) || null;
  }

  /**
   * Get conferences with upcoming deadlines
   */
  async getUpcomingDeadlines(daysAhead: number = 90): Promise<Conference[]> {
    const now = new Date();
    const cutoff = new Date(now.getTime() + daysAhead * 24 * 60 * 60 * 1000);

    return this.staticConferences
      .filter(conf => {
        const deadline = conf.abstractDeadline;
        return deadline && deadline > now && deadline <= cutoff;
      })
      .sort((a, b) => {
        const aTime = a.abstractDeadline?.getTime() || 0;
        const bTime = b.abstractDeadline?.getTime() || 0;
        return aTime - bTime;
      });
  }

  /**
   * Get all available conferences
   */
  async getAllConferences(): Promise<Conference[]> {
    return [...this.staticConferences];
  }
}

export const conferenceFinderService = new ConferenceFinderService();
