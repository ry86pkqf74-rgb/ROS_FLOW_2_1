"""
Reference Management System Examples

Practical examples demonstrating how to use the enhanced reference management system.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
from typing import List, Dict, Any

from .reference_types import ReferenceState, CitationStyle, Reference
from .reference_management_service import get_reference_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_basic_reference_processing():
    """
    Example 1: Basic reference processing workflow.
    
    This example shows how to process a simple manuscript with citations.
    """
    print("\n" + "="*50)
    print("EXAMPLE 1: Basic Reference Processing")
    print("="*50)
    
    # Sample manuscript text with citation needs
    manuscript_text = """
    INTRODUCTION
    Diabetes mellitus affects millions of people worldwide [citation needed]. 
    Studies have shown that early intervention improves outcomes [1]. 
    Recent meta-analyses indicate [2-4] that combination therapy is most effective.
    
    METHODS
    We conducted a randomized controlled trial following CONSORT guidelines [5].
    
    RESULTS
    Our findings demonstrate significant improvement in HbA1c levels [citation needed].
    """
    
    # Sample literature results (would come from Stage 6)
    literature_results = [
        {
            "id": "lit_001",
            "title": "Global Diabetes Prevalence: A Systematic Review",
            "authors": ["Smith, J.A.", "Johnson, M.B."],
            "year": 2023,
            "journal": "Diabetes Care",
            "doi": "10.2337/dc23-0001",
            "abstract": "This systematic review examines global diabetes prevalence...",
            "pmid": "36789123"
        },
        {
            "id": "lit_002", 
            "title": "Early Diabetes Intervention: A Longitudinal Study",
            "authors": ["Brown, K.L.", "Davis, R.T.", "Wilson, A.S."],
            "year": 2022,
            "journal": "New England Journal of Medicine",
            "doi": "10.1056/NEJMoa2200001",
            "abstract": "Early intervention in diabetes significantly improves...",
            "pmid": "35678234"
        },
        {
            "id": "lit_003",
            "title": "Combination Therapy in Type 2 Diabetes: Meta-Analysis",
            "authors": ["Lee, H.J.", "Garcia, C.M."],
            "year": 2023,
            "journal": "The Lancet",
            "doi": "10.1016/S0140-6736(23)00001-1",
            "abstract": "Meta-analysis of 50 randomized trials examining...",
            "pmid": "37123789"
        }
    ]
    
    # Create reference state
    ref_state = ReferenceState(
        study_id="example_basic",
        manuscript_text=manuscript_text,
        literature_results=literature_results,
        target_style=CitationStyle.AMA,
        enable_doi_validation=True,
        enable_duplicate_detection=True,
        enable_quality_assessment=True,
        manuscript_type="research_article",
        research_field="medical"
    )
    
    # Process references
    try:
        service = await get_reference_service()
        result = await service.process_references(ref_state)
        
        # Display results
        print(f"\nProcessing Results:")
        print(f"- Study ID: {result.study_id}")
        print(f"- Total References: {result.total_references}")
        print(f"- Processing Time: {result.processing_time_seconds:.2f}s")
        print(f"- Style Compliance: {result.style_compliance_score:.1%}")
        
        print(f"\nCitations Found ({len(result.citations)}):")
        for i, citation in enumerate(result.citations[:3], 1):
            print(f"{i}. {citation.formatted_text}")
        
        print(f"\nQuality Assessment:")
        if result.quality_scores:
            avg_quality = sum(score.overall_score for score in result.quality_scores) / len(result.quality_scores)
            print(f"- Average Quality Score: {avg_quality:.2f}")
            print(f"- Quality Levels: {[score.quality_level.value for score in result.quality_scores]}")
        
        if result.warnings:
            print(f"\nWarnings ({len(result.warnings)}):")
            for warning in result.warnings[:3]:
                print(f"- {warning.warning_type}: {warning.message}")
        
        print(f"\nBibliography Preview:")
        print(result.bibliography[:500] + "..." if len(result.bibliography) > 500 else result.bibliography)
        
    except Exception as e:
        print(f"Error: {e}")


async def example_advanced_quality_assessment():
    """
    Example 2: Advanced quality assessment and filtering.
    
    This example shows how to use quality assessment to filter references.
    """
    print("\n" + "="*50)
    print("EXAMPLE 2: Advanced Quality Assessment")
    print("="*50)
    
    # Mixed quality literature results
    literature_results = [
        {
            "id": "high_quality",
            "title": "Randomized Controlled Trial of New Diabetes Drug",
            "authors": ["Expert, A.", "Researcher, B.", "Scholar, C."],
            "year": 2023,
            "journal": "New England Journal of Medicine",
            "doi": "10.1056/NEJMoa2300001",
            "abstract": "Double-blind randomized controlled trial...",
            "pmid": "37234567"
        },
        {
            "id": "medium_quality",
            "title": "Observational Study of Diabetes Patients",
            "authors": ["Clinician, D."],
            "year": 2020,
            "journal": "Diabetes Research",
            "doi": "10.1007/s00125-020-05001-1",
            "abstract": "Retrospective analysis of patient data..."
        },
        {
            "id": "low_quality",
            "title": "Case Report: Unusual Diabetes Presentation",
            "authors": ["Doctor, E."],
            "year": 2018,
            "journal": "Case Reports in Medicine",
            "abstract": "We report a case of unusual diabetes presentation..."
        },
        {
            "id": "predatory_journal",
            "title": "Miracle Cure for Diabetes",
            "authors": ["Questionable, F."],
            "year": 2023,
            "journal": "International Journal of Advanced Research",  # Known predatory pattern
            "abstract": "Amazing results with new treatment..."
        }
    ]
    
    ref_state = ReferenceState(
        study_id="example_quality",
        manuscript_text="Sample text for quality assessment [citation needed].",
        literature_results=literature_results,
        target_style=CitationStyle.AMA,
        enable_quality_assessment=True,
        research_field="medical"
    )
    
    try:
        service = await get_reference_service()
        result = await service.process_references(ref_state)
        
        print(f"\nQuality Assessment Results:")
        print(f"{'Reference':<25} {'Quality':<12} {'Score':<8} {'Issues':<15}")
        print("-" * 70)
        
        for ref, quality in zip(result.references, result.quality_scores):
            issues = len([w for w in result.warnings if w.reference_id == ref.id])
            print(f"{ref.title[:24]:<25} {quality.quality_level.value:<12} {quality.overall_score:.2f}    {issues} issues")
        
        # Show quality distribution
        quality_levels = [score.quality_level.value for score in result.quality_scores]
        quality_counts = {level: quality_levels.count(level) for level in set(quality_levels)}
        print(f"\nQuality Distribution: {quality_counts}")
        
        # Show warnings
        if result.warnings:
            print(f"\nQuality Warnings:")
            for warning in result.warnings:
                ref_title = next((ref.title for ref in result.references if ref.id == warning.reference_id), "Unknown")
                print(f"- {ref_title[:30]}: {warning.message}")
        
        # Filter high-quality references
        high_quality_refs = [
            ref for ref, score in zip(result.references, result.quality_scores)
            if score.overall_score >= 0.7
        ]
        print(f"\nHigh-Quality References ({len(high_quality_refs)} of {len(result.references)}):")
        for ref in high_quality_refs:
            print(f"- {ref.title}")
        
    except Exception as e:
        print(f"Error: {e}")


async def example_duplicate_detection():
    """
    Example 3: Duplicate detection and resolution.
    
    This example demonstrates duplicate detection with similar references.
    """
    print("\n" + "="*50)
    print("EXAMPLE 3: Duplicate Detection")
    print("="*50)
    
    # Literature with intentional duplicates
    literature_results = [
        {
            "id": "original",
            "title": "COVID-19 and Diabetes: A Comprehensive Review",
            "authors": ["Smith, J.A.", "Johnson, M.B."],
            "year": 2023,
            "journal": "Diabetes Care",
            "doi": "10.2337/dc23-1001"
        },
        {
            "id": "duplicate_same_doi",
            "title": "COVID-19 and diabetes: a comprehensive review",  # Different capitalization
            "authors": ["Smith, John A.", "Johnson, Mary B."],  # Full names
            "year": 2023,
            "journal": "Diabetes Care",
            "doi": "10.2337/dc23-1001"  # Same DOI
        },
        {
            "id": "similar_title",
            "title": "COVID-19 and Diabetes: Comprehensive Review",  # Very similar title
            "authors": ["Smith, J.", "Johnson, M."],  # Similar authors
            "year": 2023,
            "journal": "Diabetes Care"
        },
        {
            "id": "different_paper",
            "title": "Machine Learning in Healthcare Applications",
            "authors": ["Brown, K.L."],
            "year": 2022,
            "journal": "Nature Medicine"
        },
        {
            "id": "preprint_version",
            "title": "COVID-19 and Diabetes: A Comprehensive Review",  # Same title
            "authors": ["Smith, J.A.", "Johnson, M.B."],
            "year": 2023,
            "journal": "medRxiv",  # Preprint
            "abstract": "This preprint examines the relationship between COVID-19 and diabetes..."
        }
    ]
    
    ref_state = ReferenceState(
        study_id="example_duplicates",
        manuscript_text="References about COVID-19 and diabetes [1-3].",
        literature_results=literature_results,
        target_style=CitationStyle.AMA,
        enable_duplicate_detection=True
    )
    
    try:
        service = await get_reference_service()
        result = await service.process_references(ref_state)
        
        print(f"\nDuplicate Detection Results:")
        print(f"- Original references: {len(literature_results)}")
        print(f"- After deduplication: {result.total_references}")
        print(f"- Duplicates removed: {len(literature_results) - result.total_references}")
        
        if result.duplicate_references:
            print(f"\nDuplicate Groups Found: {len(result.duplicate_references)}")
            
        print(f"\nFinal Reference List:")
        for i, ref in enumerate(result.references, 1):
            print(f"{i}. {ref.title}")
            print(f"   Authors: {', '.join(ref.authors)}")
            print(f"   Journal: {ref.journal}")
            if ref.doi:
                print(f"   DOI: {ref.doi}")
            print()
        
    except Exception as e:
        print(f"Error: {e}")


async def example_citation_style_comparison():
    """
    Example 4: Citation style comparison.
    
    This example shows the same references formatted in different citation styles.
    """
    print("\n" + "="*50)
    print("EXAMPLE 4: Citation Style Comparison")
    print("="*50)
    
    # Sample literature result
    literature_results = [
        {
            "id": "sample_ref",
            "title": "Machine Learning Applications in Medical Diagnosis",
            "authors": ["Smith, John A.", "Johnson, Mary B.", "Brown, Robert C."],
            "year": 2023,
            "journal": "Nature Medicine",
            "volume": "29",
            "issue": "3",
            "pages": "123-135",
            "doi": "10.1038/s41591-023-02234-5",
            "pmid": "36789012"
        }
    ]
    
    styles_to_test = [
        CitationStyle.AMA,
        CitationStyle.APA, 
        CitationStyle.VANCOUVER,
        CitationStyle.HARVARD,
        CitationStyle.NATURE
    ]
    
    print(f"Reference: {literature_results[0]['title']}")
    print(f"Authors: {', '.join(literature_results[0]['authors'])}")
    print(f"Journal: {literature_results[0]['journal']}")
    print()
    
    for style in styles_to_test:
        try:
            ref_state = ReferenceState(
                study_id=f"style_test_{style.value}",
                manuscript_text="Sample citation [1].",
                literature_results=literature_results,
                target_style=style
            )
            
            service = await get_reference_service()
            result = await service.process_references(ref_state)
            
            if result.citations:
                citation_text = result.citations[0].formatted_text
                print(f"{style.value.upper():<12}: {citation_text}")
            
        except Exception as e:
            print(f"{style.value.upper():<12}: Error - {e}")
    
    print()


async def example_performance_benchmark():
    """
    Example 5: Performance benchmarking.
    
    This example benchmarks the system with different loads.
    """
    print("\n" + "="*50)
    print("EXAMPLE 5: Performance Benchmarking")
    print("="*50)
    
    import time
    
    # Create different sized datasets
    test_sizes = [10, 50, 100]
    
    for size in test_sizes:
        print(f"\nTesting with {size} references...")
        
        # Generate test literature
        literature_results = [
            {
                "id": f"ref_{i}",
                "title": f"Research Paper {i}: A Study of Topic {i % 10}",
                "authors": [f"Author_{i}_A, J.", f"Author_{i}_B, M."],
                "year": 2020 + (i % 4),
                "journal": f"Journal of Field {i % 5}",
                "doi": f"10.1234/journal.2023.{i:03d}",
                "abstract": f"This study examines topic {i % 10} using methodology {i % 3}..."
            }
            for i in range(size)
        ]
        
        # Create manuscript with multiple citation needs
        manuscript_text = f"""
        INTRODUCTION
        Multiple studies have examined this topic [1-{min(5, size)}].
        Research indicates [citation needed] various approaches.
        
        METHODS  
        We followed established protocols [citation needed].
        
        RESULTS
        Our findings show significant results [citation needed].
        """
        
        ref_state = ReferenceState(
            study_id=f"benchmark_{size}",
            manuscript_text=manuscript_text,
            literature_results=literature_results,
            target_style=CitationStyle.AMA,
            enable_doi_validation=False,  # Skip API calls for benchmarking
            enable_duplicate_detection=True,
            enable_quality_assessment=True
        )
        
        try:
            start_time = time.time()
            service = await get_reference_service()
            result = await service.process_references(ref_state)
            end_time = time.time()
            
            processing_time = end_time - start_time
            refs_per_second = size / processing_time if processing_time > 0 else 0
            
            print(f"- Processing time: {processing_time:.2f}s")
            print(f"- References/second: {refs_per_second:.1f}")
            print(f"- Total references processed: {result.total_references}")
            print(f"- Citations generated: {len(result.citations)}")
            print(f"- Quality assessments: {len(result.quality_scores)}")
            
        except Exception as e:
            print(f"- Error: {e}")


async def run_all_examples():
    """Run all examples in sequence."""
    print("Reference Management System Examples")
    print("=" * 60)
    
    examples = [
        example_basic_reference_processing,
        example_advanced_quality_assessment,
        example_duplicate_detection,
        example_citation_style_comparison,
        example_performance_benchmark
    ]
    
    for example in examples:
        try:
            await example()
            await asyncio.sleep(1)  # Brief pause between examples
        except Exception as e:
            print(f"Example failed: {e}")
            continue
    
    print("\n" + "="*60)
    print("All examples completed!")


if __name__ == "__main__":
    # Run examples
    asyncio.run(run_all_examples())