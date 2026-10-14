import logging
import sys


logger = logging.getLogger("infrastructure_events")

logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(handler)
