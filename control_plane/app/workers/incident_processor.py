import json
import logging

from control_plane.app.core.logging import configure_logging
from control_plane.app.messaging.redis_streams import RedisStreamsBus
from control_plane.app.messaging.topics import INCIDENT_STREAM


LOGGER = logging.getLogger(__name__)
GROUP_NAME = "incident-workers"
CONSUMER_NAME = "incident-processor-1"


def main() -> None:
    configure_logging()
    LOGGER.info("Starting incident processor worker")
    bus = RedisStreamsBus()
    while True:
        batches = bus.consume(INCIDENT_STREAM, GROUP_NAME, CONSUMER_NAME, count=10, block_ms=3000)
        if not batches:
            continue
        for stream_name, messages in batches:
            for message_id, fields in messages:
                payload = json.loads(fields["payload"])
                LOGGER.info("Observed incident event %s", payload.get("event_type"))
                bus.ack(stream_name, GROUP_NAME, message_id)


if __name__ == "__main__":
    main()
