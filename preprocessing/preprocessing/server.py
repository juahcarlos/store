import asyncio
import logging
import os
from typing import AsyncIterator

from grpclib.server import Server
from prometheus_client import start_http_server

from lib.proto import (
    ImgstabRe,
    PreprocessingBase,
    PreprocessingRequest,
    PreprocessingResponse,
    PreprocessingType,
)
from lib.utils.log_utils import init_logging
from lib.utils.start_sentry import start_sentry
from preprocessing.process_stream import JoinMainStream

log = logging.getLogger("preprocessing.server")


class PreprocessingService(PreprocessingBase):
    def __init__(self) -> None:
        self.types: list[PreprocessingType] = []
        self.process = JoinMainStream()

    async def preprocess(
        self, request_iterator: AsyncIterator[PreprocessingRequest]
    ) -> AsyncIterator[PreprocessingResponse]:

        # feed = self.request_iterated(request_iterator)
        feeder = self.process.preprocess_stream(request_iterator)
        """
        feedr = self.imgstab(feed)
        feede = self.deblur(feedr)
        feeder = self.denoise(feede)
        """

        i = 0
        async for request in feeder:
            i += 1
            log.debug(f"request in feeder {type(request)} {len(request.frame)}")
            print(f"request in feeder {type(request)} {len(request.frame)}")
            # processed_img_data = await JoinMainStream().preprocess_image(request.frame, self.types)

            yield PreprocessingResponse(timest=request.timest, frame=request.frame)
        print("-- i --", i)

    async def request_iterated(
        self, request_iterator: AsyncIterator[PreprocessingRequest]
    ) -> AsyncIterator[ImgstabRe]:
        """Just iterates input to convert received data to the async iterator

        Args:
            request_iterator: AsyncIterator[TrackerRe]
        Returnd:
            AsyncIterator[ImgstabRe]
        """
        async for frame in request_iterator:
            self.types = frame.types
            log.debug("request_iterated frame")
            res = ImgstabRe(timest=frame.timest, frame=frame.frame)
            log.debug(f"request_iterator frame {type(res)}")
            yield res


async def run_server(host: str = "0.0.0.0", port: int = 50051) -> None:
    server = Server([PreprocessingService()])

    await server.start(host, port)
    await server.wait_closed()


if __name__ == "__main__":
    init_logging("preprocessing")

    PORT = int(os.getenv("PORT", 9090))

    start_sentry()

    start_http_server(8000)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_server(port=PORT))
