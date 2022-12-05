import io
import logging
from typing import Optional

import cv2
import numpy as np
from PIL import Image
from sentry_sdk import capture_exception

log = logging.getLogger(__name__)


def load_and_encode_image_pillow(img_path: str) -> Optional[bytes]:
    """Function to load an image from specified path using Pillow and encode it to bytes

    Args:
        img_path (str): Full or relative path to image

    Returns:
        bytes: Encoded image into byte array using BytesIO
    """
    log.debug("Loading image using Pillow backend")
    try:
        b = io.BytesIO()
        with Image.open(img_path) as img:
            img.save(b, "jpeg")
        img_data = b.getvalue()
        return img_data
    except Exception as exc:
        log.exception(exc)
        capture_exception(exc)
        return None


def load_and_encode_image_opencv(img_path: str) -> Optional[memoryview]:
    """Function to load an image using OpenCV from specified path and encode it to bytes

    Args:
        img_path (str): Full or relative path to image

    Returns:
        bytes: Encoded image into byte array using BytesIO
    """
    log.debug("Loading image using OpenCV backend")
    try:
        img = cv2.imread(img_path, 0)
        is_success, buffer = cv2.imencode(".jpg", img)
        io_buf = io.BytesIO(buffer)
        img_data = io_buf.getbuffer()
        return img_data
    except Exception as exc:
        log.exception(exc)
        capture_exception(exc)
        return None


def byte_to_opencv(img: bytes) -> np.ndarray:
    """
    Args:
        img: bytes of a coded jpg image
    Returns:
        opencv image: decode byte into image using opencv
    """
    log.debug("Decode image using OpenCV backend")
    img_bytes = io.BytesIO(img)
    image = cv2.imdecode(np.frombuffer(img_bytes.read(), np.uint8), 1)
    print("byte_to_opencv", type(image))
    return image


def encode_image_opencv(img: np.ndarray) -> memoryview:
    """
    Args:
        img: image in opencv format

    Returns:
        bytes: Encoded image into byte array using BytesIO
    """
    log.debug("Encode image using OpenCV backend")
    is_success, buffer = cv2.imencode(".jpg", img)
    io_buf = io.BytesIO(buffer)
    img_data = io_buf.getbuffer()
    return img_data


def img_to_bytearray(image: bytes) -> memoryview:
    """Function to convert an image to opencv image
    using already existance libraryes

    Args:
        img: bytes
    Returns:
        opencv image: decode byte into image using opencv
    """
    img_np = byte_to_opencv(image)
    img_data = encode_image_opencv(img_np)
    return img_data
