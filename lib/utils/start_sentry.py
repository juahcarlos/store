import logging
import os

import sentry_sdk

log = logging.getLogger(__name__)


def start_sentry() -> bool:
    """
    Initializes sentry if correct environemnt variables are specified
    """
    sentry_url = os.getenv("SENTRY_URL")
    sentry_env = os.getenv("SENTRY_ENV")
    sentry_release = os.getenv("SENTRY_RELEASE")

    if sentry_url:
        assert sentry_env, "SENTRY_ENV is required"
        assert sentry_release, "SENTRY_RELEASE is required"
        log.info("Sentry enabled env: %s, release: %s, url: %s", sentry_env, sentry_release, sentry_url)
        sentry_sdk.init(sentry_url, traces_sample_rate=1.0, environment=sentry_env, release=sentry_release)
        return True

    log.info("Sentry is not enabled missing env variables")
    return False
