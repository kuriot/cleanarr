"""
Logging configuration for Cleanarr
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class CleanarrLogger:
    """Custom logger for Cleanarr with file and console handlers"""

    def __init__(self, log_level: str = "INFO", log_file: Optional[Path] = None):
        self.log_level = log_level.upper()
        self.log_file = (
            log_file or Path.home() / ".config" / "cleanarr" / "cleanarr.log"
        )
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging configuration"""
        # Create log directory if it doesn't exist
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create root logger
        self.logger = logging.getLogger("cleanarr")
        self.logger.setLevel(getattr(logging, self.log_level))

        # Clear any existing handlers
        self.logger.handlers.clear()

        # Console handler - only INFO and above, clean format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler - all levels, detailed format
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        return self.logger


# Global logger instance
_logger_instance: Optional[CleanarrLogger] = None
_logger: Optional[logging.Logger] = None


def setup_logging(
    log_level: str = "INFO", log_file: Optional[Path] = None
) -> logging.Logger:
    """Setup global logging configuration"""
    global _logger_instance, _logger

    _logger_instance = CleanarrLogger(log_level, log_file)
    _logger = _logger_instance.get_logger()

    return _logger


def get_logger() -> logging.Logger:
    """Get the global logger instance"""
    global _logger

    if _logger is None:
        _logger = setup_logging()

    return _logger


# Convenience functions for common log levels
def debug(message: str):
    """Log debug message"""
    get_logger().debug(message)


def info(message: str):
    """Log info message (shows on console and file)"""
    get_logger().info(message)


def warning(message: str):
    """Log warning message"""
    get_logger().warning(message)


def error(message: str):
    """Log error message"""
    get_logger().error(message)


def success(message: str):
    """Log success message (info level with emoji)"""
    get_logger().info(f"✅ {message}")


def failure(message: str):
    """Log failure message (warning level with emoji)"""
    get_logger().warning(f"❌ {message}")


def skip(message: str):
    """Log skip message (info level with emoji)"""
    get_logger().info(f"⏭️  {message}")


def progress(message: str):
    """Log progress message (info level with emoji)"""
    get_logger().info(f"🔍 {message}")


def config_info(message: str):
    """Log configuration info (debug level)"""
    get_logger().debug(f"🔧 CONFIG: {message}")


def api_debug(service: str, message: str):
    """Log API debug information"""
    get_logger().debug(f"🌐 {service.upper()} API: {message}")


def connection_success(service: str, message: str = ""):
    """Log successful connection"""
    get_logger().info(
        f"✅ {service} connection successful{f' - {message}' if message else ''}"
    )


def connection_failure(service: str, message: str = ""):
    """Log failed connection"""
    get_logger().warning(
        f"❌ Cannot connect to {service}{f': {message}' if message else ''}"
    )


def cleanup_summary(movies: int, series: int):
    """Log cleanup summary"""
    get_logger().info(f"📊 Cleanup Summary: {movies} movies, {series} series to delete")


def cleanup_result(
    movies_deleted: int, movies_failed: int, series_deleted: int, series_failed: int
):
    """Log cleanup results"""
    logger = get_logger()
    logger.info(f"✅ Cleanup Results:")
    logger.info(f"   Movies: {movies_deleted} deleted, {movies_failed} failed")
    logger.info(f"   Series: {series_deleted} deleted, {series_failed} failed")
