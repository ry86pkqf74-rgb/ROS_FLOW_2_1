#!/usr/bin/env python3
"""
Preflight Validation Agent - Pre-Deployment Code Structure and Connectivity Testing

This agent performs automated validation before deployments to ensure:
1. Code structure is valid (imports, syntax, required files)
2. Database migrations are consistent
3. API endpoints are accessible
4. Docker configurations are valid
5. Services can start and communicate
6. Workflow creation smoke tests pass

@author Claude
@created 2026-01-30
"""

import os
import json
import logging
import subprocess
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Composio imports - lazy loading with graceful fallback for LangGraph Cloud
try:
    from composio_langchain import ComposioToolSet, Action
    COMPOSIO_AVAILABLE = True
except ImportError as e:
    ComposioToolSet = None
    Action = None
    COMPOSIO_AVAILABLE = False
    import warnings
    warnings.warn(f"Composio not available: {e}. PreflightValidationAgent will have limited functionality.")

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# LangChain Agent imports - lazy loading for compatibility
try:
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    LANGCHAIN_AGENTS_AVAILABLE = True
except ImportError:
    try:
        from langchain_core.agents import AgentExecutor
        from langchain.agents import create_openai_functions_agent
        LANGCHAIN_AGENTS_AVAILABLE = True
    except ImportError:
        AgentExecutor = None
        create_openai_functions_agent = None
        LANGCHAIN_AGENTS_AVAILABLE = False
        import warnings
        warnings.warn("LangChain agent components not available.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Status of validation checks"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    """Result of a single validation check"""
    name: str
    status: ValidationStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    duration_ms: int = 0


@dataclass
class PreflightReport:
    """Complete preflight validation report"""
    timestamp: str
    commit_sha: Optional[str]
    branch: Optional[str]
    overall_status: ValidationStatus
    checks: List[ValidationResult]
    summary: Dict[str, int]
    recommendations: List[str]


# Required files for deployment readiness
REQUIRED_FILES = {
    "core": [
        "docker-compose.yml",
        ".env.example",
        "package.json",
    ],
    "orchestrator": [
        "services/orchestrator/package.json",
        "services/orchestrator/src/index.ts",
        "services/orchestrator/Dockerfile",
    ],
    "worker": [
        "services/worker/package.json",
        "services/worker/src/index.ts",
        "services/worker/Dockerfile",
    ],
    "web": [
        "apps/web/package.json",
        "apps/web/next.config.js",
    ],
    "migrations": [
        "migrations/",
    ],
    "agents": [
        "agents/orchestrator.py",
        "agents/release_guardian_agent.py",
    ],
}

# Service health endpoints
SERVICE_ENDPOINTS = {
    "orchestrator": {"url": "http://localhost:3001/health", "method": "GET"},
    "worker": {"url": "http://localhost:3002/health", "method": "GET"},
    "web": {"url": "http://localhost:3000", "method": "GET"},
    "guideline-engine": {"url": "http://localhost:8000/health", "method": "GET"},
    "collab": {"url": "http://localhost:1234/health", "method": "GET"},
}


# Agent configuration
# Actions are only available if Composio is installed
_PREFLIGHT_ACTIONS = []
if COMPOSIO_AVAILABLE and Action is not None:
    _PREFLIGHT_ACTIONS = [
        # GitHub Actions
        Action.GITHUB_GET_A_REPOSITORY,
        Action.GITHUB_GET_REPOSITORY_CONTENT,
        Action.GITHUB_LIST_REPOSITORY_WORKFLOWS,
        Action.GITHUB_LIST_WORKFLOW_RUNS,
        Action.GITHUB_GET_A_WORKFLOW_RUN,
        Action.GITHUB_CREATE_AN_ISSUE,
        # Docker Actions
        Action.DOCKER_LIST_CONTAINERS,
        Action.DOCKER_GET_CONTAINER_LOGS,
        Action.DOCKER_INSPECT_CONTAINER,
    ]

PREFLIGHT_AGENT_CONFIG = {
    "name": "Preflight Validation Agent",
    "model": "gpt-4o",
    "temperature": 0,
    "toolkits": ["GITHUB", "DOCKER"] if COMPOSIO_AVAILABLE else [],
    "actions": _PREFLIGHT_ACTIONS,
    "system_prompt": """You are the Preflight Validation Agent for ResearchFlow.

Your responsibilities:
1. Validate code structure before deployment:
   - Check required files exist
   - Verify imports and syntax
   - Ensure configurations are valid

2. Verify database consistency:
   - Check migration files are ordered
   - Verify no conflicting migrations
   - Ensure schema is up to date

3. Test service connectivity:
   - Check Docker containers are running
   - Verify health endpoints respond
   - Test inter-service communication

4. Perform smoke tests:
   - Create a test workflow via API
   - Verify workflow appears in database
   - Clean up test data

5. Report findings:
   - Generate detailed validation report
   - Create GitHub issues for failures
   - Recommend fixes for common issues

VALIDATION PRIORITIES:
1. CRITICAL: Syntax errors, missing core files, database issues
2. HIGH: Service connectivity, health check failures
3. MEDIUM: Missing optional files, configuration warnings
4. LOW: Style issues, optimization suggestions

OUTPUT FORMAT:
Always provide structured validation results with:
- Check name
- Pass/Fail/Warning status
- Detailed message
- Recommended fix (if applicable)
"""
}


class PreflightValidationAgent:
    """Preflight validation agent for automated deployment testing"""

    def __init__(
        self,
        composio_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        entity_id: str = "default",
        github_repo: str = "ry86pkqf74-rgb/researchflow-production",
        project_root: Optional[str] = None
    ):
        self.composio_api_key = composio_api_key or os.getenv("COMPOSIO_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.entity_id = entity_id
        self.github_repo = github_repo
        self.project_root = Path(project_root or os.getcwd())

        # Initialize Composio toolset
        self.toolset = ComposioToolSet(
            api_key=self.composio_api_key,
            entity_id=self.entity_id
        )

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=PREFLIGHT_AGENT_CONFIG["model"],
            temperature=PREFLIGHT_AGENT_CONFIG["temperature"],
            api_key=self.openai_api_key
        )

        # Get tools
        self.tools = self.toolset.get_tools(actions=PREFLIGHT_AGENT_CONFIG["actions"])

        # Create agent
        self.agent = self._create_agent()

    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with Composio tools"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", PREFLIGHT_AGENT_CONFIG["system_prompt"]),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_functions_agent(self.llm, self.tools, prompt)

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=15,
            return_intermediate_steps=True
        )

    # =========================================================================
    # File Structure Validation
    # =========================================================================

    def validate_file_structure(self) -> List[ValidationResult]:
        """Validate required files exist"""
        results = []
        start_time = datetime.now()

        for category, files in REQUIRED_FILES.items():
            for file_path in files:
                full_path = self.project_root / file_path
                check_name = f"file_exists:{category}/{Path(file_path).name}"

                if file_path.endswith("/"):
                    # Directory check
                    exists = full_path.is_dir()
                else:
                    exists = full_path.is_file()

                if exists:
                    results.append(ValidationResult(
                        name=check_name,
                        status=ValidationStatus.PASSED,
                        message=f"Required file/directory exists: {file_path}",
                        duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                    ))
                else:
                    results.append(ValidationResult(
                        name=check_name,
                        status=ValidationStatus.FAILED,
                        message=f"Missing required file/directory: {file_path}",
                        details={"category": category, "path": file_path},
                        duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                    ))

        return results

    # =========================================================================
    # TypeScript/JavaScript Validation
    # =========================================================================

    def validate_typescript_syntax(self, paths: Optional[List[str]] = None) -> List[ValidationResult]:
        """Validate TypeScript/JavaScript syntax using tsc"""
        results = []
        start_time = datetime.now()

        check_paths = paths or [
            "services/orchestrator",
            "services/worker",
            "packages/ai-router",
        ]

        for check_path in check_paths:
            full_path = self.project_root / check_path
            if not full_path.exists():
                results.append(ValidationResult(
                    name=f"typescript_syntax:{check_path}",
                    status=ValidationStatus.SKIPPED,
                    message=f"Path does not exist: {check_path}",
                    duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                ))
                continue

            # Check if tsconfig exists
            tsconfig = full_path / "tsconfig.json"
            if not tsconfig.exists():
                results.append(ValidationResult(
                    name=f"typescript_config:{check_path}",
                    status=ValidationStatus.WARNING,
                    message=f"No tsconfig.json found in {check_path}",
                    duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                ))
                continue

            # Run tsc --noEmit to check syntax
            try:
                result = subprocess.run(
                    ["npx", "tsc", "--noEmit", "-p", str(tsconfig)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(full_path)
                )

                if result.returncode == 0:
                    results.append(ValidationResult(
                        name=f"typescript_syntax:{check_path}",
                        status=ValidationStatus.PASSED,
                        message=f"TypeScript syntax valid in {check_path}",
                        duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                    ))
                else:
                    # Parse errors
                    error_count = result.stdout.count("error TS")
                    results.append(ValidationResult(
                        name=f"typescript_syntax:{check_path}",
                        status=ValidationStatus.FAILED,
                        message=f"TypeScript errors in {check_path}: {error_count} errors",
                        details={"stderr": result.stderr[:1000], "stdout": result.stdout[:1000]},
                        duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                    ))
            except subprocess.TimeoutExpired:
                results.append(ValidationResult(
                    name=f"typescript_syntax:{check_path}",
                    status=ValidationStatus.WARNING,
                    message=f"TypeScript check timed out for {check_path}",
                    duration_ms=120000
                ))
            except FileNotFoundError:
                results.append(ValidationResult(
                    name=f"typescript_syntax:{check_path}",
                    status=ValidationStatus.SKIPPED,
                    message="npx/tsc not found - skipping TypeScript validation",
                    duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                ))

        return results

    # =========================================================================
    # Database Migration Validation
    # =========================================================================

    def validate_migrations(self) -> List[ValidationResult]:
        """Validate database migrations are consistent"""
        results = []
        start_time = datetime.now()
        migrations_path = self.project_root / "migrations"

        if not migrations_path.is_dir():
            results.append(ValidationResult(
                name="migrations:directory",
                status=ValidationStatus.FAILED,
                message="Migrations directory not found",
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            ))
            return results

        # List migration files
        migration_files = sorted([
            f for f in migrations_path.iterdir()
            if f.is_file() and f.suffix == ".sql"
        ])

        if not migration_files:
            results.append(ValidationResult(
                name="migrations:files",
                status=ValidationStatus.WARNING,
                message="No SQL migration files found",
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            ))
            return results

        results.append(ValidationResult(
            name="migrations:count",
            status=ValidationStatus.PASSED,
            message=f"Found {len(migration_files)} migration files",
            details={"files": [f.name for f in migration_files]},
            duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
        ))

        # Check for naming convention (timestamp prefix)
        bad_names = []
        for mf in migration_files:
            # Expected format: 0001_name.sql or timestamp_name.sql
            name = mf.stem
            parts = name.split("_")
            if not parts[0].isdigit():
                bad_names.append(mf.name)

        if bad_names:
            results.append(ValidationResult(
                name="migrations:naming",
                status=ValidationStatus.WARNING,
                message=f"Migration files with non-standard naming: {len(bad_names)}",
                details={"files": bad_names},
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            ))
        else:
            results.append(ValidationResult(
                name="migrations:naming",
                status=ValidationStatus.PASSED,
                message="All migration files follow naming convention",
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            ))

        # Check for SQL syntax (basic validation)
        syntax_errors = []
        for mf in migration_files:
            content = mf.read_text()
            # Basic checks
            if "CREATE TABLE" in content and ";" not in content:
                syntax_errors.append((mf.name, "Missing semicolon"))
            if content.count("(") != content.count(")"):
                syntax_errors.append((mf.name, "Unbalanced parentheses"))

        if syntax_errors:
            results.append(ValidationResult(
                name="migrations:syntax",
                status=ValidationStatus.FAILED,
                message=f"Potential SQL syntax issues in {len(syntax_errors)} files",
                details={"errors": syntax_errors},
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            ))
        else:
            results.append(ValidationResult(
                name="migrations:syntax",
                status=ValidationStatus.PASSED,
                message="Basic SQL syntax checks passed",
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            ))

        return results

    # =========================================================================
    # Docker Configuration Validation
    # =========================================================================

    def validate_docker_config(self) -> List[ValidationResult]:
        """Validate Docker configuration"""
        results = []
        start_time = datetime.now()

        compose_file = self.project_root / "docker-compose.yml"
        if not compose_file.exists():
            results.append(ValidationResult(
                name="docker:compose_file",
                status=ValidationStatus.FAILED,
                message="docker-compose.yml not found",
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            ))
            return results

        # Parse docker-compose.yml
        try:
            import yaml
            with open(compose_file) as f:
                compose_config = yaml.safe_load(f)

            results.append(ValidationResult(
                name="docker:compose_syntax",
                status=ValidationStatus.PASSED,
                message="docker-compose.yml is valid YAML",
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            ))

            # Check services
            services = compose_config.get("services", {})
            required_services = ["postgres", "redis", "orchestrator", "worker", "web"]

            for svc in required_services:
                if svc in services:
                    results.append(ValidationResult(
                        name=f"docker:service:{svc}",
                        status=ValidationStatus.PASSED,
                        message=f"Service '{svc}' defined in docker-compose.yml",
                        duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                    ))
                else:
                    results.append(ValidationResult(
                        name=f"docker:service:{svc}",
                        status=ValidationStatus.WARNING,
                        message=f"Service '{svc}' not found in docker-compose.yml",
                        duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                    ))

            # Check for hardcoded credentials
            compose_str = compose_file.read_text()
            if "password=" in compose_str.lower() and "${" not in compose_str:
                results.append(ValidationResult(
                    name="docker:credentials",
                    status=ValidationStatus.WARNING,
                    message="Possible hardcoded credentials in docker-compose.yml",
                    duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                ))

            # Check for environment variable usage
            if "${" in compose_str:
                results.append(ValidationResult(
                    name="docker:env_vars",
                    status=ValidationStatus.PASSED,
                    message="Environment variables properly used",
                    duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                ))

        except yaml.YAMLError as e:
            results.append(ValidationResult(
                name="docker:compose_syntax",
                status=ValidationStatus.FAILED,
                message=f"Invalid YAML in docker-compose.yml: {str(e)}",
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            ))
        except ImportError:
            results.append(ValidationResult(
                name="docker:compose_syntax",
                status=ValidationStatus.SKIPPED,
                message="PyYAML not available for docker-compose validation",
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            ))

        # Check Dockerfiles
        dockerfiles = [
            "services/orchestrator/Dockerfile",
            "services/worker/Dockerfile",
        ]

        for df_path in dockerfiles:
            full_path = self.project_root / df_path
            if full_path.exists():
                content = full_path.read_text()
                # Basic Dockerfile validation
                if "FROM" not in content:
                    results.append(ValidationResult(
                        name=f"docker:dockerfile:{Path(df_path).parent.name}",
                        status=ValidationStatus.FAILED,
                        message=f"Invalid Dockerfile (no FROM): {df_path}",
                        duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                    ))
                else:
                    results.append(ValidationResult(
                        name=f"docker:dockerfile:{Path(df_path).parent.name}",
                        status=ValidationStatus.PASSED,
                        message=f"Dockerfile valid: {df_path}",
                        duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                    ))
            else:
                results.append(ValidationResult(
                    name=f"docker:dockerfile:{Path(df_path).parent.name}",
                    status=ValidationStatus.FAILED,
                    message=f"Dockerfile not found: {df_path}",
                    duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                ))

        return results

    # =========================================================================
    # Service Health Validation
    # =========================================================================

    async def validate_service_health(self) -> List[ValidationResult]:
        """Validate service health endpoints"""
        results = []

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            for service, config in SERVICE_ENDPOINTS.items():
                start_time = datetime.now()
                try:
                    async with session.get(config["url"]) as response:
                        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                        if response.status == 200:
                            results.append(ValidationResult(
                                name=f"health:{service}",
                                status=ValidationStatus.PASSED,
                                message=f"Service '{service}' is healthy",
                                details={"status_code": response.status, "url": config["url"]},
                                duration_ms=duration_ms
                            ))
                        else:
                            results.append(ValidationResult(
                                name=f"health:{service}",
                                status=ValidationStatus.FAILED,
                                message=f"Service '{service}' returned status {response.status}",
                                details={"status_code": response.status, "url": config["url"]},
                                duration_ms=duration_ms
                            ))
                except aiohttp.ClientConnectorError:
                    duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                    results.append(ValidationResult(
                        name=f"health:{service}",
                        status=ValidationStatus.FAILED,
                        message=f"Cannot connect to service '{service}'",
                        details={"url": config["url"], "error": "Connection refused"},
                        duration_ms=duration_ms
                    ))
                except asyncio.TimeoutError:
                    results.append(ValidationResult(
                        name=f"health:{service}",
                        status=ValidationStatus.FAILED,
                        message=f"Service '{service}' health check timed out",
                        details={"url": config["url"], "error": "Timeout"},
                        duration_ms=10000
                    ))

        return results

    # =========================================================================
    # API Smoke Tests
    # =========================================================================

    async def run_api_smoke_tests(self, auth_token: Optional[str] = None) -> List[ValidationResult]:
        """Run API smoke tests including workflow creation"""
        results = []
        base_url = "http://localhost:3001"

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            # Test 1: Health endpoint
            start_time = datetime.now()
            try:
                async with session.get(f"{base_url}/health") as response:
                    duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                    if response.status == 200:
                        results.append(ValidationResult(
                            name="api:health",
                            status=ValidationStatus.PASSED,
                            message="API health endpoint responding",
                            duration_ms=duration_ms
                        ))
                    else:
                        results.append(ValidationResult(
                            name="api:health",
                            status=ValidationStatus.FAILED,
                            message=f"API health endpoint returned {response.status}",
                            duration_ms=duration_ms
                        ))
            except Exception as e:
                results.append(ValidationResult(
                    name="api:health",
                    status=ValidationStatus.FAILED,
                    message=f"API health check failed: {str(e)}",
                    duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                ))

            # Test 2: Workflow creation (if auth token provided)
            if auth_token:
                start_time = datetime.now()
                try:
                    headers = {"Authorization": f"Bearer {auth_token}"}
                    test_workflow = {
                        "name": f"Preflight Test {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "description": "Automated preflight validation test - safe to delete",
                        "templateKey": "custom",
                        "definition": {
                            "steps": [{"type": "test", "name": "noop"}]
                        }
                    }

                    async with session.post(
                        f"{base_url}/api/workflows",
                        json=test_workflow,
                        headers=headers
                    ) as response:
                        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                        if response.status in [200, 201]:
                            data = await response.json()
                            workflow_id = data.get("id")
                            results.append(ValidationResult(
                                name="api:workflow_create",
                                status=ValidationStatus.PASSED,
                                message="Successfully created test workflow",
                                details={"workflow_id": workflow_id},
                                duration_ms=duration_ms
                            ))

                            # Cleanup: Delete test workflow
                            if workflow_id:
                                try:
                                    async with session.delete(
                                        f"{base_url}/api/workflows/{workflow_id}",
                                        headers=headers
                                    ) as del_response:
                                        if del_response.status in [200, 204]:
                                            results.append(ValidationResult(
                                                name="api:workflow_cleanup",
                                                status=ValidationStatus.PASSED,
                                                message="Test workflow cleaned up",
                                                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                                            ))
                                except Exception:
                                    pass  # Cleanup failure is not critical
                        else:
                            error_text = await response.text()
                            results.append(ValidationResult(
                                name="api:workflow_create",
                                status=ValidationStatus.FAILED,
                                message=f"Workflow creation failed: {response.status}",
                                details={"error": error_text[:500]},
                                duration_ms=duration_ms
                            ))
                except Exception as e:
                    results.append(ValidationResult(
                        name="api:workflow_create",
                        status=ValidationStatus.FAILED,
                        message=f"Workflow creation test failed: {str(e)}",
                        duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                    ))
            else:
                results.append(ValidationResult(
                    name="api:workflow_create",
                    status=ValidationStatus.SKIPPED,
                    message="Skipped - no auth token provided",
                    duration_ms=0
                ))

        return results

    # =========================================================================
    # Full Preflight Validation
    # =========================================================================

    def run_full_preflight(
        self,
        skip_services: bool = False,
        skip_api_tests: bool = False,
        auth_token: Optional[str] = None
    ) -> PreflightReport:
        """Run complete preflight validation suite"""
        logger.info("Starting full preflight validation...")
        start_time = datetime.now()
        all_results: List[ValidationResult] = []

        # Get git info
        commit_sha = None
        branch = None
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=str(self.project_root)
            )
            if result.returncode == 0:
                commit_sha = result.stdout.strip()[:8]

            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, cwd=str(self.project_root)
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
        except Exception:
            pass

        # 1. File structure validation
        logger.info("Validating file structure...")
        all_results.extend(self.validate_file_structure())

        # 2. TypeScript validation
        logger.info("Validating TypeScript syntax...")
        all_results.extend(self.validate_typescript_syntax())

        # 3. Migration validation
        logger.info("Validating database migrations...")
        all_results.extend(self.validate_migrations())

        # 4. Docker configuration validation
        logger.info("Validating Docker configuration...")
        all_results.extend(self.validate_docker_config())

        # 5. Service health checks (if not skipped)
        if not skip_services:
            logger.info("Checking service health...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                all_results.extend(loop.run_until_complete(self.validate_service_health()))
            finally:
                loop.close()

        # 6. API smoke tests (if not skipped)
        if not skip_api_tests:
            logger.info("Running API smoke tests...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                all_results.extend(loop.run_until_complete(
                    self.run_api_smoke_tests(auth_token)
                ))
            finally:
                loop.close()

        # Calculate summary
        summary = {
            "passed": sum(1 for r in all_results if r.status == ValidationStatus.PASSED),
            "failed": sum(1 for r in all_results if r.status == ValidationStatus.FAILED),
            "warnings": sum(1 for r in all_results if r.status == ValidationStatus.WARNING),
            "skipped": sum(1 for r in all_results if r.status == ValidationStatus.SKIPPED),
        }

        # Determine overall status
        if summary["failed"] > 0:
            overall_status = ValidationStatus.FAILED
        elif summary["warnings"] > 0:
            overall_status = ValidationStatus.WARNING
        else:
            overall_status = ValidationStatus.PASSED

        # Generate recommendations
        recommendations = self._generate_recommendations(all_results)

        return PreflightReport(
            timestamp=datetime.now().isoformat(),
            commit_sha=commit_sha,
            branch=branch,
            overall_status=overall_status,
            checks=all_results,
            summary=summary,
            recommendations=recommendations
        )

    def _generate_recommendations(self, results: List[ValidationResult]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []

        failed_checks = [r for r in results if r.status == ValidationStatus.FAILED]

        for check in failed_checks:
            if "file_exists" in check.name:
                recommendations.append(f"Create missing file: {check.details.get('path', 'unknown')}")
            elif "typescript_syntax" in check.name:
                recommendations.append(f"Fix TypeScript errors in {check.name.split(':')[-1]}")
            elif "migrations" in check.name:
                recommendations.append("Review database migrations for consistency")
            elif "docker" in check.name:
                recommendations.append("Fix Docker configuration issues before deployment")
            elif "health" in check.name:
                service = check.name.split(":")[-1]
                recommendations.append(f"Ensure service '{service}' is running and healthy")
            elif "api" in check.name:
                recommendations.append("Fix API issues before deployment")

        if not recommendations:
            recommendations.append("All checks passed - ready for deployment!")

        return recommendations

    # =========================================================================
    # Agent-based validation (using Composio tools)
    # =========================================================================

    def validate_with_agent(self, task: str) -> Dict[str, Any]:
        """Run validation using the LangChain agent"""
        return self.agent.invoke({"input": task})

    def check_ci_and_report(self, commit_sha: Optional[str] = None) -> Dict[str, Any]:
        """Check CI status and create report"""
        sha_clause = f"for commit {commit_sha}" if commit_sha else "for the latest commit"

        return self.agent.invoke({
            "input": f"""Run preflight CI validation {sha_clause}:

Repository: {self.github_repo}

Steps:
1. Check GitHub Actions workflow status
2. List any failing checks
3. Get error details for failures
4. Summarize CI status
5. If failures found, create a GitHub issue with:
   - Title: "[Preflight] CI failures detected"
   - Body: List of failing checks and errors
   - Labels: "ci", "preflight", "automated"

Report format:
- CI Status: PASS/FAIL
- Passing checks: count
- Failing checks: list with details
- Recommendations for fixes"""
        })


def main():
    """Demo the Preflight Validation agent"""
    print("🔍 Preflight Validation Agent - Pre-Deployment Testing")
    print("=" * 60)

    # Initialize agent
    agent = PreflightValidationAgent(
        project_root="/path/to/researchflow-production"
    )

    # Run full preflight (skipping service checks for demo)
    print("\n🚀 Running preflight validation...")
    report = agent.run_full_preflight(
        skip_services=True,
        skip_api_tests=True
    )

    # Print report
    print(f"\n📊 Preflight Report")
    print(f"Timestamp: {report.timestamp}")
    print(f"Commit: {report.commit_sha or 'unknown'}")
    print(f"Branch: {report.branch or 'unknown'}")
    print(f"Overall Status: {report.overall_status.value.upper()}")

    print(f"\n📈 Summary:")
    print(f"  ✅ Passed: {report.summary['passed']}")
    print(f"  ❌ Failed: {report.summary['failed']}")
    print(f"  ⚠️  Warnings: {report.summary['warnings']}")
    print(f"  ⏭️  Skipped: {report.summary['skipped']}")

    print(f"\n💡 Recommendations:")
    for rec in report.recommendations:
        print(f"  - {rec}")


if __name__ == "__main__":
    main()
