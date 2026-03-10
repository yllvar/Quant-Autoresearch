import os
import sys
import subprocess
import json
import re
import ast
from groq import Groq
from dotenv import load_dotenv
from .research import get_research_context

# Load environment variables from .env file
load_dotenv()

# Configuration
STRATEGY_FILE = os.environ.get("STRATEGY_FILE", "src/strategies/active_strategy.py")
PROGRAM_FILE = os.environ.get("PROGRAM_FILE", "src/prompts/program.md")
BACKTEST_RUNNER = os.environ.get("BACKTEST_RUNNER", "src/core/backtester.py")
EXPERIMENT_LOG = os.environ.get("EXPERIMENT_LOG", "experiments/results/experiment_log.json")
# The API key is now loaded from the environment/ .env file
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

def get_current_strategy():
    with open(STRATEGY_FILE, "r") as f:
        return f.read()

def get_program_constitution():
    with open(PROGRAM_FILE, "r") as f:
        return f.read()

def run_backtest_with_output():
    result = subprocess.run(["uv", "run", "python", BACKTEST_RUNNER], capture_output=True, text=True)
    output = result.stdout
    error_output = result.stderr
    score = -10.0
    drawdown = 0.0
    trades = 0
    
    match_score = re.search(r"SCORE:\s*(-?[\d\.]+)", output)
    if match_score:
        score = float(match_score.group(1))
        if score == -10.0:
            print("--- BACKTEST RETURNED ERROR SCORE ---")
            print("STDOUT:", output)
            print("STDERR:", error_output)
    else:
        print("--- BACKTEST FAILED COMPLETELY ---")
        print("STDOUT:", output)
        print("STDERR:", error_output)
    
    match_dd = re.search(r"DRAWDOWN:\s*(-?[\d\.]+)", output)
    if match_dd:
        drawdown = float(match_dd.group(1))
        
    match_trades = re.search(r"TRADES:\s*(\d+)", output)
    if match_trades:
        trades = int(match_trades.group(1))
        
    return score, drawdown, trades, {"stdout": output, "stderr": error_output}

def load_experiment_log():
    if os.path.exists(EXPERIMENT_LOG):
        with open(EXPERIMENT_LOG, "r") as f:
            return json.load(f)
    return []

def save_experiment_log(log):
    with open(EXPERIMENT_LOG, "w") as f:
        json.dump(log, f, indent=2)

def log_to_tsv(score, drawdown, trades, status, description):
    results_path = "experiments/results/results.tsv"
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    file_exists = os.path.exists(results_path)
    with open(results_path, "a") as f:
        if not file_exists:
            f.write("commit\tscore\tdrawdown\ttrades\tstatus\tdescription\n")
        timestamp = subprocess.check_output(["date", "+%Y%m%d_%H%M%S"]).decode().strip()
        f.write(f"{timestamp}\t{score}\t{drawdown}\t{trades}\t{status}\t{description}\n")

def agent_iteration():
    print("--- Starting Agent Iteration ---")
    program = get_program_constitution()
    current_code = get_current_strategy()
    current_score, current_dd, current_trades, _ = run_backtest_with_output()
    
    if not os.path.exists("results.tsv"):
        log_to_tsv(current_score, current_dd, current_trades, "KEEP", "Baseline Strategy")

    print(f"Current Score: {current_score}")
    log = load_experiment_log()
    
    # STEP 1: Hypothesis Generation
    print("Step 1: Generating Hypothesis...")
    hypothesis_prompt = f"""
{program}

Current Strategy Code:
```python
{current_code}
```

Current Baseline Score: {current_score}

Previous Experiments Summaries:
{json.dumps([{"hypothesis": e["hypothesis"], "score": e["score"], "status": e.get("status"), "error": e.get("error")} for e in log[-5:]], indent=2)}

Task:
Propose a single focused quantitative hypothesis to improve the Sharpe Ratio. 
Focus on specific features (volatility, momentum, mean reversion) or regime detection.

Return only a JSON object: {{"hypothesis": "Your reasoning here", "search_query": "specific terms for arxiv search"}}
"""
    try:
        resp_h = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": hypothesis_prompt}],
            response_format={"type": "json_object"}
        )
        res_h = json.loads(resp_h.choices[0].message.content)
        hypothesis = res_h["hypothesis"]
        search_query = res_h.get("search_query", hypothesis)
    except Exception as e:
        print(f"Hypothesis Generation API Error: {str(e)}")
        return

    print(f"  Proposed Hypothesis: {hypothesis}")
    
    print("Step 2: Fetching Research Context...")
    research_context = get_research_context(search_query)
    
    # STEP 3: Code Generation & Self-Correction Loop
    max_tries = 2
    for attempt in range(max_tries):
        print(f"Step 3: Generating Strategy Code (Attempt {attempt+1}/{max_tries})...")
        
        extra_instr = ""
        if attempt > 0:
            extra_instr = f"\n\nERROR FROM PREVIOUS ATTEMPT:\n{error_msg}\n\nPlease fix the error. Ensure valid indentation and syntax. Use only pandas and numpy."

        code_prompt = f"""
{program}

Current Strategy Code:
```python
{current_code}
```

Proposed Hypothesis:
{hypothesis}

{research_context}
{extra_instr}

Task:
Implement the proposed logic in the `generate_signals` method body for the `# --- EDITABLE REGION ---`.
Cite the relevant concepts from the research context in your code comments.

Return only a JSON object: {{"code": "The entire content of the generate_signals method body"}}
"""
        try:
            resp_c = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": code_prompt}],
                response_format={"type": "json_object"}
            )
            res_c = json.loads(resp_c.choices[0].message.content)
            new_code_body = res_c["code"]
        except Exception as e:
            error_msg = f"Code Generation API Error: {str(e)}"
            print(f"  {error_msg}")
            if attempt < max_tries - 1:
                continue
            else:
                new_score, new_dd, new_trades = -10.0, 0.0, 0
                backtest_output = {"stderr": error_msg}
                new_code_body = ""
                break
                
        # Indentation cleanup
        indented_body = clean_and_indent(new_code_body)
        
        pattern = r"(# --- EDITABLE REGION BREAK ---)(.*?)(# --- EDITABLE REGION END ---)"
        new_strategy_content = re.sub(pattern, f"\\1\n{indented_body}\n        \\3", current_code, flags=re.DOTALL)
        
        # AST Check before writing
        try:
            ast.parse(new_strategy_content)
        except Exception as e:
            error_msg = f"Syntax Error: {e}"
            print(f"  Pre-write AST Check Failed: {error_msg}")
            if attempt < max_tries - 1: continue
            else: break

        # Write and Backtest
        with open(STRATEGY_FILE, "w") as f: f.write(new_strategy_content)
        new_score, new_dd, new_trades, backtest_output = run_backtest_with_output()
        
        if new_score != -10.0:
            break # Success or valid result
        else:
            error_msg = backtest_output.get("stderr", "Unknown Error")
            print(f"  Backtest Failed: {error_msg[:100]}...")
            if attempt < max_tries - 1:
                # Revert before next try
                with open(STRATEGY_FILE, "w") as f: f.write(current_code)
                continue
    
    print(f"Final Score: {new_score}")
    status = "KEEP" if (new_score > current_score and new_score != -10.0) else "DISCARD"
    error_msg = ""
    if new_score == -10.0:
        status = "CRASH"
        error_msg = backtest_output.get("stderr", "Syntax/Indentation Error")
        
    log_to_tsv(new_score, new_dd, new_trades, status, hypothesis)
    log.append({"hypothesis": hypothesis, "score": new_score, "status": status, "error": error_msg[:500], "code": new_code_body})
    save_experiment_log(log)
    
    if status != "KEEP":
        with open(STRATEGY_FILE, "w") as f: f.write(current_code)
    else:
        print("Improvement found! Keeping changes.")

def clean_and_indent(code_body):
    lines = code_body.split("\n")
    while lines and not lines[0].strip(): lines.pop(0)
    min_indent = 999
    for line in lines:
        if line.strip():
            indent = len(line) - len(line.lstrip())
            if indent < min_indent: min_indent = indent
    if min_indent == 999: min_indent = 0
    cleaned_lines = []
    for line in lines:
        cleaned_line = line[min_indent:] if len(line) >= min_indent else line.lstrip()
        cleaned_lines.append("        " + cleaned_line if cleaned_line.strip() else "")
    return "\n".join(cleaned_lines)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1)
    args = parser.parse_args()
    
    for i in range(args.iterations):
        agent_iteration()
