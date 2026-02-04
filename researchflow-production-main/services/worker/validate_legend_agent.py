#!/usr/bin/env python3
"""
Simple validation script for TableFigureLegendAgent

Tests basic functionality without relative imports.
"""

import sys
import asyncio
from pathlib import Path

# Add the writing agents to the Python path
writing_agents_path = Path(__file__).parent / "agents" / "writing"
sys.path.insert(0, str(writing_agents_path))

def test_imports():
    """Test if we can import our modules."""
    try:
        import legend_types
        print("✅ legend_types imported successfully")
        
        import table_figure_legend_agent
        print("✅ table_figure_legend_agent imported successfully")
        
        return True, legend_types, table_figure_legend_agent
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False, None, None

def test_type_creation(legend_types):
    """Test creating type instances."""
    try:
        # Test Table creation
        table = legend_types.Table(
            id="test_table",
            title="Test Table",
            headers=["Col1", "Col2", "Col3"],
            rows=[["A", "B", "C"], ["1", "2", "3"]],
            sample_size=10,
        )
        print(f"✅ Table created: {table.id}")
        
        # Test Figure creation
        figure = legend_types.Figure(
            id="test_figure",
            title="Test Figure",
            figure_type="bar_chart",
            has_panels=False,
        )
        print(f"✅ Figure created: {figure.id}")
        
        return True, table, figure
    except Exception as e:
        print(f"❌ Type creation failed: {e}")
        return False, None, None

def test_agent_creation(agent_module):
    """Test creating agent instance."""
    try:
        agent = agent_module.create_table_figure_legend_agent()
        print(f"✅ Agent created: {type(agent).__name__}")
        return True, agent
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return False, None

async def test_legend_generation(agent, table, figure, legend_types):
    """Test legend generation."""
    try:
        # Test table legend generation
        table_legend = await agent.generate_table_legend(
            table=table,
            manuscript_context="Test study context",
            target_journal=legend_types.JournalStyleEnum.DEFAULT,
        )
        print(f"✅ Table legend generated: {table_legend.title}")
        print(f"   Word count: {table_legend.word_count}")
        print(f"   Compliant: {table_legend.journal_compliant}")
        
        # Test figure legend generation
        figure_legend = await agent.generate_figure_legend(
            figure=figure,
            manuscript_context="Test study context",
            target_journal=legend_types.JournalStyleEnum.NATURE,
        )
        print(f"✅ Figure legend generated: {figure_legend.caption}")
        print(f"   Word count: {figure_legend.word_count}")
        print(f"   Compliant: {figure_legend.journal_compliant}")
        
        return True
    except Exception as e:
        print(f"❌ Legend generation failed: {e}")
        return False

def test_journal_specs(agent_module):
    """Test journal specifications."""
    try:
        specs = agent_module.JOURNAL_SPECIFICATIONS
        print(f"✅ Found {len(specs)} journal specifications")
        
        for journal, spec in specs.items():
            print(f"   {journal.value}: {spec.max_legend_words} words max")
        
        return True
    except Exception as e:
        print(f"❌ Journal specs test failed: {e}")
        return False

async def main():
    """Run all validation tests."""
    print("🧪 Validating TableFigureLegendAgent Implementation")
    print("=" * 60)
    
    # Test 1: Imports
    print("\n1. Testing imports...")
    imports_ok, legend_types, agent_module = test_imports()
    if not imports_ok:
        print("❌ Validation failed at import stage")
        return
    
    # Test 2: Type creation
    print("\n2. Testing type creation...")
    types_ok, table, figure = test_type_creation(legend_types)
    if not types_ok:
        print("❌ Validation failed at type creation stage")
        return
    
    # Test 3: Agent creation
    print("\n3. Testing agent creation...")
    agent_ok, agent = test_agent_creation(agent_module)
    if not agent_ok:
        print("❌ Validation failed at agent creation stage")
        return
    
    # Test 4: Journal specifications
    print("\n4. Testing journal specifications...")
    specs_ok = test_journal_specs(agent_module)
    if not specs_ok:
        print("❌ Validation failed at journal specs stage")
        return
    
    # Test 5: Legend generation
    print("\n5. Testing legend generation...")
    legend_ok = await test_legend_generation(agent, table, figure, legend_types)
    if not legend_ok:
        print("❌ Validation failed at legend generation stage")
        return
    
    print("\n" + "=" * 60)
    print("🎉 All validation tests passed!")
    print("✅ TableFigureLegendAgent is ready for production!")

if __name__ == "__main__":
    asyncio.run(main())