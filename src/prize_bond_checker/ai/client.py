"""AI provider abstraction with auto-detection and graceful fallback."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

import requests

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


class AIProvider(Protocol):
    name: str

    def complete(self, prompt: str, system: str = "") -> str: ...


@dataclass
class ProviderInfo:
    name: str
    model: str


class OllamaProvider:
    name = "ollama"

    def __init__(self, host: str, model: str) -> None:
        self.host = host.rstrip("/")
        self.model = model

    @classmethod
    def from_env(cls) -> OllamaProvider | None:
        host = os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
        model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        try:
            response = requests.get(f"{host.rstrip('/')}/api/tags", timeout=2)
            if response.ok:
                return cls(host=host, model=model)
        except requests.RequestException:
            return None
        return None

    def complete(self, prompt: str, system: str = "") -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system or "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        response = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"].strip()

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(name=self.name, model=self.model)


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    @classmethod
    def from_env(cls) -> OpenAIProvider | None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        return cls(api_key=api_key, model=model)

    def complete(self, prompt: str, system: str = "") -> str:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system or "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(name=self.name, model=self.model)


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    @classmethod
    def from_env(cls) -> GeminiProvider | None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        return cls(api_key=api_key, model=model)

    def complete(self, prompt: str, system: str = "") -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        response = requests.post(
            url,
            json={
                "systemInstruction": {"parts": [{"text": system or "You are a helpful assistant."}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(name=self.name, model=self.model)


def get_ai_provider(preferred: str = "auto") -> AIProvider | None:
    providers: dict[str, type] = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
    }

    if preferred != "auto":
        factory = providers.get(preferred)
        if factory is None:
            raise ValueError(f"Unknown AI provider: {preferred}")
        provider = factory.from_env()
        return provider

    for name in ("ollama", "gemini", "openai"):
        provider = providers[name].from_env()
        if provider is not None:
            return provider

    return None


def provider_label(provider: AIProvider | None) -> str:
    if provider is None:
        return "none"
    info = provider.info if hasattr(provider, "info") else ProviderInfo(provider.name, "unknown")
    return f"{info.name} ({info.model})"


def extract_json_object(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())
