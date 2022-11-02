pip install build
$release_version = python setup.py --version | select-object -last 1
$archive_directory = "\\everlingsrv.robarts.ca\Data\Touchscreen\marmtouch_releases"
python -m build --no-isolation --wheel --outdir releases
cp "releases/marmtouch-$release_version-py3-none-any.whl" $archive_directory

cp $archive_path $archive_directory
# $archive_path = "releases\marmtouch_$release_version.tz"
# pip download `
#     -d $path `
#     --extra-index-url https://www.piwheels.org/simple `
#     --implementation cp `
#     --platform linux_armv7l `
#     --abi cp37m `
#     --only-binary :all: `
#     .
# tar cf $archive_path $path
# cp $archive_path $archive_directory