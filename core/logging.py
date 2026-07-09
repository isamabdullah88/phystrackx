"""
logging.py

Handles logging setup by routing colored output to the console and 
creating unique timestamped file logs for each unique runtime session.

Author: Isam Balghari
"""

import os
import logging
from datetime import datetime
import colorlog


def setup_logging() -> None:
    """
    Dynamically builds a unique log file per runtime session inside a 
    dedicated directory, configuring colored console streaming profiles.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Format: YYYYMMDD_HHMMSS -> e.g., logs/20260707_170500.log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"{timestamp}.log")

    # Formatter for colored console output
    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'bold_red',
        }
    )

    # Console handler with color
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(color_formatter)

    # File handler
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler]
    )