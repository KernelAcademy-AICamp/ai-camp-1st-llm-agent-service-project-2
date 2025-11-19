from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from loguru import logger

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

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


class OpenAIClient(LLMClient):
    """OpenAI GPT 클라이언트"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.1,
        max_tokens: int = 2000
    ):
        if OpenAI is None:
            raise ImportError("openai package not installed. Run: pip install openai")

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        logger.info(f"Initialized OpenAI client (model={model})")

    def generate(self, prompt: str, **kwargs) -> str:
        """텍스트 생성"""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, **kwargs)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """대화형 생성"""
        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)

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
            logger.error(f"OpenAI API error: {e}")
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
    **kwargs
) -> LLMClient:
    """
    LLM 클라이언트 팩토리 함수

    Args:
        provider: 'openai', 'anthropic', or 'ollama'
        api_key: API 키 (ollama의 경우 필요 없음)
        model: 모델 이름 (None이면 기본값 사용)
        **kwargs: 추가 파라미터

    Returns:
        LLMClient 인스턴스
    """
    if provider.lower() == "openai":
        default_model = "gpt-4-turbo-preview"
        return OpenAIClient(
            api_key=api_key,
            model=model or default_model,
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
