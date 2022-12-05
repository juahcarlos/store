import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from bluelib.proto import PreprocessingType

log = logging.getLogger("preprocessing.server")


class SeparateMain(ABC):
    @abstractmethod
    async def deblur(self, img_data: bytes) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def denoise(self, img_data: bytes) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def imgstab(self, img_data: bytes) -> bytes:
        raise NotImplementedError


class SeparateMainMixin(SeparateMain):
    # interface for normal using extracted main method by gRPC call
    async def deblur(self, img_data: bytes) -> bytes:
        print("preprocess_img main deblur")
        # async with Channel ... gRPC call of an outer service
        return img_data

    async def denoise(self, img_data: bytes) -> bytes:
        log.debug("denoise")
        print("preprocess_img main denoise")
        # async with Channel ... gRPC call of an outer service
        return img_data

    async def imgstab(self, img_data: bytes) -> bytes:
        log.debug("imgstab")
        print("preprocess_img main imgstab")
        # async with Channel ... gRPC call of an outer service
        return img_data


class SeparateTestMixin(SeparateMain):
    async def deblur(self, img_data: bytes) -> bytes:
        print("preprocess_img test deblur")
        return img_data

    async def denoise(self, img_data: bytes) -> bytes:
        print("preprocess_img test denoise")
        return img_data

    async def imgstab(self, img_data: bytes) -> bytes:
        print("preprocess_img test imgstab")
        return img_data


# the main method extracted for using in unit test with mocking data to avoid call outer services
class Preprocess(SeparateMain):
    async def preprocess_img(self, img_data: bytes, types: Optional[List[PreprocessingType]]) -> bytes:
        if types is None:
            return img_data

        preprocess_img_data = img_data

        for type_ in types:
            if type_ == PreprocessingType.PREPROCESSING_TYPE_DEBLURRING:
                preprocess_img_data = await self.deblur(preprocess_img_data)
            elif type_ == PreprocessingType.PREPROCESSING_TYPE_DENOISING:
                preprocess_img_data = await self.denoise(preprocess_img_data)
            elif type_ == PreprocessingType.PREPROCESSING_TYPE_STABILIZATION:
                preprocess_img_data = await self.imgstab(preprocess_img_data)

        return preprocess_img_data


class JoinMain(SeparateMainMixin, Preprocess):
    async def preprocess_image(self, img_data: bytes, types: Optional[List[PreprocessingType]]) -> bytes:
        pre_res = await self.preprocess_img(img_data, types)
        return pre_res


class JoinTest(SeparateTestMixin, Preprocess):
    async def preprocess_image(self, img_data: bytes, types: Optional[List[PreprocessingType]]) -> bytes:
        pre_res = await self.preprocess_img(img_data, types)
        return pre_res
