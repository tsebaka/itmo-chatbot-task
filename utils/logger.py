from loguru import logger
import sys
from pathlib import Path

def setup_logging(log_file: str | None = None, level: str = "INFO"):
    logger.remove()
    logger.add(
        sys.stdout,
        level=level
    )
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(log_path, rotation="1 day", retention="7 days", compression="zip", level=level)
    
    return logger

