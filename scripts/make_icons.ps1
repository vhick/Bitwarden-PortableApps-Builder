# Extract the *official vendor* signed app's own icon; no third-party image downloads.
param([Parameter(Mandatory=$true)][string]$SourceExe,[Parameter(Mandatory=$true)][string]$AppInfo)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Drawing
if (!(Test-Path -LiteralPath $SourceExe -PathType Leaf)) { throw "Official application binary missing: $SourceExe" }
New-Item -Path $AppInfo -ItemType Directory -Force | Out-Null
$ico=[System.Drawing.Icon]::ExtractAssociatedIcon($SourceExe)
if ($null -eq $ico) { throw 'Could not extract genuine vendor icon' }
$stream=[IO.File]::Create((Join-Path $AppInfo 'appicon.ico'))
try { $ico.Save($stream) } finally { $stream.Dispose() }
foreach ($px in @(16,32)) {
  $bmp=$ico.ToBitmap()
  $scaled=[System.Drawing.Bitmap]::new($bmp, [int]$px, [int]$px)
  try { $scaled.Save((Join-Path $AppInfo "appicon_$px.png"),[System.Drawing.Imaging.ImageFormat]::Png) }
  finally { $scaled.Dispose(); $bmp.Dispose() }
}
$ico.Dispose()
Write-Host 'Extracted vendor application icon and PNG sizes from official app'
