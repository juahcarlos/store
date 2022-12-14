import logging
import os
from abc import ABC, abstractmethod
from typing import AsyncIterator, List

from grpclib.client import Channel

from lib.image.encode import img_to_bytearray
from lib.proto import (
    DeblurStub,
    Image,
    ImgstabRe,
    ImgstabStub,
    PreprocessingRequest,
    PreprocessingResponse,
    PreprocessingType,
)

log = logging.getLogger("preprocessing.process_stream")


class SeparateMain(ABC):
    @abstractmethod
    async def imgstab(self, stream: AsyncIterator[ImgstabRe]) -> AsyncIterator[PreprocessingResponse]:
        raise NotImplementedError("SeparateMain.imgstab should be implemented here")
        yield PreprocessingResponse()

    @abstractmethod
    async def deblur(self, stream: AsyncIterator[PreprocessingResponse]) -> AsyncIterator[PreprocessingResponse]:
        raise NotImplementedError("SeparateMain.imgstab should be implemented here")
        yield PreprocessingResponse()

    @abstractmethod
    async def denoise(self, stream: AsyncIterator[PreprocessingResponse]) -> AsyncIterator[PreprocessingResponse]:
        raise NotImplementedError("SeparateMain.imgstab should be implemented here")
        yield PreprocessingResponse()


class SeparateMainMixin(SeparateMain):
    def __init__(self) -> None:
        self.types: List[PreprocessingType] = []

    # interface for normal using extracted main method by gRPC call
    async def imgstab(self, stream: AsyncIterator[ImgstabRe]) -> AsyncIterator[PreprocessingResponse]:
        """receives stream of images, send it to Imgstab service and
        returns stabilized resulting stream of images.

        Args:
            stream: AsyncIterator[ImgstabRe]
        Returns:
            AsyncIterator[PreprocessingResponse]:
        """
        try:
            async with Channel(os.getenv("IMGSTAB_SERVICE"), int(os.getenv("IMGSTAB_PORT", 9090))) as channel:
                stub = ImgstabStub(channel)
                if PreprocessingType.PREPROCESSING_TYPE_STABILIZATION in self.types:
                    stream = stub.upload(stream)
                async for frame in stream:
                    if PreprocessingType.PREPROCESSING_TYPE_STABILIZATION in self.types:
                        print("IMGSTAB_SERVICE", type(frame.frame))
                    yield PreprocessingResponse(timest=frame.timest, frame=frame.frame)
        except Exception as ex:
            print("ImgstabStub ex", ex)

    async def deblur(self, stream: AsyncIterator[PreprocessingResponse]) -> AsyncIterator[PreprocessingResponse]:
        """receives stream of images, send it to Imgstab service and
        returns stabilized resulting stream of images.

        Args:
            stream: AsyncIterator[PreprocessingResponse]
        ReturnsPreprocessingResponse
            AsyncIterator[PreprocessingResponse]:
        """
        async with Channel(os.getenv("DEBLUR_SERVICE"), int(os.getenv("DEBLUR_PORT", 9090))) as channel:
            stub = DeblurStub(channel)
            async for img in stream:
                frame = img.frame
                print("frame deblur", len(frame))
                if PreprocessingType.PREPROCESSING_TYPE_DEBLURRING in self.types:
                    img_bytear = img_to_bytearray(frame)
                    print("DEBLUR_SERVICE before img_data =", type(img_bytear))
                    try:
                        res = await stub.deblurring(image=Image(data=img_bytear))
                        frame = res.data
                    except Exception as ex:
                        print("DEBLUR ex", ex)
                    print("DEBLUR_SERVICE after", type(frame))

                yield PreprocessingResponse(timest=img.timest, frame=frame)

    async def denoise(self, stream: AsyncIterator[PreprocessingResponse]) -> AsyncIterator[PreprocessingResponse]:
        """receives stream of images, send it to Imgstab service and
        returns stabilized resulting stream of images.

        Args:
            stream: AsyncIterator[PreprocessingResponse]
        Returns:
            AsyncIterator[PreprocessingResponse]:
        """

        log.debug("preprocess_stream main denoise")
        print("preprocess_stream main denoise")

        async for img in stream:
            frame = img.frame
            print("denoising frame", len(frame))
            if PreprocessingType.PREPROCESSING_TYPE_DENOISING in self.types:
                log.debug("faking denoising while it is not ready")
                print("faking denoising while it is so slow")
            yield PreprocessingResponse(timest=img.timest, frame=frame)


class SeparateTestMixin(SeparateMain):
    def __init__(self) -> None:
        self.types: List[PreprocessingType] = []

    async def imgstab(self, stream: AsyncIterator[ImgstabRe]) -> AsyncIterator[PreprocessingResponse]:
        print("preprocess_stream test imgstab")
        log.debug("preprocess_stream test imgstab")
        async for st in stream:
            yield PreprocessingResponse(timest=st.timest, frame=st.frame)

    async def deblur(self, stream: AsyncIterator[PreprocessingResponse]) -> AsyncIterator[PreprocessingResponse]:
        print("preprocess_stream test deblur")
        log.debug("preprocess_stream test deblur")
        async for st in stream:
            yield PreprocessingResponse(timest=st.timest, frame=st.frame)

    async def denoise(self, stream: AsyncIterator[PreprocessingResponse]) -> AsyncIterator[PreprocessingResponse]:
        print("preprocess_stream test denoise")
        log.debug("preprocess_stream test denoise")
        async for st in stream:
            yield PreprocessingResponse(timest=st.timest, frame=st.frame)


# the main method extracted for using in unit test with mocking data to avoid call outer services
class Preprocess(SeparateMain):
    async def preprocess_main(
        self, stream: AsyncIterator[PreprocessingRequest]
    ) -> AsyncIterator[PreprocessingResponse]:

        stream_iter = self.request_iterated(stream)
        stream_stab = self.imgstab(stream_iter)
        stream_deblur = self.deblur(stream_stab)
        stream_denoise = self.denoise(stream_deblur)

        async for st in stream_denoise:
            yield PreprocessingResponse(timest=st.timest, frame=st.frame)

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
            log.debug(f"types preprocess_stream {frame.types}")
            print(f"types preprocess_stream {frame.types}")
            self.types = frame.types
            res = ImgstabRe(timest=frame.timest, frame=frame.frame)
            yield res


class JoinMainStream(SeparateMainMixin, Preprocess):
    async def preprocess_stream(
        self, stream: AsyncIterator[PreprocessingRequest]
    ) -> AsyncIterator[PreprocessingResponse]:

        result = self.preprocess_main(stream)
        async for stm in result:
            yield PreprocessingResponse(timest=stm.timest, frame=stm.frame)


class JoinTestStream(SeparateTestMixin, Preprocess):
    async def preprocess_stream(
        self, stream: AsyncIterator[PreprocessingRequest]
    ) -> AsyncIterator[PreprocessingResponse]:

        res = self.preprocess_main(stream)
        async for st in res:
            yield PreprocessingResponse(timest=st.timest, frame=st.frame)
