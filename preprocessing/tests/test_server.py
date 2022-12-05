import logging
import os
from datetime import datetime
from typing import AsyncIterator, List, Optional, Union

import cv2
import pytest

from lib.image.encode import load_and_encode_image_opencv
from lib.proto import PreprocessingRequest, PreprocessingResponse, PreprocessingType
from preprocessing.process import JoinMain, JoinTest
from preprocessing.process_stream import JoinMainStream, JoinTestStream

log = logging.getLogger(__name__)
encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
test_dir = os.path.dirname(__file__)


@pytest.fixture()
async def img_data() -> Optional[memoryview]:
    img_path = os.path.join(test_dir, "test_imgs/test_crop.png")
    log.info(f"Image path {img_path}")
    img_data = load_and_encode_image_opencv(img_path)
    print("img_data", type(img_data))
    return img_data


@pytest.fixture()
async def join_test_stream() -> JoinTestStream:
    jt = JoinTestStream()
    return jt


@pytest.fixture()
async def join_main_stream() -> JoinMainStream:
    jm = JoinMainStream()
    return jm


async def framefeeder(all_types: List[PreprocessingType]) -> AsyncIterator[PreprocessingRequest]:
    """setting up the channes with Frame Feeder with STREAM_URL parameter,
    receives and returns the stream of images.

    Returns the stream of TrackerRe
    """
    stream_url = os.getenv("STREAM_URL", "rtsp://admin:Formule.123@10.14.50.100:554/profile1/media.smp")
    # stream_url = "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"
    video_capture = cv2.VideoCapture(stream_url)
    i = 0
    while True:
        ret, image = video_capture.read()
        if ret:
            _, frame = cv2.imencode(".jpg", image, encode_param)
            i += 1
            if i == 54:
                break
            print("i", i)
            yield PreprocessingRequest(timest=datetime.now(), frame=frame.tobytes(), types=all_types)


async def framefeeder_one(
    img_data: memoryview, all_types: List[PreprocessingType]
) -> AsyncIterator[PreprocessingRequest]:
    while True:
        yield PreprocessingRequest(timest=datetime.now(), frame=img_data.tobytes(), types=all_types)
        break


async def request_stream(feed: AsyncIterator[PreprocessingResponse]) -> None:
    """Repeated part of test_request_stream and test_request_stream_integrated test
    to avoid violation of DRY principle

    Args:
        feed: AsyncIterator[PreprocessingRequest]
    Returns:
        None
    """
    i = 0
    async for res in feed:
        print("test res in feed", res.timest, len(res.frame), type(res.frame))
        i += 1
        if i == 100:
            break
        assert type(res.timest) == datetime
        assert len(res.frame) > 0
        assert type(res.frame) == bytes


async def single_process(
    ptest: Union[JoinTest, JoinMain], img_data: memoryview, all_types: List[PreprocessingType]
) -> bytes:
    """common part for 2 tests below"""
    if img_data is None:
        raise Exception("Failed to load image")

    res = await ptest.preprocess_image(img_data.tobytes(), all_types)
    return res


@pytest.mark.asyncio
async def test_request_stream(
    join_test_stream: JoinTestStream, all_types: List[PreprocessingType]
) -> None:  # -> AsyncIterator[PreprocessingResponse]:
    """stream without outer services
    unit testing join_test_stream.preprocess_stream
    """
    images = framefeeder(all_types)
    feed = join_test_stream.preprocess_stream(images)
    async for img in feed:
        assert type(img.timest) == datetime
        assert type(img.frame) == bytes
        assert len(img.frame) > 0


@pytest.mark.asyncio
async def test_single_process_test(img_data: memoryview, all_types: List[PreprocessingType]) -> None:
    """Just ckecking a splitting unit testing environment
    for work with single images, not a stream
    """
    await single_process(JoinTest(), img_data, all_types)
