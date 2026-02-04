#!/usr/bin/env python3
"""
Docker Operations Agent - Container Management for Model Deployment

This agent manages Docker containers for ML model deployment:
1. Builds Docker images from model artifacts
2. Manages container lifecycle (create, start, stop, remove)
3. Handles container health checks and monitoring
4. Integrates with CI/CD for automated deployments
5. Manages Docker registries for image distribution
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from composio_langchain import ComposioToolSet, Action
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Docker Operations Agent Configuration
DOCKER_OPS_CONFIG = {
    "name": "Docker Operations Agent",
    "model": "gpt-4o",
    "temperature": 0,
    "toolkits": ["DOCKER", "GITHUB"],
    "actions": [
        # Docker Actions
        Action.DOCKER_LIST_CONTAINERS,
        Action.DOCKER_CREATE_CONTAINER,
        Action.DOCKER_START_CONTAINER,
        Action.DOCKER_STOP_CONTAINER,
        Action.DOCKER_REMOVE_CONTAINER,
        Action.DOCKER_GET_CONTAINER_LOGS,
        Action.DOCKER_LIST_IMAGES,
        Action.DOCKER_BUILD_IMAGE,
        Action.DOCKER_PULL_IMAGE,
        Action.DOCKER_PUSH_IMAGE,
        Action.DOCKER_REMOVE_IMAGE,
        Action.DOCKER_INSPECT_CONTAINER,
        # GitHub Actions for CI/CD integration
        Action.GITHUB_GET_A_REPOSITORY,
        Action.GITHUB_GET_REPOSITORY_CONTENT,
        Action.GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS,
        Action.GITHUB_CREATE_AN_ISSUE,
    ],
    "system_prompt": """You are the Docker Operations Agent for ResearchFlow.

Your responsibilities:
1. Build Docker images for ML model deployment:
   - Use standardized Dockerfile templates
   - Include model artifacts and dependencies
   - Tag images with version and environment info

2. Manage container lifecycle:
   - Create containers with proper configuration
   - Start/stop containers for deployments
   - Monitor container health and logs
   - Clean up unused containers and images

3. Registry management:
   - Push images to container registry
   - Pull images for deployment
   - Manage image tags and versions

4. CI/CD integration:
   - Trigger builds from GitHub Actions
   - Update deployment manifests
   - Report build status

Image Naming Convention:
- Development: researchflow/{model_name}:dev-{commit_sha}
- Staging: researchflow/{model_name}:staging-{version}
- Production: researchflow/{model_name}:{version}

Container Naming Convention:
- rf-{model_name}-{environment}-{instance}

Required Labels:
- app: researchflow
- model: {model_name}
- version: {version}
- environment: dev|staging|prod
- deployed-at: {timestamp}

Health Check Configuration:
- Endpoint: /health
- Interval: 30s
- Timeout: 10s
- Retries: 3
- Start period: 60s

Environment Variables (standard):
- MODEL_VERSION: Version string
- ENVIRONMENT: dev|staging|prod
- LOG_LEVEL: INFO|DEBUG|WARNING|ERROR
- METRICS_PORT: 9090
- API_PORT: 8080

IMPORTANT:
- Always verify Dockerfile exists before building
- Always tag images before pushing
- Always check container health after starting
- Clean up failed containers and dangling images
- Report all operations to GitHub/Notion for tracking
"""
}


# Dockerfile Templates
DOCKERFILE_TEMPLATES = {
    "python_model": '''# ResearchFlow ML Model Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy model artifacts
COPY model/ ./model/
COPY src/ ./src/

# Copy configuration
COPY config/ ./config/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MODEL_VERSION={version}
ENV ENVIRONMENT={environment}
ENV API_PORT=8080
ENV METRICS_PORT=9090

# Expose ports
EXPOSE 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Run the model server
CMD ["python", "-m", "src.serve"]
''',

    "fastapi_model": '''# ResearchFlow FastAPI Model Server
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

ENV PYTHONUNBUFFERED=1
ENV MODEL_VERSION={version}
ENV ENVIRONMENT={environment}

EXPOSE 8080 9090

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
''',

    "pytorch_model": '''# ResearchFlow PyTorch Model Server
FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY model/ ./model/
COPY src/ ./src/

ENV PYTHONUNBUFFERED=1
ENV MODEL_VERSION={version}
ENV ENVIRONMENT={environment}

EXPOSE 8080 9090

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "src.serve"]
'''
}


class DockerOpsAgent:
    """Docker Operations Agent for container management"""

    def __init__(
        self,
        composio_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        entity_id: str = "default",
        github_repo: str = "ry86pkqf74-rgb/researchflow-production",
        registry_url: str = "ghcr.io/researchflow"
    ):
        self.composio_api_key = composio_api_key or os.getenv("COMPOSIO_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.entity_id = entity_id
        self.github_repo = github_repo
        self.registry_url = registry_url

        # Initialize Composio toolset
        self.toolset = ComposioToolSet(
            api_key=self.composio_api_key,
            entity_id=self.entity_id
        )

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=DOCKER_OPS_CONFIG["model"],
            temperature=DOCKER_OPS_CONFIG["temperature"],
            api_key=self.openai_api_key
        )

        # Get tools
        self.tools = self.toolset.get_tools(actions=DOCKER_OPS_CONFIG["actions"])

        # Create agent
        self.agent = self._create_agent()

    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with Composio tools"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", DOCKER_OPS_CONFIG["system_prompt"]),
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

    def build_model_image(
        self,
        model_name: str,
        model_version: str,
        dockerfile_path: str,
        environment: str = "dev"
    ) -> Dict[str, Any]:
        """Build a Docker image for a model"""
        logger.info(f"Building Docker image for model: {model_name}:{model_version}")

        image_tag = f"{self.registry_url}/{model_name}:{environment}-{model_version}"

        result = self.agent.invoke({
            "input": f"""Build Docker image for ML model deployment:

Model: {model_name}
Version: {model_version}
Environment: {environment}
Dockerfile: {dockerfile_path}

Steps:
1. Verify Dockerfile exists at {dockerfile_path}
2. Build image with tag: {image_tag}
3. Add labels:
   - app=researchflow
   - model={model_name}
   - version={model_version}
   - environment={environment}
   - built-at={datetime.now().isoformat()}
4. List the built image to verify
5. Report image size and layer count

Repository: {self.github_repo}"""
        })

        return result

    def deploy_model_container(
        self,
        model_name: str,
        model_version: str,
        environment: str = "dev",
        port: int = 8080,
        replicas: int = 1
    ) -> Dict[str, Any]:
        """Deploy a model as a Docker container"""
        logger.info(f"Deploying container for: {model_name}:{model_version}")

        image_tag = f"{self.registry_url}/{model_name}:{environment}-{model_version}"
        container_name = f"rf-{model_name}-{environment}"

        result = self.agent.invoke({
            "input": f"""Deploy ML model as Docker container:

Model: {model_name}
Version: {model_version}
Environment: {environment}
Image: {image_tag}
Container Name: {container_name}
Port: {port}

Steps:
1. Check if container {container_name} already exists
   - If running: stop and remove it
   - If stopped: remove it
2. Pull latest image if needed
3. Create new container with:
   - Name: {container_name}
   - Image: {image_tag}
   - Port mapping: {port}:8080
   - Environment variables:
     - MODEL_VERSION={model_version}
     - ENVIRONMENT={environment}
   - Labels as per naming convention
   - Restart policy: unless-stopped
4. Start the container
5. Wait for health check to pass (up to 90 seconds)
6. Verify container is running
7. Get initial logs

Report deployment status and container ID."""
        })

        return result

    def check_container_health(self, container_name: str) -> Dict[str, Any]:
        """Check health of a running container"""
        logger.info(f"Checking health of container: {container_name}")

        result = self.agent.invoke({
            "input": f"""Check health status of container:

Container: {container_name}

Steps:
1. Inspect container to get status
2. Check health check results
3. Get recent logs (last 50 lines)
4. Report:
   - Container status (running/stopped/unhealthy)
   - Health check status
   - Uptime
   - Resource usage if available
   - Any error messages in logs"""
        })

        return result

    def get_container_logs(
        self,
        container_name: str,
        tail: int = 100
    ) -> Dict[str, Any]:
        """Get logs from a container"""
        logger.info(f"Getting logs for container: {container_name}")

        result = self.agent.invoke({
            "input": f"""Get logs from Docker container:

Container: {container_name}
Lines: Last {tail} lines

Steps:
1. Get container logs
2. Filter for any ERROR or WARNING messages
3. Report log summary and any issues found"""
        })

        return result

    def stop_and_cleanup(self, container_name: str) -> Dict[str, Any]:
        """Stop container and clean up resources"""
        logger.info(f"Stopping and cleaning up: {container_name}")

        result = self.agent.invoke({
            "input": f"""Stop and clean up container:

Container: {container_name}

Steps:
1. Stop the container gracefully (10s timeout)
2. Remove the container
3. List any dangling images and remove them
4. Report cleanup summary"""
        })

        return result

    def push_image_to_registry(
        self,
        model_name: str,
        model_version: str,
        environment: str = "dev"
    ) -> Dict[str, Any]:
        """Push image to container registry"""
        logger.info(f"Pushing image to registry: {model_name}:{model_version}")

        image_tag = f"{self.registry_url}/{model_name}:{environment}-{model_version}"

        result = self.agent.invoke({
            "input": f"""Push Docker image to registry:

Image: {image_tag}
Registry: {self.registry_url}

Steps:
1. Verify image exists locally
2. Push image to registry
3. Verify push was successful
4. Report image digest and URL"""
        })

        return result

    def list_deployments(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """List all ResearchFlow container deployments"""
        logger.info(f"Listing deployments for environment: {environment or 'all'}")

        env_filter = f"with label environment={environment}" if environment else ""

        result = self.agent.invoke({
            "input": f"""List all ResearchFlow container deployments {env_filter}:

Steps:
1. List all containers with label app=researchflow
2. For each container, show:
   - Name
   - Model and version
   - Environment
   - Status
   - Uptime
   - Port mappings
3. Summarize deployment count by environment"""
        })

        return result

    def rollback_deployment(
        self,
        model_name: str,
        target_version: str,
        environment: str
    ) -> Dict[str, Any]:
        """Rollback to a previous model version"""
        logger.info(f"Rolling back {model_name} to version {target_version}")

        result = self.agent.invoke({
            "input": f"""Rollback model deployment:

Model: {model_name}
Target Version: {target_version}
Environment: {environment}

EMERGENCY ROLLBACK PROCEDURE:
1. Verify target version image exists in registry
2. Pull target version image if not local
3. Stop current container
4. Deploy target version container
5. Verify health check passes
6. If health check fails:
   - Log error
   - Attempt to restart previous version
   - Create incident report
7. Report rollback status

This is a critical operation - ensure all steps are logged."""
        })

        return result

    def generate_dockerfile(
        self,
        model_name: str,
        model_version: str,
        template: str = "python_model",
        environment: str = "dev"
    ) -> str:
        """Generate a Dockerfile from template"""
        if template not in DOCKERFILE_TEMPLATES:
            template = "python_model"

        dockerfile = DOCKERFILE_TEMPLATES[template].format(
            version=model_version,
            environment=environment
        )

        return dockerfile

    def run(self, task: str) -> Dict[str, Any]:
        """Run the agent with a custom task"""
        return self.agent.invoke({"input": task})


def main():
    """Demo the Docker Operations agent"""
    print("🐳 Docker Operations Agent - Container Management")
    print("=" * 60)

    # Check for required environment variables
    if not os.getenv("COMPOSIO_API_KEY"):
        print("⚠️  Set COMPOSIO_API_KEY environment variable")
        return
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Set OPENAI_API_KEY environment variable")
        return

    agent = DockerOpsAgent()

    # List available tools
    print("\n📦 Available tools:")
    for tool in agent.tools:
        print(f"  - {tool.name}")

    # Show Dockerfile templates
    print("\n📄 Available Dockerfile Templates:")
    for template in DOCKERFILE_TEMPLATES.keys():
        print(f"  - {template}")

    # Example task
    print("\n🚀 Running example task...")
    result = agent.run(
        "List all running containers with the researchflow label"
    )
    print(f"\n📋 Result: {result['output']}")


if __name__ == "__main__":
    main()
