"""Prefetch the ONNX artifacts used for local embeddings + reranking.

The embedder auto-downloads on first use (small, required for retrieval). The
reranker is large (~1GB) and cache-only on the request path, so run this once
to enable reranking:

    python -m scripts.download_onnx_models
"""
from __future__ import annotations

import os

from huggingface_hub import snapshot_download

from app.config import get_settings


def download(repo_id: str) -> str:
    settings = get_settings()
    local_dir = os.path.join(settings.onnx_model_dir, repo_id.replace("/", "_"))
    print(f"Downloading {repo_id} -> {local_dir}")
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        allow_patterns=["tokenizer.json", "config.json", "onnx/*.onnx"],
    )
    return local_dir


def main() -> None:
    settings = get_settings()
    for repo_id in (settings.onnx_embedding_repo, settings.onnx_reranker_repo):
        print(f"OK: {download(repo_id)}")


if __name__ == "__main__":
    main()
