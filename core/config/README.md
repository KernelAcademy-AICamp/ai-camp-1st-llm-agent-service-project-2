# Config Validation Module

## Overview

This module provides comprehensive validation for RAG experiment configurations to prevent runtime errors and improve debugging experience.

## Features

### 1. **Pre-execution Validation**
- Validates all config parameters before experiment starts
- Catches errors early (before expensive indexing operations)
- Provides clear, actionable error messages

### 2. **Comprehensive Checks**
- **Chunking**: strategy, chunk_size, overlap validation
- **Embedding**: type, model, API keys validation
- **Vector Store**: type, index settings validation
- **Retrieval**: method, parameters validation
- **Generation**: provider, model, temperature validation
- **Evaluation**: dataset paths, metrics validation

### 3. **Smart Error Messages**
- Specific error descriptions
- Valid value ranges
- Helpful hints (e.g., "Check your .env file for API keys")

## Usage

### Automatic Validation (Integrated in run.py)

Config validation happens automatically when running experiments:

```bash
python run.py index --config my_config.yaml
python run.py experiment --config my_config.yaml
```

### Manual Validation

You can also validate configs programmatically:

```python
from core.config.validator import validate_config
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Validate
is_valid, errors, warnings = validate_config(config, verbose=True)

if not is_valid:
    print("Config has errors:")
    for error in errors:
        print(f"  - {error}")
```

## Validation Rules

### Chunking

| Parameter | Valid Values | Default |
|-----------|-------------|---------|
| `strategy` | `fixed`, `semantic`, `recursive`, `sliding_window` | `fixed` |
| `chunk_size` | 50-4000 | 512 |
| `overlap` | 0 to chunk_size | 50 |

### Embedding

| Parameter | Valid Values | Default |
|-----------|-------------|---------|
| `type` | `openai`, `huggingface` | `openai` |
| `model` | (required) | - |
| `device` | `cpu`, `cuda`, `mps` | `cpu` |
| `batch_size` | > 0 | 32 |

**Note**: OpenAI requires `OPENAI_API_KEY` environment variable

### Vector Store

| Parameter | Valid Values | Default |
|-----------|-------------|---------|
| `type` | `faiss`, `chroma`, `qdrant` | `faiss` |
| `index_type` (FAISS) | `flat`, `ivf`, `hnsw` | `flat` |

### Retrieval

| Parameter | Valid Values | Default |
|-----------|-------------|---------|
| `method` | `similarity`, `mmr`, `hybrid` | `similarity` |
| `top_k` | 1-100 | 5 |
| `lambda_mult` (MMR) | 0.0-1.0 | 0.5 |
| `bm25_weight` (Hybrid) | 0.0-1.0 | 0.3 |

### Generation

| Parameter | Valid Values | Default |
|-----------|-------------|---------|
| `provider` | `openai`, `gemini`, `anthropic` | `openai` |
| `model` | (required) | - |
| `temperature` | 0.0-2.0 | 0.7 |
| `max_tokens` | 1-8000 | 500 |

**Note**: OpenAI requires `OPENAI_API_KEY`, Gemini requires `GOOGLE_API_KEY`

## Example Error Output

When validation fails, you get clear error messages:

```
❌ Configuration Validation Errors:
  1. Invalid chunking strategy 'wrong'. Must be one of: fixed, semantic, recursive, sliding_window
  2. Invalid chunk_size '10000'. Must be an integer between 50 and 4000
  3. Missing embedding 'model' name
  4. Invalid top_k '200'. Must be an integer between 1 and 100
  5. Missing OpenAI API key. Set 'api_key' in config or OPENAI_API_KEY environment variable

⚠️  Configuration Warnings:
  1. Data path 'data/missing/' does not exist - will use sample data

❌ Configuration validation failed. Please fix the errors above.
```

## Example Warning Output

Warnings don't stop execution but alert you to potential issues:

```
⚠️  Configuration Warnings:
  1. No persist_directory set for ChromaDB - data will be in-memory only
  2. Evaluation dataset 'data/eval.json' not found - will use config queries

✅ Configuration is valid (with warnings)
```

## Adding New Validation Rules

To add validation for new config parameters:

1. Add validation method to `ConfigValidator` class:

```python
def _validate_my_new_section(self, config: Dict[str, Any]):
    """Validate my new section."""
    my_section = config.get('my_section', {})

    # Add validation logic
    if 'required_param' not in my_section:
        self.errors.append("Missing 'required_param' in my_section")

    value = my_section.get('some_value', 0)
    if not (0 <= value <= 100):
        self.errors.append(f"Invalid value '{value}'. Must be between 0 and 100")
```

2. Call it from `validate()` method:

```python
def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    # ... existing validations ...
    self._validate_my_new_section(config)
    # ...
```

## Integration with Pipeline

The validation module is integrated with error handling in the RAG pipeline:

1. **Config Validation** → Catches config errors
2. **Component Initialization** → Catches setup errors (API keys, libraries, etc.)
3. **Indexing** → Catches data/embedding errors
4. **Retrieval** → Catches search errors
5. **Generation** → Catches LLM errors

Each stage has specific error types with helpful messages.

## Benefits

1. **Faster debugging**: Find config errors in seconds instead of after long indexing
2. **Better error messages**: Know exactly what's wrong and how to fix it
3. **Safer experiments**: Validate before expensive operations
4. **Team-friendly**: Help teammates catch config mistakes early
