import arxiv
import bm25s
import json
import os
import re

CACHE_FILE = "experiments/results/research_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def get_unique_papers():
    cache = load_cache()
    papers = []
    seen_urls = set()
    
    # Add papers from cache
    for query_results in cache.values():
        for p in query_results:
            if p["url"] not in seen_urls:
                papers.append(p)
                seen_urls.add(p["url"])
    
    # Add papers from local corpus
    corpus_file = "data/bm25_papers.json"
    if os.path.exists(corpus_file):
        with open(corpus_file, "r") as f:
            corpus_papers = json.load(f)
            for p in corpus_papers:
                if p["url"] not in seen_urls:
                    p["source"] = "local_corpus"
                    papers.append(p)
                    seen_urls.add(p["url"])
                    
    return papers

def local_bm25_search(query, top_n=3):
    """
    Search papers already in the cache using BM25.
    """
    papers = get_unique_papers()
    if not papers:
        return []
    
    # Simple tokenization
    def tokenize(text):
        return re.sub(r'[^a-zA-Z0-9\s]', '', text.lower()).split()

    corpus = [tokenize(f"{p['title']} {p['summary']}") for p in papers]
    
    try:
        retriever = bm25s.BM25(corpus=papers)
        retriever.index(corpus)
        
        query_tokens = tokenize(query)
        # BM25S expects a list of queries [ [tokens], [tokens] ]
        results, scores = retriever.retrieve([query_tokens], k=top_n)
        
        # Filter by a small threshold to ensure relevance
        relevant_papers = []
        for i in range(len(results[0])):
            if scores[0, i] > 0.5: # Threshold for BM25 score relevance
                relevant_papers.append(results[0, i])
        return relevant_papers
    except Exception as e:
        print(f"  [Research] BM25 Error: {e}")
        return []

def search_arxiv(query, max_results=5):
    """
    Searches ArXiv for papers matching the query and returns metadata.
    """
    # First, try local BM25
    local_results = local_bm25_search(query, top_n=max_results)
    if local_results:
        print(f"  [Research] Local BM25 hit: Found {len(local_results)} relevant papers.")
        return local_results

    # If nothing relevant locally, check exact query cache
    cache = load_cache()
    if query in cache:
        print(f"  [Research] Cache hit for: {query}")
        return cache[query]

    print(f"  [Research] Searching ArXiv for: {query}...")
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )

    results = []
    for result in client.results(search):
        results.append({
            "title": result.title,
            "summary": result.summary,
            "url": result.pdf_url,
            "published": result.published.strftime("%Y-%m-%d")
        })

    cache[query] = results
    save_cache(cache)
    return results

def get_research_context(hypothesis, max_papers=3):
    """
    High-level helper to get academic context for a given hypothesis.
    Uses BM25 to search locally before going to ArXiv.
    """
    # Clean query
    query = re.sub(r'[^a-zA-Z0-9\s]', '', hypothesis)
    papers = search_arxiv(query, max_results=max_papers)
    
    context = "\n--- Academic Research Context ---\n"
    if not papers:
        context += "No specific academic papers found for this hypothesis.\n"
    else:
        for p in papers:
            context += f"PAPER: {p['title']} ({p['published']})\n"
            context += f"SUMMARY: {p['summary'][:500]}...\n"
            context += f"URL: {p['url']}\n\n"
    
    return context

if __name__ == "__main__":
    # Test
    test_q = "momentum strategy with volatility targeting"
    print(get_research_context(test_q))
