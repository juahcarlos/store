from typing import List, Optional

from lib.proto import PreprocessingType


async def preprocess_image(img_data: bytes, types: Optional[List[PreprocessingType]]) -> bytes:
    if types is None:
        return img_data

    preprocess_img_data = img_data

    for type in types:
        if type == PreprocessingType.PREPROCESSING_TYPE_DEBLURRING:
            preprocess_img_data = await get_deblurred_image(preprocess_img_data)
        elif type == PreprocessingType.PREPROCESSING_TYPE_DENOISING:
            preprocess_img_data = await get_denoised_image(preprocess_img_data)
        elif type == PreprocessingType.PREPROCESSING_TYPE_STABILIZATION:
            preprocess_img_data = await get_stabilized_image(preprocess_img_data)

    return preprocess_img_data


async def get_deblurred_image(img_data: bytes) -> bytes:
    return img_data

    # TODO: realize this


async def get_denoised_image(img_data: bytes) -> bytes:
    return img_data

    # TODO: realize this


async def get_stabilized_image(img_data: bytes) -> bytes:
    return img_data

    # TODO: realize this
