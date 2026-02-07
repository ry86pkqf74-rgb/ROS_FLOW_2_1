/**
 * IRB Generator Service
 * 
 * Generates IRB protocol documents by orchestrating ClaudeWriterService
 * and MethodsPopulatorService to create comprehensive IRB submission materials.
 */

import type { ManuscriptSection } from '../types';

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
  institution?: string;
  expectedDuration?: string;
  risks?: string[];
  benefits?: string[];
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

/**
 * IRB Generator Service
 * Orchestrates multiple services to generate comprehensive IRB protocols
 */
export class IrbGeneratorService {
  private claudeWriter: ClaudeWriterService;
  private methodsPopulator: MethodsPopulatorService;

  constructor(
    claudeWriter?: ClaudeWriterService,
    methodsPopulator?: MethodsPopulatorService
  ) {
    this.claudeWriter = claudeWriter ?? new ClaudeWriterService();
    this.methodsPopulator = methodsPopulator ?? new MethodsPopulatorService();
  }

  /**
   * Generate a complete IRB protocol document
   */
  async generateProtocol(request: IrbProtocolRequest): Promise<IrbProtocol> {
    // Generate all sections
    const sections = await this.generateSections(request);
    
    // Generate consent form
    const consentForm = await this.generateConsentForm(request);
    
    // Generate protocol number
    const protocolNumber = `IRB-${Date.now()}`;
    
    return {
      protocolNumber,
      title: request.studyTitle,
      sections,
      attachments: {
        consentFormDraft: consentForm,
        dataCollectionInstruments: []
      },
      generatedAt: new Date().toISOString()
    };
  }

  /**
   * Generate all IRB protocol sections
   */
  private async generateSections(request: IrbProtocolRequest) {
    // Background section
    const background = await this.claudeWriter.generateParagraph({
      topic: `Background and rationale for: ${request.studyTitle}`,
      context: request.hypothesis,
      keyPoints: [
        `Study type: ${request.studyType}`,
        `Population: ${request.population}`,
        `Data source: ${request.dataSource}`
      ],
      section: 'background' as ManuscriptSection,
      tone: 'formal'
    });

    // Objectives section
    const objectives = await this.claudeWriter.generateParagraph({
      topic: `Research objectives for: ${request.studyTitle}`,
      context: request.hypothesis,
      keyPoints: [
        `Primary objective: ${request.hypothesis}`,
        `Analysis approach: ${request.analysisApproach}`
      ],
      section: 'methods' as ManuscriptSection,
      tone: 'formal'
    });

    // Study design section
    const studyDesign = await this.claudeWriter.generateParagraph({
      topic: `Study design for: ${request.studyTitle}`,
      context: `This is a ${request.studyType} study`,
      keyPoints: [
        `Study type: ${request.studyType}`,
        `Data source: ${request.dataSource}`,
        `Variables: ${request.variables.join(', ')}`
      ],
      section: 'methods' as ManuscriptSection,
      tone: 'formal'
    });

    // Population section
    const population = await this.claudeWriter.generateParagraph({
      topic: `Study population for: ${request.studyTitle}`,
      context: request.population,
      keyPoints: [
        `Target population: ${request.population}`,
        `Data source: ${request.dataSource}`
      ],
      section: 'methods' as ManuscriptSection,
      tone: 'formal'
    });

    // Data collection section
    const dataCollection = await this.claudeWriter.generateParagraph({
      topic: `Data collection procedures for: ${request.studyTitle}`,
      context: `Data will be obtained from ${request.dataSource}`,
      keyPoints: [
        `Variables to be collected: ${request.variables.join(', ')}`,
        `Data source: ${request.dataSource}`
      ],
      section: 'methods' as ManuscriptSection,
      tone: 'formal'
    });

    // Data management section
    const dataManagement = await this.claudeWriter.generateParagraph({
      topic: `Data management and security for: ${request.studyTitle}`,
      context: 'Data will be stored securely and in compliance with HIPAA regulations',
      keyPoints: [
        'Secure data storage',
        'Access controls',
        'Data encryption',
        'Audit logging'
      ],
      section: 'methods' as ManuscriptSection,
      tone: 'formal'
    });

    // Statistical analysis section
    const statisticalAnalysis = await this.claudeWriter.generateParagraph({
      topic: `Statistical analysis plan for: ${request.studyTitle}`,
      context: request.analysisApproach,
      keyPoints: [
        `Analysis approach: ${request.analysisApproach}`,
        `Variables: ${request.variables.join(', ')}`
      ],
      section: 'methods' as ManuscriptSection,
      tone: 'formal'
    });

    // Ethics considerations section
    const ethicsConsiderations = await this.claudeWriter.generateParagraph({
      topic: `Ethical considerations for: ${request.studyTitle}`,
      context: 'This study will comply with all ethical guidelines and regulations',
      keyPoints: [
        'Informed consent',
        'Privacy protection',
        'Data security',
        'Minimal risk to participants'
      ],
      section: 'methods' as ManuscriptSection,
      tone: 'formal'
    });

    // Risks section
    const risks = request.risks && request.risks.length > 0
      ? request.risks.join('. ')
      : await this.claudeWriter.generateParagraph({
          topic: `Potential risks for: ${request.studyTitle}`,
          context: 'This study involves minimal risk to participants',
          keyPoints: ['Minimal risk', 'Privacy concerns', 'Data breach potential'],
          section: 'methods' as ManuscriptSection,
          tone: 'formal'
        }).then(r => r.paragraph);

    // Benefits section
    const benefits = request.benefits && request.benefits.length > 0
      ? request.benefits.join('. ')
      : await this.claudeWriter.generateParagraph({
          topic: `Potential benefits for: ${request.studyTitle}`,
          context: 'This study may contribute to scientific knowledge',
          keyPoints: ['Scientific advancement', 'Improved patient care', 'Knowledge generation'],
          section: 'methods' as ManuscriptSection,
          tone: 'formal'
        }).then(r => r.paragraph);

    // Privacy protection section
    const privacyProtection = await this.claudeWriter.generateParagraph({
      topic: `Privacy protection measures for: ${request.studyTitle}`,
      context: 'All data will be de-identified and stored securely',
      keyPoints: [
        'Data de-identification',
        'Secure storage',
        'Access controls',
        'HIPAA compliance'
      ],
      section: 'methods' as ManuscriptSection,
      tone: 'formal'
    });

    // Consent process section
    const consentProcess = await this.claudeWriter.generateParagraph({
      topic: `Informed consent process for: ${request.studyTitle}`,
      context: 'Participants will be provided with detailed information about the study',
      keyPoints: [
        'Written consent',
        'Information disclosure',
        'Right to withdraw',
        'Contact information'
      ],
      section: 'methods' as ManuscriptSection,
      tone: 'formal'
    });

    return {
      background: background.paragraph,
      objectives: objectives.paragraph,
      studyDesign: studyDesign.paragraph,
      population: population.paragraph,
      dataCollection: dataCollection.paragraph,
      dataManagement: dataManagement.paragraph,
      statisticalAnalysis: statisticalAnalysis.paragraph,
      ethicsConsiderations: ethicsConsiderations.paragraph,
      risks: typeof risks === 'string' ? risks : risks,
      benefits: typeof benefits === 'string' ? benefits : benefits,
      privacyProtection: privacyProtection.paragraph,
      consentProcess: consentProcess.paragraph
    };
  }

  /**
   * Generate consent form draft
   */
  private async generateConsentForm(request: IrbProtocolRequest): Promise<string> {
    const result = await this.claudeWriter.generateParagraph({
      topic: `Informed consent form for: ${request.studyTitle}`,
      context: `Study type: ${request.studyType}, Population: ${request.population}`,
      keyPoints: [
        'Study purpose',
        'Procedures',
        'Risks and benefits',
        'Confidentiality',
        'Right to withdraw',
        'Contact information'
      ],
      section: 'methods' as ManuscriptSection,
      tone: 'formal',
      targetLength: 500
    });
    
    return result.paragraph;
  }
}
