Add-Type -assembly System.IO.Compression.FileSystem

$compressionLevel = [System.IO.Compression.CompressionLevel]::Optimal

pyinstaller  --windowed rvclient-win32.spec
pyinstaller --onefile --windowed rvclient-win32-standalone.spec

$currentwd= (Convert-Path .)
$currentdate = (Get-Date -format yyyyMMdd)
$rvversion = (git describe)
$suffix = "$rvversion-$currentdate"

$distpath = (Join-Path $currentwd "dist")
$bundle_path = (Join-Path $distpath "rvclient-win32")
$temp_bundle = (Join-Path $distpath "temp.zip")


$bundle_final_path = (Join-Path $currentwd "\bundles\rvclient-win32-$suffix.zip")
$exe_final_path = (Join-Path $currentwd "\bundles\rvclient-win32-standalone-$suffix.exe")


if ( (Test-Path "bundles") -eq $False)
{
	echo "Creating bundles directory"
	New-Item -ItemType directory -Path (Join-Path $currentwd "bundles")
}

if (Test-Path "$temp_bundle")
{
	Delete-Item "$temp_bundle"
}

[System.IO.Compression.ZipFile]::CreateFromDirectory("$bundle_path", "$temp_bundle", $compressionLevel, $false)
Move-Item -force "$temp_bundle" "$bundle_final_path"


Copy-Item -force dist\rvclient-win32-standalone.exe "$exe_final_path"
