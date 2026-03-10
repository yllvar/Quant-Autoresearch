import pytest
from context.composer import PromptComposer

def test_composer_initialization():
    composer = PromptComposer()
    assert len(composer.prompt_sections) > 0
    assert "identity" in composer.prompt_sections

def test_compose_prompt_basic():
    composer = PromptComposer()
    context = {
        "iteration": 1
    }
    result = composer.compose_prompt("thinking", context, "planner")
    prompt = result["prompt"]
    assert "THINKING" in prompt.upper()
    assert "Iteration: 1" in prompt

def test_system_reminders():
    composer = PromptComposer()
    # High context pressure context
    context = {
        "context_usage_percent": 85,
        "iteration": 5
    }
    reminders = composer._generate_system_reminders(context)
    assert any("CONTEXT" in r.upper() for r in reminders)

def test_assemble_prompt():
    composer = PromptComposer()
    components = {
        "base_constitution": "I am an agent.",
        "dynamic_sections": [{"name": "goal", "content": "My goal is to trade."}],
        "system_reminders": [],
        "context_injection": "",
        "schema_gating": ""
    }
    full_prompt = composer._assemble_prompt(components, "reasoning")
    assert "I am an agent." in full_prompt
    assert "My goal is to trade." in full_prompt
    assert "JSON" in full_prompt.upper()  # Should have JSON instructions for reasoning
