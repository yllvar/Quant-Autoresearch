"""
Enhanced BM25 search tool wrapper for Quant Autoresearch
"""
import sys
import os
from typing import Dict, Any, List, Optional

from core.research import get_research_context, search_arxiv, local_bm25_search

class BM25SearchTool:
    """Tool wrapper for BM25 search functionality"""
    
    def __init__(self):
        self.search_stats = {
            "total_searches": 0,
            "local_hits": 0,
            "arxiv_searches": 0,
            "errors": 0,
            "cache_hits": 0
        }
    
    def search_research(self, query: str, max_papers: int = 3, 
                      prefer_local: bool = True) -> Dict[str, Any]:
        """
        Search for academic research papers using BM25 and ArXiv
        
        Args:
            query: Search query for research papers
            max_papers: Maximum number of papers to return
            prefer_local: Whether to prefer local BM25 results first
            
        Returns:
            Dictionary with search results and metadata
        """
        self.search_stats["total_searches"] += 1
        
        try:
            # Use existing research engine functionality
            context = get_research_context(query, max_papers=max_papers)
            
            # Parse the context to extract paper information
            papers = self._parse_research_context(context)
            
            # Check if we got local BM25 hits
            if papers and any("local_cache" in str(paper) for paper in papers):
                self.search_stats["local_hits"] += 1
            else:
                self.search_stats["arxiv_searches"] += 1
            
            return {
                "success": True,
                "query": query,
                "papers": papers,
                "context": context,
                "papers_found": len(papers),
                "search_type": "local_bm25" if self.search_stats["local_hits"] > 0 else "arxiv"
            }
            
        except Exception as e:
            self.search_stats["errors"] += 1
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def _parse_research_context(self, context: str) -> List[Dict[str, Any]]:
        """Parse research context to extract structured paper information"""
        papers = []
        
        lines = context.split('\n')
        current_paper = {}
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("PAPER:"):
                if current_paper:
                    papers.append(current_paper)
                current_paper = {"title": line[6:].strip()}
            
            elif line.startswith("SUMMARY:"):
                current_paper["summary"] = line[8:].strip()
            
            elif line.startswith("URL:"):
                current_paper["url"] = line[4:].strip()
            
            elif line.startswith("(") and line.endswith(")"):
                # Extract publication date
                current_paper["published"] = line[1:-1]
        
        # Add the last paper if exists
        if current_paper:
            papers.append(current_paper)
        
        return papers
    
    def search_similar_strategies(self, strategy_description: str, 
                                 max_results: int = 5) -> Dict[str, Any]:
        """
        Search for similar trading strategies in research corpus
        
        Args:
            strategy_description: Description of the trading strategy
            max_results: Maximum number of similar strategies to return
            
        Returns:
            Dictionary with similar strategies and relevance scores
        """
        # Create search query from strategy description
        query = self._create_strategy_query(strategy_description)
        
        # Perform search
        result = self.search_research(query, max_papers=max_results)
        
        if result["success"]:
            # Add strategy-specific analysis
            papers = result["papers"]
            similar_strategies = []
            
            for paper in papers:
                strategy_info = {
                    "title": paper.get("title", ""),
                    "summary": paper.get("summary", ""),
                    "relevance_score": self._calculate_relevance(strategy_description, paper),
                    "url": paper.get("url", ""),
                    "published": paper.get("published", "")
                }
                similar_strategies.append(strategy_info)
            
            # Sort by relevance
            similar_strategies.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            result["similar_strategies"] = similar_strategies
            result["query_used"] = query
        
        return result
    
    def _create_strategy_query(self, strategy_description: str) -> str:
        """Create optimized search query from strategy description"""
        # Extract key terms from strategy description
        strategy_terms = []
        
        # Common trading strategy keywords
        trading_keywords = [
            "momentum", "mean reversion", "arbitrage", "trend following",
            "volatility", "pairs trading", "statistical arbitrage",
            "machine learning", "neural network", "random forest",
            "support vector", "deep learning", "reinforcement learning"
        ]
        
        # Technical indicators
        indicator_keywords = [
            "moving average", "RSI", "MACD", "Bollinger Bands",
            "ATR", "stochastic", "Williams %R", "CCI"
        ]
        
        description_lower = strategy_description.lower()
        
        # Find matching keywords
        for keyword in trading_keywords + indicator_keywords:
            if keyword in description_lower:
                strategy_terms.append(keyword)
        
        # Add original description terms if no keywords found
        if not strategy_terms:
            # Extract important words (simple approach)
            words = description_lower.split()
            strategy_terms = [word for word in words if len(word) > 3][:5]
        
        return " ".join(strategy_terms) if strategy_terms else strategy_description
    
    def _calculate_relevance(self, strategy_description: str, paper: Dict[str, Any]) -> float:
        """Calculate relevance score between strategy and paper"""
        description_words = set(strategy_description.lower().split())
        
        # Get paper text
        paper_text = f"{paper.get('title', '')} {paper.get('summary', '')}".lower()
        paper_words = set(paper_text.split())
        
        # Calculate Jaccard similarity
        intersection = description_words.intersection(paper_words)
        union = description_words.union(paper_words)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get search statistics and performance metrics"""
        total = self.search_stats["total_searches"]
        
        return {
            "total_searches": total,
            "local_hit_rate": self.search_stats["local_hits"] / max(total, 1),
            "arxiv_search_rate": self.search_stats["arxiv_searches"] / max(total, 1),
            "error_rate": self.search_stats["errors"] / max(total, 1),
            "cache_efficiency": self.search_stats["cache_hits"] / max(total, 1),
            "stats": self.search_stats
        }
    
    def reset_statistics(self):
        """Reset search statistics"""
        self.search_stats = {
            "total_searches": 0,
            "local_hits": 0,
            "arxiv_searches": 0,
            "errors": 0,
            "cache_hits": 0
        }

# Global instance for easy access
bm25_tool = BM25SearchTool()

def search_research(query: str, max_papers: int = 3) -> Dict[str, Any]:
    """Convenience function for research search"""
    return bm25_tool.search_research(query, max_papers)

def search_similar_strategies(strategy_description: str, max_results: int = 5) -> Dict[str, Any]:
    """Convenience function for similar strategy search"""
    return bm25_tool.search_similar_strategies(strategy_description, max_results)

if __name__ == "__main__":
    # Test the BM25 search tool
    tool = BM25SearchTool()
    
    # Test basic search
    result = tool.search_research("momentum strategy volatility targeting")
    print("Basic search result:", result)
    
    # Test similar strategy search
    strategy_desc = "A momentum strategy that uses moving averages and volatility targeting"
    similar = tool.search_similar_strategies(strategy_desc)
    print("Similar strategies:", similar)
    
    # Test statistics
    print("Search statistics:", tool.get_search_statistics())
