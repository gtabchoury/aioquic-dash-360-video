# File location
CLIENT_FILE_LOCATION = 'data/client_files/'
SERVER_FILE_LOCATION = 'data/segments/'
FILE_BASE_NAME = 'video_tiled_'
FILE_END_NAME = '_dash_track'
CLIENT_FILE_BASE_NAME = 'data/client_files/video_tiled_dash_track'
SERVER_FILE_BASE_NAME = 'data/segments/video_tiled_dash_track'
FILE_FORMAT = '.m4s'

# Video information
DASH = '10000'
MAX_TILE = 201
VIDEO_FPS = 30
FRAME_TIME_MS = 33333
N_SEGMENTS = 6
CLIENT_BITRATE = 1

# Priorities
HIGH_PRIORITY = 1
LOW_PRIORITY = 2

# Server Connection
TILE_REQUEST = 'tile'
PUSH_REQUEST = 'push'
CLOSE_REQUEST = 'close'

# Queues
WFQ_QUEUE = 'WFQ'
SP_QUEUE = 'SP'
FIFO_QUEUE = 'FIFO'