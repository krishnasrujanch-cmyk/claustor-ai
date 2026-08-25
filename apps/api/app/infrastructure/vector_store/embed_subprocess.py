#!/usr/bin/env python3
"""
Standalone bge-m3 embedding script.
Called as subprocess from chunk_indexer to avoid OOM in Celery worker.
Input: JSON list of texts via stdin
Output: JSON list of embeddings via stdout
"""
import sys, json, os

cache_dir = os.getenv("SENTENCE_TRANSFORMERS_HOME",
    os.path.expanduser("~/.cache/sentence_transformers"))

from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-m3", cache_folder=cache_dir)

texts = json.load(sys.stdin)
embeddings = model.encode(texts, normalize_embeddings=True,
    show_progress_bar=False).tolist()
json.dump(embeddings, sys.stdout)
