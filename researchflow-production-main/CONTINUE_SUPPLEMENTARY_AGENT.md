# 🚀 Continue SupplementaryMaterialAgent - Quick Start

## Copy This Prompt to New Chat:

```
Continue SupplementaryMaterialAgent implementation - Phase 2: Core Agent.

CONTEXT:
- Phase 1 complete: Type definitions in supplementary_types.py (committed to main)
- Repository uses LangGraphBaseAgent pattern from services/worker/src/agents/base/
- Follow existing patterns from manuscript/agent.py
- State management via AgentState (from base/state.py)
- All LLM calls through self.call_llm() for PHI compliance

TASK:
Create services/worker/agents/writing/supplementary_material_agent.py

REQUIREMENTS:
1. Inherit from LangGraphBaseAgent
2. Handle stage 16 (after Results Refinement)
3. Implement 8 core nodes:
   - identify_supplementary_content (determine main vs supplement)
   - organize_supplementary_tables (S1, S2 numbering)
   - organize_supplementary_figures (S1, S2 numbering)
   - compile_extended_methods (detailed protocols)
   - generate_data_statement (data availability)
   - create_appendices (forms, checklists)
   - package_materials (manifest generation)
   - quality_gate (validation)

4. Build LangGraph with parallel processing for tables/figures/methods
5. Implement get_quality_criteria() method
6. Add custom _evaluate_criterion() for supplementary-specific checks
7. Use async/await patterns consistently
8. Include comprehensive docstrings
9. Follow type hints throughout

REFERENCE FILES:
- services/worker/agents/writing/supplementary_types.py (already created)
- services/worker/src/agents/base/langgraph_base.py (base class)
- services/worker/src/agents/manuscript/agent.py (pattern reference)

CONSIDERATIONS:
- Journal-specific formatting (NEJM, JAMA, PLOS, etc.)
- File size limits and validation
- Cross-reference checking
- STROBE/CONSORT checklist integration
- Automated numbering (S1, S2, etc.)
- Manifest generation with file descriptions

Start with the core agent class structure and first 3 nodes, then we'll iterate.
```

---

## What's Done ✅

1. **Type Definitions** (`supplementary_types.py`)
   - SupplementaryTable, SupplementaryFigure, Appendix classes
   - SupplementaryMaterialState Pydantic model
   - Journal requirements (NEJM, JAMA, PLOS, etc.)
   - STROBE/CONSORT checklists
   - 484 lines, fully typed

2. **Documentation** (`SUPPLEMENTARY_MATERIAL_AGENT_IMPLEMENTATION.md`)
   - Complete architecture plan
   - 6-phase implementation roadmap
   - Integration strategy
   - Success criteria

3. **Git Status**
   - Committed: 3f3df2e
   - Pushed to: origin/main
   - Branch: main

---

## Next Steps (Phase 2)

### File to Create:
`services/worker/agents/writing/supplementary_material_agent.py`

### Core Structure:
```python
class SupplementaryMaterialAgent(LangGraphBaseAgent):
    def __init__(self, llm_bridge, checkpointer=None):
        super().__init__(
            llm_bridge=llm_bridge,
            stages=[16],  # After Results Refinement
            agent_id='supplementary',
            checkpointer=checkpointer,
        )
    
    def build_graph(self) -> StateGraph:
        # Build the LangGraph workflow
        pass
    
    def get_quality_criteria(self) -> Dict[str, Any]:
        # Define quality gates
        pass
    
    # Node implementations...
    async def identify_supplementary_content_node(self, state):
        pass
```

---

## Key Patterns to Follow

### 1. Async Node Methods
```python
async def node_name(self, state: AgentState) -> Dict[str, Any]:
    """Node docstring."""
    logger.info(f"[Supplementary] Action", extra={'run_id': state.get('run_id')})
    
    result = await self.call_llm(
        prompt=prompt,
        task_type='task_name',
        state=state,
        model_tier='STANDARD',
    )
    
    return {'output_key': result}
```

### 2. Graph Building
```python
graph = StateGraph(AgentState)
graph.add_node("node_name", self.node_method)
graph.add_edge("node1", "node2")
graph.set_entry_point("first_node")
return graph.compile(checkpointer=self.checkpointer)
```

### 3. Quality Criteria
```python
def get_quality_criteria(self) -> Dict[str, Any]:
    return {
        'has_data_statement': True,
        'tables_numbered': True,
        'file_size_ok': 50,  # MB
    }
```

---

## Files to Reference

1. **Base Class:** `services/worker/src/agents/base/langgraph_base.py`
2. **Example Agent:** `services/worker/src/agents/manuscript/agent.py`
3. **State Types:** `services/worker/src/agents/base/state.py`
4. **Our Types:** `services/worker/agents/writing/supplementary_types.py`

---

## Success Checklist

- [ ] Agent class created and inherits from LangGraphBaseAgent
- [ ] Constructor properly calls super().__init__()
- [ ] build_graph() method implemented
- [ ] 8 node methods defined (async)
- [ ] Graph compiled with proper edges
- [ ] get_quality_criteria() returns dict
- [ ] _evaluate_criterion() handles custom checks
- [ ] All methods have docstrings
- [ ] Type hints throughout
- [ ] Follows existing patterns

---

## Quick Commands

```bash
# Check current branch
git status

# View recent changes
git log --oneline -5

# View type definitions
cat services/worker/agents/writing/supplementary_types.py | head -50

# View manuscript agent pattern
cat services/worker/src/agents/manuscript/agent.py | head -100
```

---

## Estimated Time

- Core agent structure: 30-45 min
- First 3 nodes: 30-45 min  
- Remaining 5 nodes: 60-90 min
- Testing: 30 min

**Total Phase 2:** ~3-4 hours

---

**START WITH:** Core agent class + first 3 nodes (identify, organize_tables, organize_figures)

**THEN:** Iterate on remaining nodes in subsequent steps

Good luck! 🎯
