import shutil
import subprocess
import time
from pathlib import Path

import click
import yaml
from tqdm import tqdm

import marmtouch.util as util


def _transfer_files(videos_directory, server_path, verbose=True):
    session = videos_directory.name
    videos_directory = Path(videos_directory)
    server_path = Path(server_path)

    if (videos_directory / "params.yaml").is_file():
        params = yaml.safe_load(open(videos_directory / "params.yaml"))
        transfer_path = params.get("transfer_path")
        if transfer_path is not None:
            server_path = server_path / transfer_path
            server_path.mkdir(parents=True, exist_ok=True)

    failed = []
    success = []

    server_session_path = server_path / session
    logger_path = server_session_path / f"{session}.log"
    copy_no = 1
    while server_session_path.is_dir():
        print(f"Folder already exists at loc: {server_session_path.as_posix()}")
        server_session_path = server_path / f"{session} ({copy_no})"
        copy_no += 1
    try:
        server_session_path.mkdir()
    except Exception as e:
        print(f"Failed to create directory {server_session_path}.")
        print(e)
        return
    logger = util.getLogger(logger_path.as_posix(), capture_errors=False)
    videos = set(video for video in videos_directory.iterdir() if video.is_file())

    if not videos:
        logger.warn(f"No files to copy in {videos_directory.as_posix()}")
        return

    videos_already_copied = set(
        video for video in videos if (server_session_path / video.name).is_file()
    )
    videos_to_copy = videos - videos_already_copied

    nvids = len(videos_already_copied)
    if videos_already_copied:
        logger.info(f"{nvids} videos have already been copied. Skipping.")

    if videos_to_copy:
        logger.info(f"{nvids} videos to copy.")
    else:
        logger.info(f"No files to copy in {videos_directory.as_posix()}")
        return

    for video_file in tqdm(videos_to_copy, desc="video"):
        target = server_session_path / video_file.name
        try:
            shutil.copy(video_file.as_posix(), target.as_posix())
        except:
            logger.warn(f"Failed to copy {video_file}", exc_info=verbose)
            failed.append((video_file, target))
        else:
            success.append((video_file, target))

    logger.info("Completed file transfers")

    corrupt = []
    for orig, copy in tqdm(success, desc="verify"):
        if orig.stat().st_size == copy.stat().st_size:
            orig.unlink()
        else:
            corrupt.append((orig, copy))

    if failed:
        logger.warn(
            f"{len(failed)} files did not transfer at all. Failed to copy: {', '.join(failed)}"
        )

    if corrupt:
        logger.warn(
            f"{len(corrupt)} files did not transfer properly. Corrupt files: {', '.join(map(str,corrupt))}"
        )
    else:
        logger.info("Verification complete. No corrupt files.")

    if failed or corrupt:
        pass
    else:
        videos_directory.rmdir()


default_source = "/home/pi/Touchscreen"
default_destination = "/mnt/Data/Touchscreen/Data"


def bulk_transfer_files(source=default_source, dest=default_destination, mount=True):
    if mount:
        subprocess.Popen("sudo mount -a", shell=True)
    videos_directory = Path(source)
    server_path = Path(dest)

    TIMEOUT = 60
    T_INTERVAL = 5
    start_time = time.time()
    while not server_path.is_dir():
        if time.time() - start_time > TIMEOUT:
            raise ValueError("Timed out. Could not connect to server!")
        print("Waiting for server mount...")
        time.sleep(T_INTERVAL)
    sessions = [f for f in videos_directory.iterdir() if f.is_dir()]
    for session_directory in tqdm(sessions, desc="sessions"):
        _transfer_files(session_directory, server_path)


@click.command()
@click.option(
    "-s",
    "--source",
    default=default_source,
    help="Directory containing folders to be copied",
)
@click.option(
    "-d",
    "--dest",
    default=default_destination,
    help="Destination where data will be saved",
)
def transfer_files(source, dest):
    videos_directory = Path(source)
    server_path = Path(dest)
    sessions = [f for f in videos_directory.iterdir() if f.is_dir()]
    for session_directory in tqdm(sessions, desc="sessions"):
        _transfer_files(session_directory, server_path)
