"""
Tests for QuasiIdentifierAnalyzer

Tests comprehensive k-anonymity analysis, quasi-identifier detection,
and privacy risk assessment capabilities.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add worker src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "services" / "worker"))

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


@pytest.mark.skipif(not PANDAS_AVAILABLE, reason="pandas not available")
class TestQuasiIdentifierAnalyzer:
    """Tests for QuasiIdentifierAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create QuasiIdentifierAnalyzer instance."""
        try:
            from src.workflow_engine.stages.phi_analyzers.quasi_identifier_analyzer import (
                QuasiIdentifierAnalyzer
            )
            return QuasiIdentifierAnalyzer(k_threshold=5, l_threshold=2, t_threshold=0.2)
        except ImportError:
            pytest.skip("QuasiIdentifierAnalyzer not available")
    
    @pytest.fixture
    def safe_dataframe(self):
        """Create a safe DataFrame with no quasi-identifiers."""
        return pd.DataFrame({
            "study_id": [1, 2, 3, 4, 5],
            "measurement": [10.5, 12.3, 9.8, 11.2, 10.9],
            "category": ["A", "B", "A", "C", "B"],
            "notes": ["normal", "elevated", "normal", "high", "normal"],
        })
    
    @pytest.fixture
    def risky_dataframe(self):
        """Create a DataFrame with potential quasi-identifiers."""
        return pd.DataFrame({
            "patient_age": [34, 67, 23, 45, 89, 34, 67],
            "zip_code": ["12345", "67890", "12345", "54321", "67890", "12345", "67890"],
            "admission_date": ["2023-01-15", "2023-02-20", "2023-01-15", "2023-03-10", "2023-02-20", "2023-01-15", "2023-02-20"],
            "diagnosis": ["diabetes", "hypertension", "diabetes", "asthma", "hypertension", "diabetes", "hypertension"],
        })
    
    @pytest.fixture
    def high_risk_dataframe(self):
        """Create a DataFrame with unique individuals (k=1)."""
        return pd.DataFrame({
            "age": [34, 67, 23, 45, 89],
            "zip_code": ["12345", "67890", "54321", "98765", "11111"],
            "gender": ["M", "F", "M", "F", "M"],
        })
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initializes with correct parameters."""
        assert analyzer.k_threshold == 5
        assert analyzer.l_threshold == 2
        assert analyzer.t_threshold == 0.2
        assert len(analyzer.quasi_patterns) > 0
    
    def test_identify_quasi_identifiers_safe_data(self, analyzer, safe_dataframe):
        """Should not identify quasi-identifiers in safe data."""
        quasi_columns = analyzer.identify_quasi_identifiers(safe_dataframe)
        # Study ID might be flagged due to high cardinality, but no typical quasi-identifiers
        assert len(quasi_columns) <= 1
        assert "patient_age" not in quasi_columns
        assert "zip_code" not in quasi_columns
        assert "admission_date" not in quasi_columns
    
    def test_identify_quasi_identifiers_risky_data(self, analyzer, risky_dataframe):
        """Should identify quasi-identifiers in risky data."""
        quasi_columns = analyzer.identify_quasi_identifiers(risky_dataframe)
        assert len(quasi_columns) >= 3
        assert "patient_age" in quasi_columns
        assert "zip_code" in quasi_columns
        assert "admission_date" in quasi_columns
    
    def test_k_anonymity_safe_data(self, analyzer, safe_dataframe):
        """Should pass k-anonymity for safe data."""
        result = analyzer.analyze_k_anonymity(safe_dataframe)
        assert result.is_anonymous is True
        assert result.unique_individuals == 0
        assert result.risk_level in ("none", "low")
    
    def test_k_anonymity_risky_data(self, analyzer, risky_dataframe):
        """Should detect k-anonymity issues in risky data."""
        result = analyzer.analyze_k_anonymity(risky_dataframe)
        # With repeated combinations, should have some anonymity
        assert result.k_value >= 1
        assert result.total_groups > 0
        # Risk level depends on group sizes
        assert result.risk_level in ("low", "medium", "high")
    
    def test_k_anonymity_high_risk_data(self, analyzer, high_risk_dataframe):
        """Should detect critical k-anonymity violations."""
        result = analyzer.analyze_k_anonymity(high_risk_dataframe)
        assert result.k_value == 1  # Each person is unique
        assert result.unique_individuals > 0
        assert result.is_anonymous is False
        assert result.risk_level == "critical"
        assert len(result.recommendations) > 0
    
    def test_l_diversity_analysis(self, analyzer, risky_dataframe):
        """Should analyze l-diversity for sensitive attributes."""
        quasi_columns = ["patient_age", "zip_code"]
        sensitive_columns = ["diagnosis"]
        
        result = analyzer.analyze_l_diversity(risky_dataframe, quasi_columns, sensitive_columns)
        assert result.l_value >= 1
        assert "diagnosis" in result.sensitive_attributes
        assert len(result.diversity_by_group) > 0
    
    def test_comprehensive_risk_analysis_safe(self, analyzer, safe_dataframe):
        """Should show low risk for safe data."""
        analysis = analyzer.analyze_comprehensive_risk(safe_dataframe)
        
        assert analysis["overall_risk"]["risk_level"] in ("low", "none")
        assert analysis["k_anonymity"]["is_anonymous"] is True
        assert len(analysis["dataset_info"]["quasi_identifier_columns"]) <= 1
        assert len(analysis["comprehensive_recommendations"]) > 0
    
    def test_comprehensive_risk_analysis_risky(self, analyzer, risky_dataframe):
        """Should detect risks in risky data."""
        analysis = analyzer.analyze_comprehensive_risk(risky_dataframe)
        
        assert len(analysis["dataset_info"]["quasi_identifier_columns"]) >= 3
        assert analysis["k_anonymity"]["k_value"] >= 1
        assert analysis["overall_risk"]["risk_level"] in ("low", "medium", "high")
        
        # Should have recommendations
        recommendations = analysis["comprehensive_recommendations"]
        assert len(recommendations) > 0
        assert any("generalization" in str(rec).lower() for rec in recommendations)
    
    def test_comprehensive_risk_analysis_high_risk(self, analyzer, high_risk_dataframe):
        """Should detect critical risks in high-risk data."""
        analysis = analyzer.analyze_comprehensive_risk(high_risk_dataframe)
        
        assert analysis["k_anonymity"]["k_value"] == 1
        assert analysis["k_anonymity"]["unique_individuals"] > 0
        assert analysis["overall_risk"]["risk_level"] in ("high", "critical")
        assert analysis["overall_risk"]["requires_immediate_action"] is True
        assert analysis["overall_risk"]["suitable_for_research"] is False
        
        # Should have specific recommendations
        recommendations = analysis["comprehensive_recommendations"]
        assert any("IMMEDIATE ACTION" in str(rec) for rec in recommendations)
    
    def test_privacy_strategies_generation(self, analyzer, risky_dataframe):
        """Should generate appropriate privacy-preserving strategies."""
        analysis = analyzer.analyze_comprehensive_risk(risky_dataframe)
        strategies = analysis["privacy_preserving_strategies"]
        
        assert "generalization" in strategies
        assert "suppression" in strategies
        assert "perturbation" in strategies
        assert "synthetic_data" in strategies
        
        # Should have specific recommendations for detected quasi-identifiers
        generalization_strategies = strategies["generalization"]
        assert len(generalization_strategies) > 0
        
        # Check for age range recommendation
        age_strategies = [s for s in generalization_strategies if "age" in s.get("column", "").lower()]
        if age_strategies:
            assert "age_ranges" in age_strategies[0]["method"]
        
        # Check for ZIP code recommendation
        zip_strategies = [s for s in generalization_strategies if "zip" in s.get("column", "").lower()]
        if zip_strategies:
            assert "zip_3digit" in zip_strategies[0]["method"]
    
    def test_empty_dataframe_handling(self, analyzer):
        """Should handle empty DataFrames gracefully."""
        empty_df = pd.DataFrame()
        result = analyzer.analyze_k_anonymity(empty_df)
        
        assert result.k_value == 0
        assert result.total_groups == 0
        assert result.unique_individuals == 0
        assert result.risk_level == "none"
    
    def test_single_row_dataframe(self, analyzer):
        """Should handle single-row DataFrames."""
        single_df = pd.DataFrame({
            "age": [25],
            "zip_code": ["12345"],
        })
        
        result = analyzer.analyze_k_anonymity(single_df)
        assert result.k_value == 1
        assert result.unique_individuals == 1
        assert result.is_anonymous is False
    
    def test_identical_rows_dataframe(self, analyzer):
        """Should handle identical rows correctly."""
        identical_df = pd.DataFrame({
            "age": [25, 25, 25, 25, 25],
            "zip_code": ["12345", "12345", "12345", "12345", "12345"],
        })
        
        result = analyzer.analyze_k_anonymity(identical_df)
        assert result.k_value == 5  # All rows identical
        assert result.unique_individuals == 0
        assert result.is_anonymous is True
        assert result.risk_level == "none"
    
    def test_missing_values_handling(self, analyzer):
        """Should handle missing values in quasi-identifiers."""
        missing_df = pd.DataFrame({
            "age": [25, None, 30, None, 35],
            "zip_code": ["12345", "67890", None, "12345", "67890"],
        })
        
        result = analyzer.analyze_k_anonymity(missing_df)
        # Should group by combinations including NaN
        assert result.k_value >= 1
        assert result.total_groups > 0
    
    def test_high_cardinality_detection(self, analyzer):
        """Should detect high-cardinality columns as quasi-identifiers."""
        high_cardinality_df = pd.DataFrame({
            "unique_id": range(100),  # 100% unique
            "category": ["A"] * 100,  # 0% unique
            "measurement": range(100),  # 100% unique
        })
        
        quasi_columns = analyzer.identify_quasi_identifiers(high_cardinality_df)
        assert "unique_id" in quasi_columns
        assert "measurement" in quasi_columns
        assert "category" not in quasi_columns
    
    def test_pattern_matching_accuracy(self, analyzer):
        """Should accurately match quasi-identifier patterns."""
        pattern_df = pd.DataFrame({
            "patient_name": ["John", "Jane", "Bob"],  # Should match "name" pattern
            "dob": ["1990-01-01", "1985-05-15", "1992-12-25"],  # Should match "dob" pattern
            "postal_code": ["12345", "67890", "54321"],  # Should match "postal" pattern
            "safe_value": [1, 2, 3],  # Should not match any pattern
        })
        
        quasi_columns = analyzer.identify_quasi_identifiers(pattern_df)
        assert "patient_name" in quasi_columns
        assert "dob" in quasi_columns  
        assert "postal_code" in quasi_columns
        assert "safe_value" not in quasi_columns
    
    def test_performance_with_large_dataset(self, analyzer):
        """Should handle reasonably large datasets efficiently."""
        # Create a moderately large dataset (1000 rows)
        large_df = pd.DataFrame({
            "age": [i % 50 + 20 for i in range(1000)],  # Ages 20-69
            "zip_code": [f"{i % 100:05d}" for i in range(1000)],  # 100 different ZIP codes
            "gender": ["M" if i % 2 else "F" for i in range(1000)],
        })
        
        # Analysis should complete in reasonable time
        import time
        start_time = time.time()
        analysis = analyzer.analyze_comprehensive_risk(large_df)
        duration = time.time() - start_time
        
        # Should complete in under 5 seconds for 1000 rows
        assert duration < 5.0
        assert analysis["dataset_info"]["total_rows"] == 1000
        assert len(analysis["dataset_info"]["quasi_identifier_columns"]) >= 2


class TestQuasiIdentifierPatterns:
    """Tests for quasi-identifier pattern definitions."""
    
    def test_pattern_categories(self):
        """Should have comprehensive pattern categories."""
        try:
            from src.workflow_engine.stages.phi_analyzers.quasi_identifier_analyzer import (
                QUASI_IDENTIFIER_PATTERNS
            )
            
            # Should have major categories
            assert "age" in QUASI_IDENTIFIER_PATTERNS
            assert "location" in QUASI_IDENTIFIER_PATTERNS
            assert "gender" in QUASI_IDENTIFIER_PATTERNS
            assert "race" in QUASI_IDENTIFIER_PATTERNS
            assert "date" in QUASI_IDENTIFIER_PATTERNS
            
            # Each category should have multiple patterns
            for category, patterns in QUASI_IDENTIFIER_PATTERNS.items():
                assert len(patterns) > 0
                assert isinstance(patterns, list)
                for pattern in patterns:
                    assert isinstance(pattern, str)
                    assert len(pattern) > 0
                    
        except ImportError:
            pytest.skip("QUASI_IDENTIFIER_PATTERNS not available")
    
    def test_sensitive_combinations(self):
        """Should have predefined sensitive combinations."""
        try:
            from src.workflow_engine.stages.phi_analyzers.quasi_identifier_analyzer import (
                SENSITIVE_QUASI_COMBINATIONS
            )
            
            # Should have multiple combinations
            assert len(SENSITIVE_QUASI_COMBINATIONS) >= 10
            
            # Should include common risky combinations
            age_zip_gender = ["age", "zip_code", "gender"]
            assert any(set(combo) == set(age_zip_gender) for combo in SENSITIVE_QUASI_COMBINATIONS)
            
            # Should have medical context combinations
            medical_combos = [combo for combo in SENSITIVE_QUASI_COMBINATIONS 
                            if any("date" in item for item in combo) and 
                               any(item in ["zip_code", "location"] for item in combo)]
            assert len(medical_combos) > 0
            
        except ImportError:
            pytest.skip("SENSITIVE_QUASI_COMBINATIONS not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])