import json, os, re
from typing import Any, Dict, List, Optional

EXPLANATION_CACHE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "dsa_explanations.json"
)

try:
    from src.llm_router import LLMRouter
    from src.problem_details import get_problem_enrichments, get_detailed_test_cases, extract_signature_and_params
except (ImportError, ModuleNotFoundError):
    from llm_router import LLMRouter
    from problem_details import get_problem_enrichments, get_detailed_test_cases, extract_signature_and_params


def get_sample_test_cases_for_problem(meta: Dict[str, Any]) -> List[Dict[str, str]]:
    """Return concrete sample test cases tailored to the problem topic and signature."""
    params, _, _ = extract_signature_and_params(meta)
    return get_detailed_test_cases(meta, params)



class ExplainerEngine:
    """Generates and caches structured step-by-step explanations for DSA problems."""

    def __init__(self):
        self.llm = LLMRouter()
        self._cache: Dict[str, Any] = {}
        self._load_cache()

    # ------------------------------------------------------------------ cache
    def _load_cache(self):
        if os.path.exists(EXPLANATION_CACHE_FILE):
            try:
                with open(EXPLANATION_CACHE_FILE, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}

    def _save_cache(self):
        os.makedirs(os.path.dirname(EXPLANATION_CACHE_FILE), exist_ok=True)
        with open(EXPLANATION_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=2, ensure_ascii=False)

    def _cache_key(self, pid, approach):
        return f"{pid}::{approach}"

    def get_cached(self, pid, approach):
        return self._cache.get(self._cache_key(pid, approach))

    def set_cached(self, pid, approach, data):
        self._cache[self._cache_key(pid, approach)] = data
        self._save_cache()

    # ----------------------------------------------------------------- AI call
    def _call_ai(self, prompt: str) -> Optional[str]:
        return self.llm.complete(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an elite DSA interview coach. Provide very clear, intuitive, and "
                        "step-by-step guidance that any learner can immediately grasp. "
                        "Always respond with ONLY valid JSON — no markdown fences, no extra text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1200,
            timeout=30,
        )

    # --------------------------------------------------------------- generate
    def generate(self, problem_id: str, approach: str, problem_meta: Dict, force: bool = False) -> Dict:
        if not force:
            cached = self.get_cached(problem_id, approach)
            if cached:
                # Ensure sample_test_cases are attached
                if "sample_test_cases" not in cached:
                    cached["sample_test_cases"] = get_sample_test_cases_for_problem(problem_meta)
                return cached

        code = (
            problem_meta.get("brute_force_solution")
            if approach == "brute"
            else problem_meta.get("reference_solution", "")
        ) or ""

        result = self._from_ai(problem_meta, approach, code) or self._fallback(problem_meta, approach, code)
        result["sample_test_cases"] = get_sample_test_cases_for_problem(problem_meta)
        self.set_cached(problem_id, approach, result)
        return result

    def _from_ai(self, meta, approach, code) -> Optional[Dict]:
        label = "BRUTE FORCE (naive/exhaustive)" if approach == "brute" else "OPTIMISED (efficient/interview-standard)"
        title = meta.get("title", "Unknown")
        topic = meta.get("topic", "")
        diff = meta.get("difficulty", "")

        prompt = (
            f"You are explaining the {label} solution for a DSA problem.\n"
            f"Problem: \"{title}\"\n"
            f"Topic: {topic}  |  Difficulty: {diff}\n\n"
            f"Code to explain:\n```python\n{code[:1800]}\n```\n\n"
            "Return ONLY valid JSON matching this exact schema:\n"
            "{\n"
            '  "intuition": "<2-3 plain-English sentences explaining the core intuition simply and clearly>",\n'
            '  "approach_name": "<short clean technique name, e.g. Hash Map Complement Lookup or Two Pointers Inward Scan>",\n'
            '  "key_insight": "<single aha sentence that makes the solution click>",\n'
            '  "steps": [{\"label\":\"Step N — action phrase\",\"detail\":\"1-2 clear, easy-to-understand sentences\"}],\n'
            '  "time_complexity": "O(...) — clear reason",\n'
            '  "space_complexity": "O(...) — clear reason",\n'
            '  "trace_template": [{\"phase\":\"Name\",\"description\":\"Use {INPUT} placeholder\",\"highlight_type\":\"init|scan|compare|update|result\"}],\n'
            '  "common_mistakes": ["mistake 1","mistake 2"]\n'
            "}\n\n"
            "trace_template must have 4-6 phases. highlight_type must be one of: init, scan, compare, update, result."
        )
        raw = self._call_ai(prompt)
        if not raw:
            return None
        # strip possible markdown code fences
        raw = re.sub(r"^```[a-z]*\n?", "", raw.strip(), flags=re.MULTILINE)
        raw = re.sub(r"\n?```$", "", raw.strip(), flags=re.MULTILINE)
        try:
            data = json.loads(raw.strip())
            if "intuition" in data and "steps" in data:
                data.update({"approach": approach, "generated_by": "ai"})
                return data
        except Exception:
            pass
        return None

    def _fallback(self, meta, approach, code) -> Dict:
        lc = code.lower()
        title = meta.get("title", "Problem")
        topic = meta.get("topic", "")

        # Time complexity heuristic
        nested = lc.count("for") >= 2 or (lc.count("for") >= 1 and lc.count("while") >= 1)
        if nested and approach == "brute":
            tc = "O(n²) — nested loops check every candidate pair/subset exhaustively"
        elif "sort" in lc:
            tc = "O(n log n) — initial sorting dominates runtime"
        elif ("left" in lc and "right" in lc) or "two" in lc or "pointer" in lc:
            tc = "O(n) — single two-pointer sweep inward or forward"
        elif "memo" in lc or ("dp" in lc and "[" in lc):
            tc = "O(n) — dynamic programming table filled in linear passes"
        else:
            tc = "O(n) — linear scan through elements"
        sc = "O(1) — constant auxiliary space" if approach == "optimized" else "O(n) — auxiliary storage for tracking candidates"

        if approach == "brute":
            return {
                "intuition": (
                    f"The brute force solution to \"{title}\" examines every possible candidate or combination "
                    "without skipping. It guarantees finding the answer by checking all options one by one, "
                    "helping us understand the problem before attempting optimizations."
                ),
                "approach_name": "Brute Force — Exhaustive Search",
                "key_insight": "Correctness first: compare every combination directly to establish an exact baseline.",
                "steps": [
                    {"label": "Step 1 — Parse the input", "detail": "Inspect the given values and define the target criteria."},
                    {"label": "Step 2 — Outer iteration", "detail": "Select the first element or starting position."},
                    {"label": "Step 3 — Inner inspection", "detail": "Compare the selected element against every remaining option."},
                    {"label": "Step 4 — Verify condition", "detail": "If the condition matches our target, capture the valid pair or result."},
                    {"label": "Step 5 — Return answer", "detail": "After evaluating all candidate pairs, return the result."},
                ],
                "time_complexity": tc,
                "space_complexity": sc,
                "trace_template": [
                    {"phase": "Initialise", "description": "Set up search bounds. Input: {INPUT}", "highlight_type": "init"},
                    {"phase": "Outer Loop", "description": "Pick element i as the first candidate.", "highlight_type": "scan"},
                    {"phase": "Inner Loop", "description": "Compare element i against element j.", "highlight_type": "compare"},
                    {"phase": "Condition Check", "description": "Check if candidate satisfies the target condition.", "highlight_type": "update"},
                    {"phase": "Return Result", "description": "Match found or search completed. Return answer.", "highlight_type": "result"},
                ],
                "common_mistakes": [
                    "Checking duplicate pairs repeatedly (e.g. comparing both (i, j) and (j, i)).",
                    "Off-by-one errors in inner loop start condition.",
                    "Failing on boundary inputs like single elements or empty lists.",
                ],
                "approach": "brute",
                "generated_by": "heuristic",
            }
        else:
            return {
                "intuition": (
                    f"The optimised solution to \"{title}\" eliminates repeated work by utilizing smart data structures "
                    "like hash tables, two pointers, or binary search. Instead of re-scanning previous elements, "
                    "we do instant O(1) lookups or halve the search space at every step."
                ),
                "approach_name": "Optimised — Efficient Single-Pass",
                "key_insight": "Trade a little space for huge time savings: store seen elements to make each step O(1).",
                "steps": [
                    {"label": "Step 1 — Select appropriate data structure", "detail": "Choose a hash map, pointer pair, or auxiliary array to eliminate redundant loops."},
                    {"label": "Step 2 — Single sweep iteration", "detail": "Walk through the elements one-by-one in a single pass."},
                    {"label": "Step 3 — Instant lookup / transition", "detail": "Query the lookup table in O(1) time or move the active pointers toward each other."},
                    {"label": "Step 4 — Update current state", "detail": "Save the current element into memory so future elements can look it up."},
                    {"label": "Step 5 — Return immediately", "detail": "Yield the final answer as soon as the target condition is met."},
                ],
                "time_complexity": tc,
                "space_complexity": sc,
                "trace_template": [
                    {"phase": "Initialise", "description": "Prepare lookup table / pointers. Input: {INPUT}", "highlight_type": "init"},
                    {"phase": "Traverse", "description": "Inspect current element at active pointer.", "highlight_type": "scan"},
                    {"phase": "Fast Lookup", "description": "Check memory table in O(1) time for the needed value.", "highlight_type": "compare"},
                    {"phase": "Update State", "description": "Save current element into memory for future elements.", "highlight_type": "update"},
                    {"phase": "Result Found", "description": "Target achieved in a single pass. Return result.", "highlight_type": "result"},
                ],
                "common_mistakes": [
                    "Inserting into the hash map before checking for complement (which can cause using the same index twice).",
                    "Forgetting to update both pointers in two-pointer inward scans.",
                    "Not handling edge cases like empty inputs, all zeroes, or negative values.",
                ],
                "approach": "optimized",
                "generated_by": "heuristic",
            }
