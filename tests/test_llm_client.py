"""Tests for UniversalLLMClient (provider-agnostic LLM client)."""

import pytest
from autoflow.llm.client import (
    LLMProvider,
    LLMClientConfig,
    UniversalLLMClient,
    create_llm_client,
)


class TestLLMProviderDetection:
    """Test automatic provider detection from model names."""

    def test_detect_openai(self):
        """Test OpenAI models are detected correctly."""
        assert LLMClientConfig._detect_provider("gpt-4") == LLMProvider.OPENAI
        assert LLMClientConfig._detect_provider("gpt-3.5-turbo") == LLMProvider.OPENAI
        assert LLMClientConfig._detect_provider("gpt-4-turbo-preview") == LLMProvider.OPENAI

    def test_detect_anthropic(self):
        """Test Anthropic models are detected correctly."""
        assert LLMClientConfig._detect_provider("claude-3-opus-20240229") == LLMProvider.ANTHROPIC
        assert LLMClientConfig._detect_provider("claude-3-5-sonnet-20241022") == LLMProvider.ANTHROPIC
        assert LLMClientConfig._detect_provider("claude-3-haiku-20240307") == LLMProvider.ANTHROPIC

    def test_detect_bedrock(self):
        """Test AWS Bedrock models are detected correctly."""
        assert LLMClientConfig._detect_provider("amazon.titan-text-express-v1") == LLMProvider.BEDROCK
        assert LLMClientConfig._detect_provider("anthropic.claude-3-sonnet-20240229-v1:0") == LLMProvider.BEDROCK
        assert LLMClientConfig._detect_provider("bedrock-model") == LLMProvider.BEDROCK

    def test_detect_xai(self):
        """Test xAI (Grok) models are detected correctly."""
        assert LLMClientConfig._detect_provider("grok-beta") == LLMProvider.XAI
        assert LLMClientConfig._detect_provider("grok-1") == LLMProvider.XAI

    def test_detect_ollama(self):
        """Test Ollama models are detected correctly."""
        assert LLMClientConfig._detect_provider("llama3:8b") == LLMProvider.OLLAMA
        assert LLMClientConfig._detect_provider("deepseek-coder:6.7b") == LLMProvider.OLLAMA
        assert LLMClientConfig._detect_provider("llama2") == LLMProvider.OLLAMA

    def test_detect_azure_openai(self):
        """Test Azure OpenAI models are detected correctly."""
        assert LLMClientConfig._detect_provider("azure/gpt-4") == LLMProvider.AZURE_OPENAI
        assert LLMClientConfig._detect_provider("azure/gpt-3.5-turbo") == LLMProvider.AZURE_OPENAI

    def test_default_to_openai(self):
        """Test unknown models default to OpenAI."""
        assert LLMClientConfig._detect_provider("unknown-model") == LLMProvider.OPENAI
        assert LLMClientConfig._detect_provider("custom-model") == LLMProvider.OPENAI


class TestLLMClientConfig:
    """Test LLM client configuration."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = LLMClientConfig()
        assert config.model == "gpt-4"
        assert config.provider is None
        assert config.temperature == 0.3
        assert config.max_tokens == 2000
        assert config.timeout == 30.0

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = LLMClientConfig(
            model="claude-3-5-sonnet-20241022",
            temperature=0.5,
            max_tokens=4000,
        )
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.temperature == 0.5
        assert config.max_tokens == 4000

    def test_from_env_openai(self):
        """Test loading OpenAI config from environment."""
        import os

        # Save original values
        original_key = os.environ.get("OPENAI_API_KEY")
        original_base = os.environ.get("OPENAI_BASE_URL")

        try:
            os.environ["OPENAI_API_KEY"] = "sk-test-key"
            os.environ["OPENAI_BASE_URL"] = "https://api.test.com"

            config = LLMClientConfig.from_env("gpt-4")
            assert config.model == "gpt-4"
            assert config.provider == LLMProvider.OPENAI
            assert config.api_key == "sk-test-key"
            assert config.base_url == "https://api.test.com"

        finally:
            # Restore original values
            if original_key is not None:
                os.environ["OPENAI_API_KEY"] = original_key
            else:
                os.environ.pop("OPENAI_API_KEY", None)

            if original_base is not None:
                os.environ["OPENAI_BASE_URL"] = original_base
            else:
                os.environ.pop("OPENAI_BASE_URL", None)

    def test_from_env_anthropic(self):
        """Test loading Anthropic config from environment."""
        import os

        # Save original values
        original_key = os.environ.get("ANTHROPIC_API_KEY")

        try:
            os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

            config = LLMClientConfig.from_env("claude-3-5-sonnet-20241022")
            assert config.model == "claude-3-5-sonnet-20241022"
            assert config.provider == LLMProvider.ANTHROPIC
            assert config.api_key == "sk-ant-test-key"

        finally:
            # Restore original values
            if original_key is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_key
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_from_env_ollama(self):
        """Test loading Ollama config from environment."""
        import os

        # Save original values
        original_base = os.environ.get("OLLAMA_BASE_URL")

        try:
            os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

            config = LLMClientConfig.from_env("llama3:8b")
            assert config.model == "llama3:8b"
            assert config.provider == LLMProvider.OLLAMA
            assert config.base_url == "http://localhost:11434"

        finally:
            # Restore original values
            if original_base is not None:
                os.environ["OLLAMA_BASE_URL"] = original_base
            else:
                os.environ.pop("OLLAMA_BASE_URL", None)


class TestCreateLLMClient:
    """Test create_llm_client factory function."""

    def test_create_openai_client(self):
        """Test creating OpenAI client."""
        client = create_llm_client(model="gpt-4")
        assert client.config.model == "gpt-4"
        assert client._provider == LLMProvider.OPENAI

    def test_create_anthropic_client(self):
        """Test creating Anthropic client."""
        client = create_llm_client(model="claude-3-5-sonnet-20241022")
        assert client.config.model == "claude-3-5-sonnet-20241022"
        assert client._provider == LLMProvider.ANTHROPIC

    def test_create_ollama_client(self):
        """Test creating Ollama client."""
        client = create_llm_client(model="llama3:8b")
        assert client.config.model == "llama3:8b"
        assert client._provider == LLMProvider.OLLAMA

    def test_create_with_custom_config(self):
        """Test creating client with custom configuration."""
        client = create_llm_client(
            model="gpt-4",
            api_key="sk-test-key",
            temperature=0.7,
            max_tokens=3000,
        )
        assert client.config.model == "gpt-4"
        assert client.config.api_key == "sk-test-key"
        assert client.config.temperature == 0.7
        assert client.config.max_tokens == 3000

    def test_create_with_explicit_provider(self):
        """Test creating client with explicit provider."""
        from autoflow.llm.client import LLMProvider

        client = create_llm_client(
            model="custom-model",
            provider="anthropic",
        )
        assert client._provider == LLMProvider.ANTHROPIC


class TestUniversalLLMClient:
    """Test UniversalLLMClient class."""

    def test_client_initialization(self):
        """Test client is initialized correctly."""
        config = LLMClientConfig(model="gpt-4")
        client = UniversalLLMClient(config)
        assert client.config is config
        assert client._provider == LLMProvider.OPENAI
        assert client._client is None  # Lazy initialization

    def test_openai_client_creation(self):
        """Test OpenAI client can be created."""
        config = LLMClientConfig(model="gpt-4")
        client = UniversalLLMClient(config)

        # This will fail if openai is not installed, which is expected
        try:
            underlying_client = client._get_client()
            assert underlying_client is not None
        except ImportError:
            # Expected if openai package is not installed
            pass

    def test_anthropic_client_creation(self):
        """Test Anthropic client can be created."""
        config = LLMClientConfig(model="claude-3-5-sonnet-20241022")
        client = UniversalLLMClient(config)

        # This will fail if anthropic is not installed, which is expected
        try:
            underlying_client = client._get_client()
            assert underlying_client is not None
        except ImportError:
            # Expected if anthropic package is not installed
            pass

    def test_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises ValueError."""
        from autoflow.llm.client import LLMProvider

        config = LLMClientConfig(
            model="test-model",
            provider=LLMProvider.CUSTOM,
        )
        client = UniversalLLMClient(config)
        client._provider = LLMProvider.CUSTOM

        with pytest.raises(ValueError, match="Unsupported provider"):
            client._get_client()
