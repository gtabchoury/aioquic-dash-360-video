import argparse
import asyncio
import binascii
import csv
import struct
import datetime
import timeit
import time
import os

from urllib.parse import urlparse
from dash import Dash
from aioquic.asyncio import QuicConnectionProtocol
from aioquic.asyncio.client import connect
from aioquic.quic.configuration import QuicConfiguration
from data_types import VideoPacket, QUICPacket
from utils import message_to_VideoPacket, get_client_file_name, segment_exists
from video_constants import HIGH_PRIORITY, FRAME_TIME_MS, LOW_PRIORITY, VIDEO_FPS, CLIENT_BITRATE, N_SEGMENTS

CLIENT_ID = '1' 

async def aioquic_client(ca_cert: str, connection_host: str, connection_port: int, dash: Dash):
    configuration = QuicConfiguration(is_client=True)
    configuration.load_verify_locations(ca_cert)
    async with connect(connection_host, connection_port, configuration=configuration) as client:
        connection_protocol = QuicConnectionProtocol
        reader, writer = await connection_protocol.create_stream(client)
        await handle_stream(reader, writer, dash)

async def send_data(writer, stream_id, end_stream, packet=None):
    data = QUICPacket(stream_id, end_stream, packet).serialize()

    writer.write(struct.pack('<L', len(data)))
    writer.write(data)

    await asyncio.sleep(0.0001)

async def handle_stream(reader, writer, dash):
    
    # User input
    asyncio.ensure_future(receive(reader, dash))
    # Server data received
    writer.write(CLIENT_ID.encode())
    await asyncio.sleep(0.0001)

    # List all tiles
    tiles_list = list(range(1,201))
    # Total frames
    total_frames = 0
    total_frames_fov = 0

    # Missed frames
    missed_frames = 0
    missed_frames_fov = 0

    # Missing ratio
    missed_frames_seg = {}
    total_frames_seg = {}
    missing_ratio = {}
    missed_frames_seg_fov = {}
    total_frames_seg_fov = {}
    missing_ratio_fov = {}
    

    # USER INPUT (currently simulated by CSV)
    with open(User_Input_File) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        frame = 0
        video_segment = 0
        frame_request = 1

        for row in csv_reader:
            frame_time = datetime.datetime.now()
            not_in_fov = tiles_list.copy()
            # Frame to make request
            if frame == frame_request:
                video_segment += 1
                
                missed_frames_seg[video_segment] = 0
                total_frames_seg[video_segment] = 0
                missed_frames_seg_fov[video_segment] = 0
                total_frames_seg_fov[video_segment] = 0

                current_bitrate = dash.get_next_bitrate(video_segment)

                # SEND REQUEST FOR TILES IN FOV WITH HIGHER PRIORITY
                index = 0
                for tile in row:
                    tile = int(tile)
                    if index != 0:
                        if not segment_exists(video_segment, tile, current_bitrate):
                            # Smaller the number, bigger the priority
                            message = VideoPacket(video_segment, tile, HIGH_PRIORITY, current_bitrate)
                            await send_data(writer, stream_id=CLIENT_ID, end_stream=False, packet=message)
                        not_in_fov.remove(tile)
                    index += 1

                # REQUESTS FOR THE TILES THAT ARE NOT IN FOV WITH LOWER PRIORITY
                for tile in not_in_fov:
                    if not segment_exists(video_segment, tile, current_bitrate):
                        message = VideoPacket(video_segment, tile, LOW_PRIORITY, current_bitrate)
                        await send_data(writer, stream_id=CLIENT_ID, end_stream=False, packet=message)
                frame_request += VIDEO_FPS

                await asyncio.sleep(0.1)

            # CHECK FOR MISSING RATIO
            if frame != 0:
                # Check for missing segments
                index = 0
                missed_tiles = 0
                missed_tiles_fov = 0
                total_tiles = 0
                total_tiles_fov = 0

                tiles_in_fov = []
                for t in row:
                    tile = int(t)
                    if index != 0:
                        tiles_in_fov.append(tile)
                    index+=1

                for tile in tiles_list:
                    total_tiles+=1
                    in_row = False

                    if (tile in tiles_in_fov):
                        total_tiles_fov +=1
                        in_row = True

                    if not segment_exists(video_segment, tile, current_bitrate):
                        missed_tiles += 1
                        if (in_row):
                            missed_tiles_fov +=1
                
                missed_frames += missed_tiles
                total_frames += total_tiles
                missed_frames_seg[video_segment] = missed_frames_seg[video_segment] + missed_tiles
                total_frames_seg[video_segment] = total_frames_seg[video_segment] + total_tiles

                missed_frames_fov += missed_tiles_fov
                total_frames_fov += total_tiles_fov
                missed_frames_seg_fov[video_segment] = missed_frames_seg_fov[video_segment] + missed_tiles_fov
                total_frames_seg_fov[video_segment] = total_frames_seg_fov[video_segment] + total_tiles_fov

                # On last segment, print the results and end connection
                if frame == (N_SEGMENTS*VIDEO_FPS):
                    i=1
                    sum_bitrate = 0
                    download_time_seg = {}
                    while (i<=N_SEGMENTS):
                        missing_ratio[i] = str(round((missed_frames_seg[i]/total_frames_seg[i])*100, 2))+"%"
                        missing_ratio_fov[i] = str(round((missed_frames_seg_fov[i]/total_frames_seg_fov[i])*100, 2))+'%'

                        sum_bitrate += dash.bitrates_seg[i]
                        download_time_seg[i] = str(round(dash.previous_segment_times_seg[i], 2))+'s'

                        i+=1

                    missing_ratio_total = round((missed_frames/total_frames)*100, 2)
                    missing_ratio_total_fov = round((missed_frames_fov/total_frames_fov)*100, 2)

                    

                    print("Missing ratio total: "+str(missing_ratio_total)+"%")
                    print("Missing ratio total (campo visão): "+str(missing_ratio_total_fov)+"%")
                    print("Missing ratio por segmento: "+str(missing_ratio))
                    print("Missing ratio por segmento (campo visão): "+str(missing_ratio_fov))
                    print("Tempo total de download: "+str(round(sum(dash.previous_segment_times), 2))+"s")
                    print("Tempo total de download por segmento: "+str(download_time_seg))
                    print("Bitrate médio: "+str(round(sum_bitrate / N_SEGMENTS, 2)))
                    print("Bitrate por segmento: "+str(dash.bitrates_seg))
                    await send_data(writer, stream_id=CLIENT_ID, end_stream=True)
                    return

            frame += 1

async def receive(reader, dash):
    while True:
        start_time = timeit.default_timer()
        try:
            size, = struct.unpack('<L', await reader.readexactly(4))
        except:
            break
            
        dash.append_download_size(size)

        file_name_data = await reader.readexactly(size)
        file_info = message_to_VideoPacket(eval(file_name_data.decode()))

        file_name = get_client_file_name(segment=file_info.segment, tile=file_info.tile, bitrate=file_info.bitrate)
        with open(file_name, "wb") as newFile:
            not_finished = True
            while not_finished:
                try:
                    file_size, = struct.unpack('<L', await reader.readexactly(4))
                    if file_size == 0:
                        not_finished = False
                    else:
                        chunk = await reader.readexactly(file_size)
                        newFile.write(binascii.hexlify(chunk))
                except:
                    break
        dash.update_download_time(timeit.default_timer() - start_time, int(file_info.segment))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTTP/3 client for video streaming")
    parser.add_argument(
        "url",
        type=str,
        help="the URL to query (must be HTTPS)"
    )
    parser.add_argument(
        "-c",
        "--ca-certs",
        type=str,
        help="load CA certificates from the specified file"
    )
    parser.add_argument(
        "-i",
        "--user-input",
        required=True,
        type=str,
        help="CSV file with user input simulation",
    )
    parser.add_argument(
        "-da",
        "--dash-algorithm",
        required=False,
        default="basic",
        type=str,
        help="dash algorithm (options: basic, basic2) - (defaults to basic)",
    )

    args = parser.parse_args()

    global User_Input_File
    User_Input_File = args.user_input

    parsed = urlparse(args.url[0])
    host = parsed.hostname

    if parsed.port is not None:
        port = parsed.port
    else:
        port = 4433

    dash = Dash([3000, 3500, 4000, 4500, 5000, 5500, 6000], args.dash_algorithm)

    os.system("rm /Users/gabriel.tabchoury/git/aioquic-dash-360-video/data/client_files/*")

    asyncio.get_event_loop().run_until_complete(aioquic_client(ca_cert=args.ca_certs, connection_host=host, connection_port=port, dash=dash))