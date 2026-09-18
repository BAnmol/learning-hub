import json
import os
from typing import Any, Dict, Generator, List, Optional

import requests

# =============================================================================
# LLMRouter — multi-provider free-tier AI backend with automatic failover.
#
# Every AI feature in Brainfreeze Algos (Ask AI mentor chat, problem explanations,
# code review, mock-interview dialogue/hints/grading) used to call OpenRouter
# directly and only fall back across OpenRouter's OWN pool of free models. If
# OpenRouter itself was down, or an account-wide rate limit kicked in, every
# AI feature broke at once — interrupting whatever the user was doing.
#
# This router adds two more independent, genuinely-free providers as backup
# tiers, so a single vendor outage no longer stalls the whole app:
#   Tier 1: OpenRouter   (OPENROUTER_API_KEY)
#   Tier 2: Groq         (GROQ_API_KEY)        — OpenAI-compatible, very fast
#   Tier 3: Google Gemini (GEMINI_API_KEY)     — different infra entirely
#
# Any tier left unconfigured (no key in .env) is skipped automatically — you
# only need ONE key for the app to work; add more for extra resilience.
# =============================================================================

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

OPENROUTER_FREE_MODELS = [
    "openrouter/free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "z-ai/glm-5.2:free",
    "google/gemma-4-31b-it:free",
]
GROQ_FREE_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]
GEMINI_FREE_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]


class LLMRouter:
    """Tries OpenRouter, then Groq, then Gemini — first healthy provider wins."""

    def __init__(self) -> None:
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip().strip('"').strip("'")
        self.openrouter_model = os.getenv("OPENROUTER_CHAT_MODEL", "").strip()
        self.groq_key = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")
        self.groq_model = os.getenv("GROQ_CHAT_MODEL", "").strip()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
        self.gemini_model = os.getenv("GEMINI_CHAT_MODEL", "").strip()

        self.site_url = os.getenv("OPENROUTER_SITE_URL", "http://127.0.0.1:5000").strip()
        self.site_name = os.getenv("OPENROUTER_SITE_NAME", "Brainfreeze Algos").strip()

    @property
    def is_configured(self) -> bool:
        """True if at least one provider has a key — the app only needs one to work."""
        return bool(self.openrouter_key or self.groq_key or self.gemini_key)

    @property
    def configured_providers(self) -> List[str]:
        names = []
        if self.openrouter_key:
            names.append("openrouter")
        if self.groq_key:
            names.append("groq")
        if self.gemini_key:
            names.append("gemini")
        return names

    # -------------------------------------------------------------------
    # Model candidate lists per provider (configured override goes first)
    # -------------------------------------------------------------------

    def _openrouter_candidates(self) -> List[str]:
        primary = self.openrouter_model or OPENROUTER_FREE_MODELS[0]
        return [primary] + [m for m in OPENROUTER_FREE_MODELS if m != primary]

    def _groq_candidates(self) -> List[str]:
        primary = self.groq_model or GROQ_FREE_MODELS[0]
        return [primary] + [m for m in GROQ_FREE_MODELS if m != primary]

    def _gemini_candidates(self) -> List[str]:
        primary = self.gemini_model or GEMINI_FREE_MODELS[0]
        return [primary] + [m for m in GEMINI_FREE_MODELS if m != primary]

    # -------------------------------------------------------------------
    # Non-streaming completion — used by explainer, code reviewer, and the
    # mock-interview engine (dialogue, hints, grading feedback).
    # -------------------------------------------------------------------

    def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1200,
        timeout: int = 20,
        max_candidates_per_provider: int = 2,
    ) -> Optional[str]:
        """Return assistant text from the first provider+model that responds, or None
        if every configured provider failed (callers fall back to static heuristics)."""
        if self.openrouter_key:
            text = self._openai_style_complete(
                OPENROUTER_BASE_URL, self.openrouter_key,
                self._openrouter_candidates()[:max_candidates_per_provider],
                messages, temperature, max_tokens, timeout,
                extra_headers={"HTTP-Referer": self.site_url, "X-Title": self.site_name},
            )
            if text:
                return text

        if self.groq_key:
            text = self._openai_style_complete(
                GROQ_BASE_URL, self.groq_key,
                self._groq_candidates()[:max_candidates_per_provider],
                messages, temperature, max_tokens, timeout,
            )
            if text:
                return text

        if self.gemini_key:
            text = self._gemini_complete(
                self._gemini_candidates()[:max_candidates_per_provider],
                messages, temperature, max_tokens, timeout,
            )
            if text:
                return text

        return None

    # -------------------------------------------------------------------
    # Streaming chat — used by the "Ask AI" mentor. Streams through
    # OpenRouter/Groq (both support real token streaming); if both are
    # down, degrades to a single non-streamed Gemini reply rather than
    # failing outright, so a full provider outage doesn't cut the user off.
    # -------------------------------------------------------------------

    def stream_chat(self, messages: List[Dict[str, str]], timeout: int = 60) -> Generator[str, None, None]:
        if not self.is_configured:
            raise RuntimeError(
                "AI Mentor isn't configured. Add OPENROUTER_API_KEY, GROQ_API_KEY, or "
                "GEMINI_API_KEY to your .env file (see .env.example) and restart the server."
            )

        last_error: Optional[Exception] = None

        if self.openrouter_key:
            try:
                yield from self._openai_style_stream(
                    OPENROUTER_BASE_URL, self.openrouter_key, self._openrouter_candidates(),
                    messages, timeout,
                    extra_headers={"HTTP-Referer": self.site_url, "X-Title": self.site_name},
                )
                return
            except RuntimeError as e:
                last_error = e

        if self.groq_key:
            try:
                yield from self._openai_style_stream(
                    GROQ_BASE_URL, self.groq_key, self._groq_candidates(), messages, timeout,
                )
                return
            except RuntimeError as e:
                last_error = e

        if self.gemini_key:
            text = self._gemini_complete(self._gemini_candidates(), messages, 0.5, 1500, timeout)
            if text:
                yield text
                return
            last_error = RuntimeError("Gemini fallback did not return a response.")

        raise last_error or RuntimeError("All AI providers are currently unavailable — try again shortly.")

    # -------------------------------------------------------------------
    # OpenAI-compatible request helpers (OpenRouter + Groq share this shape)
    # -------------------------------------------------------------------

    @staticmethod
    def _openai_style_complete(
        base_url: str,
        api_key: str,
        models: List[str],
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: int,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        headers.update(extra_headers or {})

        for model in models:
            try:
                resp = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    choices = resp.json().get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        if content and content.strip():
                            return content.strip()
            except Exception:
                continue
        return None

    @staticmethod
    def _openai_style_stream(
        base_url: str,
        api_key: str,
        models: List[str],
        messages: List[Dict[str, str]],
        timeout: int,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Generator[str, None, None]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        headers.update(extra_headers or {})

        last_error: Optional[RuntimeError] = None
        for model in models:
            try:
                resp = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json={"model": model, "messages": messages, "stream": True},
                    stream=True,
                    timeout=timeout,
                )
            except requests.RequestException as e:
                last_error = RuntimeError(f"Could not reach {base_url}: {e}")
                continue

            if resp.status_code != 200:
                last_error = RuntimeError(f"{base_url} error {resp.status_code} ({model}): {resp.text[:300]}")
                resp.close()
                continue

            # Healthy model found — stream it. No more fallback once real
            # content starts flowing back to the caller.
            with resp:
                for raw_line in resp.iter_lines(decode_unicode=True):
                    if not raw_line or not raw_line.startswith("data:"):
                        continue
                    data = raw_line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or [{}]
                    delta = choices[0].get("delta", {}) if choices else {}
                    content = delta.get("content")
                    if content:
                        yield content
            return

        raise last_error or RuntimeError(f"All models exhausted for {base_url}.")

    # -------------------------------------------------------------------
    # Gemini — different request/response shape (generateContent REST API)
    # -------------------------------------------------------------------

    @staticmethod
    def _to_gemini_payload(messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> Dict[str, Any]:
        system_parts = []
        contents = []
        for m in messages:
            role = m.get("role")
            text = m.get("content") or ""
            if not text:
                continue
            if role == "system":
                system_parts.append(text)
            else:
                contents.append({"role": "model" if role == "assistant" else "user", "parts": [{"text": text}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system_parts:
            payload["system_instruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        return payload

    @classmethod
    def _gemini_complete(
        cls,
        models: List[str],
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: int,
    ) -> Optional[str]:
        api_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
        if not api_key:
            return None
        payload = cls._to_gemini_payload(messages, temperature, max_tokens)

        for model in models:
            try:
                resp = requests.post(
                    f"{GEMINI_BASE_URL}/models/{model}:generateContent",
                    params={"key": api_key},
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates") or []
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts).strip()
                        if text:
                            return text
            except Exception:
                continue
        return None
