import logging

from hexdoc.utils import setup_logging
from pytest import CaptureFixture


def test_setup_logging_idempotent(capsys: CaptureFixture[str]):
    setup_logging(0, False)
    setup_logging(0, False)
    logger = logging.getLogger()

    logger.info("message")

    _, err = capsys.readouterr()
    assert len(err.splitlines()) == 1
    assert "message" in err
