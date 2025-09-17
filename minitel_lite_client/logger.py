import logging
import sys
from loguru import logger

def get_logger(name: str):
    """
    Configure and get a logger instance for the MiniTel-Lite client
    
    Args:
        name: Name of the logger (typically __name__ of the module)
        
    Returns:
        Configured logger instance
    """
    # Configure Loguru logger
    logger.remove()  # Remove default handler
    
    # Add stdout handler with debug level
    logger.add(
        sys.stdout,
        level="DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Add file handler with info level
    logger.add(
        "minitel_lite_client.log",
        level="INFO",
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    return logger.opt(depth=1)
