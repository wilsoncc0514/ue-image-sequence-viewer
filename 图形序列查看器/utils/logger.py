"""Application logging and uncaught exception hook."""
import datetime
import logging
import os
import sys
from pathlib import Path
from typing import Any


class DelayedFileHandler(logging.Handler):
    """Create a timestamped log file only when the first error is emitted."""

    def __init__(self, log_dir: str | os.PathLike[str] | None = None) -> None:
        super().__init__()
        self.log_dir = Path(log_dir) if log_dir is not None else None
        self.file_handler: logging.FileHandler | None = None

    def emit(self, record: Any) -> Any:
        if self.file_handler is None:
            script_dir = self.log_dir or Path(
                os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv else os.getcwd()
            )
            script_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = script_dir / f'{timestamp}.log'
            handler = logging.FileHandler(log_file, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.file_handler = handler
        self.file_handler.emit(record)

    def close(self) -> None:
        if self.file_handler is not None:
            self.file_handler.close()
            self.file_handler = None
        super().close()


logger = logging.getLogger('image_sequence_viewer')
logger.setLevel(logging.ERROR)
if not logger.handlers:
    # Library imports and expected test failures must not create runtime files.
    logger.addHandler(logging.NullHandler())


def handle_exception(exc_type: Any, exc_value: Any, exc_traceback: Any) -> Any:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error('Uncaught exception', exc_info=(exc_type, exc_value, exc_traceback))


def install_exception_hook(log_dir: str | os.PathLike[str] | None = None) -> Any:
    if not any(isinstance(handler, DelayedFileHandler) for handler in logger.handlers):
        logger.addHandler(DelayedFileHandler(log_dir=log_dir))
    sys.excepthook = handle_exception
