import threading


class _BoundSignal:
    """Per-instance thread-safe signal slot registry."""

    def __init__(self):
        self._slots = []
        self._lock = threading.Lock()

    def connect(self, slot):
        if callable(slot):
            with self._lock:
                if slot not in self._slots:
                    self._slots.append(slot)

    def disconnect(self, slot=None):
        with self._lock:
            if slot is None:
                self._slots.clear()
            elif slot in self._slots:
                self._slots.remove(slot)

    def emit(self, *args):
        with self._lock:
            slots = list(self._slots)
        for slot in slots:
            try:
                slot(*args)
            except Exception:
                pass


class Signal:
    """Descriptor replicating per-instance Qt signal semantics without PyQt6."""

    def __init__(self, *_types):
        self._name = None

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        key = f"__sig_{self._name or id(self)}"
        sig = instance.__dict__.get(key)
        if sig is None:
            sig = _BoundSignal()
            instance.__dict__[key] = sig
        return sig


class WorkerThread:
    """Pure-Python QThread replacement supporting start(), run(), stop(), isRunning(), wait()."""

    def __init__(self, parent=None):
        self.parent = parent
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def run(self):
        pass

    def isRunning(self):
        return bool(self._thread and self._thread.is_alive())

    def wait(self, msecs=None):
        t = self._thread
        if t and t.is_alive():
            timeout = None if msecs is None else (max(0, msecs) / 1000.0)
            t.join(timeout=timeout)
        return not (t and t.is_alive())
