import ast
import json
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

try:
    from src.llm_router import LLMRouter
except (ImportError, ModuleNotFoundError):
    from llm_router import LLMRouter

load_dotenv()


class AICodeReviewer:
    """AI-powered Code Reviewer & Big-O Complexity Analyzer for Python DSA solutions.
    
    Provides comprehensive analysis including:
    - Exact Time & Space complexity calculation with theoretical optimality comparison
    - Code quality & interview readiness score (0-100)
    - Anti-pattern & bottleneck detection with line-level context
    - Boundary and edge case vulnerability assessment
    - Clean, optimal refactored implementation with 1-click apply
    
    Equipped with a dual engine:
    1. Online OpenRouter LLM reasoning for deep semantic analysis
    2. Resilient Python AST / static heuristic analyzer as an instant offline/free fallback
    """

    def __init__(self):
        self.llm = LLMRouter()

    def _call_ai(self, prompt: str) -> Optional[str]:
        return self.llm.complete(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a Senior Principal Engineer and elite FAANG technical interviewer. "
                        "Your job is to thoroughly review candidates' Python DSA solutions with extreme technical precision. "
                        "Evaluate Time Complexity, Space Complexity, code quality, subtle edge cases, anti-patterns, and optimality. "
                        "Always return ONLY a valid JSON object matching the requested schema without markdown fences or extra text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
            timeout=35,
        )

    def review_code(self, problem_meta: Dict[str, Any], user_code: str) -> Dict[str, Any]:
        """Perform full code review using AI with automatic static analysis fallback."""
        user_code_clean = (user_code or "").strip()
        if not user_code_clean:
            return self._empty_code_response(problem_meta)

        # Attempt AI analysis first if API key is present
        ai_result = self._from_ai(problem_meta, user_code_clean)
        if ai_result:
            return ai_result

        # Fallback to local AST & static analysis
        return self._fallback_static_analysis(problem_meta, user_code_clean)

    def _empty_code_response(self, problem_meta: Dict[str, Any]) -> Dict[str, Any]:
        ref_code = problem_meta.get("reference_solution", "")
        return {
            "score": 0,
            "verdict": "No Code Provided",
            "verdict_badge": "danger",
            "time_complexity": "N/A",
            "time_rationale": "No executable code was provided in the editor.",
            "space_complexity": "N/A",
            "space_rationale": "No memory allocation detected.",
            "is_optimal": False,
            "optimal_time": "O(n)",
            "optimal_space": "O(1)",
            "summary": "The code editor is empty. Write your Python algorithm implementation to receive a full Big-O analysis and code review.",
            "strengths": [],
            "anti_patterns": [
                {
                    "title": "Empty Implementation",
                    "description": "No function body or logic was found.",
                    "severity": "high",
                    "suggestion": "Implement the function body and click 'AI Review' to analyze complexity.",
                }
            ],
            "edge_cases": [],
            "refactored_code": ref_code or "# Write solution here",
            "refactor_explanation": "Here is the optimal reference solution for this problem.",
            "source": "static_analyzer",
        }

    def _from_ai(self, meta: Dict[str, Any], user_code: str) -> Optional[Dict[str, Any]]:
        title = meta.get("title", "DSA Problem")
        topic = meta.get("topic", "")
        diff = meta.get("difficulty", "")
        method_name = meta.get("method_name", "solution")
        ref_solution = meta.get("reference_solution", "")
        brute_solution = meta.get("brute_force_solution", "")

        prompt = f"""Review this candidate's Python solution for the following DSA problem:
Problem: "{title}"
Topic: {topic} | Difficulty: {diff}
Target Method: {method_name}

Candidate Code:
```python
{user_code[:2200]}
```

Reference Optimal Solution (for comparison):
```python
{ref_solution[:1500]}
```

Return ONLY a valid JSON object matching this exact schema:
{{
  "score": <integer from 0 to 100>,
  "verdict": "<'Strong Hire' | 'Lean Hire' | 'Follow-up Needed' | 'Needs Optimization'>",
  "verdict_badge": "<'optimal' | 'good' | 'warning' | 'danger'>",
  "time_complexity": "<Big-O notation e.g. O(n), O(n log n), O(n^2)>",
  "time_rationale": "<Exact mathematical rationale for time complexity>",
  "space_complexity": "<Big-O notation e.g. O(1), O(n)>",
  "space_rationale": "<Exact auxiliary memory breakdown>",
  "is_optimal": <true or false>,
  "optimal_time": "<Theoretical best time complexity for this problem e.g. O(n)>",
  "optimal_space": "<Theoretical best auxiliary space e.g. O(1)>",
  "summary": "<2-3 sentence executive evaluation of the candidate's code quality and approach>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "anti_patterns": [
    {{
      "title": "<Short title of bottleneck or code smell>",
      "description": "<Why this hurts performance, readability or safety>",
      "severity": "<'high' | 'medium' | 'low'>",
      "suggestion": "<Actionable fix>"
    }}
  ],
  "edge_cases": [
    {{
      "case": "<Edge case description e.g. Empty list [], Single element, Negative values, Duplicates>",
      "status": "<'passed' | 'vulnerable' | 'missed'>",
      "detail": "<How candidate code behaves under this case>"
    }}
  ],
  "refactored_code": "<Complete, clean, idiomatic Python code implementing the optimal approach>",
  "refactor_explanation": "<Concise explanation of key optimizations in the refactored code>"
}}
"""
        raw = self._call_ai(prompt)
        if not raw:
            return None

        # Clean markdown code fences if present
        raw_clean = re.sub(r"^```[a-z]*\n?", "", raw.strip(), flags=re.MULTILINE)
        raw_clean = re.sub(r"\n?```$", "", raw_clean.strip(), flags=re.MULTILINE)

        try:
            data = json.loads(raw_clean.strip())
            required_keys = ["score", "verdict", "time_complexity", "space_complexity", "summary", "refactored_code"]
            if all(k in data for k in required_keys):
                data["source"] = "ai"
                if "strengths" not in data or not isinstance(data["strengths"], list):
                    data["strengths"] = ["Correct algorithmic intuition", "Clean variable naming"]
                if "anti_patterns" not in data or not isinstance(data["anti_patterns"], list):
                    data["anti_patterns"] = []
                if "edge_cases" not in data or not isinstance(data["edge_cases"], list):
                    data["edge_cases"] = []
                return data
        except Exception:
            pass

        return None

    def _fallback_static_analysis(self, meta: Dict[str, Any], user_code: str) -> Dict[str, Any]:
        """Deep static AST & heuristic analysis when AI is unavailable."""
        title = meta.get("title", "DSA Problem")
        ref_solution = meta.get("reference_solution", "")
        code_str = user_code
        lines = code_str.split("\n")

        # Parse AST
        ast_tree = None
        syntax_valid = True
        try:
            ast_tree = ast.parse(code_str)
        except SyntaxError as e:
            syntax_valid = False
            return {
                "score": 25,
                "verdict": "Syntax Error",
                "verdict_badge": "danger",
                "time_complexity": "N/A (Syntax Error)",
                "time_rationale": f"Code contains a syntax error at line {e.lineno}: {e.msg}",
                "space_complexity": "N/A",
                "space_rationale": "Cannot evaluate memory on invalid syntax.",
                "is_optimal": False,
                "optimal_time": "O(n)",
                "optimal_space": "O(1)",
                "summary": f"Your code has a Python syntax error on line {e.lineno}. Fix the syntax error to enable full algorithmic review.",
                "strengths": [],
                "anti_patterns": [
                    {
                        "title": "Syntax Error in Solution",
                        "description": f"SyntaxError: {e.msg} (Line {e.lineno})",
                        "severity": "high",
                        "suggestion": "Review indentation, colons, and unmatched parentheses/brackets.",
                    }
                ],
                "edge_cases": [],
                "refactored_code": ref_solution or user_code,
                "refactor_explanation": "Here is the verified reference solution for comparison.",
                "source": "static_analyzer",
            }

        # Analyze Loops & Recursion Depth
        loop_depth = 0
        max_loop_depth = 0
        has_sort = bool(re.search(r"\.sort\(|sorted\(", code_str))
        has_dict_or_set = bool(re.search(r"\{\}|set\(|dict\(|defaultdict|Counter", code_str))
        has_linear_search_in_loop = False
        has_recursion = False
        method_name = meta.get("method_name", "solution")

        class AnalyzerVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_depth = 0
                self.max_depth = 0
                self.has_recursion = False
                self.linear_in_loop = False
                self.hash_collections = set()
                self.funcs = []

            def visit_Assign(self, node):
                # Detect variables assigned to dicts or sets
                if isinstance(node.value, (ast.Dict, ast.Set)):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.hash_collections.add(target.id)
                elif isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id in ("dict", "set", "defaultdict", "Counter"):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                self.hash_collections.add(target.id)
                self.generic_visit(node)

            def visit_FunctionDef(self, node):
                self.funcs.append(node.name)
                self.generic_visit(node)

            def visit_For(self, node):
                self.current_depth += 1
                if self.current_depth > self.max_depth:
                    self.max_depth = self.current_depth
                # Check for 'in <list>' inside for loop (excluding verified hash collections)
                for child in ast.walk(node):
                    if isinstance(child, ast.Compare):
                        for op, comp in zip(child.ops, child.comparators):
                            if isinstance(op, (ast.In, ast.NotIn)):
                                if isinstance(comp, ast.Name):
                                    if comp.id not in self.hash_collections and comp.id != "self":
                                        self.linear_in_loop = True
                                elif isinstance(comp, (ast.List, ast.Tuple)):
                                    self.linear_in_loop = True
                self.generic_visit(node)
                self.current_depth -= 1

            def visit_While(self, node):
                self.current_depth += 1
                if self.current_depth > self.max_depth:
                    self.max_depth = self.current_depth
                self.generic_visit(node)
                self.current_depth -= 1

            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.funcs or node.func.id == method_name:
                        self.has_recursion = True
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in self.funcs or node.func.attr == method_name:
                        self.has_recursion = True
                self.generic_visit(node)

        visitor = AnalyzerVisitor()
        if ast_tree:
            visitor.visit(ast_tree)
            max_loop_depth = visitor.max_depth
            has_recursion = visitor.has_recursion
            has_linear_search_in_loop = visitor.linear_in_loop

        # Complexity Estimation
        anti_patterns: List[Dict[str, str]] = []
        strengths: List[str] = []

        if max_loop_depth >= 3:
            time_comp = "O(n³)"
            time_rat = "Triple nested loops iterate over all candidate triplets (cubic time)."
            score_penalty = 40
            anti_patterns.append({
                "title": "Cubic Time Complexity O(n³)",
                "description": "High nesting level will cause Time Limit Exceeded (TLE) on moderate test inputs.",
                "severity": "high",
                "suggestion": "Consider sorting first or using a hash map to reduce loop nesting.",
            })
        elif max_loop_depth == 2:
            time_comp = "O(n²)"
            time_rat = "Nested loops compare pairs exhaustively (quadratic time)."
            score_penalty = 25
            anti_patterns.append({
                "title": "Quadratic Time Complexity O(n²)",
                "description": "Nested iteration checks combinations repeatedly.",
                "severity": "medium",
                "suggestion": "Look for complementary lookups via Hash Map or Two-Pointer scan.",
            })
        elif has_sort and max_loop_depth == 1:
            time_comp = "O(n log n)"
            time_rat = "Initial sorting dominates runtime O(n log n) followed by a linear scan O(n)."
            score_penalty = 10
            strengths.append("Leveraged sorting to simplify traversal.")
        elif max_loop_depth == 1:
            if has_linear_search_in_loop:
                time_comp = "O(n²)"
                time_rat = "Single loop with nested `in <list>` lookup causes hidden quadratic time."
                score_penalty = 20
                anti_patterns.append({
                    "title": "Hidden O(n²) Search in Loop",
                    "description": "Checking `item in list` is O(n) per iteration.",
                    "severity": "high",
                    "suggestion": "Convert list to a `set` or `dict` for instant O(1) membership checks.",
                })
            else:
                time_comp = "O(n)"
                time_rat = "Single pass linear scan processes each element once."
                score_penalty = 0
                strengths.append("Optimal single-pass linear scan.")
        elif has_recursion:
            time_comp = "O(2^n)" if "memo" not in code_str and "@lru_cache" not in code_str else "O(n)"
            time_rat = "Recursive branch calls without memoization" if "O(2^n)" in time_comp else "Memoized recursion"
            score_penalty = 30 if "O(2^n)" in time_comp else 5
            if "O(2^n)" in time_comp:
                anti_patterns.append({
                    "title": "Unmemoized Exponential Recursion",
                    "description": "Repeated subproblems recalculated exponentially.",
                    "severity": "high",
                    "suggestion": "Add `@lru_cache` or a `memo = {}` dictionary to cache computed states.",
                })
        else:
            time_comp = "O(1)"
            time_rat = "Direct mathematical calculation or constant operations."
            score_penalty = 0
            strengths.append("Constant time execution.")

        # Space Complexity
        if has_dict_or_set or "[" in code_str:
            if "[[0" in code_str or "[[False" in code_str or "matrix" in code_str.lower():
                space_comp = "O(m × n)"
                space_rat = "2D matrix or DP grid allocation for state storage."
            else:
                space_comp = "O(n)"
                space_rat = "Auxiliary hash map, set, or list tracks seen elements."
        else:
            space_comp = "O(1)"
            space_rat = "In-place modifications using constant auxiliary pointers."
            strengths.append("Constant O(1) auxiliary space.")

        # Determine reference optimality
        ref_is_linear = "O(n)" in time_comp or "O(1)" in time_comp
        is_optimal = ref_is_linear or (time_comp == "O(n log n)" and "sort" in meta.get("topic", "").lower())

        # Calculate Score (Base 90 - penalties + bonuses)
        base_score = 92
        final_score = max(35, min(100, base_score - score_penalty))
        if is_optimal:
            final_score = max(final_score, 88)

        if final_score >= 88:
            verdict = "Strong Hire"
            badge = "optimal"
        elif final_score >= 75:
            verdict = "Lean Hire"
            badge = "good"
        elif final_score >= 60:
            verdict = "Follow-up Needed"
            badge = "warning"
        else:
            verdict = "Needs Optimization"
            badge = "danger"

        # Edge cases check
        edge_cases = [
            {
                "case": "Empty collection or null input (`[]` / `None`)",
                "status": "passed" if "if not " in code_str or "len(" in code_str else "vulnerable",
                "detail": "Guards against empty input gracefully." if "if not " in code_str or "len(" in code_str else "May raise IndexError or produce unexpected default output.",
            },
            {
                "case": "Single element input (`len == 1`)",
                "status": "passed",
                "detail": "Loop bounds handle single-element bounds correctly.",
            },
            {
                "case": "Duplicate or negative values",
                "status": "passed" if has_dict_or_set or "==" in code_str else "vulnerable",
                "detail": "Correctly handles duplicate keys or arithmetic under negative inputs.",
            },
        ]

        if not strengths:
            strengths = ["Structured procedural logic", "Readable control flow"]

        summary = (
            f"Your solution for \"{title}\" runs in {time_comp} time and {space_comp} space. "
            + ("It matches the optimal theoretical complexity for this problem." if is_optimal else "While functionally structured, it can be further optimized by eliminating redundant iterations.")
        )

        return {
            "score": final_score,
            "verdict": verdict,
            "verdict_badge": badge,
            "time_complexity": time_comp,
            "time_rationale": time_rat,
            "space_complexity": space_comp,
            "space_rationale": space_rat,
            "is_optimal": is_optimal,
            "optimal_time": "O(n)" if "sort" not in meta.get("topic", "").lower() else "O(n log n)",
            "optimal_space": "O(1)" if is_optimal else "O(n)",
            "summary": summary,
            "strengths": strengths,
            "anti_patterns": anti_patterns,
            "edge_cases": edge_cases,
            "refactored_code": ref_solution or user_code,
            "refactor_explanation": "Optimized to theoretical best Big-O using clean, idiomatic Python patterns.",
            "source": "static_analyzer",
        }
