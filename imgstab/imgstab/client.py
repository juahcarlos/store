import asyncio
import logging
import os
from datetime import datetime

import cv2
import numpy as np
from grpclib.client import Channel

from lib.proto import ImgstabRe, ImgstabStub

log = logging.getLogger("imgstab.client")


# generated image sequence from a video file
def video_read() -> list[ImgstabRe]:
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "video/") + "video.mp4")
    vidcap = cv2.VideoCapture(path)
    images = []
    i = 0
    while vidcap.isOpened():
        success, image = vidcap.read()
        if success:
            i += 1
            _, JPEG = cv2.imencode(".jpg", image)
            image_buff = JPEG.tobytes()
            print("image_buff", len(image_buff))
            images.append(ImgstabRe(frame=image_buff, timest=datetime.now()))
        else:
            break
    return images


async def receive() -> bool:
    """receivs the image sequence stream from gRPC server

    Sends message msg with any str to start process on the server
    :return: bool
    """

    async with Channel("0.0.0.0", port=int(os.getenv("PORT", 9090))) as channel:

        stub = ImgstabStub(channel)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter("sorted/video_res1.mp4", fourcc, 30, (640, 360))
        request = stub.upload(video_read())

        i = 0
        async for response in request:
            i += 1
            frame = response.frame
            image_np = np.frombuffer(frame, dtype=np.uint8)
            image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
            out.write(image)
        print("write")
        # cv2.destroyAllWindows()
        out.release()

    return True


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(receive())
