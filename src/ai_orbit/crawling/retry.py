import asyncio
import logging
import random
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    def __init__(self, retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s")

def async_retry(max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 30.0):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            retries = 0
            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except RateLimitError as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Max retries reached for {func.__name__}")
                        raise
                    
                    delay = e.retry_after if e.retry_after else min(base_delay * (2 ** retries), max_delay)
                    jitter = random.uniform(0, 0.1 * delay)
                    total_delay = delay + jitter
                    
                    logger.warning(f"Rate limited in {func.__name__}. Retrying in {total_delay:.2f}s (Attempt {retries}/{max_retries})")
                    await asyncio.sleep(total_delay)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Max retries reached for {func.__name__} due to error: {e}")
                        raise
                    delay = min(base_delay * (2 ** retries), max_delay)
                    jitter = random.uniform(0, 0.1 * delay)
                    total_delay = delay + jitter
                    logger.warning(f"Error in {func.__name__}: {e}. Retrying in {total_delay:.2f}s (Attempt {retries}/{max_retries})")
                    await asyncio.sleep(total_delay)
            return None
        return wrapper
    return decorator
