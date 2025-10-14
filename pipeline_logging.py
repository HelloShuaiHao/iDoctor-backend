import os
import threading
import time

_log_locks = {}

def _get_lock(path: str):
    return _log_locks.setdefault(path, threading.Lock())

def write_log(output_root: str, message: str, filename: str = "pipeline.log"):
    """Append a timestamped line to output_root/filename.

    Creates directory if missing. Thread-safe. Swallows IO errors silently.
    """
    if not output_root:
        return
    try:
        os.makedirs(output_root, exist_ok=True)
        log_path = os.path.join(output_root, filename)
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{ts}] {message}\n"
        lock = _get_lock(log_path)
        with lock:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(line)
    except Exception:
        pass

def log_section(output_root: str, title: str, filename: str = "pipeline.log"):
    write_log(output_root, f"===== {title} =====", filename=filename)
