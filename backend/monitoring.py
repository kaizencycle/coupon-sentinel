"""
Coupon Sentinel - Monitoring (Milestone 5)

Sentry error tracking, initialized only when SENTRY_DSN is set — importing
this module and calling init_monitoring() is always safe without a DSN,
same guarded pattern as every other integration in this project (Stripe,
Kroger, email, Mixpanel). Unverified against a real Sentry project: no DSN
exists for this project yet.

Must be called before the FastAPI app is constructed — sentry_sdk's
Starlette/FastAPI integration instruments new ASGI apps created after init().
"""

import logging
import os

logger = logging.getLogger(__name__)

SENTRY_DSN = os.environ.get("SENTRY_DSN")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


def configure_logging() -> None:
    """
    Apply LOG_LEVEL to Python's actual logging config.

    LOG_LEVEL has been declared in render.yaml and docker-compose.yml since
    before this module existed, but nothing ever read it — app-level log
    calls (including the request-timing middleware this milestone adds)
    were silently dropped by the default root logger level (WARNING) in any
    real run. Must be called before other loggers emit anything.
    """
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def init_monitoring() -> None:
    if not SENTRY_DSN:
        return

    import sentry_sdk

    sentry_sdk.init(dsn=SENTRY_DSN, environment=ENVIRONMENT, traces_sample_rate=0.1)
    logger.info("Sentry error tracking initialized (environment=%s)", ENVIRONMENT)
