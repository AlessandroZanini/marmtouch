python3 -m venv dev/env
source dev/env/bin/activate
pip install -r dev/requirements.txt
copy dev/simulated_packages/* dev/env/Lib/site-packages/
marmtouch() {
    python -m marmtouch.scripts "$@"
}
export -f marmtouch
export MARMTOUCH_SYSTEM_CONFIG=$SERVER_DIR/Touchscreen/setup/marmtouch_system_config.yaml
export MARMTOUCH_STIMULUS_DIRECTORY=$SERVER_DIR/Touchscreen/stimuli
export MARMTOUCH_CONFIG_DIRECTORY=$SERVER_DIR/Touchscreen/configs
export MARMTOUCH_DATA_DIRECTORY=$SERVER_DIR/Touchscreen/data