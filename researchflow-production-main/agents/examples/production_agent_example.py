#!/usr/bin/env python3
"""
Production-Ready Agent Example

Demonstrates how to use the production infrastructure in a real agent.

Features:
- Structured logging
- Environment validation
- Health checks
- Secret management
- AI helper integration
- Error handling with AI analysis

Usage:
    python -m agents.examples.production_agent_example
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.utils import (
    # Logging
    setup_structured_logging,
    get_agent_logger,
    LogContext,
    log_async_execution_time,
    # Validation
    validate_startup_environment,
    # Health
    get_agent_health_checker,
    # Secrets
    get_secrets_manager,
    # AI Helper
    get_ai_helper,
    # NEW: Error tracking and startup orchestration
    initialize_error_tracking,
    track_error,
    create_span,
    TraceContext,
    get_error_stats,
    managed_agent_lifecycle,
    register_startup_check,
    get_startup_orchestrator,
    # Existing production features
    track_agent_task,
    retry_api_call,
    timeout_api_call,
    rate_limit_api_calls,
)


class ProductionAgent:
    """
    Example production-ready agent with all infrastructure integrated.
    """
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = get_agent_logger(agent_name)
        self.secrets = get_secrets_manager()
        self.ai_helper = get_ai_helper()
        self.health_checker = get_agent_health_checker()
        
        self.logger.info(f"Agent '{agent_name}' initialized")
        
    async def register_custom_startup_checks(self):
        """Register custom startup checks for this agent"""
        
        @register_startup_check(
            name="ai_service_validation",
            priority=10,
            timeout=30.0,
            description="Validate AI service connectivity"
        )
        async def check_ai_services():
            """Check if AI services are accessible"""
            try:
                # Test OpenAI API access
                response = await self.ai_helper.ask_openai(
                    prompt="Hello, this is a test.",
                    model="gpt-4o",
                    max_tokens=10
                )
                
                ai_available = response and not response.error
                
                return {
                    "openai_accessible": ai_available,
                    "ai_helper_initialized": True
                }
            except Exception as e:
                raise RuntimeError(f"AI services validation failed: {e}")
                
        @register_startup_check(
            name="agent_dependencies",
            priority=11,
            timeout=15.0,
            depends_on=["ai_service_validation"],
            critical=False,  # Non-critical
            description="Validate agent-specific dependencies"
        )
        async def check_agent_deps():
            """Check agent-specific dependencies"""
            return {
                "agent_name": self.agent_name,
                "logger_ready": self.logger is not None,
                "secrets_ready": self.secrets is not None,
                "health_checker_ready": self.health_checker is not None
            }
    
    @track_error(component="ProductionAgent", operation="execute_task")
    @create_span("task_execution")
    @track_agent_task("ProductionAgent", "task_execution")
    @retry_api_call(max_attempts=3, base_delay=1.0)
    @timeout_api_call(300.0)  # 5 minute timeout
    @rate_limit_api_calls(requests_per_second=5.0)
    @log_async_execution_time()
    async def execute_task(self, task_id: str, task_description: str):
        """
        Execute a task with full production infrastructure.
        
        Demonstrates:
        - Contextual logging with correlation IDs
        - AI helper for code generation
        - Error handling with AI analysis
        - Health monitoring
        """
        # Set log context for tracing
        with LogContext(
            agent_name=self.agent_name,
            workflow_id=f"wf-{task_id}",
            correlation_id=f"task-{task_id}"
        ):
            self.logger.info(
                "Task started",
                extra={
                    "task_id": task_id,
                    "description": task_description
                }
            )
            
            try:
                # Check health before proceeding
                health = await self.health_checker.check_all()
                if not health.status.value == "healthy":
                    self.logger.warning(
                        "System health degraded",
                        extra={"health_status": health.status.value}
                    )
                
                # Simulate task execution with AI help
                self.logger.info("Requesting AI assistance for task")
                
                # Use AI helper to generate solution with tracing
                async with TraceContext("ai_request", "OpenAI") as ai_trace:
                    response = await self.ai_helper.ask_openai(
                        prompt=f"How would you implement: {task_description}",
                        model="gpt-4o",
                        system_prompt="You are a helpful coding assistant."
                    )
                    
                    # Add trace metadata
                    if response:
                        ai_trace.tags = {
                            "model": response.model,
                            "tokens_used": response.tokens_used,
                            "has_error": bool(response.error)
                        }
                
                if response and not response.error:
                    self.logger.info(
                        "AI suggestion received",
                        extra={
                            "task_id": task_id,
                            "model": response.model,
                            "tokens_used": response.tokens_used,
                            "cost_estimate": response.cost_estimate
                        }
                    )
                    
                    # Process the response
                    await self._process_ai_response(task_id, response.content)
                else:
                    self.logger.error(
                        "AI helper failed",
                        extra={
                            "task_id": task_id,
                            "error": response.error if response else "No response"
                        }
                    )
                
                self.logger.info(
                    "Task completed successfully",
                    extra={"task_id": task_id, "status": "success"}
                )
                
            except Exception as e:
                self.logger.error(
                    "Task failed",
                    extra={"task_id": task_id, "error": str(e)},
                    exc_info=True
                )
                
                # Use AI to analyze the error
                await self._analyze_error_with_ai(task_id, e)
                
                raise
    
    async def _process_ai_response(self, task_id: str, response_text: str):
        """Process AI-generated response"""
        self.logger.debug(
            "Processing AI response",
            extra={
                "task_id": task_id,
                "response_length": len(response_text)
            }
        )
        
        # Simulate processing
        await asyncio.sleep(0.1)
    
    async def _analyze_error_with_ai(self, task_id: str, error: Exception):
        """Use AI to analyze errors and suggest fixes"""
        self.logger.info("Analyzing error with AI", extra={"task_id": task_id})
        
        try:
            analysis = await self.ai_helper.analyze_error(
                error_message=str(error),
                stack_trace=None,  # Could extract from traceback
                language="python"
            )
            
            if analysis:
                self.logger.info(
                    "Error analysis complete",
                    extra={
                        "task_id": task_id,
                        "root_cause": analysis.get("root_cause", "Unknown"),
                        "suggestions_count": len(analysis.get("suggested_fixes", []))
                    }
                )
                
                # Log suggested fixes
                for i, fix in enumerate(analysis.get("suggested_fixes", []), 1):
                    self.logger.info(
                        f"Suggested fix {i}",
                        extra={"task_id": task_id, "fix": fix}
                    )
        
        except Exception as ai_error:
            self.logger.warning(
                "AI error analysis failed",
                extra={"task_id": task_id, "ai_error": str(ai_error)}
            )
    
    async def health_check(self):
        """Perform health check"""
        health = await self.health_checker.check_all()
        
        self.logger.info(
            "Health check completed",
            extra={
                "status": health.status.value,
                "uptime": health.uptime_seconds,
                "component_count": len(health.components)
            }
        )
        
        return health


async def run_with_full_infrastructure():
    """Run the complete production infrastructure example"""
    
    print("🚀 Full Production Infrastructure Demo")
    print("=" * 70)
    
    # Step 1: Initialize error tracking
    print("\n📊 Step 1: Setting up error tracking...")
    import os
    sentry_dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENV", "development")
    
    initialize_error_tracking(
        dsn=sentry_dsn,  # Will gracefully degrade if not available
        environment=environment,
        sample_rate=1.0
    )
    
    # Step 2: Setup logging
    print("\n📋 Step 2: Setting up structured logging...")
    setup_structured_logging(level="INFO", json_format=False)
    
    # Step 3: Initialize agent and register checks
    agent = ProductionAgent("ProductionDemoAgent")
    await agent.register_custom_startup_checks()
    
    # Step 4: Use managed lifecycle for complete startup/shutdown
    try:
        async with managed_agent_lifecycle() as orchestrator:
            print("\n✅ Agent system startup completed!")
            
            # Show startup metrics
            startup_status = orchestrator.get_startup_status()
            print(f"📈 Startup checks completed: {len(startup_status['checks'])}")
            print(f"🔄 System ready: {startup_status['ready']}")
            
            # Run example tasks with error tracking
            print("\n⚙️  Running example tasks with full monitoring...")
            
            tasks = [
                ("task-001", "Create a Python function to validate email addresses"),
                ("task-002", "Implement a circuit breaker pattern"),
                ("task-003", "Design a caching strategy for API responses"),
                ("task-004", "This will fail intentionally"),  # For error tracking demo
            ]
            
            for i, (task_id, description) in enumerate(tasks):
                try:
                    print(f"\n  📝 Executing {task_id}: {description[:50]}...")
                    
                    # Simulate error on last task
                    if i == 3:
                        raise ValueError("Intentional error for demonstration")
                        
                    await agent.execute_task(task_id, description)
                    print(f"  ✅ {task_id} completed")
                    
                except Exception as e:
                    print(f"  ❌ {task_id} failed: {e}")
                    # Errors are automatically tracked by decorators
                    
            # Show error statistics
            print("\n📊 Error tracking statistics:")
            error_stats = await get_error_stats(last_minutes=5)
            print(f"  - Total errors: {error_stats.total_errors}")
            print(f"  - Error rate: {error_stats.error_rate:.2f}/min")
            print(f"  - Error types: {list(error_stats.error_types.keys())}")
            
            # Show health status
            print("\n💊 Health check:")
            readiness = await orchestrator.check_readiness()
            liveness = await orchestrator.check_liveness()
            print(f"  - Ready: {readiness['ready']}")
            print(f"  - Alive: {liveness['alive']}")
            
            print("\n⏳ Demo complete! (System will shutdown gracefully)")
            
    except Exception as e:
        print(f"💥 System failed: {e}")
        raise
        
    print("\n✅ Production infrastructure demo completed!")
    

async def main():
    """Main entry point demonstrating production agent"""
    
    print("🚀 Production-Ready Agent Example")
    print("=" * 70)
    
    # Step 1: Setup structured logging
    print("\n📋 Step 1: Setting up structured logging...")
    setup_structured_logging(level="INFO", json_format=False)  # Use text for demo
    
    # Step 2: Validate environment
    print("\n🔍 Step 2: Validating environment...")
    if not validate_startup_environment():
        print("❌ Environment validation failed!")
        print("Note: This is expected if you haven't set API keys.")
        print("Set COMPOSIO_API_KEY and OPENAI_API_KEY to run fully.")
        
        # Continue anyway for demo
        print("\n⚠️  Continuing anyway for demonstration...")
    
    # Step 3: Initialize agent
    print("\n🤖 Step 3: Initializing agent...")
    agent = ProductionAgent("DemoAgent")
    
    # Step 4: Check health
    print("\n💚 Step 4: Running health check...")
    health = await agent.health_check()
    print(f"Health status: {health.status.value}")
    
    # Step 5: Execute tasks
    print("\n⚙️  Step 5: Executing tasks...")
    
    tasks = [
        ("task-001", "Create a Python function to validate email addresses"),
        ("task-002", "Implement a circuit breaker pattern"),
        ("task-003", "Design a caching strategy for API responses"),
    ]
    
    for task_id, description in tasks:
        try:
            print(f"\n  📝 Executing {task_id}: {description[:50]}...")
            await agent.execute_task(task_id, description)
            print(f"  ✅ {task_id} completed")
        except Exception as e:
            print(f"  ❌ {task_id} failed: {e}")
    
    # Step 6: Final health check
    print("\n🏁 Step 6: Final health check...")
    final_health = await agent.health_check()
    print(f"Final health status: {final_health.status.value}")
    
    print("\n" + "=" * 70)
    print("✨ Demo completed!")
    print("\nThis demonstrated:")
    print("  ✅ Structured logging with context")
    print("  ✅ Environment validation")
    print("  ✅ Health monitoring")
    print("  ✅ Secret management")
    print("  ✅ AI helper integration")
    print("  ✅ Error analysis with AI")
    print("\nCheck the logs above for structured output examples.")
    
    # Ask user if they want to see the full infrastructure demo
    print("\n" + "="*70)
    print("🚀 Want to see the FULL production infrastructure demo?")
    print("This includes:")
    print("  🔍 Startup orchestration with dependency checks")
    print("  📊 Error tracking and distributed tracing")
    print("  🛡️ Circuit breakers and retry logic")
    print("  ⏱️ Timeout protection and rate limiting")
    print("  💊 Kubernetes readiness/liveness probes")
    print("  🔄 Graceful startup and shutdown")
    
    import sys
    if "--full" in sys.argv or "--production" in sys.argv:
        print("\n🎯 Running full production infrastructure demo...")
        await run_with_full_infrastructure()
    else:
        print("\n💡 Tip: Run with --full flag to see complete production infrastructure:")
        print("   python agents/examples/production_agent_example.py --full")


if __name__ == "__main__":
    import sys
    
    # Setup signal handling for graceful shutdown
    import signal
    
    def signal_handler(signum, frame):
        print(f"\n🔔 Received signal {signum} - shutting down gracefully...")
        # The managed_agent_lifecycle will handle actual shutdown
        
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Check for different run modes
    if "--health" in sys.argv:
        # Health check mode (useful for containers)
        print("💊 Health check mode")
        
        async def health_check():
            orchestrator = get_startup_orchestrator()
            readiness = await orchestrator.check_readiness()
            print(f"Ready: {readiness['ready']}")
            return readiness["ready"]
            
        healthy = asyncio.run(health_check())
        sys.exit(0 if healthy else 1)
        
    else:
        # Run the async main function
        asyncio.run(main())
