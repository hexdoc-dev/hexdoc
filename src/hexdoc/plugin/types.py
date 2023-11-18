from typing import TypeVar

_T = TypeVar("_T")

HookReturn = _T | list[_T]

HookReturns = list[HookReturn[_T]]
