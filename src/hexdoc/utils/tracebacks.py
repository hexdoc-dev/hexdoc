import contextlib
import inspect
import io
import sys
import traceback
from types import CodeType, FrameType, TracebackType
from typing import cast


class FilteredTracebackWrapper:
    """Wrapper for `types.TracebackType` to allow hiding modules from tracebacks."""

    def __init__(self, tb: TracebackType, hidden_modules: set[str]):
        self._tb = tb
        self._hidden_modules = hidden_modules
        self._skipped = 0

    @classmethod
    def wrap_cast(cls, tb: TracebackType | None, hidden_modules: set[str]):
        if tb is None:
            return None
        return cls(tb, hidden_modules).cast()

    @classmethod
    def _wrap(cls, tb: TracebackType | None, hidden_modules: set[str]):
        if tb is None:
            return None
        return cls(tb, hidden_modules)

    @property
    def tb_frame(self) -> FrameType:
        frame = self._tb.tb_frame
        if not self._skipped:
            return frame
        return SkippedCallsFrameWrapper(frame, self._skipped).cast()

    @property
    def tb_next(self) -> TracebackType | None:
        tb_next = self._wrap_next()
        skipped = 0

        while tb_next:
            if tb_next._is_hidden():
                tb_next = tb_next._wrap_next()
                skipped += 1
                continue

            tb_next._skipped = skipped
            return tb_next.cast()

        return None

    def cast(self):
        return cast(TracebackType, self)

    def _is_hidden(self):
        # never filter out the last frame
        if self._tb.tb_next is None:
            return False

        mod = self._get_module()
        return mod is not None and mod.__name__ in self._hidden_modules

    def _get_module(self):
        return inspect.getmodule(self.tb_frame)

    def _wrap_next(self):
        return self._wrap(self._tb.tb_next, self._hidden_modules)

    def __getattr__(self, name: str):
        return getattr(self._tb, name)


class SkippedCallsFrameWrapper:
    """Wrapper for `types.FrameType` to allow changing read-only attributes."""

    def __init__(self, frame: FrameType, skipped: int):
        self._frame = frame
        self.f_code = SkippedCallsCodeWrapper(frame.f_code, skipped)

    def cast(self):
        return cast(FrameType, self)

    def __getattr__(self, name: str):
        return getattr(self._frame, name)


class SkippedCallsCodeWrapper:
    """Wrapper for `types.CodeType` to allow changing read-only attributes."""

    def __init__(self, code: CodeType, skipped: int):
        self._code = code

        s = "" if skipped == 1 else "s"
        self.co_name = f"{code.co_name} (...after {skipped} skipped call{s})"

    def cast(self):
        return cast(CodeType, self)

    def __getattr__(self, name: str):
        return getattr(self._code, name)


def create_filtered_excepthook(hidden_modules: set[str]):
    """Creates a replacement for `sys.excepthook` using `FilteredTracebackWrapper`.

    Traceback frames where the `__name__` of the source module is in `hidden_modules`
    will not be printed by this hook.
    """

    def filtered_excepthook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ):
        exc_tb = FilteredTracebackWrapper.wrap_cast(exc_tb, hidden_modules)
        traceback.print_exception(exc_type, exc_value, exc_tb)

    return filtered_excepthook


# https://github.com/python/cpython/blob/6f9ca53a6ac343a5/Lib/idlelib/run.py#L225
def get_message_with_hints(exc: AttributeError | NameError, removeprefix: bool = True):
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        sys.__excepthook__(type(exc), exc, None)
    message = err.getvalue().strip().split("\n")[-1]
    if removeprefix:
        message = message.removeprefix(f"{type(exc).__name__}: ")
    return message
