"""
Validation functions for SupplementaryMaterial Agent.
Phase 3 implementation providing specialized validation capabilities
for different aspects of supplementary material packages.
"""

from typing import List, Dict, Any, Optional, Set
import re
from pathlib import Path
import logging
from .supplementary_types import (
    SupplementaryMaterialState, 
    SupplementaryTable, 
    SupplementaryFigure,
    Appendix,
    JournalRequirements,
    JournalFormat
)

logger = logging.getLogger(__name__)


class ContentStructureValidator:
    """Validates the structure and organization of supplementary content."""
    
    def __init__(self, state: SupplementaryMaterialState):
        self.state = state
    
    def validate_table_structure(self) -> Dict[str, Any]:
        """Validate supplementary table structure and content."""
        issues = []
        warnings = []
        
        for table in self.state.supplementary_tables:
            # Check table numbering format
            if not re.match(r'^S\d+$', table.number):
                issues.append(f"Table {table.number} has invalid numbering format (should be S1, S2, etc.)")
            
            # Check title presence and quality
            if not table.title or len(table.title) < 10:
                issues.append(f"Table {table.number} has missing or inadequate title")
            
            # Check caption completeness
            if not table.caption or len(table.caption) < 50:
                warnings.append(f"Table {table.number} caption may be too brief (< 50 characters)")
            
            # Check content presence
            if not table.content:
                issues.append(f"Table {table.number} has no content")
            
            # Validate table formatting
            content_issues = self._validate_table_content(table)
            issues.extend(content_issues)
        
        return {
            "issues": issues,
            "warnings": warnings,
            "table_count": len(self.state.supplementary_tables),
            "validation_score": self._calculate_score(issues, warnings),
            "structure_compliance": len(issues) == 0
        }
    
    def validate_figure_structure(self) -> Dict[str, Any]:
        """Validate supplementary figure structure and content."""
        issues = []
        warnings = []
        
        for figure in self.state.supplementary_figures:
            # Check figure numbering format
            if not re.match(r'^S\d+$', figure.number):
                issues.append(f"Figure {figure.number} has invalid numbering format (should be S1, S2, etc.)")
            
            # Check title presence and quality
            if not figure.title or len(figure.title) < 10:
                issues.append(f"Figure {figure.number} has missing or inadequate title")
            
            # Check caption completeness
            if not figure.caption or len(figure.caption) < 100:
                warnings.append(f"Figure {figure.number} caption may be too brief (< 100 characters)")
            
            # Check file path
            if not figure.file_path:
                issues.append(f"Figure {figure.number} has no file path specified")
            
            # Validate figure specifications
            spec_issues = self._validate_figure_specs(figure)
            issues.extend(spec_issues)
        
        return {
            "issues": issues,
            "warnings": warnings,
            "figure_count": len(self.state.supplementary_figures),
            "validation_score": self._calculate_score(issues, warnings),
            "structure_compliance": len(issues) == 0
        }
    
    def validate_appendix_structure(self) -> Dict[str, Any]:
        """Validate appendix structure and organization."""
        issues = []
        warnings = []
        
        for appendix in self.state.appendices:
            # Check appendix numbering format
            if not re.match(r'^A\d*$', appendix.id):
                issues.append(f"Appendix {appendix.id} has invalid numbering format (should be A, A1, A2, etc.)")
            
            # Check title presence
            if not appendix.title:
                issues.append(f"Appendix {appendix.id} has no title")
            
            # Check content presence
            if not appendix.content:
                issues.append(f"Appendix {appendix.id} has no content")
            
            # Check type assignment
            if not appendix.type:
                warnings.append(f"Appendix {appendix.id} has no type specified")
        
        return {
            "issues": issues,
            "warnings": warnings,
            "appendix_count": len(self.state.appendices),
            "validation_score": self._calculate_score(issues, warnings),
            "structure_compliance": len(issues) == 0
        }
    
    def _validate_table_content(self, table: SupplementaryTable) -> List[str]:
        """Validate specific table content structure."""
        issues = []
        
        content = table.content.lower()
        
        # Check for basic table elements
        if 'table' not in content and '<table>' not in content and '|' not in content:
            issues.append(f"Table {table.number} content doesn't appear to be in table format")
        
        # Check for headers
        if 'header' not in content and '<th>' not in content and not any(
            keyword in content for keyword in ['variable', 'parameter', 'measure', 'outcome']
        ):
            issues.append(f"Table {table.number} may be missing column headers")
        
        return issues
    
    def _validate_figure_specs(self, figure: SupplementaryFigure) -> List[str]:
        """Validate figure technical specifications."""
        issues = []
        
        # Check file format
        if hasattr(figure, 'format'):
            valid_formats = ['pdf', 'png', 'jpeg', 'svg', 'tiff']
            if figure.format.lower() not in valid_formats:
                issues.append(f"Figure {figure.number} has unsupported format: {figure.format}")
        
        # Check DPI for raster formats
        if hasattr(figure, 'format') and hasattr(figure, 'dpi'):
            if figure.format.lower() in ['png', 'jpeg', 'tiff'] and figure.dpi < 300:
                issues.append(f"Figure {figure.number} DPI ({figure.dpi}) is below minimum requirement (300)")
        
        return issues
    
    def _calculate_score(self, issues: List[str], warnings: List[str]) -> float:
        """Calculate validation score based on issues and warnings."""
        if not issues and not warnings:
            return 1.0
        
        # Deduct points for issues and warnings
        score = 1.0 - (len(issues) * 0.2) - (len(warnings) * 0.1)
        return max(0.0, score)


class CrossReferenceIntegrityValidator:
    """Validates cross-reference integrity across the entire package."""
    
    def __init__(self, state: SupplementaryMaterialState):
        self.state = state
    
    def validate_all_references(self) -> Dict[str, Any]:
        """Comprehensive cross-reference validation."""
        
        # Get all references from different sources
        main_text_refs = self._extract_references(self.state.main_manuscript, "main_text")
        table_refs = self._extract_table_references()
        figure_refs = self._extract_figure_references()
        appendix_refs = self._extract_appendix_references()
        
        all_references = {
            **main_text_refs,
            **table_refs,
            **figure_refs,
            **appendix_refs
        }
        
        # Validate each reference
        broken_refs = []
        orphaned_items = []
        circular_refs = []
        
        for source, refs in all_references.items():
            for ref in refs:
                validation_result = self._validate_reference(ref, source)
                if not validation_result['valid']:
                    broken_refs.append({
                        "source": source,
                        "reference": ref,
                        "issue": validation_result['issue']
                    })
        
        # Find orphaned items
        orphaned_items = self._find_orphaned_items(all_references)
        
        # Check for circular references
        circular_refs = self._detect_circular_references(all_references)
        
        return {
            "total_references": sum(len(refs) for refs in all_references.values()),
            "broken_references": broken_refs,
            "orphaned_items": orphaned_items,
            "circular_references": circular_refs,
            "reference_map": all_references,
            "validation_score": self._calculate_reference_score(
                len(broken_refs), len(orphaned_items), len(circular_refs), 
                sum(len(refs) for refs in all_references.values())
            ),
            "integrity_passed": len(broken_refs) == 0 and len(orphaned_items) == 0
        }
    
    def _extract_references(self, text: str, source: str) -> Dict[str, List[str]]:
        """Extract all types of references from text."""
        if not text:
            return {source: []}
        
        patterns = {
            'table': r'(?:Table\s+S\d+|Supplementary\s+Table\s+\d+)',
            'figure': r'(?:Figure\s+S\d+|Supplementary\s+Figure\s+\d+)',
            'appendix': r'(?:Appendix\s+[A-Z]\d*|Supplementary\s+Appendix\s+[A-Z]\d*)',
            'method': r'(?:Supplementary\s+Method\s+\d+|Method\s+S\d+)',
            'section': r'(?:Section\s+S\d+|Supplementary\s+Section\s+\d+)'
        }
        
        all_refs = []
        for ref_type, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            all_refs.extend(matches)
        
        return {source: list(set(all_refs))}  # Remove duplicates
    
    def _extract_table_references(self) -> Dict[str, List[str]]:
        """Extract references from all table captions and content."""
        table_refs = {}
        
        for table in self.state.supplementary_tables:
            source = f"table_{table.number}"
            text = table.caption + " " + table.content
            refs = self._extract_references(text, source)
            table_refs.update(refs)
        
        return table_refs
    
    def _extract_figure_references(self) -> Dict[str, List[str]]:
        """Extract references from all figure captions."""
        figure_refs = {}
        
        for figure in self.state.supplementary_figures:
            source = f"figure_{figure.number}"
            text = figure.caption
            if figure.legend:
                text += " " + figure.legend
            refs = self._extract_references(text, source)
            figure_refs.update(refs)
        
        return figure_refs
    
    def _extract_appendix_references(self) -> Dict[str, List[str]]:
        """Extract references from all appendix content."""
        appendix_refs = {}
        
        for appendix in self.state.appendices:
            source = f"appendix_{appendix.id}"
            text = appendix.content
            refs = self._extract_references(text, source)
            appendix_refs.update(refs)
        
        return appendix_refs
    
    def _validate_reference(self, ref: str, source: str) -> Dict[str, Any]:
        """Validate a single reference."""
        ref_lower = ref.lower()
        
        # Parse reference type and number
        if 'table' in ref_lower:
            # Extract table number
            table_match = re.search(r's?(\d+)', ref_lower)
            if table_match:
                expected_id = f"S{table_match.group(1)}"
                exists = any(table.number == expected_id for table in self.state.supplementary_tables)
                if not exists:
                    return {"valid": False, "issue": f"Table {expected_id} not found"}
        
        elif 'figure' in ref_lower:
            # Extract figure number
            figure_match = re.search(r's?(\d+)', ref_lower)
            if figure_match:
                expected_id = f"S{figure_match.group(1)}"
                exists = any(figure.number == expected_id for figure in self.state.supplementary_figures)
                if not exists:
                    return {"valid": False, "issue": f"Figure {expected_id} not found"}
        
        elif 'appendix' in ref_lower:
            # Extract appendix ID
            appendix_match = re.search(r'appendix\s+([a-z]\d*)', ref_lower)
            if appendix_match:
                expected_id = appendix_match.group(1).upper()
                exists = any(appendix.id == expected_id for appendix in self.state.appendices)
                if not exists:
                    return {"valid": False, "issue": f"Appendix {expected_id} not found"}
        
        return {"valid": True, "issue": None}
    
    def _find_orphaned_items(self, all_references: Dict[str, List[str]]) -> List[Dict[str, str]]:
        """Find supplementary items that are never referenced."""
        orphaned = []
        
        # Collect all referenced items
        referenced_items = set()
        for refs in all_references.values():
            for ref in refs:
                # Normalize reference
                ref_lower = ref.lower()
                if 'table' in ref_lower:
                    match = re.search(r's?(\d+)', ref_lower)
                    if match:
                        referenced_items.add(f"table_S{match.group(1)}")
                elif 'figure' in ref_lower:
                    match = re.search(r's?(\d+)', ref_lower)
                    if match:
                        referenced_items.add(f"figure_S{match.group(1)}")
                elif 'appendix' in ref_lower:
                    match = re.search(r'appendix\s+([a-z]\d*)', ref_lower)
                    if match:
                        referenced_items.add(f"appendix_{match.group(1).upper()}")
        
        # Check tables
        for table in self.state.supplementary_tables:
            item_id = f"table_{table.number}"
            if item_id not in referenced_items:
                orphaned.append({"type": "table", "id": table.number, "title": table.title})
        
        # Check figures
        for figure in self.state.supplementary_figures:
            item_id = f"figure_{figure.number}"
            if item_id not in referenced_items:
                orphaned.append({"type": "figure", "id": figure.number, "title": figure.title})
        
        # Check appendices
        for appendix in self.state.appendices:
            item_id = f"appendix_{appendix.id}"
            if item_id not in referenced_items:
                orphaned.append({"type": "appendix", "id": appendix.id, "title": appendix.title})
        
        return orphaned
    
    def _detect_circular_references(self, all_references: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Detect circular references between items."""
        circular = []
        
        # Build reference graph
        ref_graph = {}
        for source, refs in all_references.items():
            ref_graph[source] = []
            for ref in refs:
                # Convert reference to source format
                normalized_ref = self._normalize_reference_to_source(ref)
                if normalized_ref and normalized_ref != source:
                    ref_graph[source].append(normalized_ref)
        
        # Find cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node, path):
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                return cycle
            
            if node in visited:
                return None
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in ref_graph.get(node, []):
                cycle = has_cycle(neighbor, path)
                if cycle:
                    return cycle
            
            rec_stack.remove(node)
            path.pop()
            return None
        
        for node in ref_graph:
            if node not in visited:
                cycle = has_cycle(node, [])
                if cycle:
                    circular.append({"cycle": cycle, "length": len(cycle) - 1})
        
        return circular
    
    def _normalize_reference_to_source(self, ref: str) -> Optional[str]:
        """Convert a reference string to source format."""
        ref_lower = ref.lower()
        
        if 'table' in ref_lower:
            match = re.search(r's?(\d+)', ref_lower)
            if match:
                return f"table_S{match.group(1)}"
        
        elif 'figure' in ref_lower:
            match = re.search(r's?(\d+)', ref_lower)
            if match:
                return f"figure_S{match.group(1)}"
        
        elif 'appendix' in ref_lower:
            match = re.search(r'appendix\s+([a-z]\d*)', ref_lower)
            if match:
                return f"appendix_{match.group(1).upper()}"
        
        return None
    
    def _calculate_reference_score(self, broken_count: int, orphaned_count: int, 
                                 circular_count: int, total_refs: int) -> float:
        """Calculate overall reference integrity score."""
        if total_refs == 0:
            return 1.0
        
        # Penalty system
        broken_penalty = broken_count * 0.3
        orphaned_penalty = orphaned_count * 0.2
        circular_penalty = circular_count * 0.4
        
        total_penalty = broken_penalty + orphaned_penalty + circular_penalty
        score = 1.0 - (total_penalty / max(total_refs, 1))
        
        return max(0.0, score)


class JournalComplianceValidator:
    """Validates compliance with specific journal requirements."""
    
    def __init__(self, state: SupplementaryMaterialState):
        self.state = state
    
    def validate_journal_compliance(self, journal_format: JournalFormat) -> Dict[str, Any]:
        """Validate compliance with specific journal requirements."""
        
        requirements = JournalRequirements.get_requirements(journal_format)
        compliance_issues = []
        warnings = []
        
        # Check file size limits
        size_check = self._check_size_limits(requirements)
        if size_check['issues']:
            compliance_issues.extend(size_check['issues'])
        if size_check['warnings']:
            warnings.extend(size_check['warnings'])
        
        # Check format requirements
        format_check = self._check_format_requirements(requirements)
        if format_check['issues']:
            compliance_issues.extend(format_check['issues'])
        
        # Check content requirements
        content_check = self._check_content_requirements(requirements)
        if content_check['issues']:
            compliance_issues.extend(content_check['issues'])
        
        # Check structural requirements
        structure_check = self._check_structural_requirements(requirements)
        if structure_check['issues']:
            compliance_issues.extend(structure_check['issues'])
        
        return {
            "journal": journal_format.value,
            "compliance_score": self._calculate_compliance_score(compliance_issues, warnings),
            "issues": compliance_issues,
            "warnings": warnings,
            "requirements_met": len(compliance_issues) == 0,
            "size_compliance": size_check,
            "format_compliance": format_check,
            "content_compliance": content_check,
            "structure_compliance": structure_check
        }
    
    def _check_size_limits(self, requirements: JournalRequirements) -> Dict[str, Any]:
        """Check package size compliance."""
        issues = []
        warnings = []
        
        current_size = self.state.package_size_mb
        max_size = requirements.max_size_mb
        
        if current_size > max_size:
            issues.append(f"Package size ({current_size:.1f}MB) exceeds journal limit ({max_size}MB)")
        elif current_size > max_size * 0.9:
            warnings.append(f"Package size ({current_size:.1f}MB) is close to journal limit ({max_size}MB)")
        
        # Check page limits if specified
        if requirements.max_supplement_pages:
            current_pages = self.state.total_supplement_pages
            max_pages = requirements.max_supplement_pages
            
            if current_pages > max_pages:
                issues.append(f"Supplement pages ({current_pages}) exceed journal limit ({max_pages})")
        
        return {
            "issues": issues,
            "warnings": warnings,
            "size_compliance_score": 1.0 if not issues else 0.5 if not warnings else 0.8
        }
    
    def _check_format_requirements(self, requirements: JournalRequirements) -> Dict[str, Any]:
        """Check file format compliance."""
        issues = []
        preferred_formats = [fmt.value for fmt in requirements.preferred_formats]
        
        # Check table formats
        for table in self.state.supplementary_tables:
            # Infer format from content or file path
            inferred_format = self._infer_table_format(table)
            if inferred_format and inferred_format not in preferred_formats:
                if requirements.table_format != inferred_format:
                    issues.append(f"Table {table.number} format ({inferred_format}) not preferred for {requirements.table_format}")
        
        # Check figure formats
        for figure in self.state.supplementary_figures:
            if hasattr(figure, 'format'):
                if figure.format not in preferred_formats:
                    if requirements.figure_format != figure.format:
                        issues.append(f"Figure {figure.number} format ({figure.format}) not preferred for {requirements.figure_format}")
        
        return {
            "issues": issues,
            "preferred_formats": preferred_formats,
            "format_compliance_score": 1.0 if not issues else max(0.3, 1.0 - len(issues) * 0.2)
        }
    
    def _check_content_requirements(self, requirements: JournalRequirements) -> Dict[str, Any]:
        """Check required content elements."""
        issues = []
        
        # Check data availability statement
        if requirements.requires_data_statement:
            if not self.state.data_availability_statement:
                issues.append("Data availability statement required but missing")
            elif len(self.state.data_availability_statement.strip()) < 50:
                issues.append("Data availability statement too brief")
        
        # Check code availability
        if requirements.requires_code:
            has_code = any("code" in item.lower() or "script" in item.lower() 
                         for item in self.state.package_manifest.values())
            if not has_code:
                issues.append("Analysis code required but not included in manifest")
        
        return {
            "issues": issues,
            "content_compliance_score": 1.0 if not issues else max(0.4, 1.0 - len(issues) * 0.3)
        }
    
    def _check_structural_requirements(self, requirements: JournalRequirements) -> Dict[str, Any]:
        """Check structural organization requirements."""
        issues = []
        
        # Check naming convention compliance
        naming_pattern = requirements.naming_convention
        
        # Validate file naming (simplified check)
        if "supplement" in naming_pattern.lower():
            # Check if items follow supplement naming
            for table in self.state.supplementary_tables:
                if not table.number.startswith('S'):
                    issues.append(f"Table {table.number} doesn't follow supplement naming convention")
        
        return {
            "issues": issues,
            "structure_compliance_score": 1.0 if not issues else max(0.5, 1.0 - len(issues) * 0.2)
        }
    
    def _infer_table_format(self, table: SupplementaryTable) -> Optional[str]:
        """Infer table format from content or metadata."""
        content = table.content.lower()
        
        if '<table>' in content or '<tr>' in content:
            return 'html'
        elif ',' in content and '\n' in content:
            return 'csv'
        elif file_path := getattr(table, 'file_path', None):
            return Path(file_path).suffix.lstrip('.').lower()
        
        return None
    
    def _calculate_compliance_score(self, issues: List[str], warnings: List[str]) -> float:
        """Calculate overall compliance score."""
        if not issues and not warnings:
            return 1.0
        
        # Weight issues more heavily than warnings
        issue_penalty = len(issues) * 0.25
        warning_penalty = len(warnings) * 0.1
        
        total_penalty = issue_penalty + warning_penalty
        score = 1.0 - total_penalty
        
        return max(0.0, score)


# Main validation interface
class SupplementaryPackageValidator:
    """Main validator that orchestrates all validation checks."""
    
    def __init__(self, state: SupplementaryMaterialState):
        self.state = state
        self.structure_validator = ContentStructureValidator(state)
        self.reference_validator = CrossReferenceIntegrityValidator(state)
        self.compliance_validator = JournalComplianceValidator(state)
    
    def run_full_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation of the entire package."""
        
        # Structure validation
        table_validation = self.structure_validator.validate_table_structure()
        figure_validation = self.structure_validator.validate_figure_structure()
        appendix_validation = self.structure_validator.validate_appendix_structure()
        
        # Reference integrity validation
        reference_validation = self.reference_validator.validate_all_references()
        
        # Journal compliance validation
        journal_validation = self.compliance_validator.validate_journal_compliance(self.state.journal_format)
        
        # Calculate overall scores
        structure_score = (
            table_validation['validation_score'] + 
            figure_validation['validation_score'] + 
            appendix_validation['validation_score']
        ) / 3
        
        reference_score = reference_validation['validation_score']
        compliance_score = journal_validation['compliance_score']
        
        overall_score = (structure_score + reference_score + compliance_score) / 3
        
        return {
            "overall_validation_score": overall_score,
            "validation_passed": overall_score >= 0.8,
            "component_scores": {
                "structure": structure_score,
                "references": reference_score,
                "compliance": compliance_score
            },
            "structure_validation": {
                "tables": table_validation,
                "figures": figure_validation,
                "appendices": appendix_validation
            },
            "reference_validation": reference_validation,
            "journal_compliance": journal_validation,
            "summary": self._generate_validation_summary(
                overall_score, table_validation, figure_validation, 
                appendix_validation, reference_validation, journal_validation
            )
        }
    
    def _generate_validation_summary(self, overall_score: float, table_val: Dict,
                                   figure_val: Dict, appendix_val: Dict,
                                   ref_val: Dict, journal_val: Dict) -> str:
        """Generate a human-readable validation summary."""
        
        if overall_score >= 0.9:
            status = "EXCELLENT"
        elif overall_score >= 0.8:
            status = "GOOD"
        elif overall_score >= 0.7:
            status = "ACCEPTABLE"
        else:
            status = "NEEDS IMPROVEMENT"
        
        summary = f"Validation Status: {status} (Score: {overall_score:.2f}/1.00)\n\n"
        
        # Add component summaries
        summary += f"📊 Tables: {table_val['validation_score']:.2f} ({table_val['table_count']} tables)\n"
        summary += f"📈 Figures: {figure_val['validation_score']:.2f} ({figure_val['figure_count']} figures)\n"
        summary += f"📋 Appendices: {appendix_val['validation_score']:.2f} ({appendix_val['appendix_count']} appendices)\n"
        summary += f"🔗 References: {ref_val['validation_score']:.2f} ({ref_val['total_references']} references)\n"
        summary += f"✅ Compliance: {journal_val['compliance_score']:.2f} ({journal_val['journal']} format)\n"
        
        # Add critical issues
        critical_issues = []
        if table_val['issues']:
            critical_issues.extend(table_val['issues'])
        if figure_val['issues']:
            critical_issues.extend(figure_val['issues'])
        if ref_val['broken_references']:
            critical_issues.extend([f"Broken reference: {ref['reference']}" for ref in ref_val['broken_references']])
        if journal_val['issues']:
            critical_issues.extend(journal_val['issues'])
        
        if critical_issues:
            summary += f"\n🚨 Critical Issues ({len(critical_issues)}):\n"
            for issue in critical_issues[:5]:  # Show top 5
                summary += f"  • {issue}\n"
            if len(critical_issues) > 5:
                summary += f"  • ... and {len(critical_issues) - 5} more\n"
        
        return summary


# Utility functions
def validate_package_structure(state: SupplementaryMaterialState) -> Dict[str, Any]:
    """Quick structure validation."""
    validator = ContentStructureValidator(state)
    return {
        "tables": validator.validate_table_structure(),
        "figures": validator.validate_figure_structure(),
        "appendices": validator.validate_appendix_structure()
    }


def validate_cross_reference_integrity(state: SupplementaryMaterialState) -> Dict[str, Any]:
    """Quick cross-reference integrity check."""
    validator = CrossReferenceIntegrityValidator(state)
    return validator.validate_all_references()


def validate_journal_compliance(state: SupplementaryMaterialState, 
                               journal: JournalFormat = None) -> Dict[str, Any]:
    """Quick journal compliance check."""
    validator = JournalComplianceValidator(state)
    journal_format = journal or state.journal_format
    return validator.validate_journal_compliance(journal_format)


def run_comprehensive_validation(state: SupplementaryMaterialState) -> Dict[str, Any]:
    """Run full comprehensive validation."""
    validator = SupplementaryPackageValidator(state)
    return validator.run_full_validation()