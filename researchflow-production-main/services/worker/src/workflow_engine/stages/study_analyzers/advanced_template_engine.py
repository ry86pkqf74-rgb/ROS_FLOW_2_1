"""
Advanced Template Engine for Clinical Protocol Generation

This module extends the basic template engine with advanced features:
- Conditional section rendering
- Nested variable support
- AI-enhanced content generation
- Dynamic template adaptation
- Multi-language support
- Advanced formatting and styling

Author: Stage 3.2 Enhancement Team
"""

import logging
import re
import json
import asyncio
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class ContentGenerationStrategy(Enum):
    """Strategies for AI-enhanced content generation."""
    TEMPLATE_ONLY = "template_only"
    AI_ENHANCED = "ai_enhanced"
    AI_GENERATED = "ai_generated"
    HYBRID = "hybrid"


class ConditionalOperator(Enum):
    """Operators for conditional logic in templates."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"


@dataclass
class ConditionalRule:
    """Represents a conditional logic rule for section rendering."""
    variable_name: str
    operator: ConditionalOperator
    expected_value: Any
    alternate_content: Optional[str] = None
    hide_section: bool = False


@dataclass
class ContentEnhancementRequest:
    """Request for AI-enhanced content generation."""
    section_id: str
    base_content: str
    study_context: Dict[str, Any]
    enhancement_strategy: ContentGenerationStrategy
    target_length: Optional[int] = None
    style_guidelines: List[str] = field(default_factory=list)
    regulatory_requirements: List[str] = field(default_factory=list)


@dataclass
class TemplateVariable:
    """Enhanced template variable with metadata and validation."""
    name: str
    variable_type: str  # string, number, list, dict, boolean
    required: bool = True
    default_value: Any = None
    validation_pattern: Optional[str] = None
    description: str = ""
    examples: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


class AdvancedTemplateEngine:
    """
    Advanced template processing engine with enhanced features.
    """
    
    def __init__(self, 
                 enable_ai_enhancement: bool = True,
                 enable_conditional_rendering: bool = True,
                 enable_nested_variables: bool = True):
        self.enable_ai_enhancement = enable_ai_enhancement
        self.enable_conditional_rendering = enable_conditional_rendering
        self.enable_nested_variables = enable_nested_variables
        
        # Enhanced processing components
        self.variable_registry: Dict[str, TemplateVariable] = {}
        self.conditional_evaluator = ConditionalEvaluator()
        self.content_enhancer = ContentEnhancer() if enable_ai_enhancement else None
        self.formatting_engine = FormattingEngine()
        
        # Processing metrics
        self.processing_stats = {
            "sections_processed": 0,
            "variables_substituted": 0,
            "conditions_evaluated": 0,
            "ai_enhancements": 0
        }
        
        logger.info("Advanced Template Engine initialized")
    
    async def process_advanced_template(self,
                                      template_content: str,
                                      variables: Dict[str, Any],
                                      conditional_rules: List[ConditionalRule] = None,
                                      enhancement_requests: List[ContentEnhancementRequest] = None) -> str:
        """
        Process template with advanced features.
        
        Args:
            template_content: Raw template content
            variables: Variable values for substitution
            conditional_rules: Rules for conditional rendering
            enhancement_requests: Requests for AI enhancement
            
        Returns:
            Processed template content
        """
        try:
            logger.info("Processing advanced template")
            
            # Step 1: Preprocess template for advanced features
            preprocessed_content = await self._preprocess_template(template_content)
            
            # Step 2: Evaluate conditional logic
            if self.enable_conditional_rendering and conditional_rules:
                preprocessed_content = await self._evaluate_conditionals(
                    preprocessed_content, variables, conditional_rules
                )
            
            # Step 3: Process nested variables
            if self.enable_nested_variables:
                processed_variables = await self._process_nested_variables(variables)
            else:
                processed_variables = variables
            
            # Step 4: Substitute variables with enhanced logic
            substituted_content = await self._enhanced_variable_substitution(
                preprocessed_content, processed_variables
            )
            
            # Step 5: AI enhancement
            if self.enable_ai_enhancement and enhancement_requests:
                substituted_content = await self._apply_ai_enhancements(
                    substituted_content, enhancement_requests
                )
            
            # Step 6: Final formatting
            final_content = await self.formatting_engine.apply_final_formatting(
                substituted_content, processed_variables
            )
            
            # Update metrics
            self.processing_stats["sections_processed"] += 1
            
            logger.info("Advanced template processing completed")
            return final_content
            
        except Exception as e:
            logger.error(f"Error in advanced template processing: {str(e)}")
            return f"Error processing template: {str(e)}"
    
    async def _preprocess_template(self, content: str) -> str:
        """Preprocess template for advanced features."""
        try:
            # Handle multiline variables
            content = re.sub(
                r'\{\{([^}]+)\}\}\s*\n\{\{([^}]+)\}\}',
                r'{{\1}} {{\2}}',
                content
            )
            
            # Process template directives
            content = await self._process_template_directives(content)
            
            return content
            
        except Exception as e:
            logger.error(f"Error preprocessing template: {str(e)}")
            return content
    
    async def _process_template_directives(self, content: str) -> str:
        """Process special template directives."""
        try:
            # Process @include directives
            include_pattern = r'@include\s+"([^"]+)"'
            includes = re.findall(include_pattern, content)
            
            for include_path in includes:
                # For now, replace with placeholder
                content = content.replace(
                    f'@include "{include_path}"',
                    f"[INCLUDED: {include_path}]"
                )
            
            # Process @format directives
            format_pattern = r'@format\s+"([^"]+)"\s+(.+)'
            formats = re.findall(format_pattern, content)
            
            for format_type, format_content in formats:
                formatted_content = await self._apply_format_directive(format_type, format_content)
                content = content.replace(
                    f'@format "{format_type}" {format_content}',
                    formatted_content
                )
            
            return content
            
        except Exception as e:
            logger.error(f"Error processing template directives: {str(e)}")
            return content
    
    async def _apply_format_directive(self, format_type: str, content: str) -> str:
        """Apply specific formatting directive."""
        try:
            if format_type == "uppercase":
                return content.upper()
            elif format_type == "lowercase":
                return content.lower()
            elif format_type == "title":
                return content.title()
            elif format_type == "bullet_list":
                items = content.split(",")
                return "\n".join(f"• {item.strip()}" for item in items)
            elif format_type == "numbered_list":
                items = content.split(",")
                return "\n".join(f"{i+1}. {item.strip()}" for i, item in enumerate(items))
            else:
                return content
                
        except Exception as e:
            logger.error(f"Error applying format directive {format_type}: {str(e)}")
            return content
    
    async def _evaluate_conditionals(self,
                                   content: str,
                                   variables: Dict[str, Any],
                                   rules: List[ConditionalRule]) -> str:
        """Evaluate conditional logic for template rendering."""
        try:
            processed_content = content
            
            for rule in rules:
                condition_met = self.conditional_evaluator.evaluate_condition(
                    variables, rule
                )
                
                if not condition_met:
                    if rule.hide_section:
                        # Remove entire section
                        section_pattern = f"<!--{rule.variable_name}_START-->.*?<!--{rule.variable_name}_END-->"
                        processed_content = re.sub(
                            section_pattern, "", processed_content, flags=re.DOTALL
                        )
                    elif rule.alternate_content:
                        # Replace with alternate content
                        processed_content = processed_content.replace(
                            f"{{{{{rule.variable_name}}}}}",
                            rule.alternate_content
                        )
                
                self.processing_stats["conditions_evaluated"] += 1
            
            return processed_content
            
        except Exception as e:
            logger.error(f"Error evaluating conditionals: {str(e)}")
            return content
    
    async def _process_nested_variables(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Process nested variables and complex data structures."""
        try:
            processed_vars = {}
            
            for key, value in variables.items():
                if isinstance(value, dict):
                    # Handle nested dictionaries
                    for nested_key, nested_value in value.items():
                        processed_vars[f"{key}.{nested_key}"] = nested_value
                    processed_vars[key] = value
                elif isinstance(value, list):
                    # Handle list variables
                    processed_vars[key] = value
                    processed_vars[f"{key}_count"] = len(value)
                    
                    if value and isinstance(value[0], dict):
                        # Handle list of dictionaries
                        for i, item in enumerate(value):
                            for item_key, item_value in item.items():
                                processed_vars[f"{key}[{i}].{item_key}"] = item_value
                    else:
                        # Handle simple list
                        for i, item in enumerate(value):
                            processed_vars[f"{key}[{i}]"] = item
                else:
                    processed_vars[key] = value
            
            return processed_vars
            
        except Exception as e:
            logger.error(f"Error processing nested variables: {str(e)}")
            return variables
    
    async def _enhanced_variable_substitution(self,
                                            content: str,
                                            variables: Dict[str, Any]) -> str:
        """Enhanced variable substitution with advanced features."""
        try:
            processed_content = content
            substitution_count = 0
            
            # Handle complex variable patterns
            complex_pattern = r'\{\{([^}]+)\|([^}]+)\}\}'  # {{variable|format}}
            complex_matches = re.findall(complex_pattern, processed_content)
            
            for variable_name, format_spec in complex_matches:
                variable_name = variable_name.strip()
                format_spec = format_spec.strip()
                
                if variable_name in variables:
                    value = variables[variable_name]
                    formatted_value = await self._apply_variable_formatting(value, format_spec)
                    processed_content = processed_content.replace(
                        f"{{{{{variable_name}|{format_spec}}}}}",
                        str(formatted_value)
                    )
                    substitution_count += 1
            
            # Handle standard variable patterns
            standard_pattern = r'\{\{([^}|]+)\}\}'
            standard_matches = re.findall(standard_pattern, processed_content)
            
            for variable_name in standard_matches:
                variable_name = variable_name.strip()
                
                if variable_name in variables:
                    value = variables[variable_name]
                    if value is not None:
                        processed_content = processed_content.replace(
                            f"{{{{{variable_name}}}}}",
                            str(value)
                        )
                        substitution_count += 1
            
            # Handle default value patterns
            default_pattern = r'\{\{([^}]+)\?\?([^}]+)\}\}'  # {{variable??default}}
            default_matches = re.findall(default_pattern, processed_content)
            
            for variable_name, default_value in default_matches:
                variable_name = variable_name.strip()
                default_value = default_value.strip()
                
                actual_value = variables.get(variable_name, default_value)
                processed_content = processed_content.replace(
                    f"{{{{{variable_name}??{default_value}}}}}",
                    str(actual_value)
                )
                substitution_count += 1
            
            self.processing_stats["variables_substituted"] += substitution_count
            return processed_content
            
        except Exception as e:
            logger.error(f"Error in enhanced variable substitution: {str(e)}")
            return content
    
    async def _apply_variable_formatting(self, value: Any, format_spec: str) -> str:
        """Apply formatting specification to variable value."""
        try:
            if format_spec == "upper":
                return str(value).upper()
            elif format_spec == "lower":
                return str(value).lower()
            elif format_spec == "title":
                return str(value).title()
            elif format_spec == "date":
                if isinstance(value, datetime):
                    return value.strftime("%Y-%m-%d")
                elif isinstance(value, str):
                    try:
                        dt = datetime.fromisoformat(value)
                        return dt.strftime("%Y-%m-%d")
                    except:
                        return str(value)
            elif format_spec == "number":
                try:
                    return f"{float(value):,.2f}"
                except:
                    return str(value)
            elif format_spec.startswith("list"):
                # Handle list formatting: list:bullet, list:numbered, list:comma
                if isinstance(value, list):
                    list_type = format_spec.split(":")[-1] if ":" in format_spec else "bullet"
                    if list_type == "bullet":
                        return "\n".join(f"• {item}" for item in value)
                    elif list_type == "numbered":
                        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(value))
                    elif list_type == "comma":
                        return ", ".join(str(item) for item in value)
                return str(value)
            else:
                return str(value)
                
        except Exception as e:
            logger.error(f"Error applying variable formatting: {str(e)}")
            return str(value)
    
    async def _apply_ai_enhancements(self,
                                   content: str,
                                   enhancement_requests: List[ContentEnhancementRequest]) -> str:
        """Apply AI enhancements to content."""
        try:
            if not self.content_enhancer:
                return content
            
            enhanced_content = content
            
            for request in enhancement_requests:
                if request.enhancement_strategy != ContentGenerationStrategy.TEMPLATE_ONLY:
                    enhanced_section = await self.content_enhancer.enhance_content(request)
                    
                    # Replace section content with enhanced version
                    section_marker = f"[SECTION:{request.section_id}]"
                    if section_marker in enhanced_content:
                        enhanced_content = enhanced_content.replace(
                            section_marker, enhanced_section
                        )
                    
                    self.processing_stats["ai_enhancements"] += 1
            
            return enhanced_content
            
        except Exception as e:
            logger.error(f"Error applying AI enhancements: {str(e)}")
            return content
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self.processing_stats.copy()


class ConditionalEvaluator:
    """Evaluates conditional logic for template rendering."""
    
    def evaluate_condition(self, variables: Dict[str, Any], rule: ConditionalRule) -> bool:
        """Evaluate a single conditional rule."""
        try:
            variable_value = variables.get(rule.variable_name)
            
            if rule.operator == ConditionalOperator.EXISTS:
                return variable_value is not None
            elif rule.operator == ConditionalOperator.NOT_EXISTS:
                return variable_value is None
            
            if variable_value is None:
                return False
            
            if rule.operator == ConditionalOperator.EQUALS:
                return variable_value == rule.expected_value
            elif rule.operator == ConditionalOperator.NOT_EQUALS:
                return variable_value != rule.expected_value
            elif rule.operator == ConditionalOperator.GREATER_THAN:
                return float(variable_value) > float(rule.expected_value)
            elif rule.operator == ConditionalOperator.LESS_THAN:
                return float(variable_value) < float(rule.expected_value)
            elif rule.operator == ConditionalOperator.CONTAINS:
                return str(rule.expected_value) in str(variable_value)
            elif rule.operator == ConditionalOperator.NOT_CONTAINS:
                return str(rule.expected_value) not in str(variable_value)
            elif rule.operator == ConditionalOperator.IN_LIST:
                return variable_value in rule.expected_value
            elif rule.operator == ConditionalOperator.NOT_IN_LIST:
                return variable_value not in rule.expected_value
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating condition: {str(e)}")
            return False


class ContentEnhancer:
    """AI-powered content enhancement for protocol sections."""
    
    def __init__(self):
        self.enhancement_cache = {}
        self.content_strategies = {
            ContentGenerationStrategy.AI_ENHANCED: self._ai_enhance_content,
            ContentGenerationStrategy.AI_GENERATED: self._ai_generate_content,
            ContentGenerationStrategy.HYBRID: self._hybrid_content_generation
        }
    
    async def enhance_content(self, request: ContentEnhancementRequest) -> str:
        """Enhance content based on the request strategy."""
        try:
            # Check cache first
            cache_key = f"{request.section_id}_{hash(request.base_content)}"
            if cache_key in self.enhancement_cache:
                return self.enhancement_cache[cache_key]
            
            strategy_func = self.content_strategies.get(request.enhancement_strategy)
            if strategy_func:
                enhanced_content = await strategy_func(request)
            else:
                enhanced_content = request.base_content
            
            # Cache the result
            self.enhancement_cache[cache_key] = enhanced_content
            
            return enhanced_content
            
        except Exception as e:
            logger.error(f"Error enhancing content: {str(e)}")
            return request.base_content
    
    async def _ai_enhance_content(self, request: ContentEnhancementRequest) -> str:
        """Enhance existing content with AI suggestions."""
        try:
            # Simulate AI enhancement (in real implementation, would call AI service)
            enhanced_content = request.base_content
            
            # Add context-aware improvements
            if "safety" in request.section_id.lower():
                enhanced_content += "\n\n**Enhanced Safety Considerations:**\n"
                enhanced_content += "• Comprehensive adverse event monitoring\n"
                enhanced_content += "• Regular safety review meetings\n"
                enhanced_content += "• Predefined stopping rules\n"
            
            if "statistical" in request.section_id.lower():
                enhanced_content += "\n\n**Statistical Enhancement:**\n"
                enhanced_content += "• Interim analysis planning\n"
                enhanced_content += "• Missing data handling strategy\n"
                enhanced_content += "• Multiple comparisons adjustment\n"
            
            return enhanced_content
            
        except Exception as e:
            logger.error(f"Error in AI content enhancement: {str(e)}")
            return request.base_content
    
    async def _ai_generate_content(self, request: ContentEnhancementRequest) -> str:
        """Generate new content using AI."""
        try:
            # Simulate AI generation
            study_type = request.study_context.get("study_type", "clinical trial")
            population = request.study_context.get("target_population", "study population")
            
            if "inclusion" in request.section_id.lower():
                return f"""**Inclusion Criteria for {study_type}:**
1. Age 18-75 years
2. Confirmed diagnosis relevant to study objectives
3. Able to provide informed consent
4. Meet specific {population} characteristics
5. Adequate organ function as defined by laboratory values"""
            
            elif "exclusion" in request.section_id.lower():
                return f"""**Exclusion Criteria:**
1. Pregnancy or lactation
2. Significant comorbidities that may interfere with study procedures
3. Current participation in another clinical trial
4. History of allergic reactions to study interventions
5. Unable to comply with study requirements"""
            
            return request.base_content
            
        except Exception as e:
            logger.error(f"Error in AI content generation: {str(e)}")
            return request.base_content
    
    async def _hybrid_content_generation(self, request: ContentEnhancementRequest) -> str:
        """Combine template content with AI-generated additions."""
        try:
            base_content = request.base_content
            ai_generated = await self._ai_generate_content(request)
            
            # Combine base and generated content intelligently
            if base_content and ai_generated and base_content != ai_generated:
                return f"{base_content}\n\n**AI-Enhanced Additions:**\n{ai_generated}"
            else:
                return ai_generated or base_content
            
        except Exception as e:
            logger.error(f"Error in hybrid content generation: {str(e)}")
            return request.base_content


class FormattingEngine:
    """Advanced formatting engine for protocol content."""
    
    def __init__(self):
        self.formatting_rules = {
            "academic": self._apply_academic_formatting,
            "regulatory": self._apply_regulatory_formatting,
            "clinical": self._apply_clinical_formatting
        }
    
    async def apply_final_formatting(self,
                                   content: str,
                                   variables: Dict[str, Any]) -> str:
        """Apply final formatting to processed content."""
        try:
            formatted_content = content
            
            # Apply general formatting improvements
            formatted_content = await self._apply_general_formatting(formatted_content)
            
            # Apply specific formatting based on document type
            document_type = variables.get("document_type", "clinical")
            if document_type in self.formatting_rules:
                formatted_content = await self.formatting_rules[document_type](formatted_content)
            
            return formatted_content
            
        except Exception as e:
            logger.error(f"Error in final formatting: {str(e)}")
            return content
    
    async def _apply_general_formatting(self, content: str) -> str:
        """Apply general formatting improvements."""
        try:
            # Normalize whitespace
            content = re.sub(r'\n{3,}', '\n\n', content)
            
            # Fix common formatting issues
            content = re.sub(r'(\w)\s*:\s*(\w)', r'\1: \2', content)  # Fix spacing around colons
            content = re.sub(r'\s+([.!?])', r'\1', content)  # Remove space before punctuation
            
            # Ensure proper section breaks
            content = re.sub(r'^(#{1,6}\s+)', r'\n\1', content, flags=re.MULTILINE)
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error in general formatting: {str(e)}")
            return content
    
    async def _apply_academic_formatting(self, content: str) -> str:
        """Apply academic-style formatting."""
        try:
            # Add academic-style references
            content = re.sub(
                r'\b(significant|effective|efficacious)\b',
                r'\1 (see supporting literature)',
                content,
                flags=re.IGNORECASE
            )
            
            return content
            
        except Exception as e:
            logger.error(f"Error in academic formatting: {str(e)}")
            return content
    
    async def _apply_regulatory_formatting(self, content: str) -> str:
        """Apply regulatory-compliant formatting."""
        try:
            # Ensure proper section numbering
            content = self._ensure_section_numbering(content)
            
            # Add regulatory disclaimers where appropriate
            if "safety" in content.lower():
                content += "\n\n*This section follows ICH-GCP guidelines for safety reporting.*"
            
            return content
            
        except Exception as e:
            logger.error(f"Error in regulatory formatting: {str(e)}")
            return content
    
    async def _apply_clinical_formatting(self, content: str) -> str:
        """Apply clinical protocol formatting."""
        try:
            # Emphasize important clinical information
            content = re.sub(
                r'\b(primary endpoint|secondary endpoint|safety endpoint)\b',
                r'**\1**',
                content,
                flags=re.IGNORECASE
            )
            
            return content
            
        except Exception as e:
            logger.error(f"Error in clinical formatting: {str(e)}")
            return content
    
    def _ensure_section_numbering(self, content: str) -> str:
        """Ensure proper section numbering."""
        try:
            lines = content.split('\n')
            processed_lines = []
            section_counter = 0
            
            for line in lines:
                if re.match(r'^#+\s+', line):
                    section_counter += 1
                    # Add section number if not already present
                    if not re.search(r'\d+\.', line):
                        line = re.sub(r'^(#+\s+)', f'\\1{section_counter}. ', line)
                
                processed_lines.append(line)
            
            return '\n'.join(processed_lines)
            
        except Exception as e:
            logger.error(f"Error ensuring section numbering: {str(e)}")
            return content