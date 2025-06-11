import time
from functools import wraps
from loguru import logger

def retry_with_timeout(func, max_attempts=3, timeout=30, delay=1):
    """
    Retry a function with timeout and exponential backoff.
    
    Args:
        func: The function to retry
        max_attempts: Maximum number of attempts
        timeout: Total timeout in seconds
        delay: Initial delay between attempts in seconds
    
    Returns:
        The result of the function if successful
    """
    start_time = time.time()
    attempt = 0
    
    while attempt < max_attempts:
        try:
            result = func()
            if result:
                return result
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}")
        
        # Check if we've exceeded the total timeout
        if time.time() - start_time > timeout:
            logger.error(f"Timeout exceeded after {timeout} seconds")
            return False
        
        # Calculate next delay with exponential backoff
        next_delay = min(delay * (2 ** attempt), 10)  # Cap at 10 seconds
        logger.info(f"Retrying in {next_delay:.1f} seconds...")
        time.sleep(next_delay)
        attempt += 1
    
    logger.error(f"Failed after {max_attempts} attempts")
    return False 