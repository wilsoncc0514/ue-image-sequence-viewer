"""Application logging and uncaught exception hook."""
import datetime
import logging
import os
import sys
from pathlib import Path
from typing import Any


def default_log_directory() -> Path:
    """Keep diagnostics outside the installation directory."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "ue-image-sequence-viewer"
    if sys.platform == "win32":
        return Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "ue-image-sequence-viewer" / "logs"
    return Path(os.getenv("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "ue-image-sequence-viewer" / "logs"


class DelayedFileHandler(logging.Handler):
    """Create a timestamped log file only when the first error is emitted."""

    def __init__(self, log_dir: str | os.PathLike[str] | None = None) -> None:
        super().__init__()
        self.log_dir = Path(log_dir) if log_dir is not None else default_log_directory()
        self.file_handler: logging.FileHandler | None = None

    def emit(self, record: Any) -> Any:
        try:
            if self.file_handler is None:
                self.log_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                log_file = self.log_dir / f'{timestamp}.log'
                handler = logging.FileHandler(log_file, encoding='utf-8')
                handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                self.file_handler = handler
            # Write explicitly so stream errors also reach the safe fallback,
            # rather than StreamHandler swallowing them in handleError.
            stream = self.file_handler.stream
            if stream is None:
                raise OSError("日志文件已关闭")
            stream.write(self.file_handler.format(record) + "\n")
            self.file_handler.flush()
        except Exception as exc:
            self._fallback(record, exc)

    def _fallback(self, record: logging.LogRecord, exc: Exception) -> None:
        for stream in (sys.stderr, sys.__stderr__):
            if stream is None:
                continue
            try:
                stream.write(f"日志写入失败（{type(exc).__name__}）：{self.format(record)}\n")
                stream.flush()
                return
            except Exception:
                continue  # Try the original stderr; diagnostics must not raise.

    def close(self) -> None:
        if self.file_handler is not None:
            try:
                self.file_handler.close()
            except (OSError, ValueError) as exc:
                self._fallback(logging.LogRecord("logger", logging.ERROR, __file__, 0, "关闭日志文件失败", (), None), exc)
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
