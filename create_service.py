import sys
import os
import types
import gc
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp

logger = hp.get_logger(__name__)

# Default path to the voice task module, relative to this file
_DEFAULT_TASKS_PATH = os.path.join(os.path.dirname(__file__), "voice", "gryd_tasks.py")


class PluginManager:
    def __init__(self):
        self.registry = {}

    def create_plugin(self, name: str, code: str):
        if name in sys.modules:
            raise ValueError(f"Plugin '{name}' already exists")

        module = types.ModuleType(name)
        exec(code, module.__dict__)

        sys.modules[name] = module
        self.registry[name] = module

        return module

    def get_plugin(self, name: str):
        return self.registry.get(name)

    def reload_plugin(self, name: str, new_code: str):
        if name not in self.registry:
            raise ValueError(f"Plugin '{name}' not found")

        module = self.registry[name]

        module.__dict__.clear()
        module.__dict__["__name__"] = name

        exec(new_code, module.__dict__)

        return module

    def delete_plugin(self, name: str):
        if name not in self.registry:
            return

        module = self.registry[name]

        if name in sys.modules:
            del sys.modules[name]

        del self.registry[name]
        del module
        gc.collect()

    def list_plugins(self):
        return list(self.registry.keys())

    def create_gryd_service(self, service_name: str, gryd_tasks_path: str = None):
        """
        Creates a dynamic module from gryd_tasks.py with gryd.SERVICE set to
        service_name, so all @is_a_task decorators register tasks under that name.

        Args:
            service_name:    The gryd service name for this instance, e.g.
                             "autocrm-voice-ambal-auto-india".
            gryd_tasks_path: Path to gryd_tasks.py. Defaults to
                             voice/gryd_tasks.py next to this file.

        Returns:
            The created (or reloaded) module.
        """
        module_name = f"gryd_tasks_{service_name}"
        tasks_path = gryd_tasks_path or _DEFAULT_TASKS_PATH

        with open(tasks_path, "r") as f:
            source = f.read()

        # Patch the SERVICE assignment so @is_a_task registers tasks under
        # the dealer-specific name instead of the shared autocrm-voice name.
        source = source.replace(
            "gryd.SERVICE = config.AUTOCRM_VOICE_SERVICE_NAME",
            f'gryd.SERVICE = "{service_name}"',
        )

        if module_name in self.registry:
            return self.reload_plugin(module_name, source)

        return self.create_plugin(module_name, source)


class VoiceServiceManager:
    """
    Manages per-dealer voice service instances for parallel campaign execution.

    Problem:
        All dealers share one queue (input-autocrm-voice) with MAX_CONCURRENCY
        threads.  When dealer A dispatches 100 calls, dealer B's 100 calls queue
        behind them — no two campaigns can run in parallel.

    Solution:
        Each dealer gets an isolated queue: input-autocrm-voice-{dealer_id}.
        A dedicated thread pool consumes that queue independently.  Campaigns
        for different dealers run fully in parallel.

    Usage:
        manager = VoiceServiceManager()
        manager.dispatch_batch("ambal-auto-india", customer_list, max_threads=10)
        manager.dispatch_batch("us-dealership-xyz", other_list,   max_threads=10)
        # Both campaigns run on separate queues/thread pools simultaneously.
        # When done:
        manager.stop("ambal-auto-india")
    """

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._initialized = False
                cls._instance = obj
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._plugin_manager = PluginManager()
        self._active = {}   # dealer_id -> {service_name, executor, stop_event}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Naming helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _service_name(dealer_id: str) -> str:
        safe = dealer_id.strip().lower().replace(" ", "-").replace("_", "-")
        return f"autocrm-voice-{safe}"

    @staticmethod
    def _queue_name(service_name: str) -> str:
        env = gryd.ENVIRONMENT   # "" in prod, "-dev" / "-staging" otherwise
        return f"input-{service_name}{env}"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, dealer_id: str, max_threads: int = 10) -> str:
        """
        Create and start an isolated voice service for dealer_id.

        Idempotent: if already running, returns the existing service name
        without spawning duplicate workers.

        Returns the service name to use with gryd.create_async_task().
        """
        service_name = self._service_name(dealer_id)

        with self._lock:
            if dealer_id in self._active:
                logger.info("Dealer service '%s' already running.", service_name)
                return service_name

            # Exec gryd_tasks.py with SERVICE = service_name so every
            # @is_a_task decorator registers under the dealer-specific name.
            self._plugin_manager.create_gryd_service(service_name)
            logger.info(
                "Created gryd service '%s'. Tasks: %s",
                service_name,
                list(gryd.LIST_OF_TASKS.get(service_name, {}).keys()),
            )

            stop_event = threading.Event()
            executor = ThreadPoolExecutor(
                max_workers=max_threads,
                thread_name_prefix=f"voice-{dealer_id[:14]}",
            )

            for _ in range(max_threads):
                executor.submit(self._worker_loop, service_name, stop_event)

            self._active[dealer_id] = {
                "service_name": service_name,
                "executor": executor,
                "stop_event": stop_event,
            }

        logger.info(
            "Started %d workers for dealer '%s' on queue '%s'.",
            max_threads, dealer_id, self._queue_name(service_name),
        )
        return service_name

    def stop(self, dealer_id: str, wait: bool = True) -> None:
        """
        Gracefully stop a dealer's workers and clean up its task registration.
        """
        with self._lock:
            state = self._active.pop(dealer_id, None)

        if state is None:
            logger.warning("No active service for dealer '%s'.", dealer_id)
            return

        state["stop_event"].set()
        state["executor"].shutdown(wait=wait, cancel_futures=False)

        gryd.LIST_OF_TASKS.pop(state["service_name"], None)
        self._plugin_manager.delete_plugin(f"gryd_tasks_{state['service_name']}")

        logger.info("Stopped voice service for dealer '%s'.", dealer_id)

    def stop_all(self, wait: bool = True) -> None:
        for dealer_id in list(self._active.keys()):
            self.stop(dealer_id, wait=wait)

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------

    def _worker_loop(self, service_name: str, stop_event: threading.Event) -> None:
        """
        Poll the dealer's queue and execute received jobs until stop_event fires.
        Blocks on listen() for up to 2 s so it doesn't busy-spin on empty queues.
        """
        from gryd_worker.backends import get_queue_manager

        queue_name = self._queue_name(service_name)
        qm = get_queue_manager(module_name=service_name, new=True)

        logger.info("Worker started — service '%s', queue '%s'.", service_name, queue_name)

        while not stop_event.is_set():
            try:
                for job in qm.listen(queue_name, service=service_name, timeout=2):
                    if stop_event.is_set():
                        break
                    try:
                        gryd.execute_task(job)
                    except Exception as exc:
                        logger.error(
                            "Task error in '%s': %s", service_name, exc, exc_info=True
                        )
            except Exception as exc:
                if not stop_event.is_set():
                    logger.error(
                        "Queue poll error in '%s': %s", service_name, exc, exc_info=True
                    )

        logger.info("Worker stopped — service '%s'.", service_name)

    # ------------------------------------------------------------------
    # Dispatch helpers
    # ------------------------------------------------------------------

    def dispatch_call(self, dealer_id: str, user_data: dict, max_threads: int = 10) -> dict:
        """
        Send a single trigger_voice_call task to the dealer's isolated queue.
        Starts the dealer service automatically on first call.
        """
        service_name = self.start(dealer_id, max_threads=max_threads)
        return gryd.create_async_task(
            "trigger_voice_call",
            service_name,
            args=[],
            kwargs={"user_data": user_data},
        )

    def dispatch_batch(
        self,
        dealer_id: str,
        user_data_list: list,
        max_threads: int = 10,
    ) -> list:
        """
        Send a batch of trigger_voice_call tasks for a single dealer.
        Starts the dealer service automatically on first call.
        Multiple dealers can call this concurrently — queues are fully isolated.
        """
        service_name = self.start(dealer_id, max_threads=max_threads)

        results = []
        for user_data in user_data_list:
            result = gryd.create_async_task(
                "trigger_voice_call",
                service_name,
                args=[],
                kwargs={"user_data": user_data},
            )
            results.append(result)

        logger.info(
            "Dispatched %d calls for dealer '%s' → service '%s'.",
            len(results), dealer_id, service_name,
        )
        return results

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_active(self) -> dict:
        """Return {dealer_id: service_name} for all running services."""
        with self._lock:
            return {did: s["service_name"] for did, s in self._active.items()}

    def is_active(self, dealer_id: str) -> bool:
        return dealer_id in self._active


def get_voice_service_manager() -> VoiceServiceManager:
    """Return the process-wide VoiceServiceManager singleton."""
    return VoiceServiceManager()
