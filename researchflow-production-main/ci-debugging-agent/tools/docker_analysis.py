#!/usr/bin/env python3
"""
Docker Analysis Tools

Dockerfile and docker-compose analysis for CI debugging.
"""
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class DockerIssue:
    """Represents a Docker configuration issue."""
    file: str
    line: int
    issue_type: str
    message: str
    severity: str
    suggested_fix: Optional[str] = None


def find_dockerfiles(repo_path: str) -> list[str]:
    """Find all Dockerfiles in the repository."""
    dockerfiles = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git']]
        for file in files:
            if file == 'Dockerfile' or file.startswith('Dockerfile.'):
                dockerfiles.append(os.path.join(root, file))
    return dockerfiles


def find_compose_files(repo_path: str) -> list[str]:
    """Find all docker-compose files."""
    compose_files = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git']]
        for file in files:
            if 'docker-compose' in file and file.endswith(('.yml', '.yaml')):
                compose_files.append(os.path.join(root, file))
    return compose_files


def analyze_dockerfile(filepath: str) -> list[DockerIssue]:
    """Analyze a Dockerfile for common issues."""
    issues = []
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return [DockerIssue(
            file=filepath,
            line=0,
            issue_type='READ_ERROR',
            message=str(e),
            severity='error'
        )]
    
    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()
        
        # Check for localhost hardcoding
        if 'localhost' in line.lower() and not line_stripped.startswith('#'):
            issues.append(DockerIssue(
                file=filepath,
                line=i,
                issue_type='LOCALHOST_HARDCODE',
                message="Hardcoded localhost found - use service names or environment variables",
                severity='warning',
                suggested_fix="Replace 'localhost' with service name or ${HOST} variable"
            ))
        
        # Check for 127.0.0.1 hardcoding
        if '127.0.0.1' in line and not line_stripped.startswith('#'):
            issues.append(DockerIssue(
                file=filepath,
                line=i,
                issue_type='LOCALHOST_HARDCODE',
                message="Hardcoded 127.0.0.1 found - use service names or environment variables",
                severity='warning',
                suggested_fix="Replace '127.0.0.1' with service name or ${HOST} variable"
            ))
        
        # Check for missing HEALTHCHECK
        if line_stripped.startswith('FROM') and 'HEALTHCHECK' not in content:
            issues.append(DockerIssue(
                file=filepath,
                line=i,
                issue_type='MISSING_HEALTHCHECK',
                message="No HEALTHCHECK instruction found",
                severity='info',
                suggested_fix="Add HEALTHCHECK instruction for better container orchestration"
            ))
        
        # Check for using latest tag
        if line_stripped.startswith('FROM') and ':latest' in line:
            issues.append(DockerIssue(
                file=filepath,
                line=i,
                issue_type='LATEST_TAG',
                message="Using :latest tag - pin to specific version for reproducibility",
                severity='warning',
                suggested_fix="Pin to specific version (e.g., node:20-alpine instead of node:latest)"
            ))
        
        # Check for running as root
        if line_stripped.startswith('USER root'):
            issues.append(DockerIssue(
                file=filepath,
                line=i,
                issue_type='ROOT_USER',
                message="Running as root user - consider using non-root user",
                severity='warning',
                suggested_fix="Add USER directive with non-root user"
            ))
        
        # Check for secrets in ENV
        if line_stripped.startswith('ENV'):
            secret_patterns = ['PASSWORD', 'SECRET', 'API_KEY', 'TOKEN', 'PRIVATE']
            for pattern in secret_patterns:
                if pattern in line.upper() and '=' in line:
                    issues.append(DockerIssue(
                        file=filepath,
                        line=i,
                        issue_type='SECRET_IN_ENV',
                        message=f"Potential secret in ENV instruction ({pattern})",
                        severity='error',
                        suggested_fix="Use Docker secrets or pass at runtime with -e flag"
                    ))
    
    return issues


def analyze_compose_file(filepath: str) -> list[DockerIssue]:
    """Analyze a docker-compose file for issues."""
    issues = []
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return [DockerIssue(
            file=filepath,
            line=0,
            issue_type='READ_ERROR',
            message=str(e),
            severity='error'
        )]
    
    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()
        
        # Check for localhost in environment
        if 'localhost' in line.lower() and not line_stripped.startswith('#'):
            issues.append(DockerIssue(
                file=filepath,
                line=i,
                issue_type='LOCALHOST_IN_COMPOSE',
                message="Hardcoded localhost - use Docker service names",
                severity='warning',
                suggested_fix="Replace 'localhost' with Docker service name (e.g., 'db', 'redis')"
            ))
        
        # Check for privileged mode
        if 'privileged: true' in line:
            issues.append(DockerIssue(
                file=filepath,
                line=i,
                issue_type='PRIVILEGED_MODE',
                message="Container running in privileged mode",
                severity='warning',
                suggested_fix="Remove privileged mode unless absolutely necessary"
            ))
        
        # Check for host network mode
        if 'network_mode: host' in line or "network_mode: 'host'" in line:
            issues.append(DockerIssue(
                file=filepath,
                line=i,
                issue_type='HOST_NETWORK',
                message="Using host network mode",
                severity='info',
                suggested_fix="Consider using bridge network for better isolation"
            ))
    
    return issues


def run_docker_analysis(repo_path: str) -> dict:
    """Run full Docker analysis on repository."""
    results = {
        'dockerfiles': [],
        'compose_files': [],
        'issues': [],
        'summary': {
            'total_issues': 0,
            'errors': 0,
            'warnings': 0,
            'info': 0
        }
    }
    
    # Find and analyze Dockerfiles
    dockerfiles = find_dockerfiles(repo_path)
    results['dockerfiles'] = dockerfiles
    
    for df in dockerfiles:
        issues = analyze_dockerfile(df)
        results['issues'].extend(issues)
    
    # Find and analyze compose files
    compose_files = find_compose_files(repo_path)
    results['compose_files'] = compose_files
    
    for cf in compose_files:
        issues = analyze_compose_file(cf)
        results['issues'].extend(issues)
    
    # Calculate summary
    for issue in results['issues']:
        results['summary']['total_issues'] += 1
        if issue.severity == 'error':
            results['summary']['errors'] += 1
        elif issue.severity == 'warning':
            results['summary']['warnings'] += 1
        else:
            results['summary']['info'] += 1
    
    return results
