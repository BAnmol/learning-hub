import ast
import json
import random
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

try:
    from src.llm_router import LLMRouter
except (ImportError, ModuleNotFoundError):
    from llm_router import LLMRouter

load_dotenv()


class InterviewEngine:
    """
    Core AI engine for the 45-Minute Timed Technical Interview Round.
    Simulates real-world FAANG & Tier-1 tech company interview panels with:
    - Smart problem matching based on candidate role, YOE, skills, and background.
    - Context-aware interviewer dialogue (scoping questions, approach pitch feedback).
    - 3-tier progressive hint system with penalty tracking.
    - Comprehensive FAANG-grade evaluation scorecard (0-100, hire decision, 4 rubric dimensions).
    """

    def __init__(self):
        self.llm = LLMRouter()

    def _call_ai_completion(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        # Live-interview dialogue needs a snappy reply — keep the timeout tight and
        # try only each provider's primary model before moving to the next tier
        # (Groq in particular is fast enough that cross-provider fallback here
        # rarely costs more than the old single-provider retry did).
        return self.llm.complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1200,
            timeout=6,
            max_candidates_per_provider=1,
        )

    # =========================================================================
    # Problem Matching
    # =========================================================================

    def select_problem(self, intake: Dict[str, Any], problems: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Intelligently match a curriculum problem to the candidate's intake specifications."""
        if not problems:
            raise ValueError("Curriculum problem pool is empty.")

        target_role = intake.get("target_role", "").lower()
        focus_skills = intake.get("focus_skills", "").lower()
        exp_level = intake.get("experience_level", "").lower()

        # Target difficulty based on experience level
        if "senior" in exp_level or "staff" in exp_level or "5+" in exp_level:
            preferred_diffs = ["Hard", "Medium"]
        elif "mid" in exp_level or "3-5" in exp_level:
            preferred_diffs = ["Medium", "Hard", "Easy"]
        else:
            # Junior / Entry
            preferred_diffs = ["Easy", "Medium"]

        # 1. AI/ML, Data Engineering specific routing
        is_aiml_role = any(k in target_role for k in ["ai", "machine learning", "llm", "deep learning"])
        is_de_role = any(k in target_role for k in ["data engineer", "streaming", "pipeline"])

        pool = problems[:]

        if is_aiml_role:
            aiml_pool = [p for p in pool if "ai/ml" in p.get("step", "").lower() or "aiml" in p.get("id", "")]
            if aiml_pool:
                pool = aiml_pool
        elif is_de_role:
            de_pool = [
                p for p in pool
                if any(k in p.get("topic", "").lower() for k in ["sliding", "window", "stream", "two pointer", "hash"])
                or "ai/ml" in p.get("step", "").lower()
            ]
            if de_pool:
                pool = de_pool

        # 2. Match focus skills if specified
        if "array" in focus_skills or "binary search" in focus_skills or "two pointer" in focus_skills:
            skill_pool = [p for p in pool if any(k in p.get("topic", "").lower() for k in ["array", "binary search", "two pointer"])]
            if skill_pool:
                pool = skill_pool
        elif "tree" in focus_skills or "graph" in focus_skills or "heap" in focus_skills:
            skill_pool = [p for p in pool if any(k in p.get("topic", "").lower() for k in ["tree", "bst", "graph", "heap"])]
            if skill_pool:
                pool = skill_pool
        elif "dynamic programming" in focus_skills or "optimization" in focus_skills:
            skill_pool = [p for p in pool if any(k in p.get("topic", "").lower() for k in ["dp", "dynamic programming", "recursion"])]
            if skill_pool:
                pool = skill_pool
        elif "tensor" in focus_skills or "attention" in focus_skills or "ml" in focus_skills:
            skill_pool = [p for p in pool if "ai/ml" in p.get("step", "").lower() or "aiml" in p.get("id", "")]
            if skill_pool:
                pool = skill_pool

        # 3. Filter by difficulty preference
        for diff in preferred_diffs:
            diff_matches = [p for p in pool if p.get("difficulty") == diff]
            if diff_matches:
                return random.choice(diff_matches)

        # Fallback to any problem in the matched pool
        return random.choice(pool)

    # =========================================================================
    # Interviewer Persona Greeting & Chat
    # =========================================================================

    def generate_initial_greeting(self, intake: Dict[str, Any], problem: Dict[str, Any]) -> str:
        """Create a tailored opening statement from the AI Interviewer."""
        company = intake.get("target_company", "Tier-1 Tech")
        role = intake.get("target_role", "Software Development Engineer")
        title = problem.get("title", "the algorithmic problem")
        topic = problem.get("topic", "Data Structures")

        company_clean = company.split("(")[0].strip()

        return (
            f"Hello! Welcome to your **45-minute technical round** for the **{role}** position at **{company_clean}**.\n\n"
            f"I will be your technical interviewer today. For this round, we are focusing on **{topic}**, and your problem is **'{title}'**.\n\n"
            f"Here is how this round is structured:\n"
            f"1. **Clarify Constraints & Edge Cases**: Ask me any questions about input boundaries, data types, or empty inputs.\n"
            f"2. **Pitch Your Approach**: Explain your intuition and state your expected Time & Space complexity before writing code.\n"
            f"3. **Implement & Test**: Write clean, modular Python code and run test cases against it.\n"
            f"4. **Progressive Hints**: If you get stuck, request a hint (Note: hints carry slight scorecard deductions).\n\n"
            f"The 45-minute clock is running. Take a moment to inspect the problem description, and let me know your thoughts or any clarifying questions!"
        )

    def generate_hint(self, problem: Dict[str, Any], hint_level: int, hint_number: int = 1) -> Dict[str, Any]:
        """Generate a 3-tier progressive hint with clear deduction attribution.

        `hint_number` is this request's 1-indexed position among all hints used so
        far in the session (regardless of tier) — the scorecard's hint penalty is
        based on how many hints were used in total, so the displayed deduction is
        computed from that same count-based schedule (see evaluate_interview) to
        stay consistent with what's actually deducted from the final score.
        """
        title = problem.get("title", "")
        topic = problem.get("topic", "")
        desc = problem.get("description", "")
        ref = problem.get("reference_solution", "")

        labels = {1: "Tier 1: Gentle Nudge", 2: "Tier 2: Structural Clue", 3: "Tier 3: Algorithmic Strategy"}

        level = max(1, min(3, hint_level))
        label = labels[level]

        # Cumulative deduction schedule mirrored from evaluate_interview's hint_penalty logic.
        cumulative_schedule = {0: 0, 1: 4, 2: 9}
        count = max(1, hint_number)
        cumulative_before = cumulative_schedule.get(count - 1, 15)
        cumulative_after = cumulative_schedule.get(count, 15)
        penalty = cumulative_after - cumulative_before

        # LLM prompt if online
        system_prompt = (
            "You are an expert technical interviewer at FAANG. The candidate requested a hint during a live coding interview. "
            "Generate an encouraging, precise hint according to the requested tier level.\n"
            "- Tier 1: Gentle Nudge (guide them towards the right observation or pattern without spoiling).\n"
            "- Tier 2: Structural Clue (mention the key data structure, two pointers, invariant, or recurrence relation).\n"
            "- Tier 3: Algorithmic Strategy (step-by-step walkthrough of the optimal algorithm without giving raw code)."
        )
        user_prompt = (
            f"Problem: {title} ({topic})\n"
            f"Description: {desc[:400]}\n"
            f"Requested Hint Level: Tier {level} ({label})\n"
            f"Reference code snippet: {ref[:300]}\n"
            f"Respond with only the concise hint message."
        )

        ai_hint = self._call_ai_completion(system_prompt, user_prompt)
        if ai_hint:
            hint_text = ai_hint
        else:
            # High quality static heuristics
            if level == 1:
                hint_text = (
                    f"**Gentle Nudge**: Think about the core invariant of {topic}. "
                    f"What information do you need at each step? Can you avoid redundant computations by storing intermediate results?"
                )
            elif level == 2:
                hint_text = (
                    f"**Structural Clue**: Consider using an optimal data structure (e.g. Hash Map, Two Pointers, or Heap). "
                    f"Notice how each element relates to the boundary or target condition to achieve sub-quadratic complexity."
                )
            else:
                hint_text = (
                    f"**Algorithmic Strategy**: Initialize your tracking variables or state table. "
                    f"Iterate through the inputs, updating the state in O(1) or O(log N) time per element. "
                    f"Check boundary conditions first (e.g. empty inputs or single-element inputs), then return the aggregated result."
                )

        return {
            "level": level,
            "label": label,
            "penalty": penalty,
            "text": hint_text,
        }

    def chat_interviewer(
        self,
        intake: Dict[str, Any],
        problem: Dict[str, Any],
        user_message: str,
        chat_history: List[Dict[str, Any]],
        current_code: str = "",
    ) -> str:
        """Handle candidate questions, approach pitches, and conversational interaction."""
        company = intake.get("target_company", "FAANG")
        role = intake.get("target_role", "Software Engineer")
        title = problem.get("title", "")
        topic = problem.get("topic", "")
        desc = problem.get("description", "")

        system_prompt = (
            f"You are a Senior Staff Software Engineer and technical interviewer at {company} conducting a live 45-minute coding interview for a {role}.\n"
            f"Problem being tested: '{title}' ({topic}).\n"
            f"Candidate is talking to you live. Rules of engagement:\n"
            f"1. Tone: Professional, warm, encouraging, but rigorous. Make them feel the authenticity and heat of a real interview.\n"
            f"2. If candidate asks clarifying questions (e.g., constraints, types, edge cases), answer them based on standard LeetCode/DSA conventions.\n"
            f"3. If candidate pitches an approach, evaluate whether it makes sense. If it's brute-force O(N^2), acknowledge it and gently challenge: 'Can we optimize this to O(N) or O(N log N)?'. If it's optimal, give them the green light to code.\n"
            f"4. Do NOT write full solutions or code for them unless explicitly answering a syntax clarifying question.\n"
            f"5. Keep responses concise (2 to 4 sentences maximum) so the candidate doesn't waste precious interview time reading."
        )

        history_context = ""
        if chat_history:
            recent = chat_history[-4:]
            for msg in recent:
                sender = "Interviewer" if msg.get("role") == "interviewer" else "Candidate"
                history_context += f"{sender}: {msg.get('text', '')}\n"

        user_prompt = (
            f"Problem details: {desc[:300]}\n"
            f"Current candidate code state:\n```python\n{current_code[:250]}\n```\n"
            f"Recent dialogue:\n{history_context}"
            f"Candidate says: \"{user_message}\"\n"
            f"Interviewer response:"
        )

        ai_reply = self._call_ai_completion(system_prompt, user_prompt)
        if ai_reply:
            return ai_reply

        # Fallback heuristic responses
        msg_lower = user_message.lower()
        if any(k in msg_lower for k in ["duplicate", "empty", "negative", "constraints", "null", "none"]):
            return (
                "Great question! You can assume the inputs fit in standard memory. "
                "Always safeguard against empty or single-element inputs at the beginning of your method."
            )
        elif any(k in msg_lower for k in ["approach", "thinking", "hash map", "two pointer", "binary search", "dp"]):
            return (
                "That sounds like a very promising intuition. What do you estimate the Time and Space complexity will be? "
                "Go ahead and begin implementing your logic in the editor, and talk through the key steps as you code."
            )
        elif any(k in msg_lower for k in ["done", "finished", "ready", "submitted"]):
            return (
                "Excellent! Let's execute your solution against the test suite to verify correctness and edge case handling."
            )
        else:
            return (
                "Understood. Keep in mind optimal time complexity and how you handle boundary cases. "
                "Feel free to write out the structure in code, or let me know if you need any clarification on the problem."
            )

    # =========================================================================
    # Evaluation & Scorecard
    # =========================================================================

    def evaluate_interview(
        self,
        intake: Dict[str, Any],
        problem: Dict[str, Any],
        user_code: str,
        test_result: Dict[str, Any],
        time_spent_seconds: int,
        hints_used: int,
        chat_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Evaluate full candidate performance across 4 FAANG dimensions:
        1. Problem Solving & Intuition (0-25)
        2. Algorithmic Efficiency & Big-O (0-25)
        3. Code Quality & Defensive Robustness (0-25)
        4. Communication & Engineering Presence (0-25)

        Ensures fair, rigorous, and accurate evaluation based on actual test results.
        """
        # 1. Resolve test execution metrics robustly
        raw_passed = test_result.get("tests_passed")
        raw_total = test_result.get("tests_total")
        results_list = test_result.get("test_results") or []

        if raw_passed is not None and raw_total is not None and int(raw_total) > 0:
            tests_passed = int(raw_passed)
            tests_total = int(raw_total)
        elif results_list:
            tests_passed = sum(1 for t in results_list if t.get("passed"))
            tests_total = len(results_list)
        else:
            is_bool_pass = bool(test_result.get("passed", False))
            prob_test_cases = problem.get("test_cases") or []
            tests_total = len(prob_test_cases) if prob_test_cases else 3
            tests_passed = tests_total if is_bool_pass else 0

        is_all_passed = bool(test_result.get("passed", False)) or (tests_total > 0 and tests_passed >= tests_total)
        pass_ratio = (tests_passed / tests_total) if tests_total > 0 else (1.0 if is_all_passed else 0.0)
        error_msg = test_result.get("error") or ""
        has_error = bool(error_msg) or test_result.get("status") in ["Runtime Error", "Time Limit Exceeded"]

        # 2. Analyze Code Structure via AST
        user_code_str = user_code or ""
        code_lines = [l.strip() for l in user_code_str.splitlines() if l.strip() and not l.strip().startswith("#")]
        is_empty_or_placeholder = (
            len(code_lines) == 0
            or user_code_str.strip() == "pass"
            or (len(code_lines) == 1 and code_lines[0].startswith("return"))
        )

        loop_depth = 0
        uses_fast_ds = False
        has_syntax_error = False

        try:
            tree = ast.parse(user_code_str)
            for node in ast.walk(tree):
                if isinstance(node, (ast.For, ast.While)):
                    loop_depth = max(loop_depth, 1)
                    for child in ast.walk(node):
                        if child is not node and isinstance(child, (ast.For, ast.While)):
                            loop_depth = 2
                            for grand_child in ast.walk(child):
                                if grand_child is not child and isinstance(grand_child, (ast.For, ast.While)):
                                    loop_depth = 3
                                    break
                if isinstance(node, ast.Name) and node.id in (
                    "set", "dict", "heapq", "deque", "defaultdict", "Counter", "bisect", "math"
                ):
                    uses_fast_ds = True
        except Exception:
            has_syntax_error = True

        # =====================================================================
        # Dimension 1: Problem Solving & Intuition (0-25)
        # =====================================================================
        if is_all_passed or pass_ratio >= 0.99:
            ps_score = 25
        elif pass_ratio >= 0.75:
            ps_score = 22
        elif pass_ratio >= 0.50:
            ps_score = 18
        elif pass_ratio > 0.0:
            ps_score = 13
        else:
            if is_empty_or_placeholder or has_syntax_error:
                ps_score = 2
            else:
                ps_score = 7  # Meaningful code structure, but failed test cases

        # =====================================================================
        # Dimension 2: Algorithmic Efficiency & Big-O (0-25)
        # =====================================================================
        if is_all_passed:
            if loop_depth <= 1 or uses_fast_ds:
                eff_score = 25  # Optimal O(1), O(log N), or O(N)
            elif loop_depth == 2:
                eff_score = 22  # O(N^2) acceptable/solved
            else:
                eff_score = 19  # High polynomial
        elif pass_ratio >= 0.50:
            eff_score = 19 if (loop_depth <= 1 or uses_fast_ds) else 16
        elif pass_ratio > 0.0:
            eff_score = 14 if loop_depth <= 1 else 11
        else:
            eff_score = 7 if not is_empty_or_placeholder else 3

        # =====================================================================
        # Dimension 3: Code Quality & Defensive Robustness (0-25)
        # =====================================================================
        if is_empty_or_placeholder:
            cq_score = 3
        else:
            base_cq = 20
            if not has_syntax_error:
                base_cq += 2
            else:
                base_cq -= 7

            # Defensive guards check (e.g. empty checks, null checks, length checks)
            lower_code = user_code_str.lower()
            if any(guard in lower_code for guard in ["if not ", "len(", " == 0", "is none", " <= 0"]):
                base_cq += 2

            if len(code_lines) >= 4:
                base_cq += 1

            if has_error:
                base_cq = max(6, base_cq - 6)

            if is_all_passed and not has_error:
                cq_score = max(23, min(25, base_cq))
            else:
                cq_score = max(5, min(25, base_cq))

        # =====================================================================
        # Dimension 4: Communication & Engineering Presence (0-25)
        # =====================================================================
        candidate_messages = [m for m in chat_history if m.get("role") == "user"]
        chat_count = len(candidate_messages)
        has_comments = "#" in user_code_str or '"""' in user_code_str or "'''" in user_code_str

        if chat_count >= 3:
            comm_score = 25
        elif chat_count >= 1:
            comm_score = 23 if has_comments else 21
        else:
            # Silent candidate: if code passed and is clean, award fair baseline
            if is_all_passed:
                comm_score = 22 if has_comments else 20
            elif pass_ratio >= 0.5:
                comm_score = 18 if has_comments else 16
            else:
                comm_score = 12 if not is_empty_or_placeholder else 6

        # =====================================================================
        # Progressive Hint Deduction
        # =====================================================================
        if hints_used == 1:
            hint_penalty = 4
        elif hints_used == 2:
            hint_penalty = 9
        elif hints_used >= 3:
            hint_penalty = 15
        else:
            hint_penalty = 0

        # Raw Total & Fair Normalization
        total_raw = ps_score + eff_score + cq_score + comm_score - hint_penalty
        overall_score = max(5, min(100, total_raw))

        # Guarantee fair floor for candidates who pass 100% of test cases
        if is_all_passed:
            overall_score = max(82, overall_score)

        # =====================================================================
        # Hiring Committee Verdict
        # =====================================================================
        if is_all_passed and overall_score >= 82:
            hire_decision = "STRONG HIRE"
        elif pass_ratio >= 0.50 and overall_score >= 68:
            hire_decision = "LEAN HIRE"
        elif overall_score >= 48:
            hire_decision = "LEAN NO HIRE"
        else:
            hire_decision = "NO HIRE"

        # =====================================================================
        # Qualitative Feedback Generation
        # =====================================================================
        system_prompt = (
            "You are a Senior Engineering Hiring Committee Member at FAANG. "
            "Write an official, constructive, and accurate interview feedback scorecard for a candidate technical round. "
            "Return a JSON object with keys: "
            "'executive_summary' (2 sentences summarizing actual performance), "
            "'strengths' (array of 3 specific bullet points), "
            "'areas_for_improvement' (array of 2 specific bullet points), "
            "'recommendations' (1 concrete follow-up study tip). "
            "Only return raw JSON without markdown or backticks."
        )
        user_prompt = (
            f"Candidate Target: {intake.get('target_role')} at {intake.get('target_company')}\n"
            f"Problem: {problem.get('title')} ({problem.get('topic')})\n"
            f"Tests: {tests_passed}/{tests_total} passed ({int(pass_ratio * 100)}% pass rate). Total time: {time_spent_seconds}s. Hints used: {hints_used}.\n"
            f"Code:\n```python\n{user_code_str[:400]}\n```\n"
            f"Score: {overall_score}, Verdict: {hire_decision}\n"
        )

        feedback_obj = None
        raw_ai = self._call_ai_completion(system_prompt, user_prompt)
        if raw_ai:
            try:
                clean_json = re.sub(r"^```(?:json)?", "", raw_ai.strip())
                clean_json = re.sub(r"```$", "", clean_json.strip())
                feedback_obj = json.loads(clean_json)
            except Exception:
                pass

        if not feedback_obj or not isinstance(feedback_obj, dict):
            if is_all_passed:
                exec_summary = (
                    f"The candidate demonstrated strong algorithmic competence on '{problem.get('title')}', "
                    f"passing all {tests_passed}/{tests_total} test cases in {time_spent_seconds // 60}m {time_spent_seconds % 60}s. "
                    f"Their solution showed solid time/space complexity and idiomatic Python structure."
                )
                strengths = [
                    f"100% test case pass rate ({tests_passed}/{tests_total}) on {problem.get('topic')}.",
                    "Structured, efficient implementation with optimal algorithmic runtime.",
                    "Clean variable naming and clear procedural flow.",
                ]
                improvements = [
                    "Consider discussing trade-offs between iterative and recursive paradigms with the interviewer.",
                    "Continue practicing with zero hints under tight 20-minute constraints.",
                ]
            elif pass_ratio >= 0.5:
                exec_summary = (
                    f"The candidate demonstrated solid algorithmic intuition on '{problem.get('title')}', "
                    f"passing {tests_passed}/{tests_total} test cases ({int(pass_ratio * 100)}%). "
                    f"The primary approach was sound, with opportunities to address remaining edge cases."
                )
                strengths = [
                    f"Core algorithm correctly implemented for majority cases ({tests_passed}/{tests_total} passing).",
                    f"Demonstrated good familiarity with {problem.get('topic')} fundamentals.",
                    "Clean code structure with readable logical blocks.",
                ]
                improvements = [
                    "Double check boundary values (empty arrays, duplicates, single elements) before submission.",
                    "Clarify input constraints early to prevent edge case regressions.",
                ]
            else:
                exec_summary = (
                    f"The candidate demonstrated partial problem comprehension on '{problem.get('title')}' "
                    f"({tests_passed}/{tests_total} tests passing). "
                    f"Re-practicing core {problem.get('topic')} patterns will build confidence for future technical rounds."
                )
                strengths = [
                    f"Attempted systematic solution structure for {problem.get('topic')}.",
                    "Showed willingness to engage with problem statement and syntax.",
                    "Maintained disciplined focus throughout the timed session.",
                ]
                improvements = [
                    "Spend the first 5 minutes diagramming edge cases before writing code.",
                    "Walk through sample inputs manually line-by-line to trace logic bugs.",
                ]

            feedback_obj = {
                "executive_summary": exec_summary,
                "strengths": strengths,
                "areas_for_improvement": improvements,
                "recommendations": f"Practice related problems in '{problem.get('topic')}' under a strict 30-minute timer.",
            }

        return {
            "score": overall_score,
            "hire_decision": hire_decision,
            "time_spent_seconds": time_spent_seconds,
            "tests_passed": tests_passed,
            "tests_total": tests_total,
            "hints_used": hints_used,
            "rubric_scores": {
                "problem_solving": ps_score,
                "efficiency": eff_score,
                "code_quality": cq_score,
                "communication": comm_score,
            },
            "feedback": feedback_obj,
        }

