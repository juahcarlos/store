from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterable, AsyncIterator, Dict, Iterable, List, Union

import betterproto
from betterproto.grpc.grpclib_server import ServiceBase
import grpclib


class PreprocessingType(betterproto.Enum):
    PREPROCESSING_TYPE_UNSPECIFIED = 0
    PREPROCESSING_TYPE_DEBLURRING = 1
    PREPROCESSING_TYPE_DENOISING = 2
    PREPROCESSING_TYPE_STABILIZATION = 3


@dataclass(eq=False, repr=False)
class Image(betterproto.Message):
    data: bytes = betterproto.bytes_field(1)


@dataclass(eq=False, repr=False)
class ImgstabRe(betterproto.Message):
    timest: datetime = betterproto.message_field(1)
    frame: bytes = betterproto.bytes_field(2)


@dataclass(eq=False, repr=False)
class PreprocessingRequest(betterproto.Message):
    timest: datetime = betterproto.message_field(1)
    frame: bytes = betterproto.bytes_field(2)
    types: List["PreprocessingType"] = betterproto.enum_field(3)


@dataclass(eq=False, repr=False)
class PreprocessingResponse(betterproto.Message):
    timest: datetime = betterproto.message_field(1)
    frame: bytes = betterproto.bytes_field(2)


class ImgstabBase(ServiceBase):
    async def upload(
        self, request_iterator: AsyncIterator["ImgstabRe"]
    ) -> AsyncIterator["ImgstabRe"]:
        raise grpclib.GRPCError(grpclib.const.Status.UNIMPLEMENTED)
        yield ImgstabRe()

    async def __rpc_upload(self, stream: grpclib.server.Stream) -> None:
        request_kwargs = {"request_iterator": stream.__aiter__()}

        await self._call_rpc_handler_server_stream(
            self.upload,
            stream,
            request_kwargs,
        )

    def __mapping__(self) -> Dict[str, grpclib.const.Handler]:
        return {
            "/Imgstab/Upload": grpclib.const.Handler(
                self.__rpc_upload,
                grpclib.const.Cardinality.STREAM_STREAM,
                ImgstabRe,
                ImgstabRe,
            ),
        }


class ImgstabStub(betterproto.ServiceStub):
    async def upload(
        self, request_iterator: Union[AsyncIterable["ImgstabRe"], Iterable["ImgstabRe"]]
    ) -> AsyncIterator["ImgstabRe"]:

        async for response in self._stream_stream(
            "/Imgstab/Upload",
            request_iterator,
            ImgstabRe,
            ImgstabRe,
        ):
            yield response


class PreprocessingStub(betterproto.ServiceStub):
    async def preprocess(
        self,
        request_iterator: Union[
            AsyncIterable["PreprocessingRequest"], Iterable["PreprocessingRequest"]
        ],
    ) -> AsyncIterator["PreprocessingResponse"]:

        async for response in self._stream_stream(
            "/Preprocessing/Preprocess",
            request_iterator,
            PreprocessingRequest,
            PreprocessingResponse,
        ):
            yield response


class DeblurStub(betterproto.ServiceStub):
    async def deblurring(
        self,
        image: "Image",
        *,
        timeout: Optional[float] = None,
        deadline: Optional["Deadline"] = None,
        metadata: Optional["MetadataLike"] = None
    ) -> "Image":
        return await self._unary_unary(
            "/Deblur/Deblurring",
            image,
            Image,
            timeout=timeout,
            deadline=deadline,
            metadata=metadata,
        )


class PreprocessingBase(ServiceBase):
    async def preprocess(
        self, request_iterator: AsyncIterator["PreprocessingRequest"]
    ) -> AsyncIterator["PreprocessingResponse"]:
        raise grpclib.GRPCError(grpclib.const.Status.UNIMPLEMENTED)
        yield PreprocessingResponse()

    async def __rpc_preprocess(self, stream: grpclib.server.Stream) -> None:
        request_kwargs = {"request_iterator": stream.__aiter__()}

        await self._call_rpc_handler_server_stream(
            self.preprocess,
            stream,
            request_kwargs,
        )

    def __mapping__(self) -> Dict[str, grpclib.const.Handler]:
        return {
            "/Preprocessing/Preprocess": grpclib.const.Handler(
                self.__rpc_preprocess,
                grpclib.const.Cardinality.STREAM_STREAM,
                PreprocessingRequest,
                PreprocessingResponse,
            ),
        }
