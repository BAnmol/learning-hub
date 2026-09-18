import json
import os
from typing import Dict, Generator, List, Optional

import requests

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Free-tier models to fall back through if the configured one is rate-limited
# (common on OpenRouter's $0 pool — shared across every free user). Order
# matters: openrouter/free is OpenRouter's own auto-router across whichever
# free model is healthy right now, so it goes first as the most resilient
# single option; the rest are concrete large models observed to work well.
FREE_FALLBACK_MODELS = [
    "openrouter/free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "z-ai/glm-5.2:free",
    "google/gemma-4-31b-it:free",
]


class OpenRouterClient:
    """Thin wrapper around OpenRouter's OpenAI-compatible Chat Completions API.

    Powers the "Ask AI" mentor chat (streamed responses). Trending AI News is
    handled separately (see ai_news_aggregator.py) from free, keyless, public
    APIs — it does not use OpenRouter at all, so it works even without a key
    or credits.

    Requires OPENROUTER_API_KEY to be set (see .env.example). Raises
    RuntimeError with a user-safe message on misconfiguration or upstream
    failure — callers surface that message directly to the UI instead of
    crashing, since this integration is optional at deploy time.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.chat_model = os.getenv("OPENROUTER_CHAT_MODEL", "openrouter/free").strip()
        # OpenRouter uses these two headers purely for attribution/leaderboard
        # purposes on their end — optional, but good practice to send.
        self.site_url = os.getenv("OPENROUTER_SITE_URL", "http://127.0.0.1:5000").strip()
        self.site_name = os.getenv("OPENROUTER_SITE_NAME", "Brainfreeze Algos").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name,
        }

    def _require_configured(self) -> None:
        if not self.is_configured:
            raise RuntimeError(
                "AI Mentor isn't configured. Add OPENROUTER_API_KEY to your .env file "
                "(see .env.example) and restart the server."
            )

    def stream_chat(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Generator[str, None, None]:
        """Yield incremental assistant text chunks from a streaming completion.

        Tries the configured model first, then falls back through
        FREE_FALLBACK_MODELS if a candidate is rate-limited or errors — all
        before any content has been yielded, so a fallback never produces a
        visible glitch mid-reply.
        """
        self._require_configured()

        primary = model or self.chat_model
        candidates = [primary] + [m for m in FREE_FALLBACK_MODELS if m != primary]

        last_error: Optional[RuntimeError] = None
        for candidate_model in candidates:
            payload = {"model": candidate_model, "messages": messages, "stream": True}

            try:
                resp = requests.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                    stream=True,
                    timeout=60,
                )
            except requests.RequestException as e:
                last_error = RuntimeError(f"Could not reach OpenRouter: {e}")
                continue

            if resp.status_code != 200:
                last_error = RuntimeError(f"OpenRouter error {resp.status_code} ({candidate_model}): {resp.text[:300]}")
                resp.close()
                continue

            # Found a healthy model — stream it. No more fallback once we
            # start yielding real content back to the caller.
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

        raise last_error or RuntimeError("All AI models are currently unavailable — try again shortly.")
