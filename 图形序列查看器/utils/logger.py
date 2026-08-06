"""Application logging and uncaught exception hook."""
import datetime
import logging
import os
import sys
from typing import Any


class DelayedFileHandler(logging.Handler):
    """Create a timestamped log file only when the first error is emitted."""

    def __init__(self) -> None:
        super().__init__()
        self.file_handler: logging.FileHandler | None = None

    def emit(self, record: Any) -> Any:
        if self.file_handler is None:
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv else os.getcwd()
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = os.path.join(script_dir, f'{timestamp}.log')
            handler = logging.FileHandler(log_file, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.file_handler = handler
        self.file_handler.emit(record)
logger = logging.getLogger('image_sequence_viewer')
logger.setLevel(logging.ERROR)
if not logger.handlers:
    logger.addHandler(DelayedFileHandler())

def handle_exception(exc_type: Any, exc_value: Any, exc_traceback: Any) -> Any:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error('Uncaught exception', exc_info=(exc_type, exc_value, exc_traceback))

def install_exception_hook() -> Any:
    sys.excepthook = handle_exception
