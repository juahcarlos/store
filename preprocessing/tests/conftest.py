from typing import AsyncGenerator, List

import pytest
from grpclib.testing import ChannelFor

from bluelib.proto import PreprocessingStub, PreprocessingType
from preprocessing.server import PreprocessingService


@pytest.fixture()
async def all_types() -> List[PreprocessingType]:
    all_types: List[PreprocessingType] = [
        PreprocessingType(PreprocessingType.PREPROCESSING_TYPE_DEBLURRING),
        PreprocessingType(PreprocessingType.PREPROCESSING_TYPE_DENOISING),
        PreprocessingType(PreprocessingType.PREPROCESSING_TYPE_STABILIZATION),
    ]
    return all_types


@pytest.fixture()
async def stub() -> AsyncGenerator:
    ser = PreprocessingService()
    async with ChannelFor([ser]) as channel:
        stub = PreprocessingStub(channel)
        yield stub
