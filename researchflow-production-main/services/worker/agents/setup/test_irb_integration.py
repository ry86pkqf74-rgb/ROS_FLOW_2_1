"""
Integration Tests for IRB Submission Agent

Tests the complete IRB submission workflow including LangGraph execution,
state management, and end-to-end submission package generation.

This provides a test harness for when LangGraph dependencies are available.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, timedelta
from typing import Dict, Any

# Try to import LangGraph for integration testing
try:
    from langgraph.graph import StateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

from .irb_submission_agent import (
    IRBSubmissionAgent,
    IRBSubmissionState,
    Investigator,
    TrainingCertification,
    COIDisclosure,
    PopulationDescription,
)


class MockLLMBridge:
    """Mock LLM bridge for testing LangGraph integration."""
    
    def __init__(self):
        self.call_count = 0
        self.responses = {
            'review_classification': """
Based on the analysis of this research protocol, I recommend **Expedited Review**.

**Justification:**
- The study involves minimal risk observational research
- No vulnerable populations are involved
- Data collection is non-invasive
- Fits expedited category for non-invasive clinical data collection

**Review Type: Expedited**
            """,
            'protocol_summary': """
# Research Study Summary

## Study Title
"Understanding Diabetes Self-Management Behaviors in Adults"

## Study Purpose
This study aims to understand how adults with diabetes manage their condition at home and what barriers they face in following treatment recommendations.

## What Participants Will Do
- Complete a 30-minute survey about diabetes management
- Answer questions about diet, exercise, medication, and challenges
- Participation is completely voluntary

## Who Can Participate
- Adults aged 18-75 with Type 2 diabetes
- Able to read and understand English
- Currently managing diabetes

## Benefits and Risks
**Benefits:** Help improve diabetes care for future patients
**Risks:** Minimal - only time to complete survey, no physical risks

## Privacy Protection
All answers will be kept confidential and stored securely. No names will be used in research reports.
            """,
            'investigator_compilation': """
# Principal Investigator Information

## Dr. Jane Smith, MD, PhD
- **Institution:** University Medical Center  
- **Department:** Internal Medicine
- **Email:** jane.smith@umc.edu
- **Phone:** (555) 123-4567

## Qualifications
- Board-certified internist with 15 years experience
- Research focus: diabetes management and patient education
- Previous IRB approvals: 12 studies over 8 years

## Human Subjects Training
- **CITI Training:** Current through March 2025
- **Modules Completed:** Basic Human Subjects Research, Informed Consent, PI Responsibilities, Vulnerable Populations
- **Certificate:** CITI12345

## Conflict of Interest
- **Status:** No financial conflicts of interest
- **Last Updated:** January 2024
- **Management Plan:** Not applicable
            """,
            'consent_form': """
INFORMED CONSENT TO PARTICIPATE IN RESEARCH

Study Title: Understanding Diabetes Self-Management Behaviors in Adults
Principal Investigator: Dr. Jane Smith, MD, PhD

You are being asked to take part in a research study. Before you agree, please read this form carefully.

WHAT IS THIS STUDY ABOUT?
We want to learn how people with diabetes manage their condition at home. This will help us improve care for future patients.

WHAT WILL I DO?
If you agree to participate, you will:
- Fill out a survey about your diabetes care (about 30 minutes)
- Answer questions about diet, exercise, and medications
- You can skip any questions you don't want to answer

WHAT ARE THE RISKS?
The risks are minimal. You might feel tired from answering questions. Some questions about your health might make you feel uncomfortable. You can stop at any time.

WHAT ARE THE BENEFITS?
You will not benefit directly from this study. However, your answers may help improve diabetes care for others.

WILL MY INFORMATION BE KEPT PRIVATE?
Yes. Your name will not be used in any reports. All information will be stored securely.

IS PARTICIPATION VOLUNTARY?
Yes. You can choose not to participate. If you start the survey, you can stop at any time without penalty.

WHO CAN I CONTACT?
Questions about the study: Dr. Jane Smith at (555) 123-4567
Questions about your rights: IRB Office at (555) 987-6543

AGREEMENT TO PARTICIPATE:
By signing below, you agree to participate in this research study.

Participant Signature: _________________ Date: _________
Researcher Signature: _________________ Date: _________
            """,
            'risk_assessment': """
# Comprehensive Risk Assessment

## Overall Risk Level: MINIMAL RISK

## Risk Categories Analysis

### 1. Physical Risks
- **Risk Level:** None identified
- **Justification:** Survey-based study with no physical procedures

### 2. Psychological Risks  
- **Risk Level:** Minimal
- **Description:** Potential mild discomfort discussing health behaviors
- **Likelihood:** Possible
- **Severity:** Minimal
- **Mitigation:** Participants can skip questions; voluntary withdrawal allowed

### 3. Social Risks
- **Risk Level:** Low
- **Description:** Potential privacy concerns if data breached
- **Likelihood:** Unlikely  
- **Severity:** Moderate
- **Mitigation:** Data encryption, de-identification, secure storage

### 4. Economic Risks
- **Risk Level:** Minimal
- **Description:** Time cost (30 minutes)
- **Mitigation:** Clear time estimate provided upfront

### 5. Legal Risks
- **Risk Level:** None identified
- **Justification:** No legal implications for participation

## Risk-Benefit Analysis
The minimal risks are outweighed by the potential societal benefit of improved diabetes care.

## Monitoring Plan
- Regular data security reviews
- Participant feedback monitoring
- Annual safety review
            """,
            'vulnerable_populations': """
# Vulnerable Populations Assessment

## Analysis Results: NO VULNERABLE POPULATIONS INVOLVED

### Population Screening Results:

**Children (Under 18):** Not included
- Study limited to adults 18-75 years old
- No additional protections needed

**Prisoners:** Not included  
- No recruitment at correctional facilities
- No additional protections needed

**Pregnant Women:** Not specifically targeted
- Pregnancy not an inclusion/exclusion criteria
- Standard consent adequate

**Cognitively Impaired:** Not included
- Study requires ability to complete written survey
- Cognitive capacity implied by inclusion criteria

**Other Vulnerable Groups:** Not identified
- Adult volunteers with diabetes
- No coercive relationships identified
- No special protections required

## Conclusion
This study involves competent adults with diabetes recruited through standard medical care channels. No additional vulnerable population protections are required.
            """,
            'hipaa_authorization': """
# HIPAA Authorization Analysis

## HIPAA Requirements Assessment: AUTHORIZATION NOT REQUIRED

### Analysis of 18 HIPAA Identifiers:

**Identifiers NOT Collected:**
- Names, addresses, phone numbers
- Social Security Numbers
- Medical record numbers
- Account numbers
- Email addresses
- Biometric identifiers
- Photographs

**Data Collection Limited To:**
- Age ranges (not specific dates of birth)
- General diabetes management behaviors
- Anonymous survey responses
- No direct PHI identifiers

### Conclusion:
Since this study collects only anonymous survey data without the 18 HIPAA identifiers, **no HIPAA authorization is required**.

### Recommendation:
Proceed with standard informed consent. Ensure data collection forms do not inadvertently collect HIPAA identifiers.
            """,
            'package_compilation': """
# IRB SUBMISSION PACKAGE

## COVER LETTER

To: University Medical Center IRB
From: Dr. Jane Smith, Principal Investigator
Date: [Submission Date]
Re: IRB Submission - "Understanding Diabetes Self-Management Behaviors in Adults"

Dear IRB Members,

I respectfully submit this research protocol for Expedited Review consideration. This minimal-risk observational study involves anonymous surveys with adults with diabetes to improve understanding of self-management behaviors.

**Submission Components:**
1. Protocol Summary (lay language)
2. Principal Investigator qualifications and training
3. Informed consent form
4. Risk assessment
5. Vulnerable populations analysis  
6. HIPAA determination

**Requested Review Type:** Expedited
**Justification:** Minimal risk survey research fitting expedited category 7

## SUBMISSION CHECKLIST

☐ IRB application form (to be completed online)
☐ Protocol summary ✓
☐ Principal investigator CV ✓
☐ CITI training certificates ✓
☐ Informed consent form ✓
☐ Risk assessment ✓
☐ Recruitment materials (if applicable)
☐ Data collection instruments ✓
☐ COI disclosure forms ✓

## PACKAGE ORGANIZATION

**Section 1:** Administrative
- Cover letter
- IRB application form

**Section 2:** Study Documentation  
- Protocol summary
- Risk assessment
- Vulnerable populations analysis

**Section 3:** Consent Materials
- Informed consent form
- HIPAA determination

**Section 4:** Investigator Qualifications
- PI CV and qualifications
- Training certificates
- COI disclosures

Ready for submission pending final signatures and online form completion.
            """,
            'completeness_validation': """
# SUBMISSION COMPLETENESS VALIDATION

## VALIDATION RESULTS: ✅ READY FOR SUBMISSION

### Completeness Checklist Review:

**Required Elements - ALL PRESENT:**
✓ Protocol summary in lay language (Grade 7.2 reading level)
✓ Principal investigator information and qualifications complete
✓ Informed consent form with all 12 required elements
✓ Comprehensive risk assessment across all categories
✓ Vulnerable populations analysis (none involved)
✓ HIPAA determination (authorization not required)
✓ Training certificates current through 2025
✓ COI disclosures up-to-date

### Quality Checks - ALL PASSED:
✓ Consent form readable at appropriate level
✓ All required consent elements present (purpose, procedures, risks, benefits, etc.)
✓ Risk mitigation strategies adequate for minimal risk study
✓ Contact information complete and accurate
✓ Signature lines properly identified

### Regulatory Compliance - CONFIRMED:
✓ 45 CFR 46 requirements met for expedited review
✓ HIPAA requirements properly addressed
✓ Institutional policies followed
✓ Review type appropriate for study design

## FINAL DETERMINATION:
This submission package is COMPLETE and READY FOR IRB SUBMISSION.

## Next Steps:
1. Obtain PI signature on consent form
2. Complete online IRB application form
3. Submit package to IRB
4. Expect review within 2-3 weeks for expedited category
            """,
            'submission_tracking': """
# SUBMISSION TRACKING AND NEXT STEPS

## SUBMISSION PROCESS

**How to Submit:**
1. Complete online IRB application at [institution portal]
2. Upload all documents as PDF files
3. Ensure PI digital signature on consent form
4. Pay IRB review fee if applicable
5. Submit by 5 PM for next business day processing

**Required Format:** Electronic submission only
**Submission Deadline:** Submit by Wednesday for Friday board review

## TRACKING SETUP

**IRB Reference Number:** Will be assigned upon submission
**Expected Timeline:** 
- Expedited Review: 2-4 weeks
- Administrative review: 1-2 business days
- PI notification: Email within 24 hours of decision

**Status Monitoring:**
- Check IRB portal weekly for updates
- Set calendar reminder for 3 weeks post-submission
- Monitor email for IRB communications

## EXPECTED TIMELINE

**Week 1:** Administrative review and assignment to expedited reviewer
**Week 2-3:** Substantive review by designated IRB member
**Week 4:** Final determination and notification

**Potential Delays:**
- Holiday periods
- Heavy IRB workload
- Need for clarification or minor revisions

## NEXT STEPS

**Before Submission:**
✓ Final PI review of all documents
✓ Department chair approval obtained
✓ Research integrity training current
✓ All signatures in place

**After Submission:**
- Monitor IRB portal for status updates
- Respond promptly to any IRB questions
- Do not begin recruitment until written approval received
- Prepare recruitment materials for post-approval review

**POST-APPROVAL REQUIREMENTS:**
- Submit continuing review application annually
- Report any protocol deviations
- Submit modifications for any changes
- Submit final report upon study completion

## COMPLETION CHECKLIST
✓ Final review by PI
✓ Department/institutional approvals obtained  
✓ Ready for submission to IRB
☐ Acknowledgment received from IRB
☐ Review completed
☐ Approval letter received

Your IRB submission package is ready for submission. The expedited review process typically takes 2-4 weeks from submission to decision.
            """,
        }
    
    async def invoke(self, prompt: str, task_type: str, **kwargs) -> Dict[str, Any]:
        """Mock LLM call that returns appropriate responses based on task type."""
        self.call_count += 1
        
        # Return appropriate response based on task type
        content = self.responses.get(task_type, f"Mock response for {task_type}")
        
        return {
            'content': content,
            'usage': {
                'prompt_tokens': len(prompt.split()),
                'completion_tokens': len(content.split()),
                'total_tokens': len(prompt.split()) + len(content.split())
            }
        }


@pytest.fixture
def mock_llm_bridge():
    """Mock LLM bridge for testing."""
    return MockLLMBridge()


@pytest.fixture
def sample_agent_state():
    """Sample agent state for testing."""
    return {
        'agent_id': 'irb_submission',
        'project_id': 'test-project-123',
        'run_id': 'test-run-456',
        'thread_id': 'test-thread-789',
        'current_stage': 2,
        'stage_range': (2, 2),
        'governance_mode': 'DEMO',
        'messages': [
            {
                'id': 'msg-1',
                'role': 'user',
                'content': """
                I need help preparing an IRB submission for a diabetes research study. 
                
                Study Details:
                - Title: "Understanding Diabetes Self-Management Behaviors in Adults"
                - Type: Observational survey study
                - Population: Adults aged 18-75 with Type 2 diabetes
                - Data Collection: Anonymous 30-minute survey about self-management behaviors
                - Risk Level: Minimal risk (survey only, no interventions)
                - Sample Size: 200 participants
                - Duration: 12 months
                
                Principal Investigator:
                - Dr. Jane Smith, MD, PhD
                - Internal Medicine, University Medical Center
                - Current CITI training, no conflicts of interest
                """,
                'timestamp': '2024-01-15T10:00:00Z',
                'phi_detected': False,
            }
        ],
        'input_artifact_ids': [],
        'output_artifact_ids': [],
        'current_output': '',
        'iteration': 0,
        'max_iterations': 3,
        'previous_versions': [],
        'gate_status': 'pending',
        'gate_score': 0.0,
        'gate_result': None,
        'improvement_enabled': True,
        'feedback': None,
        'token_count': 0,
        'tool_call_count': 0,
        'start_time': '2024-01-15T10:00:00Z',
        'awaiting_approval': False,
        'approval_request_id': None,
    }


class TestIRBIntegrationWorkflow:
    """Integration tests for IRB submission workflow."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization_with_llm_bridge(self, mock_llm_bridge):
        """Test agent initialization with LLM bridge."""
        agent = IRBSubmissionAgent(llm_bridge=mock_llm_bridge)
        
        assert agent.agent_id == 'irb_submission'
        assert agent.stage == 2
        assert agent.stages == [2]
        assert agent.llm_bridge == mock_llm_bridge
        
        # Test quality criteria
        criteria = agent.get_quality_criteria()
        expected_criteria = [
            'protocol_summary_complete',
            'investigator_info_complete', 
            'consent_form_readable',
            'risk_assessment_complete',
            'vulnerable_populations_addressed',
            'submission_package_complete',
            'regulatory_compliance'
        ]
        
        for criterion in expected_criteria:
            assert criterion in criteria
    
    @pytest.mark.asyncio
    async def test_node_execution_sequence(self, mock_llm_bridge, sample_agent_state):
        """Test individual node execution in sequence."""
        agent = IRBSubmissionAgent(llm_bridge=mock_llm_bridge)
        
        # Test assess_review_type_node
        result1 = await agent.assess_review_type_node(sample_agent_state)
        assert 'review_type' in result1
        assert 'review_analysis' in result1
        assert result1['review_type'] in ['Exempt', 'Expedited', 'Full Board']
        
        # Update state with result
        sample_agent_state.update(result1)
        
        # Test generate_protocol_summary_node
        result2 = await agent.generate_protocol_summary_node(sample_agent_state)
        assert 'protocol_summary' in result2
        assert 'protocol_reading_level' in result2
        assert isinstance(result2['protocol_reading_level'], float)
        
        # Update state with result
        sample_agent_state.update(result2)
        
        # Test compile_investigator_info_node
        result3 = await agent.compile_investigator_info_node(sample_agent_state)
        assert 'investigator_info' in result3
        assert 'training_warnings' in result3
        assert isinstance(result3['training_warnings'], list)
        
        # Verify LLM was called for each node
        assert mock_llm_bridge.call_count == 3
    
    @pytest.mark.asyncio 
    async def test_parallel_nodes_execution(self, mock_llm_bridge, sample_agent_state):
        """Test parallel nodes can execute independently."""
        agent = IRBSubmissionAgent(llm_bridge=mock_llm_bridge)
        
        # Set up state with prerequisites
        sample_agent_state.update({
            'protocol_summary': 'Sample protocol summary for testing',
            'review_type': 'Expedited'
        })
        
        # Execute parallel nodes concurrently
        tasks = [
            agent.generate_consent_form_node(sample_agent_state),
            agent.assess_risks_node(sample_agent_state),
            agent.check_vulnerable_populations_node(sample_agent_state)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all nodes completed successfully
        consent_result, risk_result, vuln_result = results
        
        assert 'consent_form' in consent_result
        assert 'consent_reading_level' in consent_result
        assert 'risk_assessment' in risk_result
        assert 'vulnerable_populations_analysis' in vuln_result
        
        assert mock_llm_bridge.call_count == 3
    
    @pytest.mark.asyncio
    async def test_quality_gate_evaluation(self, mock_llm_bridge, sample_agent_state):
        """Test quality gate evaluation with IRB-specific criteria."""
        agent = IRBSubmissionAgent(llm_bridge=mock_llm_bridge)
        
        # Set up state with all required components
        test_state = sample_agent_state.copy()
        test_state.update({
            'protocol_summary': 'Study purpose: diabetes management. Participants: adults with diabetes. Procedures: survey completion. Risks: minimal survey fatigue. Benefits: improved care.',
            'investigator_info': 'Principal investigator: Dr. Smith. Training: current CITI certification. Contact: email@institution.edu. Qualifications: board certified.',
            'consent_reading_level': 7.5,  # Below 8th grade threshold
            'risk_assessment': 'Physical risks: none. Psychological risks: minimal discomfort. Social risks: privacy. Economic risks: time. Legal risks: none.',
            'vulnerable_populations_analysis': 'Vulnerable populations: none identified. Adults only study.',
            'submission_package': 'Protocol summary included. Consent form complete. Investigator qualifications documented. Risk assessment comprehensive. Checklist complete.',
            'current_output': '45 CFR 46 compliance documented. HIPAA requirements addressed. IRB submission ready. Human subjects protections in place. Consent elements complete.'
        })
        
        # Execute quality gate
        result = agent.quality_gate_node(test_state)
        
        # Verify quality gate evaluation
        assert 'gate_status' in result
        assert 'gate_score' in result
        assert 'gate_result' in result
        
        gate_result = result['gate_result']
        assert isinstance(gate_result.get('score'), float)
        assert isinstance(gate_result.get('criteria_met'), list)
        assert isinstance(gate_result.get('criteria_failed'), list)
        
        # Should pass most criteria with proper state
        assert result['gate_score'] > 0.5
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow_simulation(self, mock_llm_bridge, sample_agent_state):
        """Test simulated end-to-end workflow without full LangGraph."""
        agent = IRBSubmissionAgent(llm_bridge=mock_llm_bridge)
        
        # Simulate the complete workflow step by step
        workflow_state = sample_agent_state.copy()
        
        # Step 1: Assess review type
        step1 = await agent.assess_review_type_node(workflow_state)
        workflow_state.update(step1)
        assert workflow_state['review_type'] in ['Exempt', 'Expedited', 'Full Board']
        
        # Step 2: Generate protocol summary  
        step2 = await agent.generate_protocol_summary_node(workflow_state)
        workflow_state.update(step2)
        assert 'protocol_summary' in workflow_state
        assert workflow_state['protocol_reading_level'] < 10  # Reasonable reading level
        
        # Step 3: Compile investigator info
        step3 = await agent.compile_investigator_info_node(workflow_state)
        workflow_state.update(step3)
        assert 'investigator_info' in workflow_state
        
        # Steps 4-6: Parallel processing (simulated sequentially)
        step4 = await agent.generate_consent_form_node(workflow_state)
        workflow_state.update(step4)
        
        step5 = await agent.assess_risks_node(workflow_state)
        workflow_state.update(step5)
        
        step6 = await agent.check_vulnerable_populations_node(workflow_state)
        workflow_state.update(step6)
        
        # Step 7: HIPAA authorization check
        step7 = await agent.generate_hipaa_authorization_node(workflow_state)
        workflow_state.update(step7)
        assert 'hipaa_analysis' in workflow_state
        assert 'needs_hipaa_authorization' in workflow_state
        
        # Step 8: Compile submission package
        step8 = await agent.compile_submission_package_node(workflow_state)
        workflow_state.update(step8)
        assert 'submission_package' in workflow_state
        assert workflow_state['package_compiled'] == True
        
        # Step 9: Validate completeness
        step9 = await agent.validate_completeness_node(workflow_state)
        workflow_state.update(step9)
        assert 'validation_result' in workflow_state
        assert 'validation_passed' in workflow_state
        
        # Step 10: Track submission status
        step10 = await agent.track_submission_status_node(workflow_state)
        workflow_state.update(step10)
        assert 'tracking_setup' in workflow_state
        assert workflow_state['submission_ready'] == True
        assert workflow_state['approval_status'] == 'Ready for Submission'
        
        # Verify all LLM calls were made
        assert mock_llm_bridge.call_count == 10
        
        # Verify final state completeness
        required_outputs = [
            'review_type', 'protocol_summary', 'investigator_info',
            'consent_form', 'risk_assessment', 'vulnerable_populations_analysis',
            'hipaa_analysis', 'submission_package', 'validation_result', 'tracking_setup'
        ]
        
        for output in required_outputs:
            assert output in workflow_state, f"Missing required output: {output}"
    
    @pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="LangGraph not available")
    @pytest.mark.asyncio
    async def test_langgraph_integration_when_available(self, mock_llm_bridge):
        """Test actual LangGraph integration when dependencies are available."""
        agent = IRBSubmissionAgent(llm_bridge=mock_llm_bridge)
        
        # Build the graph
        graph = agent.build_graph()
        assert graph is not None
        
        # Test basic graph structure
        assert hasattr(graph, 'nodes')
        assert hasattr(graph, 'edges')
        
        # Verify key nodes exist
        expected_nodes = [
            'assess_review_type',
            'generate_protocol_summary',
            'compile_investigator_info',
            'generate_consent_form',
            'assess_risks',
            'check_vulnerable_populations',
            'generate_hipaa_authorization',
            'compile_submission_package',
            'validate_completeness',
            'track_submission_status'
        ]
        
        # Note: Actual node verification would require inspecting LangGraph internals
        # This is a basic integration test to ensure the graph compiles
    
    @pytest.mark.asyncio
    async def test_error_handling_in_workflow(self, mock_llm_bridge, sample_agent_state):
        """Test error handling during workflow execution."""
        # Create a bridge that will fail on certain calls
        failing_bridge = AsyncMock()
        failing_bridge.invoke.side_effect = Exception("LLM service unavailable")
        
        agent = IRBSubmissionAgent(llm_bridge=failing_bridge)
        
        # Test node execution with failure
        with pytest.raises(Exception, match="LLM service unavailable"):
            await agent.assess_review_type_node(sample_agent_state)
        
        # Test fallback behavior
        agent_without_bridge = IRBSubmissionAgent(llm_bridge=None)
        
        result = await agent_without_bridge.assess_review_type_node(sample_agent_state)
        
        # Should get mock response when no bridge available
        assert 'review_analysis' in result
        assert 'Mock LLM response' in result['review_analysis']
    
    @pytest.mark.asyncio 
    async def test_backward_compatibility_methods(self, mock_llm_bridge):
        """Test that backward compatibility methods still work."""
        agent = IRBSubmissionAgent(llm_bridge=mock_llm_bridge)
        
        # Create test data
        protocol = {
            "study_type": "observational survey",
            "risk_level": "minimal risk"
        }
        
        population = PopulationDescription(
            target_population="Adults with diabetes",
            inclusion_criteria=["Age 18-75", "Type 2 diabetes"],
            exclusion_criteria=["Type 1 diabetes"],
            sample_size=100,
            vulnerable_populations=[],
            recruitment_sites=["Medical Center"]
        )
        
        investigator = Investigator(
            name="Dr. Test",
            credentials=["MD"],
            institution="Test Hospital",
            department="Medicine",
            email="test@example.com",
            role="PI",
            human_subjects_training=TrainingCertification(
                type="CITI",
                completion_date=date.today() - timedelta(days=30),
                expiration_date=date.today() + timedelta(days=330),
                modules_completed=[
                    "Basic Human Subjects Research",
                    "Informed Consent", 
                    "Responsibilities of Principal Investigators",
                    "Research with Vulnerable Populations"
                ]
            ),
            coi_disclosure=COIDisclosure(
                has_conflicts=False,
                financial_interests=[],
                last_updated=date.today()
            )
        )
        
        # Test backward compatibility methods
        review_type = agent.determine_review_type(protocol, population)
        assert review_type in ["Full Board", "Expedited", "Exempt"]
        
        reading_level = agent.assess_reading_level("This is a simple test sentence.")
        assert isinstance(reading_level, float)
        assert reading_level >= 0
        
        hipaa_needed = agent.check_hipaa_requirements(["age", "survey_responses"])
        assert isinstance(hipaa_needed, bool)
        
        training_errors = agent.validate_investigator_training(investigator)
        assert isinstance(training_errors, list)
        assert len(training_errors) == 0  # Should be valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])