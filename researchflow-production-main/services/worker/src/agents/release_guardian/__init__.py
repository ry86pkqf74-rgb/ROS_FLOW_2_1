"""
Release Guardian Agent Module

Implements pre-deployment gate enforcement for ResearchFlow releases.
Ensures all checks pass before allowing deployment to production.

Linear Issue: ROS-150
"""

from .agent import ReleaseGuardianAgent
from .gates import (
    Gate,
    CIStatusGate,
    EvidencePackGate,
    FAVESGate,
    RollbackGate,
    MonitoringGate,
)
from .validators import (
    GitHubCIValidator,
    EvidenceHashValidator,
    NotionSignoffValidator,
    DeploymentModeValidator,
)
from .actions import (
    BlockDeployment,
    ApproveDeployment,
    RequestSignoff,
    GenerateReleaseReport,
)

__all__ = [
    "ReleaseGuardianAgent",
    "Gate",
    "CIStatusGate",
    "EvidencePackGate",
    "FAVESGate",
    "RollbackGate",
    "MonitoringGate",
    "GitHubCIValidator",
    "EvidenceHashValidator",
    "NotionSignoffValidator",
    "DeploymentModeValidator",
    "BlockDeployment",
    "ApproveDeployment",
    "RequestSignoff",
    "GenerateReleaseReport",
]
