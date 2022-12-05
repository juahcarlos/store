import asyncio
import logging
from typing import List

from grpclib.testing import ChannelFor

from lib.proto import PreprocessingStub, PreprocessingType
from lib.utils.log_utils import init_logging
from preprocessing.server import PreprocessingService
from tests.test_server import framefeeder

log = logging.getLogger(__name__)


all_types: list[PreprocessingType] = [
    PreprocessingType(PreprocessingType.PREPROCESSING_TYPE_DEBLURRING),
    PreprocessingType(PreprocessingType.PREPROCESSING_TYPE_DENOISING),
    PreprocessingType(PreprocessingType.PREPROCESSING_TYPE_STABILIZATION),
]


async def preprocess_image(types: List[PreprocessingType] = all_types, image_backend: str = "opencv") -> bool:

    service = PreprocessingService()

    images = framefeeder(all_types)

    async with ChannelFor([service]) as channel:
        stub = PreprocessingStub(channel)
        response = stub.preprocess(images)

        async for res in response:
            log.info(f"Server response image length: {len(res.frame)})")
    return True


if __name__ == "__main__":
    init_logging("preprocessing")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(preprocess_image())
