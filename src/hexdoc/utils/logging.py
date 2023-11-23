import logging
import sys

TRACE = 5
"""For even more verbose logs than `logging.DEBUG`."""


def setup_logging(verbosity: int):
    logging.basicConfig(
        style="{",
        format="\033[1m[{relativeCreated:.02f} | {levelname} | {name}]\033[0m {message}",
        level=verbosity_log_level(verbosity),
    )
    logging.addLevelName(TRACE, "TRACE")
    logging.getLogger(__name__).info("Starting.")


def verbosity_log_level(verbosity: int) -> int:
    match verbosity:
        case 0:
            return logging.WARNING
        case 1:
            return logging.INFO
        case 2:
            return logging.DEBUG
        case _:
            return TRACE


def repl_readfunc():
    exit_next = False

    def inner(prompt: str) -> str:
        nonlocal exit_next
        try:
            response = input(prompt)
            exit_next = False
            return response
        except KeyboardInterrupt:
            if exit_next:
                print("\nExiting.")
                sys.exit()

            print("\nPress ctrl+c again to exit.", end="")
            exit_next = True
            raise

    return inner
