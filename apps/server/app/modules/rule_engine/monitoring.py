"""Performance monitoring helpers for the rule engine."""

import functools
import time as time_module


def monitor_performance(operation: str):
    """Async decorator that records rule-engine call metrics."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time_module.time()

            try:
                result = await func(self, *args, **kwargs)

                duration_ms = (time_module.time() - start_time) * 1000
                shift_type_id = None
                if args and isinstance(args[0], str):
                    shift_type_id = args[0]
                elif kwargs.get("shift_type_id"):
                    shift_type_id = kwargs["shift_type_id"]

                from app.modules.rule_engine.rule_performance_service import performance_monitor

                await performance_monitor.record_call(
                    operation=operation,
                    duration_ms=duration_ms,
                    shift_type_id=shift_type_id,
                    metadata={
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                    },
                )

                return result

            except Exception as e:
                duration_ms = (time_module.time() - start_time) * 1000
                from app.modules.rule_engine.rule_performance_service import performance_monitor

                await performance_monitor.record_call(
                    operation=operation,
                    duration_ms=duration_ms,
                    metadata={"error": str(e)},
                )
                raise

        return wrapper

    return decorator
