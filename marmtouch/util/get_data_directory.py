import os
from pathlib import Path
import time

default_data_dir = Path("/home/pi/Touchscreen")
def get_data_directory():
    data_dir = os.environ.get("MARMTOUCH_DATA_DIRECTORY", default_data_dir)
    session = time.strftime("%Y-%m-%d_%H-%M-%S")
    data_dir = Path(data_dir, session)
    return data_dir