"""
Production-grade logging configuration
"""
import sys
from pathlib import Path
from loguru import logger
from datetime import datetime


class LoggerSetup:
    """Configure loguru for production logging"""
    
    @staticmethod
    def setup(log_dir: Path, level: str = "INFO"):
        """
        Setup production-grade logging with rotation and structured output
        
        Args:
            log_dir: Directory to store log files
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Remove default handler
        logger.remove()
        
        # Console handler with colors
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=level,
            colorize=True,
        )
        
        # File handler - General logs
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=level,
            rotation="00:00",  # Rotate daily
            retention="30 days",
            compression="zip",
        )
        
        # File handler - Error logs
        logger.add(
            log_dir / "errors_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
            level="ERROR",
            rotation="00:00",
            retention="90 days",
            compression="zip",
            backtrace=True,
            diagnose=True,
        )
        
        # File handler - Anomaly detection logs
        logger.add(
            log_dir / "anomalies_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
            level="INFO",
            filter=lambda record: "anomaly" in record["extra"],
            rotation="00:00",
            retention="180 days",
            compression="zip",
        )
        
        logger.info(f"✅ Logger initialized - Level: {level}")
        return logger


# Singleton logger instance
def get_logger():
    """Get configured logger instance"""
    return logger


# Context manager for logging specific operations
class LogContext:
    """Context manager for structured logging of operations"""
    
    def __init__(self, operation: str, **kwargs):
        self.operation = operation
        self.context = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        logger.bind(**self.context).info(f"▶️  Starting: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            logger.bind(**self.context).success(f"✅ Completed: {self.operation} ({duration:.2f}s)")
        else:
            logger.bind(**self.context).error(f"❌ Failed: {self.operation} ({duration:.2f}s) - {exc_val}")
        
        return False  # Don't suppress exceptions
