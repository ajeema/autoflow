"""
Provider-agnostic LLM client for AutoFlow LLM Judge.

Supports:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude 3, Claude 3.5 Sonnet, etc.)
- AWS Bedrock (multiple models)
- xAI (Grok)
- Ollama (local open-source models)
- Any provider via litellm unified interface
"""

import os
import asyncio
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    XAI = "xai"  # Grok
    OLLAMA = "ollama"
    AZURE_OPENAI = "azure_openai"
    CUSTOM = "custom"  # litellm custom endpoint


@dataclass
class LLMClientConfig:
    """Configuration for LLM client."""

    # Model selection
    model: str = "gpt-4"
    provider: Optional[LLMProvider] = None  # Auto-detect if None

    # API credentials
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    region: Optional[str] = None  # For Bedrock

    # Generation parameters
    temperature: float = 0.3
    max_tokens: int = 2000

    # Request timeout
    timeout: float = 30.0

    @classmethod
    def from_env(cls, model: str = None) -> "LLMClientConfig":
        """Load config from environment variables."""
        model = model or os.getenv("AUTOFLOW_LLM_MODEL", "gpt-4")

        # Auto-detect provider from model name
        provider = cls._detect_provider(model)

        # Provider-specific defaults
        if provider == LLMProvider.OPENAI:
            return cls(
                model=model,
                provider=provider,
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
            )
        elif provider == LLMProvider.ANTHROPIC:
            return cls(
                model=model,
                provider=provider,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
        elif provider == LLMProvider.BEDROCK:
            return cls(
                model=model,
                provider=provider,
                api_key=os.getenv("AWS_ACCESS_KEY_ID"),
                region=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            )
        elif provider == LLMProvider.XAI:
            return cls(
                model=model,
                provider=provider,
                api_key=os.getenv("XAI_API_KEY"),
            )
        elif provider == LLMProvider.OLLAMA:
            return cls(
                model=model,
                provider=provider,
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            )
        else:
            # Default to OpenAI
            return cls(
                model=model,
                provider=LLMProvider.OPENAI,
                api_key=os.getenv("OPENAI_API_KEY"),
            )

    @staticmethod
    def _detect_provider(model: str) -> LLMProvider:
        """Auto-detect provider from model name."""
        model_lower = model.lower()

        # AWS Bedrock models (check first as they contain dots/colons)
        # Formats: amazon.*, anthropic.*, ai21.*, cohere.*, meta.*, mistral.*, stability.*
        if (
            model_lower.startswith("amazon.")
            or model_lower.startswith("anthropic.")
            or model_lower.startswith("ai21.")
            or model_lower.startswith("cohere.")
            or model_lower.startswith("meta.")
            or model_lower.startswith("mistral.")
            or model_lower.startswith("stability.")
            or "bedrock" in model_lower
        ):
            return LLMProvider.BEDROCK

        # Anthropic models
        if model_lower.startswith("claude"):
            return LLMProvider.ANTHROPIC

        # xAI models (Grok)
        if model_lower.startswith("grok-"):
            return LLMProvider.XAI

        # Azure OpenAI
        if "azure" in model_lower:
            return LLMProvider.AZURE_OPENAI

        # Ollama models (local)
        # Must check after Bedrock as Bedrock models can contain colons
        if ":" in model_lower or model_lower.startswith("llama"):
            return LLMProvider.OLLAMA

        # Default to OpenAI (GPT models, etc.)
        return LLMProvider.OPENAI


class UniversalLLMClient:
    """
    Universal LLM client that works with any provider.

    Supports:
    - Direct provider clients (OpenAI, Anthropic, etc.)
    - litellm unified interface (optional)
    - Custom endpoints
    """

    def __init__(self, config: LLMClientConfig):
        self.config = config
        self._client = None
        self._provider = config.provider or LLMClientConfig._detect_provider(config.model)

    def _get_client(self):
        """Lazy-initialize the appropriate client."""
        if self._client is not None:
            return self._client

        if self._provider == LLMProvider.OPENAI:
            self._client = self._create_openai_client()
        elif self._provider == LLMProvider.ANTHROPIC:
            self._client = self._create_anthropic_client()
        elif self._provider == LLMProvider.BEDROCK:
            self._client = self._create_bedrock_client()
        elif self._provider == LLMProvider.XAI:
            self._client = self._create_xai_client()
        elif self._provider == LLMProvider.OLLAMA:
            self._client = self._create_ollama_client()
        else:
            raise ValueError(f"Unsupported provider: {self._provider}")

        return self._client

    def _create_openai_client(self):
        """Create OpenAI client."""
        try:
            from openai import OpenAI
            return OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )

    def _create_anthropic_client(self):
        """Create Anthropic client."""
        try:
            from anthropic import Anthropic
            return Anthropic(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
        except ImportError:
            raise ImportError(
                "Anthropic package not installed. Install with: pip install anthropic"
            )

    def _create_bedrock_client(self):
        """Create AWS Bedrock client."""
        try:
            import boto3
            return boto3.client(
                "bedrock-runtime",
                region_name=self.config.region,
                api_key=self.config.api_key,
            )
        except ImportError:
            raise ImportError(
                "boto3 package not installed. Install with: pip install boto3"
            )

    def _create_xai_client(self):
        """Create xAI (Grok) client."""
        try:
            from openai import OpenAI  # xAI uses OpenAI-compatible API
            return OpenAI(
                api_key=self.config.api_key,
                base_url="https://api.x.ai/v1",
                timeout=self.config.timeout,
            )
        except ImportError:
            raise ImportError(
                "OpenAI package not installed (required for xAI). Install with: pip install openai"
            )

    def _create_ollama_client(self):
        """Create Ollama client for local models."""
        try:
            from openai import OpenAI  # Ollama has OpenAI-compatible API
            return OpenAI(
                base_url=self.config.base_url or "http://localhost:11434/v1",
                timeout=self.config.timeout,
                # No API key needed for local Ollama
            )
        except ImportError:
            raise ImportError(
                "OpenAI package not installed (required for Ollama). Install with: pip install openai"
            )

    def chat_completion(
        self,
        messages: list[Dict[str, str]],
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Send chat completion request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            response_format: Optional {"type": "json_object"} for structured output

        Returns:
            The LLM response content
        """
        client = self._get_client()
        provider = self._provider

        try:
            if provider == LLMProvider.OPENAI:
                return self._openai_completion(client, messages, response_format)
            elif provider == LLMProvider.ANTHROPIC:
                return self._anthropic_completion(client, messages, response_format)
            elif provider == LLMProvider.BEDROCK:
                return self._bedrock_completion(client, messages, response_format)
            elif provider == LLMProvider.XAI:
                return self._xai_completion(client, messages, response_format)
            elif provider == LLMProvider.OLLAMA:
                return self._ollama_completion(client, messages, response_format)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

        except Exception as e:
            raise RuntimeError(f"LLM API call failed to {provider.value}: {e}")

    def _openai_completion(
        self,
        client,
        messages: list[Dict[str, str]],
        response_format: Optional[Dict[str, str]],
    ) -> str:
        """OpenAI chat completion."""
        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _anthropic_completion(
        self,
        client,
        messages: list[Dict[str, str]],
        response_format: Optional[Dict[str, str]],
    ) -> str:
        """Anthropic (Claude) chat completion."""
        # Convert messages to Anthropic format
        system_msg = None
        user_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)

        kwargs = {
            "model": self.config.model,
            "messages": user_messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        if system_msg:
            kwargs["system"] = system_msg

        # Anthropic doesn't support response_format like OpenAI
        # We rely on system prompt to request JSON
        response = client.messages.create(**kwargs)
        return response.content[0].text

    def _bedrock_completion(
        self,
        client,
        messages: list[Dict[str, str]],
        response_format: Optional[Dict[str, str]],
    ) -> str:
        """AWS Bedrock chat completion."""
        # Convert to Bedrock format
        system_msg = None
        user_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)

        inference_config = {
            "temperature": self.config.temperature,
            "maxTokens": self.config.max_tokens,
        }

        if system_msg:
            inference_config["system"] = system_msg

        # Bedrock ConverseCommand
        response = client.converse(
            modelId=self.config.model,
            messages=user_messages,
            inferenceConfig=inference_config,
        )

        return response["output"]["message"]["content"][0]["text"]

    def _xai_completion(
        self,
        client,
        messages: list[Dict[str, str]],
        response_format: Optional[Dict[str, str]],
    ) -> str:
        """xAI (Grok) chat completion - uses OpenAI-compatible API."""
        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _ollama_completion(
        self,
        client,
        messages: list[Dict[str, str]],
        response_format: Optional[Dict[str, str]],
    ) -> str:
        """Ollama (local models) chat completion."""
        # Ollama uses OpenAI-compatible API
        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "format": "json" if response_format else None,
        }

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content


def create_llm_client(
    model: str = None,
    api_key: str = None,
    base_url: str = None,
    provider: str = None,
    **kwargs,
) -> UniversalLLMClient:
    """
    Create an LLM client with auto-detected provider.

    Args:
        model: Model name (gpt-4, claude-3-sonnet, llama3, etc.)
        api_key: API key (auto-detected from env if not provided)
        base_url: Custom base URL for custom endpoints
        provider: Force specific provider (auto-detected from model name if not provided)
        **kwargs: Additional config options

    Returns:
        UniversalLLMClient instance

    Examples:
        # OpenAI GPT-4
        client = create_llm_client(model="gpt-4")

        # Anthropic Claude
        client = create_llm_client(model="claude-3-5-sonnet-20241022")

        # Ollama local model
        client = create_llm_client(model="llama3:8b")

        # AWS Bedrock
        client = create_llm_client(model="amazon.titan-text-express-v1")

        # xAI Grok
        client = create_llm_client(model="grok-beta")

        # With custom API key
        client = create_llm_client(
            model="claude-3-sonnet-20240229",
            api_key="sk-ant-..."
        )

        # With custom endpoint
        client = create_llm_client(
            model="phi-3",
            base_url="http://localhost:8000/v1",
        )
    """
    config = LLMClientConfig(
        model=model or "gpt-4",
        api_key=api_key,
        base_url=base_url,
        provider=LLMProvider(provider) if provider else None,
        **kwargs,
    )

    return UniversalLLMClient(config)


__all__ = [
    "LLMProvider",
    "LLMClientConfig",
    "UniversalLLMClient",
    "create_llm_client",
]
