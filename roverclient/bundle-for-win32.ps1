Add-Type -assembly System.IO.Compression.FileSystem

$compressionLevel = [System.IO.Compression.CompressionLevel]::Optimal

pyinstaller  --windowed rvclient-win32.spec

cd dist
   [System.IO.Compression.ZipFile]::CreateFromDirectory("rvclient-win32","..\bundles\rvclient-win32.zip", $compressionLevel, $false)


cd ..

pyinstaller --onefile --windowed rvclient-win32-standalone.spec
cp dist\rvclient-win32-standalone.exe bundles\.
