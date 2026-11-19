"""Phase 9: Measure real RSS memory footprint and Render deployment compatibility."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _rss_mb() -> float:
    """Return current process Resident Set Size (Working Set on Windows) in MiB."""
    if sys.platform == "win32":
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi = ctypes.windll.psapi
        psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        proc = k32.GetCurrentProcess()
        psapi.GetProcessMemoryInfo(proc, ctypes.byref(counters), counters.cb)
        return counters.WorkingSetSize / (1024 * 1024)
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def main() -> None:
    rss_start = _rss_mb()

    # Step 1: Load existing FastAPI backend without moderation model
    t0 = time.perf_counter()
    from backend.app.main import app  # noqa: F401
    backend_import_ms = (time.perf_counter() - t0) * 1000.0
    rss_after_backend = _rss_mb()

    # Step 2: Load production ML moderation model once
    from ml_moderation.config import DEFAULT_MODEL_PATH, REPORTS_DIR
    from ml_moderation.predictor import get_moderator

    t1 = time.perf_counter()
    moderator = get_moderator(DEFAULT_MODEL_PATH)
    model_load_ms = (time.perf_counter() - t1) * 1000.0
    rss_after_model = _rss_mb()

    # Step 3: Warm single-request inference check
    probe = [
        "Assignment_12.pdf",
        "Class_Notes.pdf",
        "Қазақстан_тарихы.pdf",
        "Лекция_математика.pdf",
        "ASS.pdf",
        "pppAAASSSS.pdf",
        "A.S.S.pdf",
        "@$$.pdf",
        "A123SS.pdf",
        "pASS.pdf",
    ]
    for p in probe:
        moderator.moderate(p)
    times = []
    for _ in range(20):
        for p in probe:
            ts = time.perf_counter()
            moderator.moderate(p)
            times.append((time.perf_counter() - ts) * 1000.0)
    times.sort()
    avg_ms = sum(times) / len(times)
    p95_ms = times[int(len(times) * 0.95)]
    rss_after_infer = _rss_mb()

    report = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "model_type": moderator.model_type,
        "model_version": moderator.model_version,
        "artifact_size_kb": round(DEFAULT_MODEL_PATH.stat().st_size / 1024.0, 2),
        "backend_import_ms": round(backend_import_ms, 2),
        "model_load_ms": round(model_load_ms, 2),
        "warm_inference_avg_ms": round(avg_ms, 4),
        "warm_inference_p95_ms": round(p95_ms, 4),
        "rss_start_mb": round(rss_start, 2),
        "rss_after_backend_mb": round(rss_after_backend, 2),
        "rss_after_model_mb": round(rss_after_model, 2),
        "rss_after_infer_mb": round(rss_after_infer, 2),
        "model_rss_delta_mb": round(rss_after_model - rss_after_backend, 2),
        "render_free_ram_limit_mb": 512,
        "estimated_headroom_mb": round(512.0 - rss_after_infer, 2),
        "smoke_checks": {
            p: {
                "allowed": moderator.moderate(p).allowed,
                "confidence": round(moderator.moderate(p).confidence, 4),
            }
            for p in probe
        },
    }
    out = REPORTS_DIR / "render_compatibility.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
