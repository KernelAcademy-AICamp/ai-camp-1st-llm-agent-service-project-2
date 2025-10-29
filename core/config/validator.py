"""
Configuration validation for RAG experiments.
Validates config files before experiment execution to prevent runtime errors.
"""

import os
from typing import Dict, Any, List, Tuple, Optional


class ConfigValidator:
    """Validator for RAG experiment configurations."""

    # Supported values for each configuration option
    VALID_CHUNKING_STRATEGIES = ['fixed', 'semantic', 'recursive', 'sliding_window']
    VALID_EMBEDDING_TYPES = ['openai', 'huggingface']
    VALID_VECTOR_STORE_TYPES = ['faiss', 'chroma', 'qdrant']
    VALID_RETRIEVAL_METHODS = ['similarity', 'mmr', 'hybrid']
    VALID_LLM_PROVIDERS = ['openai', 'gemini', 'anthropic']
    VALID_FAISS_INDEX_TYPES = ['flat', 'ivf', 'hnsw']

    def __init__(self):
        """Initialize the validator."""
        self.errors = []
        self.warnings = []

    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a configuration dictionary.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        # Validate each section
        self._validate_experiment_metadata(config)
        self._validate_data_config(config)
        self._validate_chunking_config(config)
        self._validate_embedding_config(config)
        self._validate_vector_store_config(config)
        self._validate_retrieval_config(config)
        self._validate_generation_config(config)
        self._validate_evaluation_config(config)

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def _validate_experiment_metadata(self, config: Dict[str, Any]):
        """Validate experiment metadata."""
        if 'experiment_name' not in config:
            self.warnings.append("Missing 'experiment_name' - using default")

        if 'description' not in config:
            self.warnings.append("Missing 'description' - experiment purpose unclear")

    def _validate_data_config(self, config: Dict[str, Any]):
        """Validate data configuration."""
        data_config = config.get('data', {})

        # Check data source
        use_real_data = data_config.get('use_real_data', False)

        if use_real_data:
            # Validate real data configuration
            split = data_config.get('split', 'all')
            if split not in ['training', 'validation', 'all']:
                self.errors.append(f"Invalid data split '{split}'. Must be 'training', 'validation', or 'all'")

            max_per_type = data_config.get('max_per_type')
            if max_per_type is not None and (not isinstance(max_per_type, int) or max_per_type <= 0):
                self.errors.append(f"Invalid max_per_type '{max_per_type}'. Must be a positive integer or null")
        else:
            # Check if data path exists
            data_path = data_config.get('path')
            if data_path and not os.path.exists(data_path):
                self.warnings.append(f"Data path '{data_path}' does not exist - will use sample data")

    def _validate_chunking_config(self, config: Dict[str, Any]):
        """Validate chunking configuration."""
        chunking_config = config.get('chunking', {})

        if not chunking_config:
            self.errors.append("Missing 'chunking' configuration")
            return

        # Validate strategy
        strategy = chunking_config.get('strategy', 'fixed')
        if strategy not in self.VALID_CHUNKING_STRATEGIES:
            self.errors.append(
                f"Invalid chunking strategy '{strategy}'. "
                f"Must be one of: {', '.join(self.VALID_CHUNKING_STRATEGIES)}"
            )

        # Validate chunk size
        chunk_size = chunking_config.get('chunk_size', 512)
        if not isinstance(chunk_size, int) or not (50 <= chunk_size <= 4000):
            self.errors.append(
                f"Invalid chunk_size '{chunk_size}'. Must be an integer between 50 and 4000"
            )

        # Validate overlap
        overlap = chunking_config.get('overlap', 50)
        if not isinstance(overlap, int) or overlap < 0 or overlap >= chunk_size:
            self.errors.append(
                f"Invalid overlap '{overlap}'. Must be a non-negative integer less than chunk_size"
            )

        # Strategy-specific validation
        if strategy == 'semantic':
            threshold = chunking_config.get('threshold', 0.8)
            if not isinstance(threshold, (int, float)) or not (0.0 <= threshold <= 1.0):
                self.errors.append(f"Invalid semantic threshold '{threshold}'. Must be between 0.0 and 1.0")

        elif strategy == 'sliding_window':
            step_size = chunking_config.get('step_size', 256)
            if not isinstance(step_size, int) or step_size <= 0:
                self.errors.append(f"Invalid step_size '{step_size}'. Must be a positive integer")

    def _validate_embedding_config(self, config: Dict[str, Any]):
        """Validate embedding configuration."""
        embedding_config = config.get('embedding', {})

        if not embedding_config:
            self.errors.append("Missing 'embedding' configuration")
            return

        # Validate type
        emb_type = embedding_config.get('type', 'openai')
        if emb_type not in self.VALID_EMBEDDING_TYPES:
            self.errors.append(
                f"Invalid embedding type '{emb_type}'. "
                f"Must be one of: {', '.join(self.VALID_EMBEDDING_TYPES)}"
            )

        # Validate model
        model = embedding_config.get('model')
        if not model:
            self.errors.append("Missing embedding 'model' name")

        # Type-specific validation
        if emb_type == 'openai':
            api_key = embedding_config.get('api_key') or os.getenv('OPENAI_API_KEY')
            if not api_key:
                self.errors.append(
                    "Missing OpenAI API key. Set 'api_key' in config or OPENAI_API_KEY environment variable"
                )

        elif emb_type == 'huggingface':
            device = embedding_config.get('device', 'cpu')
            if device not in ['cpu', 'cuda', 'mps']:
                self.warnings.append(
                    f"Unusual device '{device}'. Typically 'cpu', 'cuda', or 'mps'"
                )

            batch_size = embedding_config.get('batch_size', 32)
            if not isinstance(batch_size, int) or batch_size <= 0:
                self.errors.append(f"Invalid batch_size '{batch_size}'. Must be a positive integer")

    def _validate_vector_store_config(self, config: Dict[str, Any]):
        """Validate vector store configuration."""
        vector_config = config.get('vector_store', {})

        if not vector_config:
            self.errors.append("Missing 'vector_store' configuration")
            return

        # Validate type
        store_type = vector_config.get('type', 'faiss')
        if store_type not in self.VALID_VECTOR_STORE_TYPES:
            self.errors.append(
                f"Invalid vector_store type '{store_type}'. "
                f"Must be one of: {', '.join(self.VALID_VECTOR_STORE_TYPES)}"
            )

        # Type-specific validation
        if store_type == 'faiss':
            index_type = vector_config.get('index_type', 'flat')
            if index_type not in self.VALID_FAISS_INDEX_TYPES:
                self.errors.append(
                    f"Invalid FAISS index_type '{index_type}'. "
                    f"Must be one of: {', '.join(self.VALID_FAISS_INDEX_TYPES)}"
                )

            if index_type == 'ivf':
                nlist = vector_config.get('nlist', 100)
                if not isinstance(nlist, int) or nlist <= 0:
                    self.errors.append(f"Invalid nlist '{nlist}'. Must be a positive integer")

        elif store_type == 'chroma':
            if not vector_config.get('persist_directory'):
                self.warnings.append("No persist_directory set for ChromaDB - data will be in-memory only")

        elif store_type == 'qdrant':
            if not vector_config.get('host'):
                self.warnings.append("No Qdrant host specified - using localhost")

    def _validate_retrieval_config(self, config: Dict[str, Any]):
        """Validate retrieval configuration."""
        retrieval_config = config.get('retrieval', {})

        if not retrieval_config:
            self.errors.append("Missing 'retrieval' configuration")
            return

        # Validate method
        method = retrieval_config.get('method', 'similarity')
        if method not in self.VALID_RETRIEVAL_METHODS:
            self.errors.append(
                f"Invalid retrieval method '{method}'. "
                f"Must be one of: {', '.join(self.VALID_RETRIEVAL_METHODS)}"
            )

        # Validate top_k
        top_k = retrieval_config.get('top_k', 5)
        if not isinstance(top_k, int) or not (1 <= top_k <= 100):
            self.errors.append(f"Invalid top_k '{top_k}'. Must be an integer between 1 and 100")

        # Method-specific validation
        if method == 'mmr':
            lambda_mult = retrieval_config.get('lambda_mult', 0.5)
            if not isinstance(lambda_mult, (int, float)) or not (0.0 <= lambda_mult <= 1.0):
                self.errors.append(f"Invalid lambda_mult '{lambda_mult}'. Must be between 0.0 and 1.0")

        elif method == 'hybrid':
            bm25_weight = retrieval_config.get('bm25_weight', 0.3)
            if not isinstance(bm25_weight, (int, float)) or not (0.0 <= bm25_weight <= 1.0):
                self.errors.append(f"Invalid bm25_weight '{bm25_weight}'. Must be between 0.0 and 1.0")

    def _validate_generation_config(self, config: Dict[str, Any]):
        """Validate generation configuration."""
        gen_config = config.get('generation', {})

        if not gen_config:
            self.errors.append("Missing 'generation' configuration")
            return

        # Validate provider
        provider = gen_config.get('provider', 'openai')
        if provider not in self.VALID_LLM_PROVIDERS:
            self.errors.append(
                f"Invalid LLM provider '{provider}'. "
                f"Must be one of: {', '.join(self.VALID_LLM_PROVIDERS)}"
            )

        # Validate model
        model = gen_config.get('model')
        if not model:
            self.errors.append("Missing generation 'model' name")

        # Validate temperature
        temperature = gen_config.get('temperature', 0.7)
        if not isinstance(temperature, (int, float)) or not (0.0 <= temperature <= 2.0):
            self.errors.append(f"Invalid temperature '{temperature}'. Must be between 0.0 and 2.0")

        # Validate max_tokens
        max_tokens = gen_config.get('max_tokens', 500)
        if not isinstance(max_tokens, int) or not (1 <= max_tokens <= 8000):
            self.errors.append(f"Invalid max_tokens '{max_tokens}'. Must be between 1 and 8000")

        # Provider-specific validation
        if provider == 'openai':
            api_key = gen_config.get('api_key') or os.getenv('OPENAI_API_KEY')
            if not api_key:
                self.errors.append(
                    "Missing OpenAI API key. Set 'api_key' in config or OPENAI_API_KEY environment variable"
                )

        elif provider == 'gemini':
            api_key = gen_config.get('api_key') or os.getenv('GOOGLE_API_KEY')
            if not api_key:
                self.errors.append(
                    "Missing Google API key. Set 'api_key' in config or GOOGLE_API_KEY environment variable"
                )

    def _validate_evaluation_config(self, config: Dict[str, Any]):
        """Validate evaluation configuration."""
        eval_config = config.get('evaluation', {})

        if not eval_config:
            self.warnings.append("No evaluation configuration - using defaults")
            return

        # Check eval_set path
        eval_set = eval_config.get('eval_set')
        if eval_set and not os.path.exists(eval_set):
            self.warnings.append(f"Evaluation dataset '{eval_set}' not found - will use config queries")

        # Validate k_values
        k_values = eval_config.get('k_values', [1, 3, 5])
        if not isinstance(k_values, list) or not all(isinstance(k, int) and k > 0 for k in k_values):
            self.errors.append(f"Invalid k_values '{k_values}'. Must be a list of positive integers")


def validate_config(config: Dict[str, Any], verbose: bool = True) -> Tuple[bool, List[str], List[str]]:
    """
    Validate a RAG configuration dictionary.

    Args:
        config: Configuration dictionary
        verbose: Print validation results

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    validator = ConfigValidator()
    is_valid, errors, warnings = validator.validate(config)

    if verbose:
        if errors:
            print("\n❌ Configuration Validation Errors:")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")

        if warnings:
            print("\n⚠️  Configuration Warnings:")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")

        if is_valid and not warnings:
            print("\n✅ Configuration is valid!")
        elif is_valid and warnings:
            print("\n✅ Configuration is valid (with warnings)")

    return is_valid, errors, warnings
