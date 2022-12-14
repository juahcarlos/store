import os
from typing import AsyncGenerator

import pytest
from grpclib.testing import ChannelFor

from lib.proto import ImgstabStub
from imgstab.client import video_read
from imgstab.server import ImgstabService

test_dir = os.path.dirname(__file__)


@pytest.fixture()
async def stub() -> AsyncGenerator:
    ser = ImgstabService()
    async with ChannelFor([ser]) as channel:
        stub = ImgstabStub(channel)
        yield stub


"""check if server is responding and len of the first frame"""
@pytest.mark.asyncio
async def test_request_and_response(stub: ImgstabStub) -> None:

    video = video_read()
    request = stub.upload(video)

    even_one = 0
    async for response in request:
        lenf = len(response.frame)
        print("len response.frame", lenf, response.timest)
        if lenf > 0:
            even_one = lenf
    assert even_one > 0
    print("even_one", even_one)


"""check if the first 10 frames aren't empty"""
@pytest.mark.asyncio
async def test_loop(stub: ImgstabStub) -> None:
    async for response in stub.upload(video_read()):
        print("len response.frame", len(response.frame))
        assert len(response.frame) > 0
