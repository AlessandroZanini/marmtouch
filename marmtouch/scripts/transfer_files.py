import marmtouch.util as util

from pathlib import Path
import shutil
import subprocess

from tqdm import tqdm
import click

def _transfer_files(videos_directory, server_path, verbose=True):
    session = videos_directory.name
    videos_directory = Path(videos_directory)
    server_path = Path(server_path)

    failed = []
    success = []

    server_session_path = server_path / session
    logger_path = server_session_path / f'{session}.log'
    if not server_session_path.is_dir():
        try:
            server_session_path.mkdir()
        except:
            print(f"Failed to create directory {server_session_path}.")
            return
    logger = util.getLogger(logger_path.as_posix())
    videos = set(video for video in videos_directory.iterdir() if video.is_file())

    if not videos:
        logger.warn(f"No files to copy in {videos_directory.as_posix()}")
        return

    videos_already_copied = set(video for video in videos if (server_session_path/video.name).is_file())
    videos_to_copy = videos - videos_already_copied

    nvids = len(videos_already_copied)
    if videos_already_copied:
        logger.info(f"{nvids} videos have already been copied. Skipping.")

    if videos_to_copy:
        logger.info(f"{nvids} videos to copy.")
    else:
        logger.info(f"No files to copy in {videos_directory.as_posix()}")
        return

    for video_file in tqdm(videos_to_copy, desc='video'):
        target = server_session_path/video_file.name
        try:
            shutil.copy(video_file.as_posix(), target.as_posix())
        except:
            logger.warn(f"Failed to copy {video_file}",exc_info=verbose)
            failed.append((video_file,target))
        else:
            success.append((video_file,target))

    logger.info('Completed file transfers')

    corrupt = []
    for orig, copy in tqdm(success, desc='verify'):
        if orig.stat().st_size == copy.stat().st_size:
            orig.unlink()
        else:
            corrupt.append((orig,copy))

    if failed:
        logger.warn(f"{len(failed)} files did not transfer at all. Failed to copy: {', '.join(failed)}")

    if corrupt:
        logger.warn(f"{len(corrupt)} files did not transfer properly. Corrupt files: {', '.join(map(str,corrupt))}")
    else:
        logger.info("Verification complete. No corrupt files.")

    if failed or corrupt:
        pass
    else:
        videos_directory.rmdir()

default_source='/home/pi/Touchscreen'
default_destination='/mnt/Data2/Touchscreen'
def bulk_transfer_files(source=default_source,dest=default_destination,mount=True):
    if mount:
        subprocess.run('sudo mount -a')
    videos_directory = Path(source)
    server_path = Path(dest)
    sessions = [f for f in videos_directory.iterdir() if f.is_dir()]
    for session_directory in tqdm(sessions, desc='sessions'):
        _transfer_files(session_directory, server_path)


@click.command()
@click.option('-s','--source',default=default_source,help='Directory containing folders to be copied')
@click.option('-d','--dest',default=default_destination,help='Destination where data will be saved')
def transfer_files(source,dest):
    videos_directory = Path(source)
    server_path = Path(dest)
    sessions = [f for f in videos_directory.iterdir() if f.is_dir()]
    for session_directory in tqdm(sessions, desc='sessions'):
        _transfer_files(session_directory, server_path)
