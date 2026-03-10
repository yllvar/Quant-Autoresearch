"""
Basic iteration tracking utility for Quant Autoresearch
"""
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class IterationTracker:
    """Track and analyze iteration patterns and performance"""
    
    def __init__(self, log_file: str = "experiments/results/iteration_log.json"):
        self.log_file = log_file
        self.iterations = []
        self.session_start = datetime.now()
        self._load_existing_log()
    
    def _load_existing_log(self):
        """Load existing iteration log if it exists"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r") as f:
                    data = json.load(f)
                    self.iterations = data.get("iterations", [])
                    session_start_str = data.get("session_start")
                    if session_start_str:
                        self.session_start = datetime.fromisoformat(session_start_str)
            except Exception as e:
                print(f"[TRACKER] Warning: Could not load existing log: {e}")
                self.iterations = []
    
    def save_log(self):
        """Save iteration log to file"""
        try:
            data = {
                "iterations": self.iterations,
                "session_start": self.session_start.isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.log_file, "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"[TRACKER] Warning: Could not save log: {e}")
    
    def log_iteration(self, iteration_data: Dict[str, Any]):
        """Log a single iteration"""
        iteration_entry = {
            "timestamp": datetime.now().isoformat(),
            "iteration_number": len(self.iterations) + 1,
            "session_duration_minutes": (datetime.now() - self.session_start).total_seconds() / 60,
            **iteration_data
        }
        
        self.iterations.append(iteration_entry)
        
        # Keep only last 1000 iterations to prevent log bloat
        if len(self.iterations) > 1000:
            self.iterations = self.iterations[-1000:]
        
        self.save_log()
    
    def get_iteration_summary(self, last_n: int = 10) -> Dict[str, Any]:
        """Get summary of recent iterations"""
        if not self.iterations:
            return {"message": "No iterations logged yet"}
        
        recent_iterations = self.iterations[-last_n:]
        
        # Calculate basic statistics
        scores = [iter_data.get("score", 0) for iter_data in recent_iterations if iter_data.get("score") is not None]
        successful_iterations = [iter_data for iter_data in recent_iterations if iter_data.get("status") == "KEEP"]
        
        summary = {
            "total_iterations": len(recent_iterations),
            "successful_iterations": len(successful_iterations),
            "success_rate": len(successful_iterations) / len(recent_iterations),
            "average_score": sum(scores) / len(scores) if scores else 0,
            "best_score": max(scores) if scores else 0,
            "worst_score": min(scores) if scores else 0,
            "session_duration_minutes": (datetime.now() - self.session_start).total_seconds() / 60,
            "recent_iterations": recent_iterations
        }
        
        return summary
    
    def get_performance_trend(self, window_size: int = 5) -> Dict[str, Any]:
        """Analyze performance trend over time"""
        if len(self.iterations) < window_size:
            return {"message": f"Need at least {window_size} iterations for trend analysis"}
        
        # Get scores from recent iterations
        recent_scores = []
        for iter_data in self.iterations[-window_size:]:
            score = iter_data.get("score")
            if score is not None:
                recent_scores.append(score)
        
        if len(recent_scores) < 2:
            return {"message": "Not enough valid scores for trend analysis"}
        
        # Calculate trend
        first_half = recent_scores[:len(recent_scores)//2]
        second_half = recent_scores[len(recent_scores)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        trend = "improving" if second_avg > first_avg else "declining" if second_avg < first_avg else "stable"
        improvement = second_avg - first_avg
        
        return {
            "trend": trend,
            "improvement": improvement,
            "recent_average": sum(recent_scores) / len(recent_scores),
            "window_size": len(recent_scores),
            "scores": recent_scores
        }
    
    def get_hypothesis_analysis(self) -> Dict[str, Any]:
        """Analyze hypothesis patterns and effectiveness"""
        hypothesis_data = []
        
        for iter_data in self.iterations:
            hypothesis = iter_data.get("hypothesis")
            if hypothesis and iter_data.get("score") is not None:
                hypothesis_data.append({
                    "hypothesis": hypothesis,
                    "score": iter_data["score"],
                    "status": iter_data.get("status", "UNKNOWN"),
                    "iteration": iter_data["iteration_number"]
                })
        
        if not hypothesis_data:
            return {"message": "No hypothesis data available"}
        
        # Sort by score
        hypothesis_data.sort(key=lambda x: x["score"], reverse=True)
        
        # Find patterns
        successful_hypotheses = [h for h in hypothesis_data if h["status"] == "KEEP"]
        
        return {
            "total_hypotheses": len(hypothesis_data),
            "successful_hypotheses": len(successful_hypotheses),
            "success_rate": len(successful_hypotheses) / len(hypothesis_data),
            "best_hypothesis": hypothesis_data[0] if hypothesis_data else None,
            "worst_hypothesis": hypothesis_data[-1] if hypothesis_data else None,
            "top_hypotheses": hypothesis_data[:5]
        }
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get comprehensive session statistics"""
        if not self.iterations:
            return {"message": "No iterations logged yet"}
        
        total_iterations = len(self.iterations)
        session_duration = datetime.now() - self.session_start
        
        # Calculate success rates
        keep_count = sum(1 for iter_data in self.iterations if iter_data.get("status") == "KEEP")
        discard_count = sum(1 for iter_data in self.iterations if iter_data.get("status") == "DISCARD")
        crash_count = sum(1 for iter_data in self.iterations if iter_data.get("status") == "CRASH")
        
        # Calculate scores
        scores = [iter_data.get("score", 0) for iter_data in self.iterations if iter_data.get("score") is not None]
        
        return {
            "session_start": self.session_start.isoformat(),
            "session_duration_minutes": session_duration.total_seconds() / 60,
            "total_iterations": total_iterations,
            "iterations_per_hour": total_iterations / (session_duration.total_seconds() / 3600) if session_duration.total_seconds() > 0 else 0,
            "keep_count": keep_count,
            "discard_count": discard_count,
            "crash_count": crash_count,
            "success_rate": keep_count / total_iterations if total_iterations > 0 else 0,
            "crash_rate": crash_count / total_iterations if total_iterations > 0 else 0,
            "average_score": sum(scores) / len(scores) if scores else 0,
            "best_score": max(scores) if scores else 0,
            "worst_score": min(scores) if scores else 0
        }
    
    def detect_stagnation(self, window_size: int = 10, threshold: float = 0.1) -> Dict[str, Any]:
        """Detect if performance is stagnating"""
        if len(self.iterations) < window_size:
            return {"stagnating": False, "message": f"Need at least {window_size} iterations"}
        
        # Get recent scores
        recent_scores = []
        for iter_data in self.iterations[-window_size:]:
            score = iter_data.get("score")
            if score is not None:
                recent_scores.append(score)
        
        if len(recent_scores) < window_size:
            return {"stagnating": False, "message": "Not enough valid scores"}
        
        # Check variance
        score_variance = max(recent_scores) - min(recent_scores)
        stagnating = score_variance < threshold
        
        return {
            "stagnating": stagnating,
            "score_variance": score_variance,
            "threshold": threshold,
            "recent_scores": recent_scores,
            "recommendation": "Consider exploring new hypothesis areas" if stagnating else "Performance is varying normally"
        }

# Global instance
iteration_tracker = IterationTracker()

def log_iteration(iteration_data: Dict[str, Any]):
    """Convenience function to log iteration"""
    iteration_tracker.log_iteration(iteration_data)

def get_iteration_summary(last_n: int = 10) -> Dict[str, Any]:
    """Convenience function to get iteration summary"""
    return iteration_tracker.get_iteration_summary(last_n)

if __name__ == "__main__":
    # Test the iteration tracker
    tracker = IterationTracker()
    
    # Log some test iterations
    test_iterations = [
        {"hypothesis": "Test momentum strategy", "score": 1.2, "status": "KEEP"},
        {"hypothesis": "Test mean reversion", "score": 0.8, "status": "DISCARD"},
        {"hypothesis": "Test volatility targeting", "score": 1.4, "status": "KEEP"}
    ]
    
    for iteration in test_iterations:
        tracker.log_iteration(iteration)
    
    print("Iteration summary:", tracker.get_iteration_summary())
    print("Performance trend:", tracker.get_performance_trend())
    print("Session stats:", tracker.get_session_stats())
    print("Stagnation detection:", tracker.detect_stagnation())
