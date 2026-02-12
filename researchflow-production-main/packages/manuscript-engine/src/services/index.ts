/**
 * Manuscript Engine Services
 * Barrel export for all services
 */

// Phase 1: Data Integration Services
export * from './phi-guard.service';
export * from './pubmed.service';
export * from './semantic-scholar.service';
export * from './arxiv.service';

// Phase 1: Writer Services
export * from './claude-writer.service';
export * from './abstract-generator.service';
export * from './introduction-builder.service';
export * from './methods-populator.service';

// Phase 2: Research Services
export * from './results-scaffold.service';
export * from './discussion-builder.service';
export * from './citation-manager.service';
export * from './visualization.service';

// Phase 3: Enhancement Services
export * from './title-generator.service';
export * from './keyword-generator.service';
export * from './references-builder.service';
export * from './acknowledgments.service';
export * from './coi-disclosure.service';
export * from './author-manager.service';

// Phase 4: Review Services
export * from './peer-review.service';
export * from './grammar-checker.service';
export * from './readability.service';
export * from './compliance-checker.service';
export * from './clarity-analyzer.service';
export * from './claim-verifier.service';
export * from './medical-nlp.service';
export * from './transition-suggester.service';

// Phase 5: Export Services
export * from './export.service';

// New services imports for singleton instances
import { AbstractGeneratorService } from './abstract-generator.service';
import { AcknowledgmentsService } from './acknowledgments.service';
import { ArxivService } from './arxiv.service';
import { AuthorManagerService } from './author-manager.service';
import { CitationManagerService } from './citation-manager.service';
import { LitReviewService } from './lit-review.service';
import { LitMatrixService } from './lit-matrix.service';
import { ClarityAnalyzerService } from './clarity-analyzer.service';
import { ClaimVerifierService } from './claim-verifier.service';
import { ClaudeWriterService } from './claude-writer.service';
import { COIDisclosureService } from './coi-disclosure.service';
import { ComplianceCheckerService } from './compliance-checker.service';
import { DiscussionBuilderService } from './discussion-builder.service';
import { ExportService } from './export.service';
import { FinalPhiScanService } from './final-phi-scan.service';
import { GrammarCheckerService } from './grammar-checker.service';
import { IntroductionBuilderService } from './introduction-builder.service';
import { IrbGeneratorService } from './irb-generator.service';
import { KeywordGeneratorService } from './keyword-generator.service';
import { MedicalNLPService } from './medical-nlp.service';
import { MethodsPopulatorService } from './methods-populator.service';
import { ParaphraseService } from './paraphrase.service';
import { PeerReviewService } from './peer-review.service';
import { PlagiarismCheckService } from './plagiarism-check.service';
import { PubMedService } from './pubmed.service';
import { ReadabilityService } from './readability.service';
import { ReferencesBuilderService } from './references-builder.service';
import { ResultsScaffoldService } from './results-scaffold.service';
import { SemanticScholarService } from './semantic-scholar.service';
import { SentenceBuilderService } from './sentence-builder.service';
import { SynonymFinderService } from './synonym-finder.service';
import { TitleGeneratorService } from './title-generator.service';
import { ToneAdjusterService } from './tone-adjuster.service';
import { TransitionSuggesterService } from './transition-suggester.service';
import { VisualizationService } from './visualization.service';

// Singleton service instances
export const pubmedService = new PubMedService();
export const semanticScholarService = new SemanticScholarService();
export const arxivService = new ArxivService();
export const claudeWriterService = new ClaudeWriterService();
export const abstractGeneratorService = new AbstractGeneratorService();
export const introductionBuilderService = new IntroductionBuilderService();
export const methodsPopulatorService = new MethodsPopulatorService();
export const irbGeneratorService = new IrbGeneratorService();
export const resultsScaffoldService = new ResultsScaffoldService();
export const discussionBuilderService = new DiscussionBuilderService();
export const titleGeneratorService = new TitleGeneratorService();
export const keywordGeneratorService = new KeywordGeneratorService();
export const referencesBuilderService = new ReferencesBuilderService();
export const acknowledgmentsService = new AcknowledgmentsService();
export const coiDisclosureService = new COIDisclosureService();
export const authorManagerService = new AuthorManagerService();
export const visualizationService = new VisualizationService();
export const citationManagerService = CitationManagerService.getInstance();
export const exportService = ExportService.getInstance();
export const peerReviewService = new PeerReviewService();
export const grammarCheckerService = new GrammarCheckerService();
export const readabilityService = new ReadabilityService();
export const complianceCheckerService = ComplianceCheckerService.getInstance();
export const finalPhiScanService = new FinalPhiScanService();
export const clarityAnalyzerService = new ClarityAnalyzerService();
export const claimVerifierService = new ClaimVerifierService();
export const medicalNLPService = new MedicalNLPService();
export const transitionSuggesterService = new TransitionSuggesterService();
export const toneAdjusterService = new ToneAdjusterService();
export const paraphraseService = new ParaphraseService();
export const sentenceBuilderService = new SentenceBuilderService();
export const synonymFinderService = new SynonymFinderService();

// Phase 2: Literature Analysis Service Instances
export const litReviewService = new LitReviewService();
export const litMatrixService = new LitMatrixService();

// Phase 5: Final Check Service Instances  
export const plagiarismCheckService = new PlagiarismCheckService();
// Note: finalPhiScanService already exists

// Zotero integration (real implementation in zotero.service.ts)
export { ZoteroService, zoteroService, type ZoteroConfig } from './zotero.service';

// Also export service classes for direct use
export {
  PubMedService,
  SemanticScholarService,
  ArxivService,
  ClaudeWriterService,
  AbstractGeneratorService,
  IntroductionBuilderService,
  MethodsPopulatorService,
  IrbGeneratorService,
  ResultsScaffoldService,
  DiscussionBuilderService,
  TitleGeneratorService,
  KeywordGeneratorService,
  ReferencesBuilderService,
  AcknowledgmentsService,
  COIDisclosureService,
  AuthorManagerService,
  VisualizationService,
  CitationManagerService,
  ExportService,
  PeerReviewService,
  GrammarCheckerService,
  ReadabilityService,
  ComplianceCheckerService,
  FinalPhiScanService,
  PlagiarismCheckService,
  LitReviewService,
  LitMatrixService,
};
