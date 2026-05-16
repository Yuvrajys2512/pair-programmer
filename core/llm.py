import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


@dataclass
class LLMConfig:
    api_key: str
    model: str
    temperature: float = 0.7


def get_config() -> LLMConfig:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise RuntimeError(
            "GROQ_API_KEY is missing. Copy .env.example to .env and add your key "
            "from https://console.groq.com/keys"
        )
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return LLMConfig(api_key=api_key, model=model)


_client: Optional[Groq] = None


def get_client() -> Groq:
    """Singleton Groq client. Reused across agent calls."""
    global _client
    if _client is None:
        _client = Groq(api_key=get_config().api_key)
    return _client


def complete_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
) -> str:
    """Call the LLM and request a JSON response. Returns the raw JSON string."""
    cfg = get_config()
    client = get_client()
    resp = client.chat.completions.create(
        model=cfg.model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content or ""
