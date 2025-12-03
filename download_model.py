#!/usr/bin/env python3
"""
Download XTTS-v2 model from HuggingFace.
Run this script first to download the model files.
"""

from huggingface_hub import snapshot_download
import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))

print("Downloading XTTS-v2 model from HuggingFace...")
print(f"Target directory: {MODEL_DIR}")

snapshot_download(
    repo_id="coqui/XTTS-v2",
    local_dir=MODEL_DIR,
    local_dir_use_symlinks=False
)

print("\nDownload complete!")
print("Model files:")
for f in os.listdir(MODEL_DIR):
    if f.endswith('.pth') or f.endswith('.json'):
        size = os.path.getsize(os.path.join(MODEL_DIR, f))
        print(f"  {f}: {size / 1024 / 1024:.1f} MB")
