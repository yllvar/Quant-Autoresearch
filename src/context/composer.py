"""
Modular Prompt Composition with System Reminders for OPENDEV architecture
"""
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

class PromptComposer:
    """Modular prompt composition with dynamic context and system reminders"""
    
    def __init__(self, program_file: str = "program.md"):
        self.program_file = program_file
        self.base_constitution = self._load_base_constitution()
        
        # Modular prompt sections (per OPENDEV paper)
        self.prompt_sections = {
            "identity": self._load_prompt_section("identity.md"),
            "safety_policy": self._load_prompt_section("safety_policy.md"),
            "tool_guidance": self._load_prompt_section("tool_guidance.md"),
            "quant_rules": self._load_prompt_section("quant_rules.md"),
            "git_rules": self._load_prompt_section("git_rules.md")
        }
        
        # System reminders registry
        self.system_reminders = []
        self.reminder_triggers = {
            "incomplete_todos": self._check_incomplete_todos,
            "high_risk_operations": self._check_high_risk_operations,
            "context_pressure": self._check_context_pressure,
            "iteration_milestone": self._check_iteration_milestone,
            "performance_decline": self._check_performance_decline
        }
        
        # Context predicates for dynamic loading (per OPENDEV paper)
        self.context_predicates = {
            "git_rules": self._has_git_repository,
            "high_risk_tools": self._has_high_risk_operations,
            "research_mode": self._is_research_mode,
            "trading_mode": self._is_trading_mode
        }
    
    def _load_base_constitution(self) -> str:
        """Load the base program constitution"""
        try:
            with open(self.program_file, "r") as f:
                return f.read()
        except FileNotFoundError:
            return self._get_default_constitution()
    
    def _get_default_constitution(self) -> str:
        """Fallback constitution if program.md is missing"""
        return """
# Quant Autoresearch: The Constitution

You are a **Senior Quantitative Researcher**. Your goal is to evolve a high-performance trading strategy through autonomous experimentation grounded in academic research.

## Your Mandate
Maximize the **Average Walk-Forward Out-of-Sample (OOS) Sharpe Ratio**.

## Available Features
The `data` DataFrame contains: `Open`, `High`, `Low`, `Close`, `Volume`, `returns`, `volatility`, `atr`.

## The Multi-Modal Workflow
1. **Hypothesis**: Propose a financial hypothesis based on current performance and history.
2. **Research**: The system will fetch relevant **ArXiv Quantitative Finance** snippets matching your hypothesis.
3. **Implementation**: Update the `# --- EDITABLE REGION ---` in `strategy.py`.
4. **Evaluation**: Backtest remains the final arbiter of truth.

## Key Rules & Constraints
1. **Vectorized Logic Only**: Use Pandas/NumPy. No `for` loops.
2. **Available Libraries**: You have `pandas as pd` and `numpy as np` already imported.
3. **No Look-Ahead Bias**: Avoid `.shift(-1)`.
4. **Security**: No external calls, no `exec()`, no `eval()`.
5. **Risk**: No Martingale. Max net exposure 1.0 per asset.

GOAL: Achieve an Average OOS Sharpe > 1.5.
"""
    
    def _load_prompt_section(self, section_file: str) -> str:
        """Load individual prompt section"""
        section_path = Path("prompts") / section_file
        if section_path.exists():
            with open(section_path, "r") as f:
                return f.read()
        return ""
    
    def compose_prompt(self, prompt_type: str, context: Dict[str, Any], 
                      subagent_type: str = "full_access") -> Dict[str, Any]:
        """Compose modular prompt with dynamic sections and system reminders"""
        
        prompt_components = {
            "base_constitution": self.base_constitution,
            "dynamic_sections": [],
            "system_reminders": [],
            "context_injection": self._generate_context_injection(context),
            "schema_gating": self._generate_schema_gating_info(subagent_type)
        }
        
        # Load dynamic sections based on context predicates
        for section_name, section_content in self.prompt_sections.items():
            if self._should_load_section(section_name, context):
                prompt_components["dynamic_sections"].append({
                    "name": section_name,
                    "content": section_content
                })
        
        # Generate system reminders based on triggers
        system_reminders = self._generate_system_reminders(context)
        prompt_components["system_reminders"] = system_reminders
        
        # Compose final prompt
        final_prompt = self._assemble_prompt(prompt_components, prompt_type)
        
        return {
            "prompt": final_prompt,
            "components": prompt_components,
            "system_reminders_count": len(system_reminders),
            "sections_loaded": len(prompt_components["dynamic_sections"]),
            "subagent_type": subagent_type
        }
    
    def _should_load_section(self, section_name: str, context: Dict[str, Any]) -> bool:
        """Check if section should be loaded based on context predicates"""
        
        if section_name == "git_rules":
            return self.context_predicates["git_rules"]()
        
        if section_name == "tool_guidance" and context.get("available_tools"):
            return True
        
        if section_name == "quant_rules":
            return self.context_predicates["trading_mode"]() or self.context_predicates["research_mode"]()
        
        # Default: load if content exists
        return bool(self.prompt_sections[section_name])
    
    def _has_git_repository(self) -> bool:
        """Check if git repository exists"""
        return os.path.exists(".git")
    
    def _has_high_risk_operations(self) -> bool:
        """Check if high-risk operations are planned"""
        # This would check context for planned high-risk operations
        return False  # Simplified for now
    
    def _is_research_mode(self) -> bool:
        """Check if in research mode"""
        return os.path.exists("data") and os.path.exists("research_cache.json")
    
    def _is_trading_mode(self) -> bool:
        """Check if in trading mode"""
        return os.path.exists("strategy.py") and os.path.exists("backtest_runner.py")
    
    def _generate_context_injection(self, context: Dict[str, Any]) -> str:
        """Generate dynamic context injection"""
        injection_parts = []
        
        # Iteration context
        if "iteration" in context:
            injection_parts.append(f"## Current Iteration\nIteration: {context['iteration']}")
        
        # Performance context
        if "current_score" in context:
            injection_parts.append(f"## Current Performance\nScore: {context['current_score']:.3f}")
        
        # Recent experiments
        if "recent_experiments" in context:
            injection_parts.append("## Recent Experiments")
            for i, exp in enumerate(context["recent_experiments"][-3:], 1):
                injection_parts.append(f"{i}. {exp.get('hypothesis', 'No hypothesis')} (Score: {exp.get('score', 'N/A')})")
        
        # Available tools
        if "available_tools" in context:
            injection_parts.append("## Available Tools")
            tools = []
            for t in context["available_tools"]:
                if isinstance(t, dict):
                    tools.append(t.get("tool_name", t.get("name", str(t))))
                else:
                    tools.append(str(t))
            injection_parts.append(", ".join(tools))
        
        return "\n\n".join(injection_parts)
    
    def _generate_schema_gating_info(self, subagent_type: str) -> str:
        """Generate schema gating information"""
        if subagent_type == "planner":
            return "## Tool Access\nYou have access to read-only tools for planning and analysis."
        elif subagent_type == "executor":
            return "## Tool Access\nYou have access to execution tools for strategy implementation."
        elif subagent_type == "analyzer":
            return "## Tool Access\nYou have access to analysis tools for result evaluation."
        else:
            return "## Tool Access\nYou have access to all available tools."
    
    def _generate_system_reminders(self, context: Dict[str, Any]) -> List[str]:
        """Generate system reminders based on triggers (per OPENDEV paper)"""
        reminders = []
        
        for trigger_name, trigger_func in self.reminder_triggers.items():
            reminder = trigger_func(context)
            if reminder:
                reminders.append(reminder)
        
        # Store reminders for tracking
        self.system_reminders.extend(reminders)
        
        return reminders
    
    def _check_incomplete_todos(self, context: Dict[str, Any]) -> Optional[str]:
        """Check for incomplete todos and generate reminder"""
        # This would check for incomplete tasks
        incomplete_tasks = context.get("incomplete_tasks", [])
        if incomplete_tasks:
            return f"⚠️ SYSTEM REMINDER: You have {len(incomplete_tasks)} incomplete tasks that need attention."
        return None
    
    def _check_high_risk_operations(self, context: Dict[str, Any]) -> Optional[str]:
        """Check for high-risk operations and generate reminder"""
        high_risk_ops = context.get("high_risk_operations", [])
        if high_risk_ops:
            return f"⚠️ SYSTEM REMINDER: {len(high_risk_ops)} high-risk operations planned. Extra caution required."
        return None
    
    def _check_context_pressure(self, context: Dict[str, Any]) -> Optional[str]:
        """Check context pressure and generate reminder"""
        context_usage = context.get("context_usage_percent", 0)
        if context_usage > 80:
            return f"⚠️ SYSTEM REMINDER: Context usage at {context_usage:.1f}%. Consider concise responses."
        return None
    
    def _check_iteration_milestone(self, context: Dict[str, Any]) -> Optional[str]:
        """Check iteration milestones and generate reminder"""
        iteration = context.get("iteration", 0)
        if iteration > 0 and iteration % 10 == 0:
            return f"🎯 SYSTEM REMINDER: Milestone reached - {iteration} iterations completed. Review progress."
        return None
    
    def _check_performance_decline(self, context: Dict[str, Any]) -> Optional[str]:
        """Check for performance decline and generate reminder"""
        recent_scores = context.get("recent_scores", [])
        if len(recent_scores) >= 3:
            avg_recent = sum(recent_scores[-3:]) / 3
            if context.get("current_score", 0) < avg_recent * 0.8:
                return f"⚠️ SYSTEM REMINDER: Performance declining. Consider strategy adjustment."
        return None
    
    def _assemble_prompt(self, components: Dict[str, Any], prompt_type: str) -> str:
        """Assemble final prompt from components"""
        
        prompt_parts = []
        
        # Base constitution
        if components["base_constitution"]:
            prompt_parts.append(components["base_constitution"])
        
        # Dynamic sections
        for section in components["dynamic_sections"]:
            if section["content"]:
                prompt_parts.append(f"\n## {section['name'].title().replace('_', ' ')}\n{section['content']}")
        
        # Context injection
        if components["context_injection"]:
            prompt_parts.append(f"\n## Dynamic Context\n{components['context_injection']}")
        
        # Schema gating info
        if components["schema_gating"]:
            prompt_parts.append(f"\n{components['schema_gating']}")
        
        # System reminders (injected as user messages per OPENDEV paper)
        if components["system_reminders"]:
            prompt_parts.append(f"\n## System Reminders\n{chr(10).join(components['system_reminders'])}")
        
        # Prompt type specific additions
        if prompt_type == "thinking":
            prompt_parts.append("\n## Thinking Phase Instructions\nGenerate reasoning trace WITHOUT using any tools. Focus on analysis and planning.")
        elif prompt_type == "reasoning":
            prompt_parts.append("\n## Reasoning Phase Instructions\nBased on your thinking trace, decide what tools to use and execute the plan.")
            prompt_parts.append("\nCRITICAL: You MUST output tool calls in JSON formatting within a code block. Example:\n```json\n[\n  {\"tool_name\": \"search_research\", \"parameters\": {\"query\": \"momentum strategy\"}}\n]\n```")
        
        return "\n".join(prompt_parts)
    
    def inject_system_reminder(self, reminder: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Inject a system reminder as user message (per OPENDEV paper)"""
        
        reminder_entry = {
            "reminder": reminder,
            "timestamp": datetime.now().isoformat(),
            "context": context
        }
        
        self.system_reminders.append(reminder_entry)
        
        return {
            "user_message": f"⚠️ SYSTEM REMINDER: {reminder}",
            "reminder_injected": True,
            "timestamp": reminder_entry["timestamp"]
        }
    
    def get_reminder_statistics(self) -> Dict[str, Any]:
        """Get system reminder statistics"""
        return {
            "total_reminders": len(self.system_reminders),
            "reminder_types": self._count_reminder_types(),
            "recent_reminders": self.system_reminders[-5:],
            "active_triggers": len([t for t in self.reminder_triggers.keys() if any(self.reminder_triggers[t]({"test": True}) for _ in [1])])
        }
    
    def _count_reminder_types(self) -> Dict[str, int]:
        """Count reminder types"""
        type_counts = {}
        for reminder in self.system_reminders:
            reminder_text = reminder.get("reminder", "")
            if "incomplete" in reminder_text.lower():
                type_counts["incomplete_todos"] = type_counts.get("incomplete_todos", 0) + 1
            elif "high risk" in reminder_text.lower():
                type_counts["high_risk"] = type_counts.get("high_risk", 0) + 1
            elif "context" in reminder_text.lower():
                type_counts["context_pressure"] = type_counts.get("context_pressure", 0) + 1
            elif "milestone" in reminder_text.lower():
                type_counts["milestone"] = type_counts.get("milestone", 0) + 1
            elif "performance" in reminder_text.lower():
                type_counts["performance"] = type_counts.get("performance", 0) + 1
        return type_counts
    
    def create_prompt_sections(self):
        """Create default prompt section files"""
        prompts_dir = Path("prompts")
        prompts_dir.mkdir(exist_ok=True)
        
        sections = {
            "identity.md": """
# Agent Identity

You are a specialized AI agent designed for quantitative trading research.

## Core Capabilities
- Strategy development and optimization
- Risk management and validation
- Performance analysis and reporting

## Primary Objective
Maximize risk-adjusted returns through systematic strategy evolution.
""",
            "safety_policy.md": """
# Safety Policy

## Critical Constraints
- No position sizes > 1.0
- No look-ahead bias in calculations
- All strategies must be backtested
- Risk limits must be enforced

## Validation Requirements
- Syntax validation for all code
- Performance verification
- Risk assessment before deployment
""",
            "tool_guidance.md": """
# Tool Guidance

## Research Tools
- search_research: Find academic papers
- analyze_data: Process market data
- validate_hypothesis: Test assumptions

## Execution Tools
- generate_strategy_code: Create trading logic
- run_backtest: Validate strategy performance
- optimize_parameters: Fine-tune strategy

## Analysis Tools
- analyze_results: Evaluate performance
- compare_strategies: Benchmark alternatives
- generate_report: Create documentation
""",
            "quant_rules.md": """
# Quantitative Rules

## Market Data Requirements
- Use only historical data (no future information)
- Ensure proper data validation
- Account for transaction costs and slippage

## Strategy Constraints
- Vectorized operations only
- No look-ahead bias
- Proper risk management
- Realistic assumptions
""",
            "git_rules.md": """
# Git Rules

## Version Control
- Commit strategy changes with descriptive messages
- Tag important milestones
- Maintain clean history

## Collaboration
- Document strategy rationale
- Share performance results
- Review before merging changes
"""
        }
        
        for filename, content in sections.items():
            file_path = prompts_dir / filename
            if not file_path.exists():
                with open(file_path, "w") as f:
                    f.write(content)

if __name__ == "__main__":
    # Test the modular prompt composer
    composer = PromptComposer()
    
    # Create prompt sections if they don't exist
    composer.create_prompt_sections()
    
    # Test prompt composition
    context = {
        "iteration": 5,
        "current_score": 1.2,
        "recent_experiments": [
            {"hypothesis": "Test momentum", "score": 1.1},
            {"hypothesis": "Test mean reversion", "score": 0.9}
        ],
        "available_tools": ["search_research", "generate_strategy_code"],
        "context_usage_percent": 85
    }
    
    result = composer.compose_prompt("reasoning", context, "executor")
    
    print("Prompt Composition Result:")
    print(f"- Sections loaded: {result['sections_loaded']}")
    print(f"- System reminders: {result['system_reminders_count']}")
    print(f"- Subagent type: {result['subagent_type']}")
    print(f"- Prompt length: {len(result['prompt'])} characters")
    
    print("\nReminder Statistics:", composer.get_reminder_statistics())
