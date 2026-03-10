import time
import functools
import logging

logger = logging.getLogger("quant_autoresearch")

def retry_with_backoff(max_retries=3, initial_delay=1, backoff_factor=2, exceptions=(Exception,)):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for i in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if i == max_retries:
                        break
                    
                    logger.warning(f"Retry {i+1}/{max_retries} for {func.__name__} after {delay}s due to: {e}")
                    time.sleep(delay)
                    delay *= backoff_factor
            
            logger.error(f"Failed {func.__name__} after {max_retries} retries. Final error: {last_exception}")
            raise last_exception
        return wrapper
    return decorator
