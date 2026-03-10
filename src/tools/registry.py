"""
Lazy Tool Discovery Registry for OPENDEV architecture
"""
import json
import hashlib
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from safety.guard import SafetyGuard, SubagentType

class LazyToolRegistry:
    """Tool registry with lazy discovery and schema gating"""
    
    def __init__(self):
        # All available tools (not loaded by default)
        self.all_tools = {}
        self._initialize_all_tools()
        
        # Currently loaded tools (schema)
        self.loaded_tools = {}
        self.tool_usage_stats = {}
        
        # Tool search index
        self.tool_search_index = {}
        self._build_search_index()
        
        # Safety integration
        self.safety_guard = SafetyGuard()
        
        # Discovery tracking
        self.discovery_history = []
        self.search_cache = {}
    
    def _initialize_all_tools(self):
        """Initialize all available tools (lazy loading)"""
        
        # Research tools
        self.all_tools.update({
            "search_research": {
                "name": "search_research",
                "description": "Search academic papers and research literature",
                "parameters": {
                    "query": {"type": "string", "description": "Search query for research papers"},
                    "max_papers": {"type": "integer", "description": "Maximum number of papers to return", "default": 5}
                },
                "category": "research",
                "subagent_access": [SubagentType.PLANNER, SubagentType.ANALYZER],
                "risk_level": "low",
                "handler": self._handle_search_research
            },
            "analyze_data": {
                "name": "analyze_data",
                "description": "Analyze market data and extract insights",
                "parameters": {
                    "data_source": {"type": "string", "description": "Data source to analyze"},
                    "analysis_type": {"type": "string", "description": "Type of analysis to perform"}
                },
                "category": "research",
                "subagent_access": [SubagentType.PLANNER, SubagentType.ANALYZER],
                "risk_level": "low",
                "handler": self._handle_analyze_data
            },
            "validate_hypothesis": {
                "name": "validate_hypothesis",
                "description": "Validate trading hypothesis against historical data",
                "parameters": {
                    "hypothesis": {"type": "string", "description": "Hypothesis to validate"},
                    "test_period": {"type": "string", "description": "Period for validation", "default": "1y"}
                },
                "category": "research",
                "subagent_access": [SubagentType.PLANNER],
                "risk_level": "low",
                "handler": self._handle_validate_hypothesis
            }
        })
        
        # Execution tools
        self.all_tools.update({
            "generate_strategy_code": {
                "name": "generate_strategy_code",
                "description": "Generate trading strategy code based on hypothesis",
                "parameters": {
                    "hypothesis": {"type": "string", "description": "Trading hypothesis"},
                    "position_size": {"type": "float", "description": "Position size (0.0-1.0)", "default": 0.5},
                    "risk_management": {"type": "boolean", "description": "Include risk management", "default": True}
                },
                "category": "execution",
                "subagent_access": [SubagentType.EXECUTOR],
                "risk_level": "medium",
                "handler": self._handle_generate_strategy_code
            },
            "run_backtest": {
                "name": "run_backtest",
                "description": "Run backtest on trading strategy",
                "parameters": {
                    "strategy_code": {"type": "string", "description": "Strategy code to backtest"},
                    "start_date": {"type": "string", "description": "Backtest start date"},
                    "end_date": {"type": "string", "description": "Backtest end date"}
                },
                "category": "execution",
                "subagent_access": [SubagentType.EXECUTOR],
                "risk_level": "medium",
                "handler": self._handle_run_backtest
            },
            "optimize_parameters": {
                "name": "optimize_parameters",
                "description": "Optimize strategy parameters using grid search",
                "parameters": {
                    "strategy_code": {"type": "string", "description": "Strategy code to optimize"},
                    "parameters": {"type": "object", "description": "Parameters to optimize"},
                    "objective": {"type": "string", "description": "Optimization objective", "default": "sharpe_ratio"}
                },
                "category": "execution",
                "subagent_access": [SubagentType.EXECUTOR],
                "risk_level": "medium",
                "handler": self._handle_optimize_parameters
            }
        })
        
        # Analysis tools
        self.all_tools.update({
            "analyze_results": {
                "name": "analyze_results",
                "description": "Analyze backtest results and performance metrics",
                "parameters": {
                    "results": {"type": "object", "description": "Backtest results to analyze"},
                    "focus_areas": {"type": "array", "description": "Areas to focus on", "default": ["risk", "returns"]}
                },
                "category": "analysis",
                "subagent_access": [SubagentType.ANALYZER],
                "risk_level": "low",
                "handler": self._handle_analyze_results
            },
            "compare_strategies": {
                "name": "compare_strategies",
                "description": "Compare multiple strategies side by side",
                "parameters": {
                    "strategies": {"type": "array", "description": "List of strategies to compare"},
                    "metrics": {"type": "array", "description": "Metrics to compare", "default": ["sharpe_ratio", "max_drawdown"]}
                },
                "category": "analysis",
                "subagent_access": [SubagentType.ANALYZER],
                "risk_level": "low",
                "handler": self._handle_compare_strategies
            },
            "generate_report": {
                "name": "generate_report",
                "description": "Generate comprehensive strategy report",
                "parameters": {
                    "strategy_data": {"type": "object", "description": "Strategy performance data"},
                    "report_type": {"type": "string", "description": "Type of report to generate", "default": "comprehensive"}
                },
                "category": "analysis",
                "subagent_access": [SubagentType.ANALYZER],
                "risk_level": "low",
                "handler": self._handle_generate_report
            }
        })
        
        # System tools (high risk)
        self.all_tools.update({
            "write_file": {
                "name": "write_file",
                "description": "Write content to a file",
                "parameters": {
                    "file_path": {"type": "string", "description": "Path to file"},
                    "content": {"type": "string", "description": "Content to write"},
                    "backup": {"type": "boolean", "description": "Create backup", "default": True}
                },
                "category": "system",
                "subagent_access": [SubagentType.FULL_ACCESS],
                "risk_level": "high",
                "handler": self._handle_write_file
            },
            "run_command": {
                "name": "run_command",
                "description": "Execute system command",
                "parameters": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30}
                },
                "category": "system",
                "subagent_access": [SubagentType.FULL_ACCESS],
                "risk_level": "high",
                "handler": self._handle_run_command
            },
            "search_tools": {
                "name": "search_tools",
                "description": "Search for available tools and their schemas",
                "parameters": {
                    "query": {"type": "string", "description": "Search query for tools"},
                    "max_results": {"type": "integer", "description": "Max tools to return", "default": 5}
                },
                "category": "meta",
                "subagent_access": [SubagentType.PLANNER, SubagentType.EXECUTOR, SubagentType.ANALYZER],
                "risk_level": "low",
                "handler": self._handle_search_tools
            }
        })
    
    def _build_search_index(self):
        """Build search index for tool discovery"""
        for tool_name, tool_info in self.all_tools.items():
            # Create searchable text
            searchable_text = f"{tool_name} {tool_info['description']} {tool_info['category']}"
            
            # Add parameter names to searchable text
            for param_name, param_info in tool_info.get("parameters", {}).items():
                searchable_text += f" {param_name} {param_info.get('description', '')}"
            
            self.tool_search_index[tool_name] = searchable_text.lower()
    
    def search_tools(self, query: str, subagent_type: SubagentType = SubagentType.FULL_ACCESS, 
                    max_results: int = 10) -> Dict[str, Any]:
        """Search for tools based on query (lazy discovery)"""
        
        # Check cache first
        cache_key = f"{query}_{subagent_type.value}_{max_results}"
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        query_lower = query.lower()
        matching_tools = []
        
        for tool_name, searchable_text in self.tool_search_index.items():
            tool_info = self.all_tools[tool_name]
            
            # Check if tool is accessible by this subagent type
            if subagent_type != SubagentType.FULL_ACCESS:
                if subagent_type not in tool_info.get("subagent_access", []):
                    continue
            
            # Simple text matching (could be enhanced with better search)
            if query_lower in searchable_text:
                # Calculate relevance score
                relevance = self._calculate_relevance(query_lower, searchable_text, tool_info)
                
                matching_tools.append({
                    "tool_name": tool_name,
                    "description": tool_info["description"],
                    "category": tool_info["category"],
                    "risk_level": tool_info["risk_level"],
                    "relevance_score": relevance,
                    "parameters": tool_info["parameters"]
                })
        
        # Sort by relevance
        matching_tools.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        result = {
            "query": query,
            "subagent_type": subagent_type.value,
            "total_matches": len(matching_tools),
            "matches": matching_tools[:max_results]
        }
        
        # Cache result
        self.search_cache[cache_key] = result
        
        # Log discovery
        self.discovery_history.append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "subagent_type": subagent_type.value,
            "matches_found": len(matching_tools),
            "tools_returned": len(result["matches"])
        })
        
        return result
    
    def _calculate_relevance(self, query: str, searchable_text: str, tool_info: Dict[str, Any]) -> float:
        """Calculate relevance score for tool matching"""
        score = 0.0
        
        # Exact name match
        if query == tool_info["name"]:
            score += 10.0
        
        # Partial name match
        if query in tool_info["name"]:
            score += 5.0
        
        # Category match
        if query in tool_info["category"]:
            score += 3.0
        
        # Description match
        if query in tool_info["description"].lower():
            score += 2.0
        
        # Parameter matches
        for param_name, param_info in tool_info.get("parameters", {}).items():
            if query in param_name.lower() or query in param_info.get("description", "").lower():
                score += 1.0
        
        return score
    
    def load_tool_schema(self, tool_name: str, subagent_type: SubagentType = SubagentType.FULL_ACCESS) -> Dict[str, Any]:
        """Load tool schema for use (lazy loading)"""
        
        if tool_name not in self.all_tools:
            return {"error": f"Tool '{tool_name}' not found"}
        
        tool_info = self.all_tools[tool_name]
        
        # Check subagent access
        if subagent_type != SubagentType.FULL_ACCESS:
            if subagent_type not in tool_info.get("subagent_access", []):
                return {"error": f"Tool '{tool_name}' not accessible by {subagent_type.value} subagent"}
        
        # Create schema for LLM
        schema = {
            "name": tool_info["name"],
            "description": tool_info["description"],
            "parameters": tool_info["parameters"],
            "category": tool_info["category"],
            "risk_level": tool_info["risk_level"]
        }
        
        # Add to loaded tools
        self.loaded_tools[tool_name] = schema
        
        return schema
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any], 
                    subagent_type: SubagentType = SubagentType.FULL_ACCESS) -> Dict[str, Any]:
        """Execute a tool with safety checks"""
        
        start_time = datetime.now()
        
        # Check if tool exists and is loaded
        if tool_name not in self.loaded_tools:
            # Try to load it
            load_result = self.load_tool_schema(tool_name, subagent_type)
            if "error" in load_result:
                return {
                    "success": False,
                    "error": load_result["error"],
                    "tool_name": tool_name
                }
        
        tool_info = self.all_tools[tool_name]
        
        # Safety check
        safety_result = self.safety_guard.defense_in_depth_check({
            "tool_name": tool_name,
            "parameters": parameters,
            "content": f"Executing {tool_name} with {parameters}"
        }, subagent_type)
        
        if not safety_result["safe"]:
            return {
                "success": False,
                "error": "Safety check failed",
                "safety_errors": safety_result["errors"],
                "tool_name": tool_name
            }
        
        # Check for approval requirement
        if safety_result["approval_required"]:
            approval_granted = self.safety_guard.request_approval({
                "tool_name": tool_name,
                "parameters": parameters
            })
            
            if not approval_granted:
                return {
                    "success": False,
                    "error": "Human approval required and not granted",
                    "tool_name": tool_name
                }
        
        # Execute the tool
        try:
            handler = tool_info["handler"]
            result = handler(parameters)
            
            # Update usage stats
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_usage_stats(tool_name, execution_time, True)
            
            return {
                "success": True,
                "result": result,
                "tool_name": tool_name,
                "execution_time": execution_time,
                "safety_passed": True
            }
            
        except Exception as e:
            # Update usage stats (failure)
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_usage_stats(tool_name, execution_time, False)
            
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name,
                "execution_time": execution_time
            }
    
    def _update_usage_stats(self, tool_name: str, execution_time: float, success: bool):
        """Update tool usage statistics"""
        if tool_name not in self.tool_usage_stats:
            self.tool_usage_stats[tool_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_execution_time": 0.0,
                "avg_execution_time": 0.0,
                "success_rate": 0.0,
                "last_used": None
            }
        
        stats = self.tool_usage_stats[tool_name]
        stats["total_calls"] += 1
        stats["total_execution_time"] += execution_time
        stats["avg_execution_time"] = stats["total_execution_time"] / stats["total_calls"]
        stats["last_used"] = datetime.now().isoformat()
        
        if success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
        
        stats["success_rate"] = stats["successful_calls"] / stats["total_calls"]
    
    def get_loaded_tools(self, subagent_type: SubagentType = SubagentType.FULL_ACCESS) -> List[str]:
        """Get list of currently loaded tools"""
        return list(self.loaded_tools.keys())
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics"""
        return {
            "total_tools_available": len(self.all_tools),
            "tools_loaded": len(self.loaded_tools),
            "discovery_history_count": len(self.discovery_history),
            "search_cache_size": len(self.search_cache),
            "tool_usage_stats": self.tool_usage_stats,
            "recent_discoveries": self.discovery_history[-10:],
            "most_used_tools": sorted(
                [(name, stats["total_calls"]) for name, stats in self.tool_usage_stats.items()],
                key=lambda x: x[1], reverse=True
            )[:5]
        }
    
    # Tool handlers (simplified implementations)
    def _handle_search_research(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search_research tool"""
        query = parameters.get("query", "")
        max_papers = parameters.get("max_papers", 5)
        
        # This would integrate with the actual research engine
        return {
            "success": True,
            "papers_found": 3,
            "papers": [
                {"title": f"Paper on {query}", "summary": "Research summary..."},
                {"title": f"Analysis of {query}", "summary": "Analysis summary..."}
            ],
            "query": query
        }
    
    def _handle_analyze_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analyze_data tool"""
        return {
            "success": True,
            "analysis_type": parameters.get("analysis_type", "basic"),
            "insights": ["Insight 1", "Insight 2"],
            "data_summary": {"rows": 1000, "columns": 10}
        }
    
    def _handle_validate_hypothesis(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle validate_hypothesis tool"""
        hypothesis = parameters.get("hypothesis", "")
        
        return {
            "success": True,
            "hypothesis": hypothesis,
            "validation_result": "PROMISING",
            "confidence": 0.75,
            "test_period": parameters.get("test_period", "1y")
        }
    
    def _handle_generate_strategy_code(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generate_strategy_code tool"""
        hypothesis = parameters.get("hypothesis", "")
        position_size = parameters.get("position_size", 0.5)
        
        # Generate simple strategy code
        code = f"""
# Strategy based on: {hypothesis}
position_size = {position_size}

# Generate signals
signals = (data['Close'] > data['Close'].rolling(20).mean()).astype(int)

# Apply position sizing
final_signals = signals * position_size
"""
        
        return {
            "success": True,
            "strategy_code": code,
            "hypothesis": hypothesis,
            "position_size": position_size
        }
    
    def _handle_run_backtest(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle run_backtest tool"""
        return {
            "success": True,
            "performance_metrics": {
                "sharpe_ratio": 1.2,
                "max_drawdown": 0.15,
                "total_return": 0.18,
                "win_rate": 0.55
            },
            "backtest_period": "2020-2023"
        }
    
    def _handle_optimize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle optimize_parameters tool"""
        return {
            "success": True,
            "best_parameters": {"lookback": 20, "threshold": 0.5},
            "best_score": 1.35,
            "optimization_trials": 100
        }
    
    def _handle_analyze_results(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analyze_results tool"""
        return {
            "success": True,
            "analysis": "Strategy shows good risk-adjusted returns",
            "recommendations": ["Consider increasing position size", "Add stop-loss mechanism"],
            "focus_areas": parameters.get("focus_areas", ["risk", "returns"])
        }
    
    def _handle_compare_strategies(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle compare_strategies tool"""
        return {
            "success": True,
            "comparison": "Strategy A outperforms Strategy B on Sharpe ratio",
            "ranking": ["Strategy A", "Strategy B"],
            "metrics": parameters.get("metrics", ["sharpe_ratio", "max_drawdown"])
        }
    
    def _handle_generate_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generate_report tool"""
        return {
            "success": True,
            "report": "Comprehensive strategy analysis report...",
            "report_type": parameters.get("report_type", "comprehensive"),
            "sections": ["Performance Summary", "Risk Analysis", "Recommendations"]
        }
    
    def _handle_write_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle write_file tool"""
        file_path = parameters.get("file_path", "")
        content = parameters.get("content", "")
        
        # In a real implementation, this would actually write the file
        return {
            "success": True,
            "file_path": file_path,
            "bytes_written": len(content),
            "backup_created": parameters.get("backup", True)
        }
    
    def _handle_run_command(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle run_command tool"""
        command = parameters.get("command", "")
        
        # In a real implementation, this would actually run the command
        return {
            "success": True,
            "command": command,
            "exit_code": 0,
            "stdout": "Command output...",
            "stderr": "",
            "execution_time": 0.5
        }

    def _handle_search_tools(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search_tools tool calling itself"""
        return self.search_tools(
            parameters.get("query", ""),
            max_results=parameters.get("max_results", 5)
        )

# Global instance
lazy_tool_registry = LazyToolRegistry()

if __name__ == "__main__":
    # Test the lazy tool registry
    registry = LazyToolRegistry()
    
    # Test tool search
    search_result = registry.search_tools("research", SubagentType.PLANNER)
    print("Search Results:", search_result["total_matches"], "tools found")
    
    # Test loading a tool
    schema = registry.load_tool_schema("search_research", SubagentType.PLANNER)
    print("Loaded schema:", schema["name"])
    
    # Test executing a tool
    result = registry.execute_tool("search_research", {"query": "momentum"}, SubagentType.PLANNER)
    print("Execution result:", result["success"])
    
    # Get usage statistics
    stats = registry.get_usage_statistics()
    print("Usage Statistics:", stats)
    print("Usage stats:", registry.get_usage_stats())
