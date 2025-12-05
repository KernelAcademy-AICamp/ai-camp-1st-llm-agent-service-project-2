from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from loguru import logger
import time
import os
import json


# =============================================================================
# Tool Use 관련 데이터 클래스
# =============================================================================

@dataclass
class ToolCall:
    """도구 호출 정보"""
    id: str
    name: str
    arguments: Dict[str, Any]

    @classmethod
    def from_openai(cls, tool_call) -> "ToolCall":
        """OpenAI tool_call 객체에서 변환"""
        return cls(
            id=tool_call.id,
            name=tool_call.function.name,
            arguments=json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
        )

    @classmethod
    def from_anthropic(cls, tool_use_block) -> "ToolCall":
        """Anthropic tool_use 블록에서 변환"""
        return cls(
            id=tool_use_block.id,
            name=tool_use_block.name,
            arguments=tool_use_block.input
        )


@dataclass
class ToolUseResponse:
    """Tool Use 응답 구조"""
    content: Optional[str] = None           # 텍스트 응답 (도구 미사용시)
    tool_calls: List[ToolCall] = field(default_factory=list)  # 도구 호출 목록
    stop_reason: str = "end_turn"           # "end_turn" | "tool_use"
    usage: Optional[Dict[str, int]] = None  # 토큰 사용량

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

    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_choice: str = "auto",
        **kwargs
    ) -> ToolUseResponse:
        """
        Tool Use 지원 대화형 생성

        Args:
            messages: 대화 메시지 목록
            tools: JSON Schema 형식의 도구 정의 목록
            tool_choice: "auto" | "none" | "required" | {"type": "tool", "name": "..."}
            **kwargs: 추가 파라미터 (temperature, max_tokens 등)

        Returns:
            ToolUseResponse:
                - content: 텍스트 응답 (도구 미사용시)
                - tool_calls: 도구 호출 목록 (도구 사용시)
                - stop_reason: "end_turn" | "tool_use"
                - usage: 토큰 사용량
        """
        # 기본 구현: 도구 미지원 (서브클래스에서 오버라이드)
        raise NotImplementedError("This LLM client does not support tool use")


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

    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_choice: str = "auto",
        **kwargs
    ) -> ToolUseResponse:
        """
        Tool Use 지원 대화형 생성 (OpenAI)

        Args:
            messages: 대화 메시지 목록
            tools: OpenAI tools 형식의 도구 정의 목록
                   [{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}]
            tool_choice: "auto" | "none" | "required"
            **kwargs: temperature, max_tokens 등

        Returns:
            ToolUseResponse
        """
        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)

        max_manual_retries = 3
        base_delay = 2.0

        for attempt in range(max_manual_retries + 1):
            try:
                # OpenAI API 호출 (tools 파라미터 포함)
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice=tool_choice if tools else None,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

                message = response.choices[0].message

                # 토큰 사용량
                usage = None
                if hasattr(response, 'usage') and response.usage:
                    usage = {
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                        'total_tokens': response.usage.total_tokens
                    }

                # Tool Use 여부 확인
                if message.tool_calls:
                    tool_calls = [ToolCall.from_openai(tc) for tc in message.tool_calls]
                    return ToolUseResponse(
                        content=message.content,
                        tool_calls=tool_calls,
                        stop_reason="tool_use",
                        usage=usage
                    )
                else:
                    return ToolUseResponse(
                        content=message.content,
                        tool_calls=[],
                        stop_reason="end_turn",
                        usage=usage
                    )

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
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.1,
        max_tokens: int = 4096
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

    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_choice: str = "auto",
        **kwargs
    ) -> ToolUseResponse:
        """
        Tool Use 지원 대화형 생성 (Anthropic Claude)

        Args:
            messages: 대화 메시지 목록
            tools: Anthropic tools 형식의 도구 정의 목록
                   [{"name": ..., "description": ..., "input_schema": {...}}]
            tool_choice: "auto" | "none" | "any" | {"type": "tool", "name": "..."}
            **kwargs: temperature, max_tokens 등

        Returns:
            ToolUseResponse
        """
        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)
        system = kwargs.get('system', None)

        try:
            # tool_choice 변환 (OpenAI 형식 → Anthropic 형식)
            anthropic_tool_choice = {"type": "auto"}
            if tool_choice == "none":
                anthropic_tool_choice = {"type": "none"}  # 도구 사용 안 함
            elif tool_choice == "required" or tool_choice == "any":
                anthropic_tool_choice = {"type": "any"}  # 반드시 도구 사용
            elif isinstance(tool_choice, dict):
                anthropic_tool_choice = tool_choice

            # Anthropic API 호출
            create_kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if tools:
                create_kwargs["tools"] = tools
                create_kwargs["tool_choice"] = anthropic_tool_choice

            if system:
                create_kwargs["system"] = system

            response = self.client.messages.create(**create_kwargs)

            # 토큰 사용량
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    'prompt_tokens': response.usage.input_tokens,
                    'completion_tokens': response.usage.output_tokens,
                    'total_tokens': response.usage.input_tokens + response.usage.output_tokens
                }

            # 응답 파싱
            text_content = None
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    text_content = block.text
                elif block.type == "tool_use":
                    tool_calls.append(ToolCall.from_anthropic(block))

            # stop_reason 결정
            stop_reason = "end_turn"
            if response.stop_reason == "tool_use" or tool_calls:
                stop_reason = "tool_use"

            return ToolUseResponse(
                content=text_content,
                tool_calls=tool_calls,
                stop_reason=stop_reason,
                usage=usage
            )

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


# 싱글톤 LLM 클라이언트 캐시
_llm_client_cache: Optional[LLMClient] = None


def get_llm_client(model_name: Optional[str] = None) -> LLMClient:
    """
    환경변수 기반으로 LLM 클라이언트를 생성하고 반환합니다.
    싱글톤 패턴으로 동일한 클라이언트를 재사용합니다.

    Args:
        model_name: 사용할 모델명 (선택). 지정하면 새 클라이언트 생성.

    환경변수:
        - LLM_PROVIDER: 'openai', 'anthropic', 'ollama' (기본값: 'openai')
        - LLM_API_KEY 또는 OPENAI_API_KEY 또는 ANTHROPIC_API_KEY
        - LLM_MODEL: 모델명 (선택)
        - LLM_BASE_URL: OpenAI 호환 엔드포인트 (선택)

    Returns:
        LLMClient 인스턴스
    """
    global _llm_client_cache

    # 환경변수에서 설정 읽기
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    env_model = os.getenv("LLM_MODEL")
    base_url = os.getenv("LLM_BASE_URL")

    # API 키 결정
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "")
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
        else:
            api_key = ""  # ollama는 API 키 불필요

    # model_name이 지정되면 새 클라이언트 생성 (캐시 안 함)
    if model_name is not None:
        return create_llm_client(
            provider=provider,
            api_key=api_key,
            model=model_name,
            base_url=base_url
        )

    # 캐시된 클라이언트 반환
    if _llm_client_cache is not None:
        return _llm_client_cache

    # 클라이언트 생성 및 캐시
    _llm_client_cache = create_llm_client(
        provider=provider,
        api_key=api_key,
        model=env_model,
        base_url=base_url
    )

    logger.info(f"Created LLM client: provider={provider}, model={env_model or 'default'}")
    return _llm_client_cache


def reset_llm_client():
    """LLM 클라이언트 캐시를 리셋합니다. (테스트용)"""
    global _llm_client_cache
    _llm_client_cache = None
