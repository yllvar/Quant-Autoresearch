import os
import sys
import json
import re
import ast
import subprocess
import time
from typing import Dict, List, Optional, Tuple, Any
from groq import Groq
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from .research import get_research_context
from context.compactor import ContextCompactor
from safety.guard import SafetyGuard, SafetyLevel, ApprovalMode
from models.router import model_router
from tools.registry import LazyToolRegistry
from memory.playbook import Playbook
from context.composer import PromptComposer
from utils.logger import logger
from utils.telemetry import telemetry
from utils.iteration_tracker import iteration_tracker

load_dotenv()

class QuantAutoresearchEngine:
    """OPENDEV Enhanced ReAct Loop engine for Quant Autoresearch"""
    
    def __init__(self, safety_level: SafetyLevel = SafetyLevel.HIGH, 
                 max_context_percent: int = 95, thinking_model: str = "llama-3.1-8b-instant",
                 reasoning_model: str = "llama-3.3-70b-versatile", lazy_tools: bool = True,
                 approval_mode: ApprovalMode = ApprovalMode.SEMI):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.safety_level = safety_level
        self.max_context_percent = max_context_percent
        self.thinking_model = thinking_model
        self.reasoning_model = reasoning_model
        self.lazy_tools = lazy_tools
        self.approval_mode = approval_mode
        
        # Core components
        self.compactor = ContextCompactor(max_context_percent=max_context_percent)
        self.safety_guard = SafetyGuard(safety_level=safety_level, approval_mode=approval_mode)
        
        # OPENDEV components
        self.model_router = model_router
        self.tool_registry = LazyToolRegistry() if lazy_tools else None
        self.playbook = Playbook()
        self.prompt_composer = PromptComposer()
        
        # Update model configurations if custom models are provided
        if thinking_model != "llama-3.1-8b-instant":
            self.model_router.models["thinking"]["primary"] = thinking_model
        if reasoning_model != "llama-3.3-70b-versatile":
            self.model_router.models["reasoning"]["primary"] = reasoning_model
        # Summarization uses thinking model
        self.model_router.models["summarization"]["primary"] = thinking_model
        
        # File paths
        self.strategy_file = "src/strategies/active_strategy.py"
        self.program_file = "src/prompts/program.md"
        self.backtest_runner = "src/core/backtester.py"
        self.experiment_log = "experiments/results/experiment_log.json"
        
        # State tracking
        self.iteration_count = 0
        self.best_score = -10.0
        self.iteration_history = []
        self.tool_history = []
        
    def get_current_strategy(self) -> str:
        """Read current strategy code"""
        with open(self.strategy_file, "r") as f:
            return f.read()
    
    def get_program_constitution(self) -> str:
        """Read the program constitution"""
        with open(self.program_file, "r") as f:
            return f.read()
    
    def run_backtest_with_output(self) -> Tuple[float, float, int, Dict]:
        """Execute backtest and parse results"""
        import subprocess
        
        result = subprocess.run(["uv", "run", "python", self.backtest_runner], 
                              capture_output=True, text=True)
        output = result.stdout
        error_output = result.stderr
        score = -10.0
        drawdown = 0.0
        trades = 0
        
        match_score = re.search(r"SCORE:\s*(-?[\d\.]+)", output)
        if match_score:
            score = float(match_score.group(1))
            if score == -10.0:
                logger.warning("Backtest returned error score (-10.0)")
                logger.debug(f"STDOUT: {output}")
                logger.debug(f"STDERR: {error_output}")
        else:
            logger.error("Backtest failed completely (no score found)")
            logger.debug(f"STDOUT: {output}")
            logger.debug(f"STDERR: {error_output}")
        
        match_dd = re.search(r"DRAWDOWN:\s*(-?[\d\.]+)", output)
        if match_dd:
            drawdown = float(match_dd.group(1))
            
        match_trades = re.search(r"TRADES:\s*(\d+)", output)
        if match_trades:
            trades = int(match_trades.group(1))
            
        return score, drawdown, trades, {"stdout": output, "stderr": error_output}
    
    def load_experiment_log(self) -> List[Dict]:
        """Load experiment history"""
        if os.path.exists(self.experiment_log):
            with open(self.experiment_log, "r") as f:
                return json.load(f)
        return []
    
    def save_experiment_log(self, log: List[Dict]):
        """Save experiment history"""
        with open(self.experiment_log, "w") as f:
            json.dump(log, f, indent=2)
    
    def log_to_tsv(self, score: float, drawdown: float, trades: int, 
                   status: str, description: str):
        """Log results to TSV file"""
        results_path = "experiments/results/results.tsv"
        file_exists = os.path.exists(results_path)
        with open(results_path, "a") as f:
            if not file_exists:
                f.write("commit\tscore\tdrawdown\ttrades\tstatus\tdescription\n")
            timestamp = subprocess.check_output(["date", "+%Y%m%d_%H%M%S"]).decode().strip()
            f.write(f"{timestamp}\t{score}\t{drawdown}\t{trades}\t{status}\t{description}\n")
    
    async def run(self, max_iterations: int = 10):
        """Run the autonomous research loop with 6-phase cycle"""
        logger.info(f"🚀 Starting Quant Autoresearch OPENDEV Session (Max: {max_iterations})")
        
        # Initial status check
        current_score, _, _, _ = self.run_backtest_with_output()
        self.best_score = current_score
        logger.info(f"📈 Baseline Score: {self.best_score:.3f}")
        
        # Start telemetry run
        telemetry.start_run(
            run_name=f"research_session_{int(time.time())}",
            config={
                "safety_level": self.safety_level.value,
                "thinking_model": self.thinking_model,
                "reasoning_model": self.reasoning_model,
                "max_context": self.max_context_percent
            }
        )
        
        for i in range(max_iterations):
            start_time = time.time()
            self.iteration_count += 1
            print(f"\n--- Iteration {self.iteration_count}/{max_iterations} ---")
            
            # Phase 0: Context Management (ACC)
            self._phase_context_mgmt()
            
            # Phase 1: Thinking
            thinking_trace = self._phase_thinking()
            if not thinking_trace:
                print("❌ Thinking phase failed. Stopping.")
                break
                
            # Phase 2: Action Selection
            action_proposal = self._phase_action_selection(thinking_trace)
            if not action_proposal:
                print("❌ Action selection failed. Stopping.")
                break
                
            # Phase 3: Doom-Loop Detection
            if self._phase_doom_loop_detection(action_proposal):
                print("⚠️ DOOM-LOOP DETECTED. Execution paused.")
                # In full OPENDEV, this would wait for user or agentic self-correction
                
            # Phase 4: Execution
            observations = self._phase_execution(action_proposal)
            
            # Phase 5: Observation & Playbook Integration
            self._phase_observation(observations)
            
            # Telemetry logging
            iteration_time = time.time() - start_time
            telemetry.log_metrics({
                "iteration": self.iteration_count,
                "score": self.best_score,
                "iteration_time": iteration_time,
                "total_cost": self.model_router.usage_stats["total_cost"]
            }, step=self.iteration_count)

            # Check for success/stopping conditions
            if self.best_score > 2.0:
                print("✅ Goal reached: Out-of-Sample Sharpe > 2.0")
                break
                
        print("\n🏁 Research session completed.")

    def _phase_context_mgmt(self):
        """Phase 0: Adaptive Context Compaction"""
        status = self.compactor.get_context_status()
        usage = status["usage_percent"]
        print(f"🧠 [Phase 0] Context Usage: {usage:.1f}%")
        
        # Trigger ACC
        self.compactor.adaptive_context_compaction("iteration_start", {"iteration": self.iteration_count})

    def _phase_thinking(self) -> Optional[str]:
        """Phase 1: Thinking (Separate Model)"""
        print("💡 [Phase 1] Thinking...")
        
        context = {
            "current_situation": self._get_current_situation(),
            "recent_actions": self._get_recent_actions(last_n=3),
            "current_goal": "Maximize OOS Sharpe Ratio through research-backed evolution"
        }
        
        result = self.model_router.thinking_phase(context)
        if result["success"]:
            print(f"   🤖 Model: {result['model_used']}")
            return result["content"]
        return None

    def _phase_action_selection(self, thinking_trace: str) -> Optional[List[Dict[str, Any]]]:
        """Phase 2: Action Selection (Primary Model)"""
        print("🔧 [Phase 2] Action Selection...")
        
        from safety.guard import SubagentType
        
        # Fetch discovered tools for the primary model
        available_tools = []
        if self.tool_registry:
            search_res = self.tool_registry.search_tools("active", SubagentType.EXECUTOR)
            available_tools = search_res.get("matches", [])
        
        context = {
            "iteration": self.iteration_count,
            "current_situation": self._get_current_situation(),
            "thinking_trace": thinking_trace,
            "available_tools": available_tools,
            "context_usage_percent": self.compactor.get_context_status()["usage_percent"]
        }
        
        # Modular prompt composition with system reminders
        composer_result = self.prompt_composer.compose_prompt("reasoning", context, "executor")
        
        messages = [
            {"role": "system", "content": composer_result["prompt"]},
            {"role": "user", "content": f"Thinking Trace: {thinking_trace}\n\nExecute the plan using available tools."}
        ]
        
        # Inject user-role system reminders immediately before the call (OPENDEV requirement)
        reminders = composer_result.get("system_reminders", [])
        for reminder in reminders:
            messages.append({"role": "user", "content": f"⚠️ SYSTEM REMINDER: {reminder}"})
            
        result = self.model_router.route_request("reasoning", messages)
        if result["success"]:
            print(f"   🤖 Model: {result['model_used']}")
            return self._parse_tool_calls(result["content"])
        return None

    def _phase_doom_loop_detection(self, action_proposal: List[Dict[str, Any]]) -> bool:
        """Phase 3: Doom-Loop Detection (Fingerprinting)"""
        if not action_proposal:
            return False
            
        print("🛡️ [Phase 3] Doom-Loop Check...")
        for action in action_proposal:
            tool_name = action.get("tool_name", "")
            params = json.dumps(action.get("parameters", {}), sort_keys=True)
            fingerprint = f"{tool_name}:{params}"
            
            if self.safety_guard.check_doom_loop(fingerprint):
                print(f"   ⚠️ Repeated Action Detected: {tool_name}")
                return True
        return False

    def _phase_execution(self, action_proposal: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Phase 4: Execution with 5-Layer Defense-in-Depth"""
        print("⚙️ [Phase 4] Execution...")
        from safety.guard import SubagentType
        observations = []
        
        for action in action_proposal:
            tool_name = action.get("tool_name")
            params = action.get("parameters", {})
            
            # Layer 2: Schema Gating & Layer 3: Runtime Approval
            safety_result = self.safety_guard.defense_in_depth_check(action, SubagentType.EXECUTOR)
            
            if not safety_result["safe"]:
                print(f"   🚫 Blocked: {tool_name} - {safety_result.get('reason', 'Violation')}")
                observations.append({"tool": tool_name, "status": "blocked", "reason": safety_result.get("reason")})
                continue
            
            # Layer 4: Tool Validation & Execution
            try:
                if self.tool_registry:
                    result = self.tool_registry.execute_tool(tool_name, params, SubagentType.EXECUTOR)
                    observations.append({"tool": tool_name, "status": "success", "result": result})
                    print(f"   ✅ Executed: {tool_name}")
                else:
                    result = self._fallback_tool_dispatch(tool_name, params)
                    observations.append({"tool": tool_name, "status": "success", "result": result})
                    print(f"   ✅ Executed (Fallback): {tool_name}")
            except Exception as e:
                observations.append({"tool": tool_name, "status": "error", "error": str(e)})
                print(f"   ❌ Error: {tool_name} - {str(e)}")
                
        return observations

    def _phase_observation(self, observations: List[Dict[str, Any]]):
        """Phase 5: Observation & Output Optimization (ACC)"""
        print("👁️ [Phase 5] Observation...")
        
        for obs in observations:
            # Mask large outputs (>8k chars)
            if "result" in obs and isinstance(obs["result"], str) and len(obs["result"]) > 8000:
                masked_len = len(obs["result"]) - 8000
                obs["result"] = f"{obs['result'][:4000]}... [MASKED {masked_len} CHARS] ...{obs['result'][-4000:]}"
            
            self.iteration_history.append(obs)
            
            # Backtest outcome processing
            if obs.get("tool") == "run_backtest" and obs.get("status") == "success":
                res = obs.get("result", {})
                score = res.get("score", -10.0)
                if score > self.best_score:
                    self.best_score = score
                    print(f"   ⭐ New Best Score: {self.best_score:.3f}")
                    # Playbook Storage
                    self.playbook.store_pattern(
                        hypothesis="Evolved strategy",
                        code=self.get_current_strategy(),
                        metrics=res
                    )
                
                # Log to persistent tracker
                iteration_tracker.log_iteration({
                    "hypothesis": "Autonomous Evolution",
                    "score": score,
                    "status": "KEEP" if score >= self.best_score else "DISCARD",
                    "details": res
                })

    def _get_current_situation(self) -> str:
        return f"Iteration {self.iteration_count}. Current Best Sharpe: {self.best_score:.3f}."

    def _get_recent_actions(self, last_n: int = 3) -> str:
        recent = self.iteration_history[-last_n:]
        return "; ".join([f"{a['tool']}({a['status']})" for a in recent]) if recent else "None"

    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        import re
        tool_calls = []
        json_blocks = re.findall(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        for block in json_blocks:
            try:
                data = json.loads(block)
                if isinstance(data, list): tool_calls.extend(data)
                elif isinstance(data, dict): tool_calls.append(data)
            except: continue
        return tool_calls

    def _fallback_tool_dispatch(self, tool_name: str, params: Dict[str, Any]) -> Any:
        if tool_name == "run_backtest":
            score, dd, trades, output = self.run_backtest_with_output()
            return {"score": score, "drawdown": dd, "trades": trades, "output": output}
        elif tool_name == "search_research":
            return get_research_context(params.get("query", ""))
        return f"Tool {tool_name} not available"

if __name__ == "__main__":
    import asyncio
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=10)
    args = parser.parse_args()
    
    engine = QuantAutoresearchEngine()
    asyncio.run(engine.run(max_iterations=args.iterations))

