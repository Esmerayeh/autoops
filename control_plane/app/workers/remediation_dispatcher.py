import json
import logging

from control_plane.app.core.logging import configure_logging
from control_plane.app.messaging.redis_streams import RedisStreamsBus
from control_plane.app.messaging.topics import REMEDIATION_STREAM


LOGGER = logging.getLogger(__name__)
GROUP_NAME = "remediation-workers"
CONSUMER_NAME = "remediation-dispatcher-1"


def main() -> None:
    configure_logging()
    LOGGER.info("Starting remediation dispatcher worker")
    bus = RedisStreamsBus()
    while True:
        batches = bus.consume(REMEDIATION_STREAM, GROUP_NAME, CONSUMER_NAME, count=10, block_ms=3000)
        if not batches:
            continue
        for stream_name, messages in batches:
            for message_id, fields in messages:
                payload = json.loads(fields["payload"])
                LOGGER.info("Would dispatch remediation action %s", payload.get("payload", {}).get("action_type"))
                bus.ack(stream_name, GROUP_NAME, message_id)


if __name__ == "__main__":
    main()
