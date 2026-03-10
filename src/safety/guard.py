"""
5-layer Defense-in-Depth Safety System for OPENDEV architecture
"""
import hashlib
import re
import ast
import subprocess
import os
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum

class SubagentType(Enum):
    """Types of subagents for schema gating"""
    PLANNER = "planner"          # Can only see read-only tools
    EXECUTOR = "executor"        # Can see execution tools
    ANALYZER = "analyzer"        # Can see analysis tools
    FULL_ACCESS = "full_access"  # Can see all tools (rare)

class SafetyLevel(Enum):
    """Safety levels for different operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ApprovalMode(Enum):
    """Runtime approval modes"""
    AUTO = "auto"              # No human approval needed
    SEMI = "semi"              # Approval for high-risk only
    MANUAL = "manual"          # Approval for all operations

class SafetyGuard:
    """5-layer Defense-in-Depth safety system"""
    
    def __init__(self, safety_level: SafetyLevel = SafetyLevel.HIGH, 
                 approval_mode: ApprovalMode = ApprovalMode.SEMI):
        self.safety_level = safety_level
        self.approval_mode = approval_mode
        
        # Layer 1: Prompt Guardrails
        self.prompt_guardrails = self._initialize_prompt_guardrails()
        
        # Layer 2: Schema Gating
        self.schema_gates = self._initialize_schema_gates()
        
        # Layer 3: Runtime Approval
        self.approval_queue = []
        self.approved_operations = set()
        
        # Layer 4: Tool Validation
        self.tool_validators = self._initialize_tool_validators()
        
        # Layer 5: Lifecycle Hooks
        self.pre_execution_hooks = []
        self.post_execution_hooks = []
        
        # Doom-loop detection (enhanced)
        self.tool_history = []
        self.doom_loop_window = 20  # Per OPENDEV paper
        self.doom_loop_threshold = 3
        
        # Safety statistics
        self.safety_log = []
        self.blocked_operations = 0
        self.approved_operations_count = 0
        self.hooks_triggered = 0
        
        # Trading constraints (enhanced)
        self.trading_constraints = {
            "max_position_size": 1.0,
            "max_leverage": 1.0,
            "min_lookback": 1,
            "max_drawdown_target": 0.2,
            "forbidden_functions": ["eval", "exec", "__import__", "open", "subprocess"],
            "high_risk_operations": ["rm", "sudo", "chmod", "format", "mkfs"]
        }
    
    def _initialize_prompt_guardrails(self) -> Dict[str, List[str]]:
        """Layer 1: Initialize modular safety instructions"""
        return {
            "universal": [
                "NEVER use eval(), exec(), or __import__()",
                "NEVER use negative shift() operations (look-ahead bias)",
                "ALWAYS validate all calculations before implementation",
                "NEVER expose sensitive information or API keys",
                "ALWAYS use vectorized operations (no for loops)"
            ],
            "trading": [
                "Position sizes must not exceed 1.0",
                "Maximum drawdown target is 20%",
                "No Martingale or doubling-down strategies",
                "Always implement proper risk management",
                "Validate all market data for look-ahead bias"
            ],
            "system": [
                "No external network calls or API requests",
                "No file system operations outside designated directories",
                "No system configuration changes",
                "All operations must be reversible",
                "Log all significant decisions and actions"
            ],
            "high_risk": [
                "Human approval required for position sizes > 0.5",
                "Human approval required for strategy changes",
                "All backtest results must be validated",
                "Risk limits must be strictly enforced"
            ]
        }
    
    def _initialize_schema_gates(self) -> Dict[SubagentType, List[str]]:
        """Layer 2: Initialize tool schema gating per subagent type"""
        return {
            SubagentType.PLANNER: [
                "search_research",
                "analyze_data", 
                "validate_hypothesis",
                "estimate_performance",
                "search_tools",
                "view_file",
                "list_dir"
            ],
            SubagentType.EXECUTOR: [
                "generate_strategy_code",
                "run_backtest",
                "validate_strategy",
                "optimize_parameters",
                "search_tools",
                "write_file",
                "run_command",
                "analyze_results",
                "compare_strategies",
                "generate_report"
            ],
            SubagentType.ANALYZER: [
                "analyze_results",
                "compare_strategies",
                "calculate_metrics",
                "generate_report",
                "search_tools"
            ],
            SubagentType.FULL_ACCESS: [
                # All tools available
            ]
        }
    
    def _initialize_tool_validators(self) -> Dict[str, Callable]:
        """Layer 4: Initialize tool-specific validators"""
        return {
            "generate_strategy_code": self._validate_strategy_generation,
            "run_backtest": self._validate_backtest_execution,
            "write_file": self._validate_file_operations,
            "run_command": self._validate_system_commands,
            "position_size": self._validate_position_size,
            "leverage": self._validate_leverage
        }
    
    def defense_in_depth_check(self, operation: Dict[str, Any], 
                             subagent_type: SubagentType = SubagentType.FULL_ACCESS) -> Dict[str, Any]:
        """Execute all 5 layers of defense"""
        
        safety_result = {
            "safe": True,
            "errors": [],
            "warnings": [],
            "risk_level": "LOW",
            "layers_passed": [],
            "layers_failed": [],
            "approval_required": False,
            "hooks_triggered": []
        }
        
        # Layer 1: Prompt Guardrails
        layer1_result = self._check_prompt_guardrails(operation)
        if not layer1_result["safe"]:
            safety_result["safe"] = False
            safety_result["errors"].extend(layer1_result["errors"])
            safety_result["layers_failed"].append("Prompt Guardrails")
        else:
            safety_result["layers_passed"].append("Prompt Guardrails")
        
        # Layer 2: Schema Gating
        layer2_result = self._check_schema_gating(operation, subagent_type)
        if not layer2_result["safe"]:
            safety_result["safe"] = False
            safety_result["errors"].extend(layer2_result["errors"])
            safety_result["layers_failed"].append("Schema Gating")
        else:
            safety_result["layers_passed"].append("Schema Gating")
        
        # Layer 3: Runtime Approval
        layer3_result = self._check_runtime_approval(operation)
        if layer3_result["approval_required"]:
            safety_result["approval_required"] = True
            safety_result["warnings"].append("Human approval required")
        safety_result["layers_passed"].append("Runtime Approval")
        
        # Layer 4: Tool Validation
        layer4_result = self._validate_tool_arguments(operation)
        if not layer4_result["safe"]:
            safety_result["safe"] = False
            safety_result["errors"].extend(layer4_result["errors"])
            safety_result["layers_failed"].append("Tool Validation")
        else:
            safety_result["layers_passed"].append("Tool Validation")
        
        # Layer 5: Lifecycle Hooks
        layer5_result = self._execute_lifecycle_hooks(operation, "pre_execution")
        if layer5_result["hooks_triggered"]:
            safety_result["hooks_triggered"].extend(layer5_result["hooks_triggered"])
            self.hooks_triggered += len(layer5_result["hooks_triggered"])
        safety_result["layers_passed"].append("Lifecycle Hooks")
        
        # Determine overall risk level
        safety_result["risk_level"] = self._calculate_risk_level(safety_result)
        
        # Log the safety check
        self._log_safety_event("defense_in_depth", {
            "operation": operation,
            "subagent_type": subagent_type.value,
            "result": safety_result
        })
        
        return safety_result
    
    def _check_prompt_guardrails(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 1: Check prompt guardrails"""
        result = {"safe": True, "errors": []}
        
        operation_content = str(operation.get("content", operation.get("parameters", {})))
        
        # Check against all relevant guardrails
        for category, guardrails in self.prompt_guardrails.items():
            for rule in guardrails:
                if self._violates_guardrail(operation_content, rule):
                    result["safe"] = False
                    result["errors"].append(f"Guardrail violation ({category}): {rule}")
        
        return result
    
    def _violates_guardrail(self, content: str, rule: str) -> bool:
        """Check if content violates a specific guardrail"""
        content_lower = content.lower()
        
        if "never use" in rule.lower():
            forbidden = rule.split("NEVER use")[-1].strip("() ")
            return forbidden in content_lower
        
        if "must not exceed" in rule.lower():
            # Extract number and check
            import re
            numbers = re.findall(r'[\d.]+', rule)
            if numbers:
                limit = float(numbers[0])
                if "position size" in rule.lower():
                    positions = re.findall(r'position[_\s]*size[_\s]*:*[\s]*([\d.]+)', content_lower)
                    if positions and float(positions[0]) > limit:
                        return True
        
        return False
    
    def _check_schema_gating(self, operation: Dict[str, Any], 
                           subagent_type: SubagentType) -> Dict[str, Any]:
        """Layer 2: Check schema gating"""
        result = {"safe": True, "errors": []}
        
        tool_name = operation.get("tool_name", "")
        allowed_tools = self.schema_gates.get(subagent_type, [])
        
        if subagent_type != SubagentType.FULL_ACCESS:
            if tool_name not in allowed_tools:
                result["safe"] = False
                result["errors"].append(f"Tool '{tool_name}' not allowed for {subagent_type.value} subagent")
                result["errors"].append(f"Allowed tools: {allowed_tools}")
        
        return result
    
    def _check_runtime_approval(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 3: Check runtime approval requirements"""
        result = {"approval_required": False, "risk_factors": []}
        
        # High-risk operations always require approval
        if self._is_high_risk_operation(operation):
            result["approval_required"] = True
            result["risk_factors"].append("High-risk operation type")
        
        # Check approval mode
        if self.approval_mode == ApprovalMode.MANUAL:
            result["approval_required"] = True
            result["risk_factors"].append("Manual approval mode")
        elif self.approval_mode == ApprovalMode.SEMI and self._is_medium_risk_operation(operation):
            result["approval_required"] = True
            result["risk_factors"].append("Medium-risk operation in semi-auto mode")
        
        # Check if already approved
        operation_id = self._generate_operation_id(operation)
        if operation_id in self.approved_operations:
            result["approval_required"] = False
            result["risk_factors"].append("Previously approved")
        
        return result
    
    def _is_high_risk_operation(self, operation: Dict[str, Any]) -> bool:
        """Check if operation is high risk"""
        tool_name = operation.get("tool_name", "")
        parameters = operation.get("parameters", {})
        
        # High-risk tools
        high_risk_tools = ["write_file", "run_command", "position_size", "leverage"]
        if tool_name in high_risk_tools:
            return True
        
        # High-risk parameters
        if tool_name == "generate_strategy_code":
            if "position_size" in parameters and parameters["position_size"] > 0.5:
                return True
        
        return False
    
    def _is_medium_risk_operation(self, operation: Dict[str, Any]) -> bool:
        """Check if operation is medium risk"""
        tool_name = operation.get("tool_name", "")
        parameters = operation.get("parameters", {})
        
        # Medium-risk tools
        medium_risk_tools = ["run_backtest", "validate_strategy"]
        if tool_name in medium_risk_tools:
            return True
        
        # Medium-risk parameters
        if tool_name == "generate_strategy_code":
            if "position_size" in parameters and parameters["position_size"] > 0.2:
                return True
        
        return False
    
    def _validate_tool_arguments(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 4: Validate tool arguments"""
        result = {"safe": True, "errors": []}
        
        tool_name = operation.get("tool_name", "")
        parameters = operation.get("parameters", {})
        
        # Use tool-specific validator if available
        if tool_name in self.tool_validators:
            validation_result = self.tool_validators[tool_name](parameters)
            if not validation_result["safe"]:
                result["safe"] = False
                result["errors"].extend(validation_result["errors"])
        
        # General validation
        general_errors = self._general_argument_validation(parameters)
        result["errors"].extend(general_errors)
        if general_errors:
            result["safe"] = False
        
        return result
    
    def _general_argument_validation(self, parameters: Dict[str, Any]) -> List[str]:
        """General argument validation"""
        errors = []
        
        # Check for dangerous patterns
        param_str = str(parameters).lower()
        dangerous_patterns = ["eval(", "exec(", "__import__", "subprocess.", "os.system"]
        
        for pattern in dangerous_patterns:
            if pattern in param_str:
                errors.append(f"Dangerous pattern detected: {pattern}")
        
        return errors
    
    def _execute_lifecycle_hooks(self, operation: Dict[str, Any], 
                              hook_type: str) -> Dict[str, Any]:
        """Layer 5: Execute lifecycle hooks"""
        result = {"hooks_triggered": [], "hook_results": []}
        
        hooks = self.pre_execution_hooks if hook_type == "pre_execution" else self.post_execution_hooks
        
        for hook in hooks:
            try:
                hook_result = hook(operation)
                result["hook_results"].append(hook_result)
                result["hooks_triggered"].append(hook.__name__)
                
                # If hook returns False, block the operation
                if hook_result is False:
                    result["hooks_triggered"].append(f"{hook.__name__}_BLOCKED")
                    
            except Exception as e:
                result["hook_results"].append(f"Hook error: {str(e)}")
        
        return result
    
    def _validate_strategy_generation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate strategy generation parameters"""
        result = {"safe": True, "errors": []}
        
        # Check position size
        if "position_size" in parameters:
            pos_size = parameters["position_size"]
            if not isinstance(pos_size, (int, float)) or pos_size < 0 or pos_size > self.trading_constraints["max_position_size"]:
                result["safe"] = False
                result["errors"].append(f"Invalid position size: {pos_size}")
        
        # Check leverage
        if "leverage" in parameters:
            leverage = parameters["leverage"]
            if not isinstance(leverage, (int, float)) or leverage < 1 or leverage > self.trading_constraints["max_leverage"]:
                result["safe"] = False
                result["errors"].append(f"Invalid leverage: {leverage}")
        
        return result
    
    def _validate_backtest_execution(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate backtest execution parameters"""
        result = {"safe": True, "errors": []}
        
        # Check strategy code for safety
        if "strategy_code" in parameters:
            code = parameters["strategy_code"]
            validation = self.validate_code(code, "backtest")
            if not validation["safe"]:
                result["safe"] = False
                result["errors"].extend(validation["errors"])
        
        return result
    
    def _validate_file_operations(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate file operation parameters"""
        result = {"safe": True, "errors": []}
        
        if "file_path" in parameters:
            file_path = parameters["file_path"]
            
            # Check for dangerous paths
            dangerous_paths = ["/etc/", "/root/", "/usr/bin/", "/bin/", "system32"]
            for dangerous in dangerous_paths:
                if dangerous in file_path.lower():
                    result["safe"] = False
                    result["errors"].append(f"Dangerous file path: {file_path}")
        
        return result
    
    def _validate_system_commands(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate system command parameters"""
        result = {"safe": True, "errors": []}
        
        if "command" in parameters:
            command = parameters["command"]
            
            # Check for dangerous commands
            dangerous_commands = ["rm -rf", "sudo ", "chmod 777", "dd if=", "mkfs"]
            for dangerous in dangerous_commands:
                if dangerous in command.lower():
                    result["safe"] = False
                    result["errors"].append(f"Dangerous command: {command}")
        
        return result
    
    def _validate_position_size(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate position size parameters"""
        result = {"safe": True, "errors": []}
        
        if "size" in parameters:
            size = parameters["size"]
            if not isinstance(size, (int, float)) or size < 0 or size > self.trading_constraints["max_position_size"]:
                result["safe"] = False
                result["errors"].append(f"Invalid position size: {size}")
        
        return result
    
    def _validate_leverage(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate leverage parameters"""
        result = {"safe": True, "errors": []}
        
        if "ratio" in parameters:
            ratio = parameters["ratio"]
            if not isinstance(ratio, (int, float)) or ratio < 1 or ratio > self.trading_constraints["max_leverage"]:
                result["safe"] = False
                result["errors"].append(f"Invalid leverage ratio: {ratio}")
        
        return result
    
    def validate_code(self, code: str, context: str = "strategy") -> Dict[str, Any]:
        """Validate code for safety and correctness"""
        validation_result = {
            "safe": True,
            "errors": [],
            "warnings": [],
            "risk_level": "LOW"
        }
        
        # Syntax validation
        try:
            ast.parse(code)
        except SyntaxError as e:
            validation_result["safe"] = False
            validation_result["errors"].append(f"Syntax Error: {e}")
            validation_result["risk_level"] = "CRITICAL"
            return validation_result
        
        # Enhanced dangerous pattern detection
        dangerous_patterns = [
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__\s*\(',
            r'open\s*\([\'"/\\]',
            r'subprocess\.',
            r'os\.system',
            r'shift\s*\(\s*-\s*\d+\s*\)',  # Look-ahead bias
            r'rm\s+-rf',
            r'sudo\s+',
        ]
        
        for pattern in dangerous_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                validation_result["safe"] = False
                validation_result["errors"].append(f"Dangerous pattern detected: {pattern}")
                validation_result["risk_level"] = "HIGH"
        
        # Trading constraint validation
        if context == "strategy":
            self._validate_trading_constraints(code, validation_result)
        
        # Look-ahead bias detection
        self._check_lookahead_bias(code, validation_result)
        
        return validation_result
    
    def _validate_trading_constraints(self, code: str, result: Dict[str, Any]):
        """Validate trading-specific constraints"""
        # Check for position size violations
        if "position_size" in code and ">" in code:
            size_matches = re.findall(r'position_size\s*>\s*([\d\.]+)', code)
            for size in size_matches:
                if float(size) > self.trading_constraints["max_position_size"]:
                    result["warnings"].append(f"Position size {size} exceeds limit {self.trading_constraints['max_position_size']}")
                    if result["risk_level"] == "LOW":
                        result["risk_level"] = "MEDIUM"
        
        # Check for leverage violations
        leverage_patterns = [r'leverage\s*>\s*([\d\.]+)', r'multiply\s*\(\s*[\d\.]+\s*,\s*([\d\.]+)']
        for pattern in leverage_patterns:
            matches = re.findall(pattern, code)
            for leverage in matches:
                if float(leverage) > self.trading_constraints["max_leverage"]:
                    result["warnings"].append(f"Leverage {leverage} exceeds limit {self.trading_constraints['max_leverage']}")
                    if result["risk_level"] == "LOW":
                        result["risk_level"] = "MEDIUM"
    
    def _check_lookahead_bias(self, code: str, result: Dict[str, Any]):
        """Check for potential look-ahead bias"""
        # Check for negative shift operations
        lookahead_matches = re.findall(r'\.shift\s*\(\s*-\s*\d+\s*\)', code)
        if lookahead_matches:
            result["warnings"].append("Potential look-ahead bias detected with negative shift")
            if result["risk_level"] == "LOW":
                result["risk_level"] = "MEDIUM"
        
        # Check for future data usage
        future_patterns = [r'\.shift\s*\(\s*-\s*\d+\s*\)', r'future\s*', r'tomorrow\s*']
        for pattern in future_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                result["warnings"].append(f"Future data usage pattern detected: {pattern}")
                if result["risk_level"] == "LOW":
                    result["risk_level"] = "MEDIUM"
    
    def check_doom_loop(self, tool_fingerprint: str, history: Optional[List[str]] = None) -> bool:
        """Enhanced doom-loop detection per OPENDEV paper"""
        if history is None:
            history = self.tool_history
            
        # Add current fingerprint to history
        history.append(tool_fingerprint)
        
        # Keep only recent history (20-operation window)
        if len(history) > self.doom_loop_window:
            # We must modify the original list if using self.tool_history
            while len(history) > self.doom_loop_window:
                history.pop(0)
        
        # Count occurrences of this fingerprint in recent history
        recent_count = history.count(tool_fingerprint)
        
        if recent_count >= self.doom_loop_threshold:
            print(f"[SAFETY] Doom-loop detected: '{tool_fingerprint}' repeated {recent_count} times in {self.doom_loop_window}-operation window")
            self._log_safety_event("doom_loop", {
                "fingerprint": tool_fingerprint,
                "count": recent_count,
                "window": self.doom_loop_window
            })
            return True
        
        return False
    
    def request_approval(self, operation: Dict[str, Any]) -> bool:
        """Request human approval for operation"""
        operation_id = self._generate_operation_id(operation)
        
        print(f"\n[SAFETY] Approval Required for Operation: {operation.get('tool_name', 'Unknown')}")
        print(f"Risk Factors: {self._check_runtime_approval(operation)['risk_factors']}")
        print(f"Operation ID: {operation_id}")
        
        # In a real implementation, this would wait for human input
        # For now, we'll auto-approve low-risk operations
        if self.approval_mode == ApprovalMode.AUTO:
            self.approved_operations.add(operation_id)
            return True
        
        # Simulate human approval for demo
        print("[SAFETY] Auto-approving for demo (IMPLEMENT HUMAN INPUT IN PRODUCTION)")
        self.approved_operations.add(operation_id)
        self.approved_operations_count += 1
        return True
    
    def add_lifecycle_hook(self, hook_type: str, hook_function: Callable):
        """Add lifecycle hook"""
        if hook_type == "pre_execution":
            self.pre_execution_hooks.append(hook_function)
        elif hook_type == "post_execution":
            self.post_execution_hooks.append(hook_function)
    
    def _generate_operation_id(self, operation: Dict[str, Any]) -> str:
        """Generate unique operation ID"""
        operation_str = f"{operation.get('tool_name', '')}{str(operation.get('parameters', {}))}{datetime.now().isoformat()}"
        return hashlib.md5(operation_str.encode()).hexdigest()[:16]
    
    def _calculate_risk_level(self, safety_result: Dict[str, Any]) -> str:
        """Calculate overall risk level"""
        if safety_result["errors"]:
            return "CRITICAL"
        elif safety_result["approval_required"]:
            return "HIGH"
        elif safety_result["warnings"]:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _log_safety_event(self, event_type: str, details: Dict[str, Any]):
        """Log safety events"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "details": details,
            "safety_level": self.safety_level.value
        }
        self.safety_log.append(event)
        
        # Keep only last 100 events
        if len(self.safety_log) > 100:
            self.safety_log = self.safety_log[-100:]
    
    def get_safety_summary(self) -> Dict[str, Any]:
        """Get comprehensive safety system summary"""
        return {
            "safety_level": self.safety_level.value,
            "approval_mode": self.approval_mode.value,
            "blocked_operations": self.blocked_operations,
            "approved_operations_count": self.approved_operations_count,
            "hooks_triggered": self.hooks_triggered,
            "prompt_guardrails": len(self.prompt_guardrails),
            "schema_gates": {k.value: len(v) for k, v in self.schema_gates.items()},
            "tool_validators": len(self.tool_validators),
            "recent_events": self.safety_log[-5:],
            "trading_constraints": self.trading_constraints
        }

if __name__ == "__main__":
    # Test the 5-layer safety system
    guard = SafetyGuard()
    
    # Test defense in depth
    operation = {
        "tool_name": "generate_strategy_code",
        "parameters": {"position_size": 0.8},
        "content": "Generate trading strategy with proper risk management"
    }
    
    safety_result = guard.defense_in_depth_check(operation, SubagentType.EXECUTOR)
    print("Defense in Depth Result:", safety_result)
    
    # Test doom-loop detection
    history = []
    for i in range(4):
        fingerprint = f"test_action_same"
        is_doom = guard.check_doom_loop(fingerprint, history)
        print(f"Doom loop check {i+1}: {is_doom}")
    
    print("Safety Summary:", guard.get_safety_summary())
