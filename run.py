#!/usr/bin/env python3
"""
RAG Pipeline CLI Tool v2
개선된 실험 워크플로우: index, search, generate 분리 실행
캐시를 통한 인덱스 재사용 지원
"""

import os
import sys
import json
import yaml
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import subprocess
import time

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from core.rag.pipeline import (
    RAGPipeline,
    ComponentInitializationError,
    IndexingError,
    RetrievalError,
    GenerationError
)
from core.rag.cache_manager import IndexCacheManager
from core.config.validator import validate_config
from core.evaluation.metrics import evaluate_answer, calculate_retrieval_metrics
from core.evaluation.advanced_metrics import (
    calculate_ndcg,
    calculate_hit_rate,
    calculate_token_usage,
    calculate_ragas_metrics
)


class RAGExperimentCLI:
    """개선된 RAG 실험 관리 CLI"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.experiments_dir = self.project_root / "experiments"
        self.experiment_log_path = self.experiments_dir / "experiment_log.json"
        self.leaderboard_path = self.experiments_dir / "leaderboard.md"
        self.cache_manager = IndexCacheManager()

    def index_command(self, config_path: str, force: bool = False):
        """
        인덱싱만 수행하는 명령어.
        캐시가 있으면 재사용, 없으면 새로 생성.

        Args:
            config_path: 설정 파일 경로
            force: True면 캐시 무시하고 재인덱싱
        """
        config_path = Path(config_path)
        if not config_path.exists():
            print(f"❌ Config file not found: {config_path}")
            return

        print(f"\n📚 Indexing with config: {config_path}")
        print("="*60)

        # Load config
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Validate config
        print("\n🔍 Validating configuration...")
        is_valid, errors, warnings = validate_config(config, verbose=True)

        if not is_valid:
            print("\n❌ Configuration validation failed. Please fix the errors above.")
            return None

        # Generate cache key
        cache_key = self.cache_manager.generate_cache_key(config)
        print(f"🔑 Cache Key: {cache_key}")

        # Check cache
        if not force and self.cache_manager.exists(cache_key):
            print(f"✅ Using cached index: {cache_key}")
            cache_info = self.cache_manager.get_cache_info(cache_key)
            if cache_info:
                stats = cache_info.get('stats', {})
                print(f"   Chunks: {stats.get('total_chunks', 'N/A')}")
                print(f"   Created: {cache_info.get('created_at', 'N/A')}")
            return cache_key

        # Need to create new index
        print("🔨 Creating new index...")

        try:
            # Initialize pipeline for indexing only
            pipeline = RAGPipeline(config, verbose=True)

        except ComponentInitializationError as e:
            print(f"\n❌ Failed to initialize pipeline: {e}")
            return None
        except Exception as e:
            print(f"\n❌ Unexpected initialization error: {e}")
            import traceback
            traceback.print_exc()
            return None

        try:
            # Load documents
            documents = self.load_data_from_config(config)
            print(f"📄 Loaded {len(documents)} documents")

            # Index documents
            start_time = time.time()
            doc_contents = [doc['content'] for doc in documents]
            doc_metadata = [doc.get('metadata', {}) for doc in documents]
            stats = pipeline.index_documents(doc_contents, doc_metadata)

            indexing_time = time.time() - start_time
            stats['indexing_time'] = indexing_time

            print(f"✅ Indexing complete: {stats.get('total_chunks')} chunks in {indexing_time:.1f}s")

        except IndexingError as e:
            print(f"\n❌ Indexing failed: {e}")
            return None

        try:
            # Save vector store to disk first
            cache_path = self.cache_manager.get_cache_path(cache_key)
            cache_path.mkdir(parents=True, exist_ok=True)
            pipeline.save_index(cache_path)

            # Save cache metadata
            cache_info = {
                'cache_key': cache_key,
                'created_at': datetime.now().isoformat(),
                'config': config,
                'stats': stats,
                'path': str(cache_path)
            }

            with open(cache_path / "cache_config.json", 'w', encoding='utf-8') as f:
                json.dump(cache_info, f, ensure_ascii=False, indent=2)

            # Update metadata
            self.cache_manager.metadata[cache_key] = cache_info
            self.cache_manager._save_metadata()

            print(f"✅ Cache saved: {cache_key}")

            return cache_key

        except Exception as e:
            print(f"❌ Failed to save cache: {e}")
            import traceback
            traceback.print_exc()
            return None

    def search_command(self, config_path: str, query: str, cache_key: Optional[str] = None):
        """
        검색만 수행하는 명령어.
        캐시된 인덱스를 사용하거나 지정된 캐시 키 사용.

        Args:
            config_path: 설정 파일 경로
            query: 검색 쿼리
            cache_key: 사용할 캐시 키 (선택)
        """
        config_path = Path(config_path)
        if not config_path.exists():
            print(f"❌ Config file not found: {config_path}")
            return

        print(f"\n🔍 Searching with config: {config_path}")
        print(f"Query: {query}")
        print("="*60)

        # Load config
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Determine cache key
        if not cache_key:
            cache_key = self.cache_manager.generate_cache_key(config)

        # Check if cache exists
        if not self.cache_manager.exists(cache_key):
            print(f"⚠️  No cached index found for cache key: {cache_key}")
            print("   Run 'python run.py index' first to create the index")

            # Suggest similar cache
            suggested = self.cache_manager.suggest_cache_key(config)
            if suggested:
                print(f"💡 Suggestion: Found similar cache '{suggested}'")
                print(f"   Use: python run.py search --config {config_path} --cache-key {suggested} --query \"{query}\"")
            return

        try:
            # Get cached index path directly (no copying)
            cache_path = self.cache_manager.get_cache_path(cache_key)

            # Initialize pipeline for search only
            pipeline = RAGPipeline(config, verbose=False)
            pipeline.load_index(cache_path)  # Load from cache path directly

            # Perform search
            start_time = time.time()
            results = pipeline.search(query, top_k=config.get('retrieval', {}).get('top_k', 5))
            search_time = time.time() - start_time

            print(f"\n📊 Found {len(results)} results in {search_time:.3f}s:")
            print("-"*60)

            for i, result in enumerate(results, 1):
                print(f"\n{i}. Score: {result.get('score', 0):.4f}")
                print(f"   Content: {result.get('content', '')[:200]}...")
                if result.get('metadata'):
                    print(f"   Source: {result.get('metadata')}")

        except Exception as e:
            print(f"❌ Search failed: {e}")
            import traceback
            traceback.print_exc()

    def generate_command(self, config_path: str, query: str, cache_key: Optional[str] = None):
        """
        전체 RAG 파이프라인 실행 (검색 + 생성).
        캐시된 인덱스 사용.

        Args:
            config_path: 설정 파일 경로
            query: 질문
            cache_key: 사용할 캐시 키 (선택)
        """
        config_path = Path(config_path)
        if not config_path.exists():
            print(f"❌ Config file not found: {config_path}")
            return

        print(f"\n🤖 Generating answer with config: {config_path}")
        print(f"Question: {query}")
        print("="*60)

        # Load config
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Determine cache key
        if not cache_key:
            cache_key = self.cache_manager.generate_cache_key(config)

        # Check if cache exists
        if not self.cache_manager.exists(cache_key):
            print(f"⚠️  No cached index found. Creating new index...")
            cache_key = self.index_command(config_path)
            if not cache_key:
                return

        try:
            # Get cached index path directly (no copying)
            cache_path = self.cache_manager.get_cache_path(cache_key)

            # Initialize pipeline
            pipeline = RAGPipeline(config, verbose=False)
            pipeline.load_index(cache_path)  # Load from cache path directly

        except ComponentInitializationError as e:
            print(f"\n❌ Failed to initialize pipeline: {e}")
            return
        except Exception as e:
            print(f"\n❌ Failed to load pipeline: {e}")
            import traceback
            traceback.print_exc()
            return

        try:
            # Run full RAG pipeline
            start_time = time.time()
            result = pipeline.query(query)
            total_time = time.time() - start_time

            print(f"\n✨ Answer generated in {total_time:.2f}s:")
            print("-"*60)
            print(result.get('answer', 'No answer generated'))

            print(f"\n📚 Sources ({len(result.get('sources', []))} documents):")
            for i, source in enumerate(result.get('sources', []), 1):
                print(f"  {i}. {source.get('content', '')[:100]}...")

        except (RetrievalError, GenerationError) as e:
            print(f"\n❌ Query failed: {e}")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()

    def list_caches_command(self):
        """사용 가능한 캐시 목록 표시."""
        print("\n📦 Available Index Caches")
        print("="*60)

        caches = self.cache_manager.list_caches()

        if not caches:
            print("No caches found. Run 'python run.py index' to create one.")
            return

        print(f"Found {len(caches)} cached indices:\n")

        for cache in caches:
            cache_key = cache.get('cache_key', 'unknown')
            created = cache.get('created_at', 'unknown')
            config = cache.get('config', {})
            stats = cache.get('stats', {})

            print(f"🔑 {cache_key}")
            print(f"   Created: {created}")
            print(f"   Chunks: {stats.get('total_chunks', 'N/A')}")
            print(f"   Config:")
            print(f"     - Chunking: {config.get('chunking', {}).get('strategy')} "
                  f"(size: {config.get('chunking', {}).get('chunk_size')})")
            print(f"     - Embedding: {config.get('embedding', {}).get('model')}")
            print(f"     - Vector DB: {config.get('vector_store', {}).get('type')}")
            print()

    def delete_cache_command(self, cache_key: str):
        """캐시 삭제."""
        print(f"\n🗑️  Deleting cache: {cache_key}")

        if self.cache_manager.delete_cache(cache_key):
            print("✅ Cache deleted successfully")
        else:
            print("❌ Cache not found or deletion failed")

    def run_baseline(self):
        """Run baseline experiment (backward compatibility)."""
        print("\n🚀 Running Baseline RAG Experiment...")
        print("="*60)

        # Use new index command with baseline config
        baseline_config = self.experiments_dir / "baseline" / "config.yaml"
        if baseline_config.exists():
            # Index
            cache_key = self.index_command(str(baseline_config))

            if cache_key:
                # Run sample queries
                sample_queries = [
                    "살인죄의 형량은?",
                    "계약 위반시 손해배상은?"
                ]

                for query in sample_queries:
                    print(f"\n{'='*60}")
                    self.generate_command(str(baseline_config), query, cache_key)
        else:
            # Fallback to old baseline script
            baseline_script = self.experiments_dir / "baseline" / "baseline_rag.py"
            if baseline_script.exists():
                subprocess.run([sys.executable, str(baseline_script)])

    def init_experiment(self, name: str, description: str):
        """Initialize a new experiment for a team member."""
        print(f"\n🔧 Initializing experiment for: {name}")

        # Create member directory and config
        member_dir = self.experiments_dir / "configs" / "members" / name
        member_dir.mkdir(parents=True, exist_ok=True)

        config_path = member_dir / f"{name}_config.yaml"

        if config_path.exists():
            print(f"⚠️  Config already exists: {config_path}")
            print(f"   Skipping creation. Edit existing file or delete it first.")
            return

        # Create results directory
        results_dir = self.experiments_dir / "results" / name
        results_dir.mkdir(parents=True, exist_ok=True)

        # Copy template
        template_path = self.experiments_dir / "configs" / "template_config.yaml"
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Customize for this experimenter
            config['experiment_name'] = f"{name}_experiment"
            config['description'] = description
            config['author'] = name
            config['date'] = datetime.now().strftime('%Y-%m-%d')
            config['experiment']['results_dir'] = f"experiments/results/{name}/"

            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            print(f"✅ Experiment initialized for {name}!")
            print(f"   Config dir: {member_dir}")
            print(f"   Results dir: {results_dir}")
            print(f"\n📝 Next steps:")
            print(f"   1. Edit config: vim {config_path}")
            print(f"   2. Run experiment: python run.py experiment --config {config_path}")
        else:
            print(f"❌ Template not found: {template_path}")

    def experiment_command(self, config_path: str):
        """
        전체 실험 실행 (index + evaluate).
        기존 experiment 명령어와 호환.
        """
        config_path = Path(config_path)
        if not config_path.exists():
            print(f"❌ Config file not found: {config_path}")
            return

        print(f"\n🔬 Running full experiment with config: {config_path}")
        print("="*60)

        # Step 1: Index
        cache_key = self.index_command(str(config_path))
        if not cache_key:
            print("❌ Indexing failed")
            return

        # Step 2: Load evaluation dataset
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Load evaluation dataset if exists
        eval_set_path = config.get('evaluation', {}).get('eval_set', 'data/evaluation/test_qa.json')
        eval_dataset = self._load_eval_dataset(eval_set_path)

        if not eval_dataset:
            # Fallback: use queries from config
            eval_queries = config.get('experiment', {}).get('evaluation_queries', [
                "살인죄의 형량은?",
                "계약 위반시 손해배상은?",
                "강도죄와 절도죄의 차이는?"
            ])
            eval_dataset = [{'id': f'q{i+1}', 'query': q} for i, q in enumerate(eval_queries)]

        print(f"\n📊 Running {len(eval_dataset)} evaluation queries...")
        results = []

        for eval_item in eval_dataset:
            query = eval_item['query']
            print(f"\nQuery: {query}")
            result = self._generate_and_collect(str(config_path), query, cache_key, eval_item)
            if result:
                results.append(result)

        # Save results to file
        results_dir = Path(config.get('experiment', {}).get('results_dir', 'experiments/results/'))
        results_dir.mkdir(parents=True, exist_ok=True)

        # Use config filename as part of result filename
        config_name = config_path.stem  # e.g., "wh_config_chunk_512"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = results_dir / f"{config_name}_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'experiment_name': config.get('experiment_name', 'unknown'),
                'config_path': str(config_path),
                'cache_key': cache_key,
                'timestamp': datetime.now().isoformat(),
                'results': results
            }, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Experiment completed!")
        print(f"📊 Results saved: {results_file}")

    def _generate_and_collect(self, config_path: str, query: str, cache_key: str, eval_item: Dict = None) -> Optional[Dict[str, Any]]:
        """
        Generate answer and collect result for saving.
        """
        config_path = Path(config_path)
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        try:
            # Get cached index path
            cache_path = self.cache_manager.get_cache_path(cache_key)

            # Initialize pipeline
            pipeline = RAGPipeline(config, verbose=False)
            pipeline.load_index(cache_path)

            # Run query with timing
            start_time = time.time()
            result = pipeline.query(query)
            total_time = time.time() - start_time

            # Extract retrieval and generation times if available
            retrieval_time = result.get('retrieval_time', None)
            generation_time = result.get('generation_time', None)

            # Print to console
            print(f"\n✨ Answer generated in {total_time:.2f}s:")
            if retrieval_time and generation_time:
                print(f"   ⏱️  Retrieval: {retrieval_time:.2f}s | Generation: {generation_time:.2f}s")
            print("-"*60)
            print(result.get('answer', 'No answer generated'))

            # Evaluate if ground truth exists
            evaluation_metrics = {}
            if eval_item and 'ground_truth' in eval_item:
                ground_truth = eval_item['ground_truth']
                answer = result.get('answer', '')

                # Basic answer quality metrics
                evaluation_metrics = evaluate_answer(ground_truth, answer)

                # Basic retrieval metrics
                k = config.get('retrieval', {}).get('top_k', 5)
                if 'relevant_docs' in eval_item:
                    retrieval_metrics = calculate_retrieval_metrics(
                        result.get('sources', []),
                        eval_item['relevant_docs'],
                        k=k
                    )
                    evaluation_metrics.update(retrieval_metrics)

                    # Advanced retrieval metrics (NDCG, Hit Rate)
                    evaluation_metrics['ndcg'] = calculate_ndcg(
                        result.get('sources', []),
                        eval_item['relevant_docs'],
                        k=k
                    )
                    evaluation_metrics['hit_rate'] = calculate_hit_rate(
                        result.get('sources', []),
                        eval_item['relevant_docs'],
                        k=k
                    )

                # Token usage
                token_info = calculate_token_usage(
                    query,
                    answer,
                    model=config.get('generation', {}).get('model', 'gpt-3.5-turbo')
                )
                evaluation_metrics['token_usage'] = token_info

                # RAGAS metrics (optional, requires OpenAI API)
                use_ragas = config.get('evaluation', {}).get('use_ragas', False)
                if use_ragas and os.getenv('OPENAI_API_KEY'):
                    contexts = [src.get('content', '') for src in result.get('sources', [])]
                    ragas_metrics = calculate_ragas_metrics(
                        query=query,
                        answer=answer,
                        contexts=contexts,
                        ground_truth=ground_truth,
                        use_ragas=True
                    )
                    evaluation_metrics['ragas'] = ragas_metrics

                print(f"📊 Evaluation metrics:")
                print(f"   F1: {evaluation_metrics.get('f1_score', 0):.3f} | "
                      f"ROUGE-L: {evaluation_metrics.get('rouge_l', 0):.3f} | "
                      f"Semantic: {evaluation_metrics.get('semantic_similarity', 0):.3f}")
                if 'ndcg' in evaluation_metrics:
                    print(f"   NDCG@{k}: {evaluation_metrics.get('ndcg', 0):.3f} | "
                          f"Hit Rate@{k}: {evaluation_metrics.get('hit_rate', 0):.3f}")
                if 'token_usage' in evaluation_metrics and evaluation_metrics['token_usage'].get('total_tokens'):
                    print(f"   Tokens: {evaluation_metrics['token_usage']['total_tokens']}")

            print(f"📚 Sources ({len(result.get('sources', []))} documents)")

            # Return for saving
            return {
                'id': eval_item.get('id', '') if eval_item else '',
                'query': query,
                'answer': result.get('answer', ''),
                'ground_truth': eval_item.get('ground_truth', '') if eval_item else '',
                'sources': result.get('sources', []),
                'response_time': total_time,
                'num_sources': len(result.get('sources', [])),
                'evaluation_metrics': evaluation_metrics,
                'category': eval_item.get('category', '') if eval_item else '',
                'difficulty': eval_item.get('difficulty', '') if eval_item else ''
            }

        except Exception as e:
            print(f"❌ Generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _load_eval_dataset(self, eval_set_path: str) -> List[Dict]:
        """
        Load evaluation dataset from JSON file.
        """
        eval_path = Path(eval_set_path)

        if not eval_path.exists():
            print(f"⚠️ Evaluation dataset not found: {eval_path}")
            return []

        try:
            with open(eval_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)

            print(f"✅ Loaded {len(dataset)} evaluation samples from {eval_path}")
            return dataset

        except Exception as e:
            print(f"❌ Failed to load evaluation dataset: {e}")
            return []

    def compare_experiments(self, experiment_files: List[str]):
        """
        Compare multiple experiment results.
        """
        print(f"\n📊 Comparing {len(experiment_files)} experiments...")
        print("="*80)

        experiments = []

        # Load all experiment results
        for exp_file in experiment_files:
            exp_path = Path(exp_file)
            if not exp_path.exists():
                print(f"⚠️ File not found: {exp_file}")
                continue

            try:
                with open(exp_path, 'r', encoding='utf-8') as f:
                    exp_data = json.load(f)
                    experiments.append({
                        'name': exp_data.get('experiment_name', exp_path.stem),
                        'file': str(exp_path),
                        'data': exp_data
                    })
            except Exception as e:
                print(f"❌ Failed to load {exp_file}: {e}")

        if len(experiments) < 2:
            print("❌ Need at least 2 valid experiment files to compare")
            return

        # Calculate aggregated metrics for each experiment
        comparison = []

        for exp in experiments:
            results = exp['data'].get('results', [])

            if not results:
                continue

            # Aggregate metrics
            total_response_time = sum(r.get('response_time', 0) for r in results)
            avg_response_time = total_response_time / len(results) if results else 0

            # Average evaluation metrics
            metrics_sum = {
                'f1_score': 0,
                'bleu': 0,
                'rouge_l': 0,
                'semantic_similarity': 0,
                'exact_match': 0
            }

            for result in results:
                eval_metrics = result.get('evaluation_metrics', {})
                for key in metrics_sum:
                    metrics_sum[key] += eval_metrics.get(key, 0)

            avg_metrics = {k: v / len(results) for k, v in metrics_sum.items()} if results else metrics_sum

            comparison.append({
                'name': exp['name'],
                'num_queries': len(results),
                'avg_response_time': round(avg_response_time, 3),
                'avg_f1': round(avg_metrics['f1_score'], 3),
                'avg_bleu': round(avg_metrics['bleu'], 3),
                'avg_rouge_l': round(avg_metrics['rouge_l'], 3),
                'avg_semantic_sim': round(avg_metrics['semantic_similarity'], 3),
                'exact_match_rate': round(avg_metrics['exact_match'] / len(results) if results else 0, 3)
            })

        # Print comparison table
        print(f"\n{'Experiment':<30} {'Queries':<10} {'Avg Time':<12} {'F1':<8} {'ROUGE-L':<10} {'Semantic':<10}")
        print("-" * 80)

        for comp in comparison:
            print(f"{comp['name']:<30} {comp['num_queries']:<10} "
                  f"{comp['avg_response_time']:<12.3f} {comp['avg_f1']:<8.3f} "
                  f"{comp['avg_rouge_l']:<10.3f} {comp['avg_semantic_sim']:<10.3f}")

        # Find best experiment
        if comparison:
            best_f1 = max(comparison, key=lambda x: x['avg_f1'])
            best_speed = min(comparison, key=lambda x: x['avg_response_time'])

            print(f"\n🏆 Best F1 Score: {best_f1['name']} ({best_f1['avg_f1']:.3f})")
            print(f"⚡ Fastest: {best_speed['name']} ({best_speed['avg_response_time']:.3f}s)")

    def load_data_from_config(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Load data based on config with support for multiple loader types.

        Args:
            config: Configuration dictionary

        Returns:
            List of document dictionaries with 'content' and 'metadata'
        """
        data_config = config.get('data', {})
        loader_type = data_config.get('loader_type', 'default')

        # ========== [NEW] Traffic Law Loader Support ==========
        if loader_type == 'traffic':
            # Use traffic law specialized loader
            from scripts.traffic_law_data_loader import TrafficLawDataLoader
            from core.database import PostgreSQLClient

            loader = TrafficLawDataLoader(data_config.get('base_path'))

            # Get configuration options
            use_source = data_config.get('use_source', True)
            use_labeled = data_config.get('use_labeled', True)
            source_types = data_config.get('source_types', ['법령', '판결문', '결정례', '해석례'])
            labeled_types = data_config.get('labeled_types', ['법령_QA', '판결문_QA', '결정례_QA', '해석례_QA'])
            max_per_type = data_config.get('max_per_type', None)
            split = data_config.get('split', 'training')
            traffic_only = data_config.get('traffic_only', True)

            # Check if PostgreSQL enrichment is enabled
            use_db_enrichment = data_config.get('use_db_enrichment', False)

            if use_db_enrichment:
                # Load with PostgreSQL context enrichment
                try:
                    db_client = PostgreSQLClient()
                    dataset = loader.load_with_enrichment(
                        db_client=db_client,
                        use_source=use_source,
                        use_labeled=use_labeled,
                        source_types=source_types,
                        labeled_types=labeled_types,
                        max_per_type=max_per_type,
                        split=split,
                        traffic_only=traffic_only
                    )
                    db_client.close()
                except Exception as e:
                    print(f"⚠️ PostgreSQL enrichment failed: {e}")
                    print("   Falling back to basic traffic loader...")
                    dataset = loader.load_traffic_only(
                        use_source=use_source,
                        use_labeled=use_labeled,
                        source_types=source_types,
                        labeled_types=labeled_types,
                        max_per_type=max_per_type,
                        split=split
                    )
            else:
                # Load traffic data only (no DB enrichment)
                dataset = loader.load_traffic_only(
                    use_source=use_source,
                    use_labeled=use_labeled,
                    source_types=source_types,
                    labeled_types=labeled_types,
                    max_per_type=max_per_type,
                    split=split
                )

            return dataset
        # ======================================================

        # Default loader (existing criminal law loader)
        return self._load_documents_for_config(config)

    def _load_documents_for_config(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Load documents based on config (default loader)."""
        data_config = config.get('data', {})

        # Check if using real criminal law data
        if data_config.get('use_real_data', False):
            # Use criminal law data loader (supports source + labeled data)
            from scripts.criminal_law_data_loader import CriminalLawDataLoader
            loader = CriminalLawDataLoader()

            # Get configuration options
            use_source = data_config.get('use_source', True)
            use_labeled = data_config.get('use_labeled', True)
            source_types = data_config.get('source_types', ['법령', '판결문', '결정례', '해석례'])
            labeled_types = data_config.get('labeled_types', ['법령_QA', '판결문_QA', '결정례_QA', '해석례_QA'])
            max_per_type = data_config.get('max_per_type', None)
            split = data_config.get('split', 'training')  # 'training', 'validation', 'all'

            # Load dataset
            dataset = loader.load_dataset(
                use_source=use_source,
                use_labeled=use_labeled,
                source_types=source_types,
                labeled_types=labeled_types,
                max_per_type=max_per_type,
                split=split
            )

            documents = []
            for item in dataset:
                documents.append({
                    'content': item.get('content', item.get('text', '')),
                    'metadata': item.get('metadata', {})
                })

            return documents

        # Use data path
        data_path = Path(data_config.get('path', 'data/'))
        max_docs = data_config.get('max_documents', None)

        if data_path.exists():
            return self._load_documents(data_path, max_docs)
        else:
            # Use sample documents
            return self._get_sample_documents()

    def _load_documents(self, data_path: Path, max_docs: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load documents from data directory."""
        documents = []

        # Load JSON files
        for json_file in data_path.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    documents.extend(data)
                else:
                    documents.append(data)

            if max_docs and len(documents) >= max_docs:
                break

        # Load text files
        if len(documents) < (max_docs or float('inf')):
            for txt_file in data_path.glob("*.txt"):
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    documents.append({
                        'content': content,
                        'metadata': {'source': txt_file.name}
                    })

                if max_docs and len(documents) >= max_docs:
                    break

        # If no documents found, use sample
        if not documents:
            documents = self._get_sample_documents()

        return documents[:max_docs] if max_docs else documents

    def _get_sample_documents(self) -> List[Dict[str, Any]]:
        """Get sample documents for testing."""
        return [
            {
                'content': "형법 제250조 (살인, 존속살해) ① 사람을 살해한 자는 사형, 무기 또는 5년 이상의 징역에 처한다. ② 자기 또는 배우자의 직계존속을 살해한 자는 사형, 무기 또는 7년 이상의 징역에 처한다.",
                'metadata': {'source': '형법', 'article': '250', 'title': '살인죄'}
            },
            {
                'content': "형법 제329조 (절도) 타인의 재물을 절취한 자는 6년 이하의 징역 또는 1천만원 이하의 벌금에 처한다.",
                'metadata': {'source': '형법', 'article': '329', 'title': '절도죄'}
            },
            {
                'content': "형법 제333조 (강도) 폭행 또는 협박으로 타인의 재물을 강취하거나 기타 재산상의 이익을 취득하거나 제삼자로 하여금 이를 취득하게 한 자는 3년 이상의 유기징역에 처한다.",
                'metadata': {'source': '형법', 'article': '333', 'title': '강도죄'}
            },
            {
                'content': "민법 제390조 (채무불이행과 손해배상) 채무자가 채무의 내용에 좇은 이행을 하지 아니한 때에는 채권자는 손해배상을 청구할 수 있다.",
                'metadata': {'source': '민법', 'article': '390', 'title': '손해배상'}
            }
        ]


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RAG Pipeline Experiment CLI v2",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'command',
        choices=['index', 'search', 'generate', 'experiment', 'list-caches',
                 'delete-cache', 'baseline', 'init-experiment', 'compare'],
        help="""Commands:
  index         - Index documents (create or use cache)
  search        - Search in indexed documents
  generate      - Generate answer using RAG pipeline
  experiment    - Run full experiment (index + evaluate)
  list-caches   - List available index caches
  delete-cache  - Delete a specific cache
  baseline      - Run baseline experiment
  init-experiment - Initialize new experiment for team member
  compare       - Compare experiment results
"""
    )

    parser.add_argument('--config', help='Config file path')
    parser.add_argument('--query', help='Search query or question')
    parser.add_argument('--cache-key', help='Specific cache key to use')
    parser.add_argument('--force', action='store_true', help='Force re-indexing (ignore cache)')
    parser.add_argument('--name', help='Experimenter name (for init-experiment)')
    parser.add_argument('--description', help='Experiment description')
    parser.add_argument('--experiments', nargs='+', help='Experiment result files to compare')

    args = parser.parse_args()

    cli = RAGExperimentCLI()

    if args.command == 'index':
        if not args.config:
            print("❌ --config required for index")
            sys.exit(1)
        cli.index_command(args.config, args.force)

    elif args.command == 'search':
        if not args.config or not args.query:
            print("❌ --config and --query required for search")
            sys.exit(1)
        cli.search_command(args.config, args.query, args.cache_key)

    elif args.command == 'generate':
        if not args.config or not args.query:
            print("❌ --config and --query required for generate")
            sys.exit(1)
        cli.generate_command(args.config, args.query, args.cache_key)

    elif args.command == 'experiment':
        if not args.config:
            print("❌ --config required for experiment")
            sys.exit(1)
        cli.experiment_command(args.config)

    elif args.command == 'list-caches':
        cli.list_caches_command()

    elif args.command == 'delete-cache':
        if not args.cache_key:
            print("❌ --cache-key required for delete-cache")
            sys.exit(1)
        cli.delete_cache_command(args.cache_key)

    elif args.command == 'baseline':
        cli.run_baseline()

    elif args.command == 'init-experiment':
        if not args.name:
            print("❌ --name required for init-experiment")
            sys.exit(1)
        description = args.description or f"Experiment by {args.name}"
        cli.init_experiment(args.name, description)

    elif args.command == 'compare':
        if not args.experiments or len(args.experiments) < 2:
            print("❌ --experiments required (at least 2 result files)")
            sys.exit(1)
        cli.compare_experiments(args.experiments)


if __name__ == "__main__":
    main()