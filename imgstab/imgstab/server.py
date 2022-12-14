import asyncio
import logging
import os
from typing import AsyncIterator

import cv2
import numpy as np
from grpclib.server import Server
from grpclib.utils import graceful_exit
from prometheus_client import start_http_server
from vidgear.gears.stabilizer import Stabilizer

from lib.proto import ImgstabBase, ImgstabRe
from lib.utils.log_utils import init_logging
from lib.utils.start_sentry import start_sentry

log = logging.getLogger("imgstab.server")


class ImgstabService(ImgstabBase):
    async def upload(self, request_iterator: AsyncIterator["ImgstabRe"]) -> AsyncIterator["ImgstabRe"]:
        stab = Stabilizer(
            smoothing_radius=50,
            crop_n_zoom=False,
            border_size=40,
        )
        async for request in request_iterator:
            image_bytes = request.frame
            image_np = np.frombuffer(image_bytes, dtype=np.uint8)  # Get a 1d-array of an image
            frame = cv2.imdecode(image_np, cv2.IMREAD_COLOR)  # Gets back a numpy array
            stabilized_frame = stab.stabilize(frame)
            # waits for stabilizer which still be initializing
            if stabilized_frame is None:
                log.debug("stabilized_frame is None")
                continue
            else:
                # converts "numpy array to jpeg image bytes"
                _, encoded_image = cv2.imencode(".jpeg", stabilized_frame)
                image_buff = encoded_image.tobytes()
                log.debug(f"image_buff {len(image_buff)}")
                yield ImgstabRe(timest=request.timest, frame=image_buff)

        stab.clean()


async def run_server(host: str = "0.0.0.0", port: int = int(os.getenv("PORT", 9090))) -> None:
    server = Server([ImgstabService()])
    with graceful_exit([server]):
        await server.start(host, port)
        print(f"Serving on {host}:{port}")
        await server.wait_closed()


if __name__ == "__main__":
    init_logging("imgstab")
    start_sentry()

    start_http_server(8000)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_server())
