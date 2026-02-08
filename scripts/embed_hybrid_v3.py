#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hybrid Embedding V2 (Split-able)
Dense (SentenceTransformer) -> .npy (streaming)
Sparse (SPLADE) -> .jsonl.gz (streaming)
Upsert -> Qdrant (reads saved files)

Modes:
  --mode dense   : Dense만 계산해서 저장
  --mode splade  : SPLADE만 계산해서 저장
  --mode upsert  : 저장된 dense/splade 파일로 Qdrant 업서트
  --mode all     : Dense -> SPLADE -> Upsert 순차 실행

Examples:
  # 1) Dense만 먼저
  python embed_hybrid_v2.py --input chunks_v2.json --mode dense --dense-batch-size 64

  # 2) SPLADE만 따로
  python embed_hybrid_v2.py --input chunks_v2.json --mode splade --splade-batch-size 16 --max-length 512

  # 3) 마지막에 업서트만
  python embed_hybrid_v2.py --input chunks_v2.json --mode upsert --collection law_documents_v2

  # 4) 전부 한 번에
  python embed_hybrid_v2.py --input chunks_v2.json --mode all --dense-batch-size 64 --splade-batch-size 16
"""

import os
import json
import time
import uuid
import gzip
import argparse
import platform
import statistics
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Iterator
from datetime import datetime
from dataclasses import dataclass

import torch
import psutil
import numpy as np
from tqdm import tqdm


# ============================================================
# Configuration
# ============================================================

@dataclass
class Config:
    # Models
    dense_model: str = "dragonkue/snowflake-arctic-embed-l-v2.0-ko"
    splade_model: str = "yjoonjang/splade-ko-v1"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "law_documents_v2"

    # Processing
    dense_batch_size: int = 32
    splade_batch_size: int = 32
    max_length: int = 512
    splade_dtype: str = "float32"
    splade_topk: Optional[int] = 256
    splade_value_threshold: Optional[float] = None
    length_sort: bool = False
    length_buckets: Optional[List[int]] = None
    ignore_saved_order: bool = False
    splade_debug_topk_tokens: int = 0

    # Outputs
    output_prefix: str = ""  # if empty, derived from input stem

    # Metrics
    metrics_interval: float = 1.0


# ============================================================
# Metrics
# ============================================================

class MetricsCollector:
    """
    - Stage metrics: dense/splade/upsert 총 소요 시간
    - Batch metrics: 배치별 latency, items/sec, splade nnz 통계
    - System metrics: CPU%, RSS, GPU mem/peak + (optional) NVML util/mem
    """

    def __init__(self, sample_interval_sec: float = 1.0):
        self.run_id = str(uuid.uuid4())
        self.sample_interval_sec = float(sample_interval_sec)

        self.meta: Dict[str, Any] = {}
        self.stages: Dict[str, Dict[str, Any]] = {}
        self.batch: Dict[str, List[Dict[str, Any]]] = {"dense": [], "splade": [], "upsert": []}
        self.system_samples: List[Dict[str, Any]] = []

        self._proc = psutil.Process(os.getpid())
        self._nvml = None
        self._nvml_handle = None
        self._last_sample_t = -1e9

        # NVML optional (nvidia-ml-py3)
        try:
            import pynvml  # type: ignore
            self._nvml = pynvml
            pynvml.nvmlInit()
            self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            self._nvml = None
            self._nvml_handle = None

    def set_meta(self, config: Config, mode: str, input_path: str):
        self.meta = {
            "run_id": self.run_id,
            "mode": mode,
            "input": input_path,
            "started_at": datetime.now().isoformat(),
            "host": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "pid": os.getpid(),
            },
            "torch": {
                "version": torch.__version__,
                "cuda_available": torch.cuda.is_available(),
                "cuda_version": getattr(torch.version, "cuda", None),
                "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            },
            "config": {
                "dense_model": config.dense_model,
                "splade_model": config.splade_model,
                "dense_batch_size": config.dense_batch_size,
                "splade_batch_size": config.splade_batch_size,
                "max_length": config.max_length,
                "splade_dtype": config.splade_dtype,
                "splade_topk": config.splade_topk,
                "splade_value_threshold": config.splade_value_threshold,
                "length_sort": config.length_sort,
                "length_buckets": config.length_buckets,
                "ignore_saved_order": config.ignore_saved_order,
                "splade_debug_topk_tokens": config.splade_debug_topk_tokens,
                "qdrant_url": config.qdrant_url,
                "collection_name": config.collection_name,
                "output_prefix": config.output_prefix,
            },
        }

    def sample_system(self, now_t: float):
        if (now_t - self._last_sample_t) < self.sample_interval_sec:
            return
        self._last_sample_t = now_t

        cpu = psutil.cpu_percent(interval=None)
        rss_bytes = int(self._proc.memory_info().rss)

        sample: Dict[str, Any] = {
            "t_sec": round(float(now_t), 3),
            "cpu_percent": float(cpu),
            "rss_bytes": rss_bytes,
        }

        if torch.cuda.is_available():
            sample["gpu_torch"] = {
                "mem_allocated": int(torch.cuda.memory_allocated()),
                "mem_reserved": int(torch.cuda.memory_reserved()),
                "max_mem_allocated": int(torch.cuda.max_memory_allocated()),
                "max_mem_reserved": int(torch.cuda.max_memory_reserved()) if hasattr(torch.cuda, "max_memory_reserved") else None,
            }

        if self._nvml and self._nvml_handle:
            try:
                util = self._nvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
                mem = self._nvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
                sample["gpu_nvml"] = {
                    "gpu_util_percent": int(util.gpu),
                    "mem_util_percent": int(util.memory),
                    "mem_used_bytes": int(mem.used),
                    "mem_total_bytes": int(mem.total),
                }
            except Exception:
                pass

        self.system_samples.append(sample)

    def stage_done(self, name: str, sec: float, extra: Optional[Dict[str, Any]] = None):
        self.stages[name] = {"sec": float(sec), **(extra or {})}

    def add_batch(self, kind: str, payload: Dict[str, Any]):
        self.batch[kind].append(payload)

    @staticmethod
    def _pctl(sorted_xs: List[float], p: float) -> float:
        if not sorted_xs:
            return float("nan")
        idx = int(p * (len(sorted_xs) - 1))
        return float(sorted_xs[idx])

    @classmethod
    def _basic_stats(cls, xs: List[float]) -> Optional[Dict[str, Any]]:
        if not xs:
            return None
        xs_sorted = sorted(xs)
        return {
            "count": len(xs_sorted),
            "mean": float(statistics.fmean(xs_sorted)),
            "p50": float(statistics.median(xs_sorted)),
            "p95": cls._pctl(xs_sorted, 0.95),
            "max": float(max(xs_sorted)),
        }

    def finalize(self, total_items: int, wall_sec: float) -> Dict[str, Any]:
        ended_at = datetime.now().isoformat()

        dense_lat = [float(b["sec"]) for b in self.batch["dense"]]
        splade_lat = [float(b["sec"]) for b in self.batch["splade"]]
        upsert_lat = [float(b["sec"]) for b in self.batch["upsert"]]

        splade_avg_nnz = [float(b["avg_nnz"]) for b in self.batch["splade"] if "avg_nnz" in b]

        out = {
            "meta": {**self.meta, "ended_at": ended_at, "wall_sec": float(wall_sec)},
            "stages": self.stages,
            "batch_stats": {
                "dense_latency_sec": self._basic_stats(dense_lat),
                "splade_latency_sec": self._basic_stats(splade_lat),
                "upsert_latency_sec": self._basic_stats(upsert_lat),
                "splade_avg_nnz": self._basic_stats(splade_avg_nnz) if splade_avg_nnz else None,
            },
            "batches": self.batch,
            "system_samples": self.system_samples,
            "total_items": int(total_items),
        }
        return out


# ============================================================
# Encoders
# ============================================================

class DenseEncoder:
    """Dense Embedding Encoder using sentence-transformers"""

    def __init__(self, model_name: str, device: str = None):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name

        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device

        print(f"[Dense] Loading model: {model_name}")
        print(f"[Dense] Device: {self.device}")

        self.model = SentenceTransformer(model_name, device=self.device)
        self.dim = int(self.model.get_sentence_embedding_dimension())
        print(f"[Dense] Loaded. Dimension: {self.dim}")

    def encode_stream_to_npy(
        self,
        texts: List[str],
        out_npy: Path,
        batch_size: int,
        metrics: Optional[MetricsCollector],
        t0: float,
    ) -> int:
        """
        Dense 임베딩을 메모리 폭발 없이 .npy에 스트리밍 저장(open_memmap).
        반환: embedding dim
        """
        n = len(texts)
        dim = self.dim

        print(f"[Dense] Writing embeddings to: {out_npy} (shape={n}x{dim}, float32)")
        mmap = np.lib.format.open_memmap(str(out_npy), mode="w+", dtype=np.float32, shape=(n, dim))

        iterator = range(0, n, batch_size)
        iterator = tqdm(iterator, desc="Dense encoding", unit="batch")

        for i in iterator:
            bt = time.perf_counter()
            batch_texts = texts[i:i + batch_size]

            emb = self.model.encode(
                batch_texts,
                batch_size=len(batch_texts),
                show_progress_bar=False,
                convert_to_numpy=True
            ).astype(np.float32, copy=False)

            mmap[i:i + len(batch_texts), :] = emb
            sec = time.perf_counter() - bt

            if metrics:
                now_t = time.perf_counter() - t0
                metrics.sample_system(now_t)
                metrics.add_batch("dense", {
                    "batch_start": i,
                    "batch_size": len(batch_texts),
                    "sec": float(sec),
                    "items_per_sec": (len(batch_texts) / sec) if sec > 0 else None,
                })

        mmap.flush()
        del mmap
        return dim


class SPLADEEncoder:
    """SPLADE Sparse Encoder"""

    def __init__(
        self,
        model_name: str,
        device: str = None,
        max_length: int = 512,
        dtype: str = "float32",
        topk: Optional[int] = None,
        value_threshold: Optional[float] = None,
    ):
        from transformers import AutoModelForMaskedLM, AutoTokenizer

        self.model_name = model_name
        self.max_length = int(max_length)
        self.topk = topk
        self.value_threshold = value_threshold
        dtype = dtype.lower()
        if dtype not in {"float32", "fp32", "float16", "fp16", "bfloat16", "bf16"}:
            raise ValueError("Invalid SPLADE dtype: %s" % dtype)
        if dtype in {"float16", "fp16"}:
            self.dtype = torch.float16
        elif dtype in {"bfloat16", "bf16"}:
            self.dtype = torch.bfloat16
        else:
            self.dtype = torch.float32

        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device

        print(f"[SPLADE] Loading model: {model_name}")
        print(f"[SPLADE] Device: {self.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForMaskedLM.from_pretrained(model_name)
        self.model.eval()
        self.model.to(self.device)
        if self.dtype in (torch.float16, torch.bfloat16):
            self.model = self.model.to(self.dtype)

        self.vocab_size = self.tokenizer.vocab_size
        print(f"[SPLADE] Loaded. Vocab size: {self.vocab_size}")

    def encode_stream_to_jsonl_gz(
        self,
        texts: List[str],
        out_jsonl_gz: Path,
        batch_size: int,
        metrics: Optional[MetricsCollector],
        t0: float,
        chunk_ids: Optional[List[str]] = None,
        top_tokens: int = 0,
        tokens_out: Optional[Path] = None,
    ) -> int:
        """
        SPLADE sparse vector를 gzip jsonl로 스트리밍 저장.
        각 라인은 순서 보장(0..n-1) 되며 upsert 시 그대로 매칭 가능.
        반환: 저장된 개수
        """
        n = len(texts)
        if chunk_ids is not None and len(chunk_ids) != n:
            raise ValueError("chunk_ids length mismatch")

        print(f"[SPLADE] Writing sparse vectors to: {out_jsonl_gz} (jsonl.gz)")
        written = 0
        token_fp = None
        if top_tokens > 0 and tokens_out is not None:
            token_fp = open(tokens_out, "w", encoding="utf-8")

        try:
            with gzip.open(out_jsonl_gz, "wt", encoding="utf-8") as f:
                iterator = range(0, n, batch_size)
                iterator = tqdm(iterator, desc="SPLADE encoding", unit="batch")

                for i in iterator:
                    bt = time.perf_counter()
                    batch_texts = texts[i:i + batch_size]

                    with torch.no_grad():
                        inputs = self.tokenizer(
                            batch_texts,
                            return_tensors="pt",
                            max_length=self.max_length,
                            truncation=True,
                            padding=True
                        )
                        inputs = {k: v.to(self.device) for k, v in inputs.items()}

                        output = self.model(**inputs)
                        logits = output.logits
                        attention_mask = inputs["attention_mask"]

                        sparse_vecs = torch.max(
                            torch.log(1 + torch.relu(logits)) * attention_mask.unsqueeze(-1),
                            dim=1
                        )[0]

                        batch_nnz: List[int] = []
                        for offset, vec in enumerate(sparse_vecs):
                            non_zero_mask = vec > 0
                            idxs = torch.nonzero(non_zero_mask).squeeze(-1).cpu().tolist()
                            vals = vec[non_zero_mask].cpu().tolist()

                            if self.value_threshold is not None:
                                filtered = [(j, v) for j, v in zip(idxs, vals) if v >= self.value_threshold]
                                if filtered:
                                    idxs, vals = zip(*filtered)
                                    idxs = list(idxs)
                                    vals = list(vals)
                                else:
                                    idxs, vals = [], []

                            if self.topk is not None and len(vals) > self.topk:
                                topk = self.topk
                                top_indices = sorted(range(len(vals)), key=lambda x: vals[x], reverse=True)[:topk]
                                idxs = [idxs[j] for j in top_indices]
                                vals = [vals[j] for j in top_indices]

                            if isinstance(idxs, int):
                                idxs = [idxs]
                                vals = [vals]

                            batch_nnz.append(len(idxs))

                            rec = {"indices": idxs, "values": vals}
                            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                            written += 1

                            if token_fp and vals:
                                top_pairs = sorted(zip(idxs, vals), key=lambda x: x[1], reverse=True)[:top_tokens]
                                if top_pairs:
                                    token_ids = [pair[0] for pair in top_pairs]
                                    token_strings = self.tokenizer.convert_ids_to_tokens(token_ids)
                                    current_chunk_id = chunk_ids[i + offset] if chunk_ids else (i + offset)
                                    token_fp.write(json.dumps({
                                        "chunk_id": current_chunk_id,
                                        "tokens": [
                                            {"token": tok, "value": float(val)}
                                            for tok, (_, val) in zip(token_strings, top_pairs)
                                        ],
                                    }, ensure_ascii=False) + "\n")

                    sec = time.perf_counter() - bt
                    if metrics:
                        now_t = time.perf_counter() - t0
                        metrics.sample_system(now_t)
                        metrics.add_batch("splade", {
                            "batch_start": i,
                            "batch_size": len(batch_texts),
                            "sec": float(sec),
                            "items_per_sec": (len(batch_texts) / sec) if sec > 0 else None,
                            "avg_nnz": (sum(batch_nnz) / len(batch_nnz)) if batch_nnz else 0.0,
                            "max_nnz": max(batch_nnz) if batch_nnz else 0,
                        })
        finally:
            if token_fp:
                token_fp.close()

        return written





# ============================================================
# Qdrant
# ============================================================

class QdrantManager:
    def __init__(self, url: str, collection_name: str, dense_dim: int):
        from qdrant_client import QdrantClient
        self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self.dense_dim = int(dense_dim)
        print(f"[Qdrant] Connected to {url}")

    def create_collection(self, recreate: bool = False):
        from qdrant_client.models import Distance, VectorParams, SparseVectorParams, SparseIndexParams

        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if exists:
            if recreate:
                print(f"[Qdrant] Deleting existing collection: {self.collection_name}")
                self.client.delete_collection(self.collection_name)
            else:
                print(f"[Qdrant] Collection already exists: {self.collection_name}")
                return False

        print(f"[Qdrant] Creating collection: {self.collection_name}")
        print(f"  - Dense dim: {self.dense_dim}")
        print(f"  - Sparse: SPLADE")

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                "dense": VectorParams(size=self.dense_dim, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))
            }
        )
        print("[Qdrant] Collection created")
        return True

    def upsert_from_files(
        self,
        dense_npy: Path,
        splade_jsonl_gz: Path,
        payloads: List[Dict[str, Any]],
        point_ids: List[str],
        batch_size: int = 100,
        recreate: bool = True,
        metrics: Optional[MetricsCollector] = None,
        t0: float = 0.0,
    ) -> Dict[str, Any]:
        """
        dense_npy (memmap load) + splade jsonl.gz (stream) 를 같은 순서로 읽어서 upsert
        """
        from qdrant_client.models import PointStruct, SparseVector

        dense = np.load(dense_npy, mmap_mode="r")
        n = dense.shape[0]
        dim = dense.shape[1]

        # 기본 검증
        assert len(payloads) == n, f"payloads({len(payloads)}) != dense_count({n})"
        assert len(point_ids) == n, f"point_ids({len(point_ids)}) != dense_count({n})"

        # collection 준비
        self.dense_dim = dim
        self.create_collection(recreate=recreate)

        def splade_iter() -> Iterator[Tuple[List[int], List[float]]]:
            with gzip.open(splade_jsonl_gz, "rt", encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line)
                    yield rec["indices"], rec["values"]

        it = splade_iter()

        total = n
        for i in tqdm(range(0, total, batch_size), desc="Upserting to Qdrant"):
            bt = time.perf_counter()

            end = min(i + batch_size, total)
            batch_dense = dense[i:end, :].astype(np.float32, copy=False).tolist()
            batch_payloads = payloads[i:end]
            batch_ids = point_ids[i:end]

            # splade batch read
            batch_sparse: List[Tuple[List[int], List[float]]] = []
            for _ in range(end - i):
                try:
                    batch_sparse.append(next(it))
                except StopIteration:
                    raise RuntimeError(
                        f"SPLADE file ended early. Needed {total} vectors, got only {i + len(batch_sparse)}."
                    )

            points = []
            for pid, dvec, (sidx, sval), payload in zip(batch_ids, batch_dense, batch_sparse, batch_payloads):
                points.append(PointStruct(
                    id=pid,
                    vector={
                        "dense": dvec,
                        "sparse": SparseVector(indices=sidx, values=sval)
                    },
                    payload=payload
                ))

            self.client.upsert(collection_name=self.collection_name, points=points)

            sec = time.perf_counter() - bt
            if metrics:
                now_t = time.perf_counter() - t0
                metrics.sample_system(now_t)
                metrics.add_batch("upsert", {
                    "batch_start": i,
                    "batch_size": (end - i),
                    "sec": float(sec),
                    "points_per_sec": ((end - i) / sec) if sec > 0 else None,
                })

        info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "status": info.status,
            "dense_dim": dim,
        }


# ============================================================
# Helpers
# ============================================================

def load_chunks(input_path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "chunks" in data:
        return data["chunks"], data.get("metadata", {})
    return data, {}

def derive_output_prefix(config: Config, input_path: str) -> str:
    if config.output_prefix.strip():
        return config.output_prefix.strip()
    return Path(input_path).stem

def build_paths(prefix: str) -> Dict[str, Path]:
    return {
        "dense_npy": Path(prefix + "_dense.npy"),
        "splade_jsonl_gz": Path(prefix + "_splade.jsonl.gz"),
        "stats": Path(prefix + "_embed_stats.json"),
        "perf": Path(prefix + "_perf_metrics.json"),
        "order_json": Path(prefix + "_order.json"),
        "splade_tokens_jsonl": Path(prefix + "_splade_top_tokens.jsonl"),
    }


def compute_chunks_signature(chunks: List[Dict[str, Any]]) -> str:
    """Compute a lightweight fingerprint of chunk contents/metadata for order validation."""
    hasher = hashlib.sha1()
    for chunk in chunks:
        meta = chunk.get("metadata", {}) or {}
        content = chunk.get("content", "")
        meta_bytes = json.dumps(meta, sort_keys=True, ensure_ascii=False).encode("utf-8")
        content_bytes = content.encode("utf-8")
        hasher.update(len(meta_bytes).to_bytes(8, "little"))
        hasher.update(meta_bytes)
        hasher.update(len(content_bytes).to_bytes(8, "little"))
        hasher.update(content_bytes)
    return hasher.hexdigest()


def save_length_order(path: Path, order: List[int], total: int, signature: str, config: Config, input_path: str) -> None:
    payload = {
        "created_at": datetime.now().isoformat(),
        "total": total,
        "signature": signature,
        "order": order,
        "input_path": input_path,
        "length_sort": config.length_sort,
        "length_buckets": config.length_buckets,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_length_order(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def derive_point_ids(chunks: List[Dict[str, Any]]) -> List[str]:
    preferred_keys = [
        "id", "chunk_id", "chunkId", "doc_id", "docId", "document_id", "documentId",
        "source_id", "sourceId", "uid", "uuid",
    ]
    ids: List[str] = []
    for chunk in chunks:
        meta = chunk.get("metadata") or {}
        value = None
        for key in preferred_keys:
            candidate = meta.get(key) or chunk.get(key)
            if candidate:
                value = str(candidate)
                break
        if not value:
            raw = json.dumps({
                "metadata": meta,
                "content": chunk.get("content", ""),
            }, ensure_ascii=False, sort_keys=True)
            value = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        ids.append(value)
    return ids


# ============================================================
# Main Pipeline (Split-able)
# ============================================================

def run_pipeline(
    input_path: str,
    config: Config,
    mode: str,
    limit: Optional[int] = None,
    dry_run: bool = False,
    recreate_collection: bool = True,
) -> None:
    chunks, src_meta = load_chunks(input_path)

    if limit:
        chunks = chunks[:limit]
        print(f"[Limit] Processing only {limit} chunks")

    total = len(chunks)
    prefix = derive_output_prefix(config, input_path)
    paths = build_paths(prefix)
    order_path = paths["order_json"]

    texts = [c.get("content", "") for c in chunks]
    payloads = [c.get("metadata", {}) for c in chunks]
    point_ids = derive_point_ids(chunks)
    chunk_signature = compute_chunks_signature(chunks)
    lengths = [len(t) for t in texts]

    length_order: Optional[List[int]] = None
    order_source: Optional[str] = None

    if config.length_sort or config.length_buckets:
        sorted_pairs = sorted((length, idx) for idx, length in enumerate(lengths))
        length_order = []
        bucket_bounds = sorted(config.length_buckets or [])
        pointer = 0
        for bound in bucket_bounds:
            bucket_count = 0
            while pointer < len(sorted_pairs) and sorted_pairs[pointer][0] <= bound:
                length_order.append(sorted_pairs[pointer][1])
                bucket_count += 1
                pointer += 1
            if bucket_count:
                print(f"[LengthBucket] <= {bound} chars : {bucket_count} items")
        if pointer < len(sorted_pairs):
            remaining = len(sorted_pairs) - pointer
            print(f"[LengthBucket] > {bucket_bounds[-1] if bucket_bounds else 'all'} chars : {remaining} items")
            length_order.extend(idx for _, idx in sorted_pairs[pointer:])
        if not length_order:
            length_order = [idx for _, idx in sorted_pairs]
        if not length_order and total > 0:
            length_order = list(range(total))
        order_source = "cli"
        ordered_lengths = [lengths[i] for i in length_order] if length_order else []
        if ordered_lengths:
            print(f"[LengthSort] Enabled. shortest={ordered_lengths[0]} longest={ordered_lengths[-1]}")
        else:
            print(f"[LengthSort] Enabled but dataset is empty.")
    elif order_path.exists() and not config.ignore_saved_order:
        saved_order = load_length_order(order_path)
        if not saved_order:
            print(f"[LengthSort] Failed to parse saved order file: {order_path}")
        else:
            saved_signature = saved_order.get("signature")
            saved_total = saved_order.get("total")
            candidate_order = saved_order.get("order")
            if saved_signature == chunk_signature and saved_total == total and isinstance(candidate_order, list) and len(candidate_order) == total:
                length_order = [int(x) for x in candidate_order]
                order_source = "saved"
                print(f"[LengthSort] Restored saved order from {order_path}")
            else:
                print(f"[LengthSort] Saved order does not match current input (signature/length mismatch). Skipping.")

    if order_source and length_order is not None:
        texts = [texts[i] for i in length_order]
        payloads = [payloads[i] for i in length_order]
        point_ids = [point_ids[i] for i in length_order]
        if order_source == "cli":
            save_length_order(order_path, length_order, total, chunk_signature, config, input_path)
            print(f"[LengthSort] Order saved to {order_path}")
    else:
        print("[LengthSort] Disabled. Natural chunk order will be used.")

    print("\n" + "=" * 70)
    print(f"Mode: {mode}")
    print(f"Input: {input_path}")
    print(f"Chunks: {total:,}")
    print(f"Output prefix: {prefix}")
    print(f"Dense batch: {config.dense_batch_size}, SPLADE batch: {config.splade_batch_size}")
    print(f"Max length: {config.max_length}")
    print(f"Dry run: {dry_run}")
    print(f"Length sort: {bool(order_source)} (source={order_source or 'none'})")
    print("=" * 70)
    if src_meta:
        print(f"[Source metadata] {src_meta}")

    # perf clocks
    t0 = time.perf_counter()
    if torch.cuda.is_available():
        try:
            torch.cuda.reset_peak_memory_stats()
        except Exception:
            pass

    metrics = MetricsCollector(sample_interval_sec=config.metrics_interval)
    metrics.set_meta(config, mode=mode, input_path=input_path)

    # ===== stages =====
    dense_dim = None
    dense_time = 0.0
    splade_time = 0.0
    upsert_time = 0.0
    qdrant_info = None
    splade_tokens_output: Optional[Path] = None

    # 1) Dense
    if mode in ("dense", "all"):
        print("\n[Stage] Dense -> file")
        s = time.perf_counter()
        dense_encoder = DenseEncoder(config.dense_model)
        dense_dim = dense_encoder.encode_stream_to_npy(
            texts=texts,
            out_npy=paths["dense_npy"],
            batch_size=config.dense_batch_size,
            metrics=metrics,
            t0=t0,
        )
        dense_time = time.perf_counter() - s
        metrics.stage_done("dense_encode_to_file", dense_time, {
            "items": total,
            "items_per_sec": (total / dense_time) if dense_time > 0 else None,
            "dense_dim": dense_dim,
            "dense_file": str(paths["dense_npy"]),
        })
        print(f"[Dense] Done. file={paths['dense_npy']} time={dense_time:.1f}s dim={dense_dim}")

    # 2) SPLADE
    if mode in ("splade", "all"):
        print("\n[Stage] SPLADE -> file")
        s = time.perf_counter()
        splade_encoder = SPLADEEncoder(
            config.splade_model,
            max_length=config.max_length,
            dtype=config.splade_dtype,
            topk=config.splade_topk,
            value_threshold=config.splade_value_threshold,
        )
        token_log_path = paths["splade_tokens_jsonl"] if config.splade_debug_topk_tokens > 0 else None
        written = splade_encoder.encode_stream_to_jsonl_gz(
            texts=texts,
            out_jsonl_gz=paths["splade_jsonl_gz"],
            batch_size=config.splade_batch_size,
            metrics=metrics,
            t0=t0,
            chunk_ids=point_ids,
            top_tokens=config.splade_debug_topk_tokens,
            tokens_out=token_log_path,
        )
        if token_log_path:
            splade_tokens_output = token_log_path
        splade_time = time.perf_counter() - s
        metrics.stage_done("splade_encode_to_file", splade_time, {
            "items": total,
            "written": written,
            "items_per_sec": (total / splade_time) if splade_time > 0 else None,
            "splade_file": str(paths["splade_jsonl_gz"]),
            "max_length": config.max_length,
        })
        print(f"[SPLADE] Done. file={paths['splade_jsonl_gz']} time={splade_time:.1f}s written={written}")
        if token_log_path:
            print(f"[SPLADE] Debug tokens log: {token_log_path}")

    # 3) Upsert
    if mode in ("upsert", "all"):
        if dry_run:
            print("\n[Stage] Upsert skipped (dry-run)")
            metrics.stage_done("qdrant_upsert", 0.0, {"skipped": True})
        else:
            print("\n[Stage] Upsert -> Qdrant")

            if not paths["dense_npy"].exists():
                raise FileNotFoundError(f"Dense file not found: {paths['dense_npy']} (run --mode dense first)")
            if not paths["splade_jsonl_gz"].exists():
                raise FileNotFoundError(f"SPLADE file not found: {paths['splade_jsonl_gz']} (run --mode splade first)")

            # 길이 검증(최소)
            dense = np.load(paths["dense_npy"], mmap_mode="r")
            assert dense.shape[0] == total, f"dense_count({dense.shape[0]}) != chunks({total})"

            s = time.perf_counter()
            qdrant = QdrantManager(config.qdrant_url, config.collection_name, dense_dim=dense.shape[1])
            qdrant_info = qdrant.upsert_from_files(
                dense_npy=paths["dense_npy"],
                splade_jsonl_gz=paths["splade_jsonl_gz"],
                payloads=payloads,
                point_ids=point_ids,
                batch_size=100,
                recreate=recreate_collection,
                metrics=metrics,
                t0=t0,
            )
            upsert_time = time.perf_counter() - s
            metrics.stage_done("qdrant_upsert", upsert_time, {
                "points": total,
                "points_per_sec": (total / upsert_time) if upsert_time > 0 else None,
                "collection": config.collection_name,
                "qdrant_url": config.qdrant_url,
            })
            print(f"[Qdrant] Done. time={upsert_time:.1f}s info={qdrant_info}")

    wall = time.perf_counter() - t0
    perf = metrics.finalize(total_items=total, wall_sec=wall)

    # summary stats
    summary = {
        "mode": mode,
        "input": input_path,
        "total_chunks": total,
        "dense_file": str(paths["dense_npy"]),
        "splade_file": str(paths["splade_jsonl_gz"]),
        "dense_time_sec": float(dense_time),
        "splade_time_sec": float(splade_time),
        "upsert_time_sec": float(upsert_time),
        "collection_name": config.collection_name,
        "qdrant_url": config.qdrant_url,
        "wall_sec": float(wall),
        "completed_at": datetime.now().isoformat(),
        "length_sort_source": order_source,
        "order_file": str(order_path) if order_source else None,
        "splade_tokens_file": str(splade_tokens_output) if splade_tokens_output else None,
    }
    if qdrant_info:
        summary["qdrant_collection_info"] = qdrant_info

    # 파일명: mode별로 따로 저장
    stats_file = Path(f"{prefix}_embed_stats_{mode}.json")
    perf_file = Path(f"{prefix}_perf_metrics_{mode}.json")

    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(perf_file, "w", encoding="utf-8") as f:
        json.dump(perf, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("DONE")
    print(f"Stats: {stats_file}")
    print(f"Perf : {perf_file}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Hybrid Embedding V2 (Split-able) + Metrics")

    parser.add_argument("--input", type=str, required=True, help="Input chunks JSON file")

    parser.add_argument("--mode", type=str, default="all",
                        choices=["all", "dense", "splade", "upsert"],
                        help="Which stage to run")

    parser.add_argument("--limit", type=int, default=None, help="Limit number of chunks")
    parser.add_argument("--dry-run", action="store_true", help="Skip Qdrant upsert")

    # models
    parser.add_argument("--dense-model", type=str, default="dragonkue/snowflake-arctic-embed-l-v2.0-ko")
    parser.add_argument("--splade-model", type=str, default="yjoonjang/splade-ko-v1")

    # batch split
    parser.add_argument("--dense-batch-size", type=int, default=32)
    parser.add_argument("--splade-batch-size", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--splade-dtype", type=str, default="float32",
                        choices=["float32", "fp32", "float16", "fp16", "bfloat16", "bf16"],
                        help="SPLADE 계산 dtype")
    parser.add_argument("--splade-topk", type=int, default=None,
                        help="SPLADE 결과에서 상위 K개 지표만 유지")
    parser.add_argument("--splade-value-threshold", type=float, default=None,
                        help="SPLADE 값 임계치 (해당 값 미만은 제거)")
    parser.add_argument("--splade-debug-topk-tokens", type=int, default=0,
                        help="Store top-N SPLADE tokens per chunk for debugging (0=off)")
    parser.add_argument("--length-sort", action="store_true", help="Sort texts by length before encoding")
    parser.add_argument("--length-buckets", type=str, default=None,
                        help="Comma-separated upper bounds for length buckets (e.g., 256,512,1024)")
    parser.add_argument("--ignore-saved-order", action="store_true",
                        help="Do not auto-restore saved length order files")

    # qdrant
    parser.add_argument("--collection", type=str, default="law_documents_v2")
    parser.add_argument("--qdrant-url", type=str, default="http://localhost:6333")
    parser.add_argument("--recreate-collection", action="store_true",
                        help="Recreate Qdrant collection (default: false)")
    parser.add_argument("--no-recreate-collection", action="store_true",
                        help="Do NOT recreate collection (overrides recreate flag)")

    # outputs
    parser.add_argument("--output-prefix", type=str, default="",
                        help="Output prefix for dense/splade files (default: input stem)")

    # metrics
    parser.add_argument("--metrics-interval", type=float, default=1.0,
                        help="System metrics sampling interval sec")

    args = parser.parse_args()

    recreate = args.recreate_collection
    if args.no_recreate_collection:
        recreate = False

    config = Config(
        dense_model=args.dense_model,
        splade_model=args.splade_model,
        qdrant_url=args.qdrant_url,
        collection_name=args.collection,
        dense_batch_size=args.dense_batch_size,
        splade_batch_size=args.splade_batch_size,
        max_length=args.max_length,
        splade_dtype=args.splade_dtype,
        splade_topk=args.splade_topk,
        splade_value_threshold=args.splade_value_threshold,
        output_prefix=args.output_prefix,
        length_sort=args.length_sort,
        length_buckets=[int(x.strip()) for x in args.length_buckets.split(",") if x.strip()] if args.length_buckets else None,
        ignore_saved_order=args.ignore_saved_order,
        splade_debug_topk_tokens=args.splade_debug_topk_tokens,
        metrics_interval=args.metrics_interval,
    )

    run_pipeline(
        input_path=args.input,
        config=config,
        mode=args.mode,
        limit=args.limit,
        dry_run=args.dry_run,
        recreate_collection=recreate,
    )


if __name__ == "__main__":
    main()
