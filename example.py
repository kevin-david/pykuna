import asyncio
import sys
from datetime import timedelta
from websockets import connect

def decode_event(bytes):
    pos = 0
    event_id = int.from_bytes(bytes[pos:pos+4], byteorder="big") + 1
    pos += 4

    if event_id == 9:
       # Cookies
        cookie = int.from_bytes(bytes[pos:pos+4], byteorder="big")
        pos += 4

        for_cookie = int.from_bytes(bytes[pos:pos+4], byteorder="big")
        pos += 4

        print("Event 9: Cookie {} for cookie {}".format(cookie, for_cookie))

        # Error Message
        error = int.from_bytes(bytes[pos:pos+4], byteorder="big")
        pos += 4

        error_message_length = int.from_bytes(
            bytes[pos:pos+4], byteorder="big", signed=True)
        pos += 4

        error_message = ""
        if error_message_length > 0:
            error_message = bytes[pos:pos+error_message_length].decode("utf-8")
            pos += error_message_length
        print("Error ID {}, Length {}: {}".format(
            error, error_message_length, error_message))

        channel_id = int.from_bytes(bytes[pos:pos+4], byteorder="big")
        print("Channel ID: {}".format(channel_id))
        pos += 4

        local_port = int.from_bytes(bytes[pos:pos+4], byteorder="big")
        print("Local port: {}".format(local_port))
        pos += 4

        # Other channel IDs?
        channel_id_length = int.from_bytes(bytes[pos:pos+4], byteorder="big")
        pos += 4
        channel_ids = []
        if channel_id_length >= 0:
            for i in range(channel_id_length):
                channel_ids.append(int.from_bytes(
                    bytes[pos:pos+4], byteorder="big"))
                pos += 4
        print("Channel IDs: {}".format(channel_ids))


def string_message(message):
    return (len(message)).to_bytes(4, byteorder="big") + bytes(message, 'utf-8')

def event_bytes(event_id):
    # Event IDs are adjusted down 1 from the enum
    return (event_id - 1).to_bytes(4, byteorder="big")


async def open_rtsp(kuna, serial):
    async with connect("wss://video.kunasystems.com/ws/rtsp/proxy?authtoken=" + kuna._token) as websocket:
        print("Connected")
        await websocket.send(bytes('hello', 'utf-8'))

        header = (
            event_bytes(8)  # Event ID
            + (1).to_bytes(4, byteorder="big")  # Cookie
            + string_message(serial)  # Camera ID
            + string_message(kuna._token)  # Auth Token
        )

        print("Sending header `{}`".format(header))
        await websocket.send(header)

        print("Awaiting response...")
        response = await websocket.recv()
        print(response)
        decode_event(response)

        # TODO - custom codec to read RTSP data? https://docs.python.org/3/library/codecs.html#codecs.CodecInfo


async def main():

    if len(sys.argv) < 3:
        print('Usage: python example.py USERNAME PASSWORD')
        exit(1)

    # create an API object, passing username, password, and an instance of aiohttp.ClientSession
    from aiohttp import ClientSession
    from pykuna import KunaAPI

    websession = ClientSession()
    kuna = KunaAPI(sys.argv[1], sys.argv[2], websession)

    # authenticate() to get/refresh the access token
    await kuna.authenticate()

    # update() to populate kuna.cameras with a dict of cameras in the account;
    # key is camera serial number, value is camera object
    await kuna.update()

    any_serial = ''
    for camera in kuna.cameras.values():
        # print the name and serial number of the camera
        print('Camera: {} (Serial No. {})'.format(
            camera.name, camera.serial_number))
        any_serial = camera.serial_number

        # retrieve a list of recording objects for all recordings for the past two hours
        recordings = await camera.get_recordings_by_time(timedelta(hours=2))
        for recording in recordings:
            print("Timestamp {}: {}".format(recording.timestamp, await recording.get_download_link()))

    await open_rtsp(kuna, any_serial)
    await websession.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
