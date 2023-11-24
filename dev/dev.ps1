python -m venv dev/env
& .\dev\env\Scripts\activate
pip install -r dev/requirements.txt
# we additionally need to setup cairocffi for windows
pip install pipwin
pipwin install cairocffi
# copy over the simulated packages
copy dev/simulated_packages/* dev/env/Lib/site-packages/
# export marmtouch script 
function marmtouch() {
    python -m marmtouch.scripts $args
}
# export marmtouch environment variables
$env:MARMTOUCH_SYSTEM_CONFIG = $env:SERVER_DIR\Touchscreen\setup\marmtouch_system_config.yaml
$env:MARMTOUCH_STIMULUS_DIRECTORY = $env:SERVER_DIR\Touchscreen\stimuli
$env:MARMTOUCH_CONFIG_DIRECTORY = $env:SERVER_DIR\Touchscreen\configs
$env:MARMTOUCH_DATA_DIRECTORY = $env:SERVER_DIR\Touchscreen\data
