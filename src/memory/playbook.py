"""
SQLite Playbook for Dual-Memory System (OPENDEV architecture)
"""
import sqlite3
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import re

class Playbook:
    """SQLite-based dual-memory system for storing successful strategy patterns"""
    
    def __init__(self, db_path: str = "experiments/database/playbook.db"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()
        
        # Semantic similarity cache
        self.similarity_cache = {}
        self.embedding_cache = {}
    
    def _initialize_database(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_hash TEXT UNIQUE NOT NULL,
                    hypothesis TEXT NOT NULL,
                    strategy_code TEXT NOT NULL,
                    performance_metrics TEXT NOT NULL,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    embedding TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_pattern_hash TEXT,
                    child_pattern_hash TEXT,
                    relationship_type TEXT,
                    similarity_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_pattern_hash) REFERENCES strategy_patterns(pattern_hash),
                    FOREIGN KEY (child_pattern_hash) REFERENCES strategy_patterns(pattern_hash)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_contexts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_hash TEXT,
                    context_type TEXT,
                    context_data TEXT,
                    performance_value REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pattern_hash) REFERENCES strategy_patterns(pattern_hash)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_type TEXT,
                    patterns_accessed INTEGER,
                    cache_hits INTEGER,
                    response_time_ms REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pattern_hash ON strategy_patterns(pattern_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_success_rate ON strategy_patterns(success_rate)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON strategy_patterns(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tags ON strategy_patterns(tags)")
            
            conn.commit()
    
    def store_pattern(self, hypothesis: str, strategy_code: str, 
                      performance_metrics: Dict[str, Any], 
                      tags: List[str] = None) -> str:
        """Store a successful strategy pattern in the playbook"""
        
        # Generate pattern hash
        pattern_content = f"{hypothesis}|{strategy_code}"
        pattern_hash = hashlib.md5(pattern_content.encode()).hexdigest()
        
        # Generate simple embedding (keyword-based for now)
        embedding = self._generate_embedding(hypothesis + " " + strategy_code)
        
        # Calculate success rate from metrics
        success_rate = self._calculate_success_rate(performance_metrics)
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO strategy_patterns 
                    (pattern_hash, hypothesis, strategy_code, performance_metrics, tags, success_rate, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern_hash,
                    hypothesis,
                    strategy_code,
                    json.dumps(performance_metrics),
                    json.dumps(tags or []),
                    success_rate,
                    json.dumps(embedding)
                ))
                
                # Store performance contexts
                for metric_name, metric_value in performance_metrics.items():
                    if isinstance(metric_value, (int, float)):
                        conn.execute("""
                            INSERT INTO performance_contexts 
                            (pattern_hash, context_type, context_data, performance_value)
                            VALUES (?, ?, ?, ?)
                        """, (
                            pattern_hash,
                            metric_name,
                            json.dumps({"metric": metric_name}),
                            metric_value
                        ))
                
                conn.commit()
                print(f"[PLAYBOOK] Stored pattern {pattern_hash[:8]} with success rate {success_rate:.2f}")
                return pattern_hash
                
            except sqlite3.Error as e:
                print(f"[PLAYBOOK] Error storing pattern: {e}")
                return None
    
    def find_similar_patterns(self, query: str, max_results: int = 5, 
                            min_similarity: float = 0.3) -> List[Dict[str, Any]]:
        """Find patterns similar to query using semantic similarity"""
        
        start_time = datetime.now()
        
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # Get all patterns with embeddings
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT pattern_hash, hypothesis, strategy_code, performance_metrics, 
                       tags, success_rate, usage_count, created_at, embedding
                FROM strategy_patterns 
                WHERE embedding IS NOT NULL
                ORDER BY success_rate DESC
            """)
            
            patterns = cursor.fetchall()
        
        # Calculate similarities
        similar_patterns = []
        cache_hits = 0
        
        for pattern in patterns:
            pattern_hash, hypothesis, strategy_code, performance_metrics, tags, success_rate, usage_count, created_at, embedding_json = pattern
            
            # Check cache first
            cache_key = f"{query}|{pattern_hash}"
            if cache_key in self.similarity_cache:
                similarity = self.similarity_cache[cache_key]
                cache_hits += 1
            else:
                try:
                    pattern_embedding = json.loads(embedding_json)
                    similarity = self._calculate_similarity(query_embedding, pattern_embedding)
                    self.similarity_cache[cache_key] = similarity
                except:
                    similarity = 0.0
            
            if similarity >= min_similarity:
                similar_patterns.append({
                    "pattern_hash": pattern_hash,
                    "hypothesis": hypothesis,
                    "strategy_code": strategy_code,
                    "performance_metrics": json.loads(performance_metrics),
                    "tags": json.loads(tags) if tags else [],
                    "success_rate": success_rate,
                    "usage_count": usage_count,
                    "created_at": created_at,
                    "similarity": similarity
                })
        
        # Sort by similarity and success rate
        similar_patterns.sort(key=lambda x: (x["similarity"], x["success_rate"]), reverse=True)
        
        # Update usage stats
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        self._log_usage_stats("find_similar_patterns", len(similar_patterns), cache_hits, response_time)
        
        return similar_patterns[:max_results]
    
    def get_best_patterns(self, metric: str = "sharpe_ratio", 
                         min_success_rate: float = 0.5, 
                         max_results: int = 10) -> List[Dict[str, Any]]:
        """Get best performing patterns for a specific metric"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT pattern_hash, hypothesis, strategy_code, performance_metrics,
                       tags, success_rate, usage_count, created_at
                FROM strategy_patterns 
                WHERE success_rate >= ?
                ORDER BY success_rate DESC, usage_count DESC
                LIMIT ?
            """, (min_success_rate, max_results))
            
            patterns = []
            for row in cursor.fetchall():
                pattern_hash, hypothesis, strategy_code, performance_metrics, tags, success_rate, usage_count, created_at = row
                
                # Extract specific metric
                metrics = json.loads(performance_metrics)
                metric_value = metrics.get(metric, 0.0)
                
                patterns.append({
                    "pattern_hash": pattern_hash,
                    "hypothesis": hypothesis,
                    "strategy_code": strategy_code,
                    "performance_metrics": metrics,
                    "tags": json.loads(tags) if tags else [],
                    "success_rate": success_rate,
                    "usage_count": usage_count,
                    "created_at": created_at,
                    metric: metric_value
                })
            
            # Sort by specific metric
            patterns.sort(key=lambda x: x[metric], reverse=True)
            return patterns
    
    def get_pattern_by_hash(self, pattern_hash: str) -> Optional[Dict[str, Any]]:
        """Get a specific pattern by its hash"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT pattern_hash, hypothesis, strategy_code, performance_metrics,
                       tags, success_rate, usage_count, created_at
                FROM strategy_patterns 
                WHERE pattern_hash = ?
            """, (pattern_hash,))
            
            row = cursor.fetchone()
            if row:
                pattern_hash, hypothesis, strategy_code, performance_metrics, tags, success_rate, usage_count, created_at = row
                
                return {
                    "pattern_hash": pattern_hash,
                    "hypothesis": hypothesis,
                    "strategy_code": strategy_code,
                    "performance_metrics": json.loads(performance_metrics),
                    "tags": json.loads(tags) if tags else [],
                    "success_rate": success_rate,
                    "usage_count": usage_count,
                    "created_at": created_at
                }
        
        return None
    
    def update_pattern_usage(self, pattern_hash: str, success: bool = True):
        """Update pattern usage statistics"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Increment usage count
            conn.execute("""
                UPDATE strategy_patterns 
                SET usage_count = usage_count + 1
                WHERE pattern_hash = ?
            """, (pattern_hash,))
            
            # Update success rate (exponential moving average)
            cursor = conn.execute("""
                SELECT success_rate FROM strategy_patterns WHERE pattern_hash = ?
            """, (pattern_hash,))
            
            row = cursor.fetchone()
            if row:
                current_success_rate = row[0]
                new_success_rate = 0.9 * current_success_rate + 0.1 * (1.0 if success else 0.0)
                
                conn.execute("""
                    UPDATE strategy_patterns 
                    SET success_rate = ?
                    WHERE pattern_hash = ?
                """, (new_success_rate, pattern_hash))
            
            conn.commit()
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate simple keyword-based embedding"""
        # Normalize text
        text = text.lower()
        
        # Extract keywords (simple approach for now)
        keywords = re.findall(r'\b(momentum|mean.*reversion|volatility|trend|breakout|rsi|macd|bollinger|atr|sharpe|drawdown|return|risk)\b', text)
        
        # Create simple embedding based on keyword presence
        all_keywords = ['momentum', 'mean_reversion', 'volatility', 'trend', 'breakout', 'rsi', 'macd', 'bollinger', 'atr', 'sharpe', 'drawdown', 'return', 'risk']
        embedding = [1.0 if kw in keywords else 0.0 for kw in all_keywords]
        
        return embedding
    
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between embeddings"""
        if len(embedding1) != len(embedding2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _calculate_success_rate(self, performance_metrics: Dict[str, Any]) -> float:
        """Calculate success rate from performance metrics"""
        
        # Simple success calculation based on Sharpe ratio
        sharpe_ratio = performance_metrics.get("sharpe_ratio", 0.0)
        max_drawdown = performance_metrics.get("max_drawdown", 1.0)
        total_return = performance_metrics.get("total_return", 0.0)
        
        # Success criteria
        success_score = 0.0
        
        # Sharpe ratio component (40% weight)
        if sharpe_ratio > 1.5:
            success_score += 0.4
        elif sharpe_ratio > 1.0:
            success_score += 0.3
        elif sharpe_ratio > 0.5:
            success_score += 0.2
        elif sharpe_ratio > 0.0:
            success_score += 0.1
        
        # Drawdown component (30% weight)
        if max_drawdown < 0.1:
            success_score += 0.3
        elif max_drawdown < 0.2:
            success_score += 0.2
        elif max_drawdown < 0.3:
            success_score += 0.1
        
        # Return component (30% weight)
        if total_return > 0.2:
            success_score += 0.3
        elif total_return > 0.1:
            success_score += 0.2
        elif total_return > 0.05:
            success_score += 0.1
        
        return min(success_score, 1.0)
    
    def _log_usage_stats(self, query_type: str, patterns_accessed: int, 
                        cache_hits: int, response_time_ms: float):
        """Log usage statistics for performance monitoring"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO memory_usage_stats 
                (query_type, patterns_accessed, cache_hits, response_time_ms)
                VALUES (?, ?, ?, ?)
            """, (query_type, patterns_accessed, cache_hits, response_time_ms))
            conn.commit()
    
    def get_playbook_statistics(self) -> Dict[str, Any]:
        """Get comprehensive playbook statistics"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Basic counts
            cursor = conn.execute("SELECT COUNT(*) FROM strategy_patterns")
            total_patterns = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT AVG(success_rate) FROM strategy_patterns")
            avg_success_rate = cursor.fetchone()[0] or 0.0
            
            cursor = conn.execute("SELECT SUM(usage_count) FROM strategy_patterns")
            total_usage = cursor.fetchone()[0] or 0
            
            # Performance stats
            cursor = conn.execute("""
                SELECT AVG(response_time_ms), COUNT(*) 
                FROM memory_usage_stats 
                WHERE timestamp > datetime('now', '-1 hour')
            """)
            recent_perf = cursor.fetchone()
            avg_response_time = recent_perf[0] or 0.0
            recent_queries = recent_perf[1] or 0
            
            # Best patterns
            cursor = conn.execute("""
                SELECT hypothesis, success_rate 
                FROM strategy_patterns 
                ORDER BY success_rate DESC 
                LIMIT 3
            """)
            top_patterns = cursor.fetchall()
            
            # Cache statistics
            cache_size = len(self.similarity_cache)
            cache_hit_rate = 0.0
            if recent_queries > 0:
                cursor = conn.execute("""
                    SELECT SUM(cache_hits) 
                    FROM memory_usage_stats 
                    WHERE timestamp > datetime('now', '-1 hour')
                """)
                total_cache_hits = cursor.fetchone()[0] or 0
                cache_hit_rate = total_cache_hits / max(recent_queries, 1)
        
        return {
            "total_patterns": total_patterns,
            "average_success_rate": avg_success_rate,
            "total_usage": total_usage,
            "cache_size": cache_size,
            "cache_hit_rate": cache_hit_rate,
            "avg_response_time_ms": avg_response_time,
            "recent_queries": recent_queries,
            "top_patterns": [{"hypothesis": h, "success_rate": s} for h, s in top_patterns]
        }
    
    def export_patterns(self, file_path: str, min_success_rate: float = 0.5):
        """Export patterns to JSON file"""
        
        patterns = self.get_best_patterns(min_success_rate=min_success_rate, max_results=1000)
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_patterns": len(patterns),
            "min_success_rate": min_success_rate,
            "patterns": patterns
        }
        
        with open(file_path, "w") as f:
            json.dump(export_data, f, indent=2)
        
        print(f"[PLAYBOOK] Exported {len(patterns)} patterns to {file_path}")
    
    def import_patterns(self, file_path: str):
        """Import patterns from JSON file"""
        
        try:
            with open(file_path, "r") as f:
                import_data = json.load(f)
            
            imported_count = 0
            for pattern in import_data.get("patterns", []):
                pattern_hash = self.store_pattern(
                    pattern["hypothesis"],
                    pattern["strategy_code"],
                    pattern["performance_metrics"],
                    pattern.get("tags", [])
                )
                if pattern_hash:
                    imported_count += 1
            
            print(f"[PLAYBOOK] Imported {imported_count} patterns from {file_path}")
            
        except Exception as e:
            print(f"[PLAYBOOK] Error importing patterns: {e}")

if __name__ == "__main__":
    # Test the playbook system
    playbook = Playbook()
    
    # Test storing a pattern
    test_hypothesis = "Use momentum indicator with volatility adjustment"
    test_code = """
    signals = (data['Close'] > data['Close'].rolling(20).mean()).astype(int)
    volatility_adj = signals * (1 / data['volatility'].rolling(10).mean())
    """
    test_metrics = {
        "sharpe_ratio": 1.2,
        "max_drawdown": 0.15,
        "total_return": 0.18,
        "win_rate": 0.55
    }
    
    pattern_hash = playbook.store_pattern(test_hypothesis, test_code, test_metrics, ["momentum", "volatility"])
    print(f"Stored pattern: {pattern_hash}")
    
    # Test finding similar patterns
    similar = playbook.find_similar_patterns("momentum strategy with risk management")
    print(f"Found {len(similar)} similar patterns")
    
    # Test getting best patterns
    best = playbook.get_best_patterns("sharpe_ratio")
    print(f"Top {len(best)} patterns by Sharpe ratio")
    
    # Get statistics
    stats = playbook.get_playbook_statistics()
    print("Playbook Statistics:", stats)
