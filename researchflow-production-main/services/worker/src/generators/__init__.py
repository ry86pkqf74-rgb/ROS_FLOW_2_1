"""
Manuscript Generators
Generate transparency artifacts and manuscript sections for regulatory compliance.
"""

from .evidence_bundle import (
    EvidenceBundleGenerator,
    create_bundle_generator,
)
from .abstract_generator import (
    AbstractGenerator,
    AbstractInput,
    AbstractOutput,
    AbstractStyle,
    create_abstract_generator,
)
from .methods_generator import (
    MethodsGenerator,
    MethodsInput,
    MethodsOutput,
    MethodsTemplate,
    StudyType,
    create_methods_generator,
)
from .results_generator import (
    FigureReference,
    ResultType,
    ResultsGenerator,
    ResultsInput,
    ResultsOutput,
    StatisticalResult,
    StatFormatter,
    TableReference,
    create_results_generator,
)
from .discussion_generator import (
    DiscussionGenerator,
    DiscussionInput,
    DiscussionOutput,
    DiscussionStyle,
    KeyFinding,
    LiteratureReference,
    Limitation,
    create_discussion_generator,
)

__all__ = [
    "EvidenceBundleGenerator",
    "create_bundle_generator",
    "AbstractGenerator",
    "AbstractInput",
    "AbstractOutput",
    "AbstractStyle",
    "create_abstract_generator",
    "MethodsGenerator",
    "MethodsInput",
    "MethodsOutput",
    "MethodsTemplate",
    "StudyType",
    "create_methods_generator",
    "ResultType",
    "StatisticalResult",
    "TableReference",
    "FigureReference",
    "StatFormatter",
    "ResultsGenerator",
    "ResultsInput",
    "ResultsOutput",
    "create_results_generator",
    "DiscussionStyle",
    "KeyFinding",
    "LiteratureReference",
    "Limitation",
    "DiscussionGenerator",
    "DiscussionInput",
    "DiscussionOutput",
    "create_discussion_generator",
]
