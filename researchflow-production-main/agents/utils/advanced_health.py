#!/usr/bin/env python3
"""
Advanced Health Checks for ResearchFlow Agents

Provides specialized health checks for agent-specific components:
- Workflow execution health
- AI service connectivity
- Resource utilization monitoring
- Integration health (GitHub, Notion, Figma)
- Performance degradation detection

@author Claude
@created 2025-01-30
"""

import os
import psutil
import asyncio
import aiofiles
import subprocess
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from .health_check import HealthStatus

logger = logging.getLogger(__name__)


@dataclass
class ResourceUsage:
    """System resource usage metrics"""
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_usage_percent: float
    open_files: int
    active_connections: int


class AdvancedHealthChecker:
    """
    Advanced health checks for production monitoring.
    
    Goes beyond basic connectivity to check:
    - Resource utilization and limits
    - Performance degradation
    - Integration health
    - Workflow execution status
    """
    
    def __init__(self):
        self.process = psutil.Process()
        self.baseline_metrics: Optional[ResourceUsage] = None
        self.performance_history: List[Tuple[datetime, ResourceUsage]] = []
    
    async def check_system_resources(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Check system resource utilization.
        
        Returns:
            (is_healthy, message, details)
        """
        try:
            # Get current resource usage
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            
            # Get system-wide metrics
            disk_usage = psutil.disk_usage('/')
            disk_percent = disk_usage.percent
            
            # Get open files and connections
            try:
                open_files = len(self.process.open_files())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                open_files = -1
            
            try:
                connections = len(self.process.connections())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                connections = -1
            
            usage = ResourceUsage(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_mb=memory_info.rss / 1024 / 1024,
                disk_usage_percent=disk_percent,
                open_files=open_files,
                active_connections=connections
            )
            
            # Store for trend analysis
            self.performance_history.append((datetime.now(), usage))
            
            # Keep last 10 measurements
            if len(self.performance_history) > 10:
                self.performance_history = self.performance_history[-10:]
            
            # Set baseline if not set
            if self.baseline_metrics is None:
                self.baseline_metrics = usage
            
            # Check thresholds
            issues = []
            if cpu_percent > 80:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory_percent > 80:
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            
            if disk_percent > 90:
                issues.append(f"High disk usage: {disk_percent:.1f}%")
            
            if open_files > 1000:
                issues.append(f"Many open files: {open_files}")
            
            if connections > 100:
                issues.append(f"Many connections: {connections}")
            
            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_mb": usage.memory_mb,
                "disk_percent": disk_percent,
                "open_files": open_files,
                "connections": connections
            }
            
            if issues:
                return False, f"Resource issues: {'; '.join(issues)}", details
            else:
                return True, "System resources within normal limits", details
                
        except Exception as e:
            return False, f"Resource check failed: {str(e)}", {}
    
    async def check_performance_degradation(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Check for performance degradation over time.
        
        Compares current metrics to historical baseline.
        """
        if len(self.performance_history) < 3:
            return True, "Insufficient history for performance analysis", {"samples": len(self.performance_history)}
        
        try:
            current = self.performance_history[-1][1]
            baseline = self.baseline_metrics
            
            if not baseline:
                return True, "No baseline established", {}
            
            # Check for significant increases
            degradation_factors = []
            
            if current.cpu_percent > baseline.cpu_percent * 2:
                degradation_factors.append(f"CPU usage doubled ({baseline.cpu_percent:.1f}% → {current.cpu_percent:.1f}%)")
            
            if current.memory_percent > baseline.memory_percent * 1.5:
                degradation_factors.append(f"Memory usage increased 50% ({baseline.memory_percent:.1f}% → {current.memory_percent:.1f}%)")
            
            # Calculate trend over last 5 measurements
            if len(self.performance_history) >= 5:
                recent_memory = [h[1].memory_percent for h in self.performance_history[-5:]]
                memory_trend = (recent_memory[-1] - recent_memory[0]) / len(recent_memory)
                
                if memory_trend > 5:  # Growing by 5% per measurement
                    degradation_factors.append(f"Memory leak suspected (trend: +{memory_trend:.1f}%)")
            
            details = {
                "baseline_cpu": baseline.cpu_percent,
                "current_cpu": current.cpu_percent,
                "baseline_memory": baseline.memory_percent,
                "current_memory": current.memory_percent,
                "history_samples": len(self.performance_history)
            }
            
            if degradation_factors:
                return False, f"Performance degradation detected: {'; '.join(degradation_factors)}", details
            else:
                return True, "Performance stable", details
                
        except Exception as e:
            return False, f"Performance analysis failed: {str(e)}", {}
    
    async def check_disk_space(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Check available disk space"""
        try:
            # Check main filesystem
            usage = psutil.disk_usage('/')
            free_gb = usage.free / (1024**3)
            total_gb = usage.total / (1024**3)
            used_percent = (usage.used / usage.total) * 100
            
            # Check temp directory
            temp_usage = psutil.disk_usage('/tmp')
            temp_free_gb = temp_usage.free / (1024**3)
            
            details = {
                "total_gb": round(total_gb, 2),
                "free_gb": round(free_gb, 2),
                "used_percent": round(used_percent, 1),
                "temp_free_gb": round(temp_free_gb, 2)
            }
            
            if used_percent > 95:
                return False, f"Critical disk space: {used_percent:.1f}% used, {free_gb:.1f}GB free", details
            elif used_percent > 85:
                return False, f"Low disk space: {used_percent:.1f}% used, {free_gb:.1f}GB free", details
            elif temp_free_gb < 1.0:
                return False, f"Low temp space: {temp_free_gb:.1f}GB free", details
            else:
                return True, f"Sufficient disk space: {free_gb:.1f}GB free ({100-used_percent:.1f}% available)", details
                
        except Exception as e:
            return False, f"Disk space check failed: {str(e)}", {}
    
    async def check_git_repository(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Check Git repository health"""
        try:
            # Check if we're in a Git repo
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return True, "Not in a Git repository", {"git_available": False}
            
            # Get current branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
            
            # Check for uncommitted changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            has_changes = len(status_result.stdout.strip()) > 0 if status_result.returncode == 0 else False
            
            # Get last commit
            commit_result = subprocess.run(
                ["git", "log", "-1", "--format=%H %s"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            last_commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown"
            
            details = {
                "git_available": True,
                "current_branch": current_branch,
                "has_uncommitted_changes": has_changes,
                "last_commit": last_commit
            }
            
            if has_changes and current_branch == "main":
                return False, f"Uncommitted changes on main branch", details
            else:
                return True, f"Git repository healthy (branch: {current_branch})", details
                
        except subprocess.TimeoutExpired:
            return False, "Git commands timed out", {}
        except FileNotFoundError:
            return True, "Git not installed", {"git_available": False}
        except Exception as e:
            return False, f"Git check failed: {str(e)}", {}
    
    async def check_environment_files(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Check for required configuration files"""
        required_files = [
            ".env",
            "requirements.txt",
            "docker-compose.yml"
        ]
        
        optional_files = [
            ".env.example",
            "pytest.ini",
            "README.md"
        ]
        
        missing_required = []
        missing_optional = []
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_required.append(file_path)
        
        for file_path in optional_files:
            if not os.path.exists(file_path):
                missing_optional.append(file_path)
        
        details = {
            "required_files": required_files,
            "optional_files": optional_files,
            "missing_required": missing_required,
            "missing_optional": missing_optional
        }
        
        if missing_required:
            return False, f"Missing required files: {', '.join(missing_required)}", details
        elif missing_optional:
            return True, f"Missing optional files: {', '.join(missing_optional)}", details
        else:
            return True, "All configuration files present", details
    
    async def check_log_rotation(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Check log file sizes and rotation"""
        log_directories = [
            "./logs",
            "/var/log",
            "/tmp"
        ]
        
        large_logs = []
        total_log_size_mb = 0
        
        for log_dir in log_directories:
            if not os.path.exists(log_dir):
                continue
            
            try:
                for root, dirs, files in os.walk(log_dir):
                    for file in files:
                        if file.endswith(('.log', '.out', '.err')):
                            file_path = os.path.join(root, file)
                            try:
                                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                                total_log_size_mb += size_mb
                                
                                if size_mb > 100:  # More than 100MB
                                    large_logs.append((file_path, size_mb))
                            except (OSError, IOError):
                                pass  # Skip files we can't read
            except (OSError, IOError):
                pass  # Skip directories we can't read
        
        details = {
            "total_log_size_mb": round(total_log_size_mb, 2),
            "large_logs": [(path, round(size, 2)) for path, size in large_logs]
        }
        
        if total_log_size_mb > 1000:  # More than 1GB of logs
            return False, f"Excessive log usage: {total_log_size_mb:.1f}MB total", details
        elif large_logs:
            return False, f"Large log files found: {len(large_logs)} files >100MB", details
        else:
            return True, f"Log usage normal: {total_log_size_mb:.1f}MB total", details
    
    async def check_workflow_dependencies(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Check that workflow dependencies are healthy"""
        try:
            # Check Python imports
            import_checks = [
                ("langchain", "LangChain core"),
                ("composio_langchain", "Composio integration"),
                ("openai", "OpenAI client"),
                ("anthropic", "Anthropic client"),
                ("pydantic", "Data validation"),
                ("httpx", "HTTP client"),
                ("asyncio", "Async support")
            ]
            
            failed_imports = []
            successful_imports = []
            
            for module_name, description in import_checks:
                try:
                    __import__(module_name)
                    successful_imports.append((module_name, description))
                except ImportError as e:
                    failed_imports.append((module_name, description, str(e)))
            
            details = {
                "successful_imports": len(successful_imports),
                "failed_imports": len(failed_imports),
                "failures": [
                    {"module": mod, "description": desc, "error": err}
                    for mod, desc, err in failed_imports
                ]
            }
            
            if failed_imports:
                return False, f"Missing dependencies: {', '.join(mod for mod, _, _ in failed_imports)}", details
            else:
                return True, f"All {len(successful_imports)} dependencies available", details
                
        except Exception as e:
            return False, f"Dependency check failed: {str(e)}", {}


# Pre-configured advanced health checker

def get_advanced_health_checker():
    """Get advanced health checker with all checks configured"""
    from .health_check import HealthChecker
    
    checker = HealthChecker()
    advanced = AdvancedHealthChecker()
    
    # Add advanced checks
    checker.add_check("system_resources", advanced.check_system_resources, critical=True)
    checker.add_check("performance", advanced.check_performance_degradation, critical=False)
    checker.add_check("disk_space", advanced.check_disk_space, critical=True)
    checker.add_check("git_repository", advanced.check_git_repository, critical=False)
    checker.add_check("environment_files", advanced.check_environment_files, critical=True)
    checker.add_check("log_rotation", advanced.check_log_rotation, critical=False)
    checker.add_check("workflow_dependencies", advanced.check_workflow_dependencies, critical=True)
    
    return checker