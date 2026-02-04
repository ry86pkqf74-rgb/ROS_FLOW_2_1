#!/usr/bin/env python3
"""
ResearchFlow Agent Runner - CLI for executing AI agents

Usage:
    python run_agent.py design --figma-file <file_key>
    python run_agent.py spec --prd-id <notion_page_id>
    python run_agent.py compliance --model <model_id> --version <version>
    python run_agent.py deploy --model <model_id> --version <version> --mode <DEMO|LIVE>
    python run_agent.py docker --action <build|deploy|status>
"""

import os
import sys
import argparse
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def check_env():
    required = ["COMPOSIO_API_KEY", "OPENAI_API_KEY"]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    return True

def run_design_ops(args):
    from agents.design_ops_agent import DesignOpsAgent
    agent = DesignOpsAgent(entity_id=args.entity_id, github_repo=args.repo)
    if args.figma_file:
        result = agent.extract_design_tokens(args.figma_file)
    elif args.create_pr:
        branch = f"design-tokens/update-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        result = agent.create_design_tokens_pr(args.create_pr, branch)
    else:
        result = agent.run(args.task or "List Figma files")
    print(f"Result: {result.get('output', result)}")
    return result

def run_spec_ops(args):
    from agents.spec_ops_agent import SpecOpsAgent
    agent = SpecOpsAgent(entity_id=args.entity_id, github_repo=args.repo)
    if args.prd_id:
        result = agent.sync_prd_to_issues(args.prd_id)
    elif args.sync_all:
        result = agent.sync_all_prds()
    else:
        result = agent.run(args.task or "Search PRDs")
    print(f"Result: {result.get('output', result)}")
    return result

def run_compliance(args):
    from agents.compliance_agent import ComplianceAgent
    agent = ComplianceAgent(entity_id=args.entity_id, github_repo=args.repo)
    if args.model and args.version:
        if args.tripod:
            result = agent.validate_tripod_ai(args.model, f"evidence/models/{args.version}/")
        elif args.faves:
            result = agent.validate_faves_gates(args.model, args.version, args.mode or "DEMO")
        elif args.hti1:
            result = agent.generate_hti1_disclosure(args.model, args.version)
        else:
            result = agent.run_full_compliance_audit(args.model, args.version, args.mode or "DEMO")
    else:
        result = agent.run(args.task or "Search Model Registry")
    print(f"Result: {result.get('output', result)}")
    return result

def run_release_guardian(args):
    from agents.release_guardian_agent import ReleaseGuardianAgent
    agent = ReleaseGuardianAgent(entity_id=args.entity_id, github_repo=args.repo)
    if args.model and args.version:
        result = agent.validate_deployment(args.model, args.version, args.mode or "DEMO")
    elif args.ci_status:
        result = agent.check_ci_status()
    elif args.rollback:
        result = agent.trigger_rollback(args.model, args.version, args.rollback, args.reason or "Rollback")
    else:
        result = agent.run(args.task or "Get deployment status")
    print(f"Result: {result.get('output', result)}")
    return result

def run_docker_ops(args):
    from agents.docker_ops_agent import DockerOpsAgent
    agent = DockerOpsAgent(entity_id=args.entity_id, github_repo=args.repo)
    if args.action == "build" and args.model:
        result = agent.build_model_image(args.model, args.version or "latest", args.dockerfile or "Dockerfile", args.env or "dev")
    elif args.action == "deploy" and args.model:
        result = agent.deploy_model_container(args.model, args.version or "latest", args.env or "dev", args.port or 8080)
    elif args.action == "status":
        result = agent.list_deployments(args.env)
    else:
        result = agent.run(args.task or "List containers")
    print(f"Result: {result.get('output', result)}")
    return result

def run_orchestrator(args):
    from agents.orchestrator import ResearchFlowOrchestrator
    orch = ResearchFlowOrchestrator(entity_id=args.entity_id, github_repo=args.repo)
    if args.workflow == "design":
        result = orch.run_design_workflow(args.figma_file)
    elif args.workflow == "prd":
        result = orch.run_prd_workflow(args.prd_id)
    elif args.workflow == "compliance":
        result = orch.run_compliance_workflow(args.model, args.version, args.mode or "DEMO")
    elif args.workflow == "deploy":
        result = orch.run_deployment_workflow(args.model, args.version, args.mode or "DEMO")
    else:
        print("Workflows: design, prd, compliance, deploy")
        return
    print(json.dumps(result, indent=2, default=str))
    return result


def run_wiring_audit(args):
    from agents.wiring_audit_agent import WiringAuditAgent
    agent = WiringAuditAgent(entity_id=args.entity_id, github_repo=args.repo)
    if args.report:
        result = agent.audit_wiring(args.report, args.scope or "full")
    else:
        result = agent.run(args.task or "Audit wiring documentation and runtime gaps")
    print(f"Result: {result.get('output', result)}")
    return result


def run_orchestration_fix(args):
    from agents.orchestration_fix_agent import OrchestrationFixAgent
    agent = OrchestrationFixAgent(entity_id=args.entity_id, github_repo=args.repo)
    if args.report:
        result = agent.fix_gaps(args.report, args.focus or "frontend-backend")
    else:
        result = agent.run(args.task or "Fix frontend/backend wiring gaps")
    print(f"Result: {result.get('output', result)}")
    return result


def run_docker_stack(args):
    from agents.docker_stack_agent import DockerStackAgent
    agent = DockerStackAgent(entity_id=args.entity_id, github_repo=args.repo)
    if args.checklist:
        result = agent.verify_stack(args.checklist)
    else:
        result = agent.run(args.task or "Verify docker stack launch readiness")
    print(f"Result: {result.get('output', result)}")
    return result

def main():
    parser = argparse.ArgumentParser(description="ResearchFlow Agent Runner")
    parser.add_argument("--entity-id", default="default")
    parser.add_argument("--repo", default="ry86pkqf74-rgb/researchflow-production")
    parser.add_argument("--task")
    sub = parser.add_subparsers(dest="agent")
    
    d = sub.add_parser("design")
    d.add_argument("--figma-file")
    d.add_argument("--create-pr")
    
    s = sub.add_parser("spec")
    s.add_argument("--prd-id")
    s.add_argument("--sync-all", action="store_true")
    
    c = sub.add_parser("compliance")
    c.add_argument("--model")
    c.add_argument("--version")
    c.add_argument("--mode", choices=["DEMO", "STAGING", "LIVE"], default="DEMO")
    c.add_argument("--tripod", action="store_true")
    c.add_argument("--faves", action="store_true")
    c.add_argument("--hti1", action="store_true")
    
    r = sub.add_parser("deploy")
    r.add_argument("--model")
    r.add_argument("--version")
    r.add_argument("--mode", choices=["DEMO", "STAGING", "LIVE"], default="DEMO")
    r.add_argument("--ci-status", action="store_true")
    r.add_argument("--rollback")
    r.add_argument("--reason")
    
    dk = sub.add_parser("docker")
    dk.add_argument("--action", choices=["build", "deploy", "status", "logs", "stop"])
    dk.add_argument("--model")
    dk.add_argument("--version")
    dk.add_argument("--container")
    dk.add_argument("--dockerfile")
    dk.add_argument("--env", choices=["dev", "staging", "prod"], default="dev")
    dk.add_argument("--port", type=int, default=8080)
    
    o = sub.add_parser("orchestrate")
    o.add_argument("--workflow", choices=["design", "prd", "compliance", "deploy"])
    o.add_argument("--figma-file")
    o.add_argument("--prd-id")
    o.add_argument("--model")
    o.add_argument("--version")
    o.add_argument("--mode", choices=["DEMO", "STAGING", "LIVE"], default="DEMO")

    w = sub.add_parser("wiring")
    w.add_argument("--report", default="docs/audit/WIRING_STATUS_REPORT.md")
    w.add_argument("--scope", default="full")

    f = sub.add_parser("fix")
    f.add_argument("--report", default="docs/audit/WIRING_STATUS_REPORT.md")
    f.add_argument("--focus", default="frontend-backend")

    st = sub.add_parser("stack")
    st.add_argument("--checklist", default="docs/operations/docker-stack-launch.md")
    
    args = parser.parse_args()
    if not args.agent:
        parser.print_help()
        return
    check_env()
    {"design": run_design_ops, "spec": run_spec_ops, "compliance": run_compliance, "deploy": run_release_guardian, "docker": run_docker_ops, "orchestrate": run_orchestrator, "wiring": run_wiring_audit, "fix": run_orchestration_fix, "stack": run_docker_stack}[args.agent](args)

if __name__ == "__main__":
    main()
