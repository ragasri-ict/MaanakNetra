import os
import gc

def log_memory(label: str):
    """Logs process RSS memory usage if psutil is available."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        rss_mb = process.memory_info().rss / (1024 * 1024)
        print(f"[MEMORY] {label:<40}: RSS = {rss_mb:.2f} MB", flush=True)
    except Exception:
        pass

def release_memory():
    """Forces garbage collection and releases unreferenced memory."""
    try:
        gc.collect()
        import torch
        if hasattr(torch, "cuda") and torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
