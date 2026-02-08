from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from loguru import logger
import time

try:
    from openai import OpenAI
    import httpx
except ImportError:
    OpenAI = None
    httpx = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    import ollama
except ImportError:
    ollama = None


class LLMClient(ABC):
    """LLM 클라이언트 인터페이스"""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """텍스트 생성"""
        pass

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """대화형 생성"""
        pass

    def chat_with_usage(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """대화형 생성 + 토큰 사용량 반환"""
        # 기본 구현: 토큰 정보 없이 답변만 반환
        content = self.chat(messages, **kwargs)
        return {
            'content': content,
            'usage': None
        }


class OpenAIClient(LLMClient):
    """OpenAI GPT 클라이언트 (OpenAI API 호환 서버 지원)"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.1,
        max_tokens: int = 2000,
        base_url: Optional[str] = None
    ):
        if OpenAI is None:
            raise ImportError("openai package not installed. Run: pip install openai")

        # base_url이 제공되면 사용 (로컬 LLM 서버 지원)
        if base_url:
            # Ensure base_url ends with /v1
            normalized_base_url = base_url.rstrip("/")
            if not normalized_base_url.endswith("/v1"):
                normalized_base_url += "/v1"

            # 긴 타임아웃 및 재시도 설정 (외부 LLM API의 불안정성 대비)
            # Note: OpenAI SDK will create its own httpx client internally
            # Custom httpx.Client causes issues with uvicorn's async event loop
            self.client = OpenAI(
                api_key=api_key,
                base_url=normalized_base_url,
                timeout=120.0,  # 2분 타임아웃
                max_retries=5,   # 최대 5회 재시도
                http_client=None  # Let OpenAI SDK manage HTTP client
            )
            logger.info(f"Initialized OpenAI-compatible client (base_url={normalized_base_url}, model={model}, timeout=120s, max_retries=5)")
        else:
            self.client = OpenAI(api_key=api_key, timeout=60.0, max_retries=3)
            logger.info(f"Initialized OpenAI client (model={model})")

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, prompt: str, **kwargs) -> str:
        """텍스트 생성"""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, **kwargs)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """대화형 생성"""
        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)

        # Manual retry with exponential backoff (in addition to OpenAI SDK's built-in retries)
        max_manual_retries = 3
        base_delay = 2.0

        for attempt in range(max_manual_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

                content = response.choices[0].message.content
                return content

            except Exception as e:
                error_str = str(e).lower()
                is_retryable = any(code in error_str for code in ['502', '503', '504', 'timeout', 'connection'])

                if is_retryable and attempt < max_manual_retries:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"OpenAI API error (attempt {attempt + 1}/{max_manual_retries + 1}): {e}")
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"OpenAI API error (final attempt): {e}")
                    raise

    def chat_with_usage(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """대화형 생성 + 토큰 사용량 반환"""
        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)

        max_manual_retries = 3
        base_delay = 2.0

        for attempt in range(max_manual_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

                content = response.choices[0].message.content

                # 토큰 사용량 추출
                usage = None
                if hasattr(response, 'usage') and response.usage:
                    usage = {
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                        'total_tokens': response.usage.total_tokens
                    }

                return {
                    'content': content,
                    'usage': usage
                }

            except Exception as e:
                error_str = str(e).lower()
                is_retryable = any(code in error_str for code in ['502', '503', '504', 'timeout', 'connection'])

                if is_retryable and attempt < max_manual_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"OpenAI API error (attempt {attempt + 1}/{max_manual_retries + 1}): {e}")
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"OpenAI API error (final attempt): {e}")
                    raise


class OllamaClient(LLMClient):
    """Ollama 로컬 LLM 클라이언트 (QDoRA Adapter 지원)"""

    def __init__(
        self,
        model: str = "kosaul-q4",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        host: str = "http://localhost:11434"
    ):
        if ollama is None:
            raise ImportError("ollama package not installed. Run: pip install ollama")

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.host = host

        # Ollama 클라이언트 초기화
        self.client = ollama.Client(host=host)

        logger.info(f"Initialized Ollama client (model={model}, host={host})")

    def generate(self, prompt: str, **kwargs) -> str:
        """텍스트 생성"""
        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)

        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': temperature,
                    'num_predict': max_tokens
                }
            )
            return response['response']

        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """대화형 생성"""
        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)

        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                options={
                    'temperature': temperature,
                    'num_predict': max_tokens
                }
            )
            return response['message']['content']

        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise

    def load_adapter(self, adapter_name: str) -> bool:
        """
        QDoRA Adapter 로드

        Args:
            adapter_name: Adapter 이름 (예: "traffic", "criminal")
                         실제 모델명은 "lawlaw:{adapter_name}"으로 변환됨

        Returns:
            bool: 성공 여부

        Example:
            >>> client.load_adapter("traffic")
            >>> # model이 "lawlaw:traffic"으로 변경됨
        """
        try:
            adapter_model = f"lawlaw:{adapter_name}"

            # Adapter 모델이 존재하는지 확인
            models = self.list_models()
            if adapter_model not in models:
                logger.warning(f"Adapter '{adapter_model}' not found in Ollama. Available: {models}")
                return False

            # 모델 전환
            old_model = self.model
            self.model = adapter_model
            logger.info(f"Loaded adapter: {old_model} → {adapter_model}")

            return True

        except Exception as e:
            logger.error(f"Failed to load adapter '{adapter_name}': {e}")
            return False

    def unload_adapter(self) -> None:
        """
        Adapter 언로드 (Base Model로 복귀)

        Example:
            >>> client.load_adapter("traffic")
            >>> client.unload_adapter()  # kosaul-q4로 복귀
        """
        base_model = "kosaul-q4"  # 기본 모델
        old_model = self.model
        self.model = base_model
        logger.info(f"Unloaded adapter: {old_model} → {base_model}")

    def list_adapters(self) -> List[str]:
        """
        사용 가능한 Adapter 목록 조회

        Returns:
            List[str]: Adapter 이름 목록 (예: ["traffic", "criminal"])

        Example:
            >>> client.list_adapters()
            ['traffic', 'criminal', 'corporate']
        """
        try:
            models = self.list_models()

            # "lawlaw:" prefix를 가진 모델만 필터링
            adapters = [
                model.replace("lawlaw:", "").split(":")[0]
                for model in models
                if model.startswith("lawlaw:")
            ]

            return sorted(set(adapters))

        except Exception as e:
            logger.error(f"Failed to list adapters: {e}")
            return []

    def list_models(self) -> List[str]:
        """
        Ollama에 있는 모든 모델 목록 조회

        Returns:
            List[str]: 모델 이름 목록
        """
        try:
            response = self.client.list()
            models = [model['name'] for model in response.get('models', [])]
            return models

        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def get_current_model(self) -> str:
        """현재 사용 중인 모델 이름 반환"""
        return self.model

    def is_adapter_loaded(self) -> bool:
        """Adapter가 로드되었는지 확인"""
        return self.model.startswith("lawlaw:")


class AnthropicClient(LLMClient):
    """Anthropic Claude 클라이언트"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-opus-20240229",
        temperature: float = 0.1,
        max_tokens: int = 2000
    ):
        if Anthropic is None:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        logger.info(f"Initialized Anthropic client (model={model})")

    def generate(self, prompt: str, **kwargs) -> str:
        """텍스트 생성"""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, **kwargs)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """대화형 생성"""
        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)

        try:
            response = self.client.messages.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response.content[0].text
            return content

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


def create_llm_client(
    provider: str,
    api_key: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> LLMClient:
    """
    LLM 클라이언트 팩토리 함수

    Args:
        provider: 'openai', 'anthropic', or 'ollama'
        api_key: API 키 (ollama의 경우 필요 없음)
        model: 모델 이름 (None이면 기본값 사용)
        base_url: Base URL for OpenAI-compatible endpoints (optional)
        **kwargs: 추가 파라미터

    Returns:
        LLMClient 인스턴스
    """
    if provider.lower() == "openai":
        default_model = "gpt-4-turbo-preview"
        return OpenAIClient(
            api_key=api_key,
            model=model or default_model,
            base_url=base_url,
            **kwargs
        )
    elif provider.lower() == "anthropic":
        default_model = "claude-3-opus-20240229"
        return AnthropicClient(
            api_key=api_key,
            model=model or default_model,
            **kwargs
        )
    elif provider.lower() == "ollama":
        default_model = "kosaul-q4"
        return OllamaClient(
            model=model or default_model,
            **kwargs
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")
