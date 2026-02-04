"""
Specialized Protocol Templates for Different Study Domains

This module provides domain-specific protocol templates optimized for:
- Oncology studies
- Cardiovascular trials
- Pediatric research
- Rare disease studies
- Device trials
- Digital health studies
- Vaccine trials

Author: Stage 3.2 Enhancement Team
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .protocol_generator import (
    ProtocolTemplate, ProtocolSection, TemplateType, 
    RegulatoryFramework, ProtocolFormat
)

# Configure logging
logger = logging.getLogger(__name__)


class SpecializedTemplateFactory:
    """Factory for creating domain-specific protocol templates."""
    
    def __init__(self, template_version: str = "v1.2"):
        self.template_version = template_version
        self.template_registry = {}
        self._initialize_specialized_templates()
    
    def _initialize_specialized_templates(self):
        """Initialize all specialized templates."""
        try:
            # Create specialized templates
            self.template_registry.update({
                "oncology_phase1": self._create_oncology_phase1_template(),
                "oncology_phase2": self._create_oncology_phase2_template(),
                "oncology_phase3": self._create_oncology_phase3_template(),
                "cardiovascular_device": self._create_cardiovascular_device_template(),
                "cardiovascular_drug": self._create_cardiovascular_drug_template(),
                "pediatric_safety": self._create_pediatric_safety_template(),
                "pediatric_efficacy": self._create_pediatric_efficacy_template(),
                "rare_disease_natural_history": self._create_rare_disease_template(),
                "digital_health_app": self._create_digital_health_template(),
                "vaccine_safety": self._create_vaccine_safety_template(),
                "vaccine_efficacy": self._create_vaccine_efficacy_template(),
                "surgical_procedure": self._create_surgical_template(),
                "behavioral_intervention": self._create_behavioral_template()
            })
            
            logger.info(f"Initialized {len(self.template_registry)} specialized templates")
            
        except Exception as e:
            logger.error(f"Error initializing specialized templates: {str(e)}")
    
    def get_template(self, template_id: str) -> Optional[ProtocolTemplate]:
        """Get a specialized template by ID."""
        return self.template_registry.get(template_id)
    
    def get_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available specialized templates."""
        templates_info = {}
        
        for template_id, template in self.template_registry.items():
            templates_info[template_id] = {
                "name": template.name,
                "description": template.description,
                "type": template.template_type.value,
                "version": template.version,
                "regulatory_frameworks": [fw.value for fw in template.regulatory_frameworks],
                "sections_count": len(template.sections),
                "required_variables": template.required_variables
            }
        
        return templates_info
    
    def _create_oncology_phase1_template(self) -> ProtocolTemplate:
        """Create Phase I oncology trial template."""
        sections = [
            ProtocolSection(
                section_id="title_page",
                title="Title Page",
                content="""**Study Title:** {{study_title}}
**Protocol Number:** {{protocol_number}}
**Phase:** Phase I {{study_phase_details}}
**Principal Investigator:** {{principal_investigator}}
**Medical Monitor:** {{medical_monitor}}
**Sponsor:** {{sponsor}}

**Cancer Type:** {{cancer_type}}
**Target Population:** {{target_population}}

**Version:** {{protocol_version}}
**Date:** {{protocol_date}}""",
                required=True,
                regulatory_requirements=[RegulatoryFramework.FDA_IND, RegulatoryFramework.ICH_GCP]
            ),
            ProtocolSection(
                section_id="dose_escalation",
                title="Dose Escalation Design",
                content="""## Primary Objective
To determine the maximum tolerated dose (MTD) and dose-limiting toxicities (DLTs) of {{investigational_product}} in patients with {{cancer_type}}.

## Dose Escalation Schema
**Starting Dose:** {{starting_dose}} {{dose_units}}
**Dose Escalation Rule:** {{escalation_rule}}
**Maximum Planned Dose:** {{max_dose}} {{dose_units}}

## Dose-Limiting Toxicity Definition
{{dlt_definition}}

## Cohort Size and Expansion
- Initial cohorts: {{initial_cohort_size}} patients
- Expansion cohort: {{expansion_cohort_size}} patients (if MTD established)

## Safety Review Committee
{{safety_committee_composition}}""",
                required=True,
                template_variables=["investigational_product", "cancer_type", "starting_dose", "escalation_rule"]
            ),
            ProtocolSection(
                section_id="eligibility_oncology",
                title="Eligibility Criteria",
                content="""## Inclusion Criteria
1. **Age:** ≥{{minimum_age}} years
2. **Histologically confirmed** {{cancer_type}}
3. **Performance Status:** ECOG {{max_ecog_score}} or better
4. **Prior Therapy:** {{prior_therapy_requirements}}
5. **Organ Function:**
   - Absolute neutrophil count ≥{{min_anc}}/μL
   - Platelet count ≥{{min_platelets}}/μL
   - Hemoglobin ≥{{min_hemoglobin}} g/dL
   - Total bilirubin ≤{{max_bilirubin}} × ULN
   - ALT/AST ≤{{max_alt_ast}} × ULN
   - Creatinine clearance ≥{{min_creatinine_clearance}} mL/min

## Exclusion Criteria
1. **Active CNS metastases** (unless previously treated and stable)
2. **Concurrent malignancy** (except {{allowed_concurrent_cancers}})
3. **Recent major surgery** within {{surgery_washout_days}} days
4. **Prior exposure** to {{investigational_product}} or similar agents
5. **Active infection** requiring systemic therapy
6. **Pregnancy or lactation**
7. **Significant cardiovascular disease**""",
                required=True
            ),
            ProtocolSection(
                section_id="safety_monitoring",
                title="Safety Monitoring and Reporting",
                content="""## Safety Monitoring Plan
{{safety_monitoring_plan}}

## Adverse Event Reporting
- **Serious Adverse Events:** Report within 24 hours
- **Safety Reports:** Monthly summary reports
- **Data Safety Monitoring Board:** {{dsmb_schedule}}

## Stopping Rules
{{stopping_rules}}

## Emergency Procedures
{{emergency_procedures}}""",
                required=True,
                regulatory_requirements=[RegulatoryFramework.FDA_IND, RegulatoryFramework.ICH_GCP]
            )
        ]
        
        return ProtocolTemplate(
            template_id="oncology_phase1",
            name="Phase I Oncology Trial Template",
            description="Specialized template for Phase I oncology dose-escalation studies",
            template_type=TemplateType.ONCOLOGY_STUDY,
            version=self.template_version,
            sections=sections,
            regulatory_frameworks=[RegulatoryFramework.FDA_IND, RegulatoryFramework.ICH_GCP],
            required_variables=[
                "study_title", "investigational_product", "cancer_type",
                "starting_dose", "escalation_rule", "principal_investigator"
            ],
            created_date=datetime.now()
        )
    
    def _create_cardiovascular_device_template(self) -> ProtocolTemplate:
        """Create cardiovascular device study template."""
        sections = [
            ProtocolSection(
                section_id="device_description",
                title="Investigational Device Description",
                content="""## Device Information
**Device Name:** {{device_name}}
**Manufacturer:** {{device_manufacturer}}
**Device Classification:** {{device_classification}}
**FDA Submission:** {{fda_submission_type}} ({{submission_number}})

## Device Specifications
{{device_specifications}}

## Mechanism of Action
{{device_mechanism}}

## Prior Clinical Experience
{{device_prior_experience}}

## Risk Analysis
{{device_risk_analysis}}""",
                required=True,
                regulatory_requirements=[RegulatoryFramework.FDA_IDE]
            ),
            ProtocolSection(
                section_id="cardiovascular_endpoints",
                title="Cardiovascular Endpoints",
                content="""## Primary Endpoint
{{primary_cv_endpoint}}

**Primary Endpoint Definition:** {{primary_endpoint_definition}}
**Assessment Method:** {{primary_endpoint_assessment}}
**Timing:** {{primary_endpoint_timing}}

## Secondary Endpoints
{{secondary_cv_endpoints}}

## Safety Endpoints
- Major Adverse Cardiovascular Events (MACE)
- Device-related complications
- Procedure-related complications

## Endpoint Adjudication
{{endpoint_adjudication_process}}""",
                required=True
            ),
            ProtocolSection(
                section_id="imaging_assessments",
                title="Cardiovascular Imaging",
                content="""## Required Imaging Studies
{{required_imaging}}

## Imaging Schedule
- **Baseline:** {{baseline_imaging}}
- **Follow-up:** {{followup_imaging_schedule}}

## Imaging Core Laboratory
{{imaging_core_lab}}

## Image Quality Requirements
{{image_quality_requirements}}""",
                required=True
            )
        ]
        
        return ProtocolTemplate(
            template_id="cardiovascular_device",
            name="Cardiovascular Device Study Template",
            description="Template for cardiovascular device clinical trials",
            template_type=TemplateType.DEVICE_STUDY,
            version=self.template_version,
            sections=sections,
            regulatory_frameworks=[RegulatoryFramework.FDA_IDE, RegulatoryFramework.ICH_GCP],
            required_variables=[
                "study_title", "device_name", "primary_cv_endpoint", "principal_investigator"
            ],
            created_date=datetime.now()
        )
    
    def _create_pediatric_safety_template(self) -> ProtocolTemplate:
        """Create pediatric safety study template."""
        sections = [
            ProtocolSection(
                section_id="pediatric_population",
                title="Pediatric Population Considerations",
                content="""## Age Groups
{{age_group_stratification}}

## Pediatric Dose Rationale
{{pediatric_dose_rationale}}

## Growth and Development Considerations
{{growth_development_considerations}}

## Pediatric Formulation
{{pediatric_formulation}}""",
                required=True
            ),
            ProtocolSection(
                section_id="pediatric_safety",
                title="Pediatric Safety Considerations",
                content="""## Age-Specific Safety Monitoring
{{age_specific_safety}}

## Developmental Toxicity Assessment
{{developmental_toxicity}}

## Growth Monitoring
- Height and weight at each visit
- Growth velocity assessment
- Pubertal development staging (if applicable)

## Neurocognitive Assessment
{{neurocognitive_assessment}}

## Pediatric Data Safety Monitoring Board
{{pediatric_dsmb}}""",
                required=True
            ),
            ProtocolSection(
                section_id="informed_consent_pediatric",
                title="Informed Consent/Assent Process",
                content="""## Parental/Guardian Consent
{{parental_consent_process}}

## Pediatric Assent
**Ages {{assent_age_range}}:** Simplified assent process
**Ages {{full_assent_age_range}}:** Full assent process

## Capacity Assessment
{{capacity_assessment}}

## Consent/Assent Documentation
{{consent_documentation}}""",
                required=True
            )
        ]
        
        return ProtocolTemplate(
            template_id="pediatric_safety",
            name="Pediatric Safety Study Template",
            description="Template for pediatric safety and pharmacokinetic studies",
            template_type=TemplateType.PEDIATRIC_STUDY,
            version=self.template_version,
            sections=sections,
            regulatory_frameworks=[RegulatoryFramework.FDA_IND, RegulatoryFramework.ICH_GCP],
            required_variables=[
                "study_title", "age_group_stratification", "pediatric_dose_rationale", "principal_investigator"
            ],
            created_date=datetime.now()
        )
    
    def _create_rare_disease_template(self) -> ProtocolTemplate:
        """Create rare disease natural history template."""
        sections = [
            ProtocolSection(
                section_id="rare_disease_background",
                title="Rare Disease Background",
                content="""## Disease Description
{{rare_disease_description}}

## Epidemiology
**Prevalence:** {{disease_prevalence}}
**Geographic Distribution:** {{geographic_distribution}}
**Age of Onset:** {{age_of_onset}}

## Natural History
{{disease_natural_history}}

## Current Standard of Care
{{current_standard_care}}

## Unmet Medical Need
{{unmet_medical_need}}""",
                required=True
            ),
            ProtocolSection(
                section_id="registry_objectives",
                title="Registry Study Objectives",
                content="""## Primary Objectives
{{primary_registry_objectives}}

## Secondary Objectives
{{secondary_registry_objectives}}

## Exploratory Objectives
{{exploratory_registry_objectives}}

## Patient Reported Outcomes
{{patient_reported_outcomes}}""",
                required=True
            ),
            ProtocolSection(
                section_id="data_collection_rare",
                title="Data Collection Strategy",
                content="""## Data Collection Schedule
{{data_collection_schedule}}

## Core Data Elements
{{core_data_elements}}

## Biospecimen Collection
{{biospecimen_collection}}

## Patient Registry Portal
{{patient_registry_portal}}

## Long-term Follow-up
{{longterm_followup_plan}}""",
                required=True
            )
        ]
        
        return ProtocolTemplate(
            template_id="rare_disease_natural_history",
            name="Rare Disease Natural History Study Template",
            description="Template for rare disease registry and natural history studies",
            template_type=TemplateType.RARE_DISEASE_STUDY,
            version=self.template_version,
            sections=sections,
            regulatory_frameworks=[RegulatoryFramework.HIPAA, RegulatoryFramework.INSTITUTIONAL],
            required_variables=[
                "study_title", "rare_disease_description", "primary_registry_objectives", "principal_investigator"
            ],
            created_date=datetime.now()
        )
    
    def _create_digital_health_template(self) -> ProtocolTemplate:
        """Create digital health study template."""
        sections = [
            ProtocolSection(
                section_id="digital_intervention",
                title="Digital Health Intervention",
                content="""## Digital Platform Description
{{digital_platform_description}}

## Technology Components
{{technology_components}}

## User Interface Design
{{user_interface_design}}

## Data Security and Privacy
{{data_security_measures}}

## Technical Requirements
**Device Compatibility:** {{device_compatibility}}
**Internet Requirements:** {{internet_requirements}}
**Operating System:** {{operating_system_requirements}}""",
                required=True
            ),
            ProtocolSection(
                section_id="digital_endpoints",
                title="Digital Health Endpoints",
                content="""## Digital Biomarkers
{{digital_biomarkers}}

## App Usage Metrics
- Session duration
- Feature utilization
- Engagement patterns
- Adherence rates

## Patient-Reported Outcomes via App
{{digital_pro_measures}}

## Real-World Evidence Collection
{{real_world_evidence}}""",
                required=True
            ),
            ProtocolSection(
                section_id="data_management_digital",
                title="Digital Data Management",
                content="""## Data Capture Methods
{{data_capture_methods}}

## Cloud Infrastructure
{{cloud_infrastructure}}

## Data Analytics Platform
{{analytics_platform}}

## Quality Assurance for Digital Data
{{digital_data_qa}}

## Remote Monitoring
{{remote_monitoring_plan}}""",
                required=True
            )
        ]
        
        return ProtocolTemplate(
            template_id="digital_health_app",
            name="Digital Health Application Study Template",
            description="Template for digital therapeutics and health app studies",
            template_type=TemplateType.DIGITAL_HEALTH_STUDY,
            version=self.template_version,
            sections=sections,
            regulatory_frameworks=[RegulatoryFramework.FDA_510K, RegulatoryFramework.HIPAA],
            required_variables=[
                "study_title", "digital_platform_description", "digital_biomarkers", "principal_investigator"
            ],
            created_date=datetime.now()
        )
    
    def _create_vaccine_efficacy_template(self) -> ProtocolTemplate:
        """Create vaccine efficacy study template."""
        sections = [
            ProtocolSection(
                section_id="vaccine_description",
                title="Vaccine Product Information",
                content="""## Vaccine Composition
{{vaccine_composition}}

## Manufacturing Information
**Manufacturer:** {{vaccine_manufacturer}}
**Lot Release Testing:** {{lot_release_testing}}
**Storage Requirements:** {{storage_requirements}}

## Immunological Rationale
{{immunological_rationale}}

## Vaccination Schedule
{{vaccination_schedule}}""",
                required=True
            ),
            ProtocolSection(
                section_id="efficacy_endpoints_vaccine",
                title="Vaccine Efficacy Endpoints",
                content="""## Primary Efficacy Endpoint
{{primary_efficacy_endpoint}}

**Case Definition:** {{case_definition}}
**Surveillance Period:** {{surveillance_period}}
**Laboratory Confirmation:** {{laboratory_confirmation}}

## Secondary Efficacy Endpoints
{{secondary_efficacy_endpoints}}

## Immunogenicity Endpoints
- Seroconversion rates
- Geometric mean titers (GMT)
- Seroprotection rates
- Duration of immunity

## Correlates of Protection
{{correlates_of_protection}}""",
                required=True
            ),
            ProtocolSection(
                section_id="vaccine_safety",
                title="Vaccine Safety Monitoring",
                content="""## Solicited Adverse Events
{{solicited_adverse_events}}

## Unsolicited Adverse Events
{{unsolicited_adverse_events}}

## Serious Adverse Events
- Immediate reporting requirements
- Brighton Collaboration case definitions
- Causality assessment

## Special Safety Considerations
{{special_safety_considerations}}

## Pregnancy Registry
{{pregnancy_registry}}""",
                required=True
            )
        ]
        
        return ProtocolTemplate(
            template_id="vaccine_efficacy",
            name="Vaccine Efficacy Study Template",
            description="Template for vaccine efficacy trials",
            template_type=TemplateType.VACCINE_STUDY,
            version=self.template_version,
            sections=sections,
            regulatory_frameworks=[RegulatoryFramework.FDA_IND, RegulatoryFramework.ICH_GCP],
            required_variables=[
                "study_title", "vaccine_composition", "primary_efficacy_endpoint", "principal_investigator"
            ],
            created_date=datetime.now()
        )
    
    def _create_surgical_template(self) -> ProtocolTemplate:
        """Create surgical procedure study template."""
        sections = [
            ProtocolSection(
                section_id="surgical_procedure",
                title="Surgical Procedure Description",
                content="""## Procedure Overview
{{surgical_procedure_description}}

## Surgical Technique
{{surgical_technique_details}}

## Equipment and Instrumentation
{{surgical_equipment}}

## Surgeon Qualifications
{{surgeon_qualifications}}

## Learning Curve Considerations
{{learning_curve}}""",
                required=True
            ),
            ProtocolSection(
                section_id="perioperative_care",
                title="Perioperative Care Protocol",
                content="""## Preoperative Preparation
{{preoperative_preparation}}

## Intraoperative Management
{{intraoperative_management}}

## Postoperative Care
{{postoperative_care}}

## Discharge Criteria
{{discharge_criteria}}

## Follow-up Schedule
{{surgical_followup_schedule}}""",
                required=True
            )
        ]
        
        return ProtocolTemplate(
            template_id="surgical_procedure",
            name="Surgical Procedure Study Template",
            description="Template for surgical intervention studies",
            template_type=TemplateType.SURGICAL_STUDY,
            version=self.template_version,
            sections=sections,
            regulatory_frameworks=[RegulatoryFramework.ICH_GCP, RegulatoryFramework.INSTITUTIONAL],
            required_variables=[
                "study_title", "surgical_procedure_description", "surgeon_qualifications", "principal_investigator"
            ],
            created_date=datetime.now()
        )
    
    def _create_behavioral_template(self) -> ProtocolTemplate:
        """Create behavioral intervention study template."""
        sections = [
            ProtocolSection(
                section_id="behavioral_intervention",
                title="Behavioral Intervention Description",
                content="""## Intervention Overview
{{behavioral_intervention_description}}

## Theoretical Framework
{{theoretical_framework}}

## Intervention Components
{{intervention_components}}

## Delivery Method
{{delivery_method}}

## Intervention Fidelity
{{intervention_fidelity}}""",
                required=True
            ),
            ProtocolSection(
                section_id="behavioral_outcomes",
                title="Behavioral Outcome Measures",
                content="""## Primary Behavioral Endpoints
{{primary_behavioral_endpoints}}

## Secondary Behavioral Endpoints
{{secondary_behavioral_endpoints}}

## Measurement Instruments
{{measurement_instruments}}

## Behavioral Assessment Schedule
{{behavioral_assessment_schedule}}""",
                required=True
            )
        ]
        
        return ProtocolTemplate(
            template_id="behavioral_intervention",
            name="Behavioral Intervention Study Template",
            description="Template for behavioral and psychological intervention studies",
            template_type=TemplateType.BEHAVIORAL_STUDY,
            version=self.template_version,
            sections=sections,
            regulatory_frameworks=[RegulatoryFramework.INSTITUTIONAL, RegulatoryFramework.HIPAA],
            required_variables=[
                "study_title", "behavioral_intervention_description", "primary_behavioral_endpoints", "principal_investigator"
            ],
            created_date=datetime.now()
        )
    
    # Additional specialized templates for other domains...
    def _create_oncology_phase2_template(self) -> ProtocolTemplate:
        """Create Phase II oncology template with efficacy focus."""
        # Implementation similar to Phase I but with efficacy endpoints
        pass
    
    def _create_oncology_phase3_template(self) -> ProtocolTemplate:
        """Create Phase III oncology template for registration studies."""
        # Implementation for confirmatory efficacy studies
        pass
    
    def _create_cardiovascular_drug_template(self) -> ProtocolTemplate:
        """Create cardiovascular drug study template."""
        # Implementation for cardiovascular pharmaceuticals
        pass
    
    def _create_pediatric_efficacy_template(self) -> ProtocolTemplate:
        """Create pediatric efficacy study template."""
        # Implementation for pediatric efficacy studies
        pass
    
    def _create_vaccine_safety_template(self) -> ProtocolTemplate:
        """Create vaccine safety study template."""
        # Implementation focusing on vaccine safety
        pass