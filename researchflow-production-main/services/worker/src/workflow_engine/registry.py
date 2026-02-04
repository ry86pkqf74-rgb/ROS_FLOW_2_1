"""
Stage Registry

This module provides a decorator-based registry for workflow stages.
Stages register themselves using @register_stage and can be retrieved
by stage_id for execution.
"""

import logging
import os
from typing import Dict, List, Optional, Type, Union

from .types import Stage

logger = logging.getLogger("workflow_engine.registry")

# Global registry: stage_id is int (1-20) for main pipeline or str (e.g. "4a") for supplementary
_stage_registry: Dict[Union[int, str], Type[Stage]] = {}

# Supplementary stage IDs allowed (e.g. "4a" for schema validation)
_SUPPLEMENTARY_IDS = frozenset({"4a"})


def _stage_sort_key(sid: Union[int, str]) -> tuple:
    """Sort key so ints 1-20 order first, then supplementary e.g. '4a' after 4."""
    if isinstance(sid, int):
        return (0, sid)
    return (1, sid)


def register_stage(cls: Type[Stage]) -> Type[Stage]:
    """Decorator to register a stage class in the global registry.

    Usage:
        @register_stage
        class MyStage:
            stage_id = 3
            stage_name = "IRB Compliance Check"

            async def execute(self, context: StageContext) -> StageResult:
                ...

    Args:
        cls: The stage class to register

    Returns:
        The original class (unmodified)

    Raises:
        ValueError: If stage_id is already registered or invalid
    """
    if not hasattr(cls, 'stage_id'):
        raise ValueError(f"Stage class {cls.__name__} must have a 'stage_id' attribute")

    if not hasattr(cls, 'stage_name'):
        raise ValueError(f"Stage class {cls.__name__} must have a 'stage_name' attribute")

    stage_id = cls.stage_id

    if isinstance(stage_id, str):
        if stage_id not in _SUPPLEMENTARY_IDS:
            raise ValueError(f"stage_id must be an integer 1-20 or a supplementary id in {_SUPPLEMENTARY_IDS}, got {stage_id!r}")
    elif not (isinstance(stage_id, int) and 1 <= stage_id <= 20):
        raise ValueError(f"stage_id must be an integer between 1 and 20, or a supplementary id, got {stage_id}")

    if stage_id in _stage_registry:
        existing = _stage_registry[stage_id]
        raise ValueError(
            f"Stage {stage_id} already registered by {existing.__name__}, "
            f"cannot register {cls.__name__}"
        )

    _stage_registry[stage_id] = cls
    logger.debug(f"Registered stage {stage_id}: {cls.stage_name}")

    return cls


def get_stage(stage_id: Union[int, str]) -> Optional[Type[Stage]]:
    """Retrieve a registered stage class by its ID.

    Args:
        stage_id: The stage identifier (1-20 or supplementary e.g. "4a")

    Returns:
        The registered Stage class, or None if not found
    """
    # Feature flag for Stage 1: ProtocolDesignAgent vs legacy UploadIntakeStage
    if stage_id == 1:
        return _get_stage_1_with_feature_flag()
    
    return _stage_registry.get(stage_id)


def _get_stage_1_with_feature_flag() -> Optional[Type[Stage]]:
    """Get Stage 1 implementation based on feature flag.
    
    Returns:
        ProtocolDesignStage (new PICO-based) if ENABLE_NEW_STAGE_1=true,
        otherwise legacy UploadIntakeStage
    """
    enable_new_stage_1 = os.getenv('ENABLE_NEW_STAGE_1', 'false').lower() == 'true'
    
    if enable_new_stage_1:
        # Look for new ProtocolDesignStage registered as stage_id=1
        # Check if it's the new implementation by class name
        stage_1_class = _stage_registry.get(1)
        if stage_1_class and 'ProtocolDesign' in stage_1_class.__name__:
            logger.info(f"Using new ProtocolDesignStage for Stage 1 (ENABLE_NEW_STAGE_1=true): {stage_1_class.__name__}")
            return stage_1_class
        else:
            logger.warning("ENABLE_NEW_STAGE_1=true but ProtocolDesignStage not found, falling back to legacy")
    
    # Default to legacy Stage 1 - look for upload-related stage
    stage_1_class = _stage_registry.get(1)
    if stage_1_class:
        if 'ProtocolDesign' in stage_1_class.__name__ and not enable_new_stage_1:
            logger.warning("Found ProtocolDesignStage but ENABLE_NEW_STAGE_1=false, this may cause issues")
        logger.info(f"Using Stage 1 implementation (ENABLE_NEW_STAGE_1={enable_new_stage_1}): {stage_1_class.__name__}")
    
    return stage_1_class


def list_stages() -> List[Dict[str, any]]:
    """List all registered stages.

    Returns:
        List of dicts with stage_id, stage_name, and class_name
    """
    stages = []
    for stage_id in sorted(_stage_registry.keys(), key=_stage_sort_key):
        cls = _stage_registry[stage_id]
        stages.append({
            "stage_id": stage_id,
            "stage_name": cls.stage_name,
            "class_name": cls.__name__,
        })
    return stages


def clear_registry() -> None:
    """Clear all registered stages. Primarily for testing."""
    _stage_registry.clear()
    logger.debug("Stage registry cleared")


def register_stage_conditionally(
    cls: Type[Stage], 
    condition_func: callable = None
) -> Type[Stage]:
    """Conditionally register a stage based on a condition function.
    
    Args:
        cls: The stage class to register
        condition_func: Function that returns True if stage should be registered
        
    Returns:
        The original class (unmodified)
    """
    if condition_func is None or condition_func():
        return register_stage(cls)
    else:
        logger.debug(f"Skipping registration of stage {cls.stage_id}: {cls.stage_name} (condition not met)")
        return cls


def setup_stage_1_registration() -> None:
    """Set up Stage 1 registration based on feature flag.
    
    This function should be called after all stage modules are imported
    to conditionally register the appropriate Stage 1 implementation.
    """
    from .config import get_config
    
    config = get_config()
    
    # Clear any existing Stage 1 registration
    if 1 in _stage_registry:
        existing = _stage_registry[1]
        logger.info(f"Clearing existing Stage 1 registration: {existing.__name__}")
        del _stage_registry[1]
    
    if config.enable_new_stage_1:
        # Register new Protocol Design Stage (workflow engine adapter)
        try:
            # Import the stage classes directly since they're not auto-registered
            import sys
            if 'src.workflow_engine.stages.stage_01_protocol_design' in sys.modules:
                from .stages.stage_01_protocol_design import ProtocolDesignStage
            else:
                # Import path for when called from workflow engine context
                from .stages.stage_01_protocol_design import ProtocolDesignStage
                
            _stage_registry[1] = ProtocolDesignStage
            logger.info(f"✅ Registered new ProtocolDesignStage for Stage 1 (PICO Framework): {ProtocolDesignStage.__name__}")
            
        except ImportError as e:
            logger.error(f"Failed to import ProtocolDesignStage: {e}")
            logger.info("Falling back to legacy UploadIntakeStage")
            config.enable_new_stage_1 = False
    
    if not config.enable_new_stage_1:
        # Register legacy Upload Intake Stage
        try:
            import sys
            if 'src.workflow_engine.stages.stage_01_upload' in sys.modules:
                from .stages.stage_01_upload import UploadIntakeStage
            else:
                from .stages.stage_01_upload import UploadIntakeStage
                
            _stage_registry[1] = UploadIntakeStage
            logger.info(f"Registered legacy UploadIntakeStage for Stage 1: {UploadIntakeStage.__name__}")
            
        except ImportError as e:
            logger.error(f"Failed to import UploadIntakeStage: {e}")
            logger.warning("No valid Stage 1 implementation available - this may cause workflow failures")
            # Don't raise error to allow system to start
