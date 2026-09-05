"""
Multi-Provider LLM Client for OCRMe pipeline.
Supports Google Gemini, OpenAI ChatGPT, Anthropic Claude, and Ollama (Local LLMs).
"""

import os
import json
import time
import re
import logging
import urllib.request
import urllib.error

# Try importing google.generativeai for native Gemini SDK fallback
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from src.prompts import (
    PROMPT_OCR_CORRECTION,
    PROMPT_CLASSIFY_DOCUMENT,
    PROMPT_PARSE_DOCUMENT,
    PROMPT_FULL_PIPELINE,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Base Provider Class
# ==============================================================================
class BaseLLMProvider:
    """Base interface for all LLM providers."""
    def call_api(self, prompt: str) -> str:
        raise NotImplementedError


# ==============================================================================
# Google Gemini Provider
# ==============================================================================
class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str = None, model_name: str = "gemini-3.6-flash", max_retries: int = 3):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model_name or os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
        self.max_retries = max_retries

        if not self.api_key:
            raise ValueError("Gemini API key is required.")

        if GENAI_AVAILABLE:
            genai.configure(api_key=self.api_key)
            try:
                self.model = genai.GenerativeModel(self.model_name)
            except Exception:
                self.model_name = "gemini-1.5-flash"
                self.model = genai.GenerativeModel(self.model_name)

    def call_api(self, prompt: str) -> str:
        if GENAI_AVAILABLE:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = self.model.generate_content(prompt)
                    if response.text:
                        return response.text.strip()
                except Exception as e:
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    raise e
        # REST API Fallback for Gemini
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()


# ==============================================================================
# OpenAI ChatGPT Provider
# ==============================================================================
class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str = None, model_name: str = "gpt-4o-mini", max_retries: int = 3):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model_name = model_name or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.max_retries = max_retries

        if not self.api_key:
            raise ValueError("OpenAI API key is required.")

    def call_api(self, prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        payload = json.dumps({
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=payload, headers=headers)
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise e


# ==============================================================================
# Anthropic Claude Provider
# ==============================================================================
class ClaudeProvider(BaseLLMProvider):
    def __init__(self, api_key: str = None, model_name: str = "claude-3-5-haiku-20241022", max_retries: int = 3):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model_name = model_name or os.environ.get("CLAUDE_MODEL", "claude-3-5-haiku-20241022")
        self.max_retries = max_retries

        if not self.api_key:
            raise ValueError("Anthropic API key is required.")

    def call_api(self, prompt: str) -> str:
        url = "https://api.anthropic.com/v1/messages"
        payload = json.dumps({
            "model": self.model_name,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=payload, headers=headers)
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["content"][0]["text"].strip()
            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise e


# ==============================================================================
# Ollama Local LLM Provider
# ==============================================================================
class OllamaProvider(BaseLLMProvider):
    def __init__(self, host: str = "http://localhost:11434", model_name: str = "llama3.1", max_retries: int = 2):
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.model_name = model_name or os.environ.get("OLLAMA_MODEL", "llama3.1")
        self.max_retries = max_retries

    def call_api(self, prompt: str) -> str:
        url = f"{self.host.rstrip('/')}/api/generate"
        payload = json.dumps({
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=payload, headers=headers)
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["response"].strip()
            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(1)
                    continue
                raise e


# ==============================================================================
# Unified Multi-Provider Client Wrapper
# ==============================================================================
class MultiProviderLLMClient:
    """
    Unified Client supporting Gemini, OpenAI (ChatGPT), Anthropic (Claude), and Ollama (Local).
    """

    def __init__(self, provider: str = "gemini", api_key: str = None, model_name: str = None, host: str = None):
        self.provider_name = provider.lower()
        self.api_key = api_key
        self.model_name = model_name

        if self.provider_name == "openai":
            self.provider = OpenAIProvider(api_key=api_key, model_name=model_name or "gpt-4o-mini")
        elif self.provider_name in ["claude", "anthropic"]:
            self.provider = ClaudeProvider(api_key=api_key, model_name=model_name or "claude-3-5-haiku-20241022")
        elif self.provider_name == "ollama":
            self.provider = OllamaProvider(host=host, model_name=model_name or "llama3.1")
        else:
            self.provider_name = "gemini"
            self.provider = GeminiProvider(api_key=api_key, model_name=model_name or "gemini-3.6-flash")

        logger.info(f"MultiProviderLLMClient initialized with provider: {self.provider_name}")

    def _call_api(self, prompt: str) -> str:
        return self.provider.call_api(prompt)

    def _parse_json_response(self, text: str) -> dict | list:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        json_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
        if json_block:
            try:
                return json.loads(json_block.group(1).strip())
            except json.JSONDecodeError:
                pass

        for start_char, end_char in [('{', '}'), ('[', ']')]:
            start_idx = text.find(start_char)
            end_idx = text.rfind(end_char)
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                try:
                    return json.loads(text[start_idx:end_idx + 1])
                except json.JSONDecodeError:
                    continue

        raise ValueError(f"Could not parse JSON from LLM response:\n{text[:500]}")

    def correct_ocr_text(self, raw_text: str) -> str:
        prompt = PROMPT_OCR_CORRECTION.format(raw_text=raw_text)
        return self._call_api(prompt)

    def classify_document(self, text: str) -> dict:
        prompt = PROMPT_CLASSIFY_DOCUMENT.format(text=text)
        response = self._call_api(prompt)
        return self._parse_json_response(response)

    def parse_document(self, text: str, doc_type: str, doc_subtype: str, detected_fields: list) -> dict | list:
        prompt = PROMPT_PARSE_DOCUMENT.format(
            text=text,
            doc_type=doc_type,
            doc_subtype=doc_subtype,
            detected_fields=", ".join(detected_fields),
        )
        response = self._call_api(prompt)
        return self._parse_json_response(response)

    def process_full(self, raw_text: str) -> dict:
        prompt = PROMPT_FULL_PIPELINE.format(raw_text=raw_text)
        response = self._call_api(prompt)
        result = self._parse_json_response(response)

        if "classification" not in result or "extracted_data" not in result:
            return self.process_three_step(raw_text)

        return result

    def process_three_step(self, raw_text: str) -> dict:
        corrected_text = self.correct_ocr_text(raw_text)
        classification = self.classify_document(corrected_text)
        extracted_data = self.parse_document(
            text=corrected_text,
            doc_type=classification.get("doc_type", "other"),
            doc_subtype=classification.get("doc_subtype", "Unknown"),
            detected_fields=classification.get("detected_fields", []),
        )

        return {
            "correction_applied": True,
            "classification": {
                "doc_type": classification.get("doc_type", "other"),
                "doc_subtype": classification.get("doc_subtype", "Unknown"),
                "confidence": classification.get("confidence", 0.0),
            },
            "extracted_data": extracted_data,
        }


# Maintain backward compatibility for existing code importing GeminiClient
GeminiClient = MultiProviderLLMClient


def is_llm_available(provider: str = "gemini") -> bool:
    provider = provider.lower()
    if provider == "openai":
        return bool(os.environ.get("OPENAI_API_KEY", ""))
    elif provider in ["claude", "anthropic"]:
        return bool(os.environ.get("ANTHROPIC_API_KEY", ""))
    elif provider == "ollama":
        return True
    return bool(os.environ.get("GEMINI_API_KEY", ""))
