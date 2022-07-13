#########################################
function safe-symboliclink {
    param (
        $path,
        $target
    )
    if (Test-Path $path) {
        echo "$path exists"
    } else {
        echo "Creating $path"
        New-Item -ItemType SymbolicLink -Path $path -Target $target
    }
}
function safe-mkdir {
    param (
        $path
    )
    if (Test-Path $path) {
        echo "$path exists"
    } else {
        echo "Creating $path"
        New-Item -ItemType Directory -Path $path
    }
}
##########################################
safe-mkdir \home\pi
safe-mkdir "test\Touchscreen"

$data_dir = (resolve-path "test\Touchscreen").Path
$paths = @(
    @('\home\pi\stimuli', '\\everlingsrv.robarts.ca\Data\Touchscreen\stimuli'),
    @('\home\pi\configs', '\\everlingsrv.robarts.ca\Data\Touchscreen\configs'),
    @('\home\pi\marmtouch_system_config.yaml', '\\everlingsrv.robarts.ca\Data\Touchscreen\setup\marmtouch_system_config.yaml'),
    @('\home\pi\Touchscreen', $data_dir)
)

foreach ( $params in $paths ) {
    safe-symboliclink $params[0] $params[1]
}

$simulated_package_dir = (resolve-path dev\simulated_packages).Path
$marmtouch_dir = (resolve-path .).Path
$env:PYTHONPATH = "$env:PYTHONPATH;$simulated_package_dir;$marmtouch_dir"
python -m marmtouch.scripts launch --debug