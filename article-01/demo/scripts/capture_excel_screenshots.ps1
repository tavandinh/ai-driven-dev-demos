# Screenshots of order_design.xlsx opened in Microsoft Excel (Windows, Excel desktop).
# Opens Excel visibly, maximizes it, and captures the Excel window for some sheets.
# Usage: powershell -ExecutionPolicy Bypass -File capture_excel_screenshots.ps1 [-TopCrop <px>]
# Check the first image: the top must not show the signed-in account; adjust -TopCrop to your DPI.
param([int]$TopCrop = 0)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Win {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
'@
[void][Win]::SetProcessDPIAware()

$demo = Split-Path -Parent $PSScriptRoot
$xlsx = Join-Path $demo 'order_design.xlsx'
$out = Join-Path $demo 'screenshots'
# Sheet indexes (this file stays ASCII-only: Windows PowerShell 5.1 reads BOM-less UTF-8 as ANSI).
# 3 = screen layout, 4 = item definition, 6 = validation rules, 7 = business rules (see build_specs.py).
$sheets = @(
  @{ Index = 3; File = 'excel-screen-layout.png' },
  @{ Index = 4; File = 'excel-item-definition.png' },
  @{ Index = 7; File = 'excel-business-rules.png' },
  @{ Index = 6; File = 'excel-validation-rules.png' }
)

$excel = New-Object -ComObject Excel.Application
try {
  $excel.Visible = $true
  $excel.DisplayAlerts = $false
  $wb = $excel.Workbooks.Open($xlsx, 0, $true)  # read-only
  $excel.WindowState = -4137                    # xlMaximized
  # Hide the ribbon (it shows the user's installed add-ins); restored in finally.
  [void]$excel.ExecuteExcel4Macro('SHOW.TOOLBAR("Ribbon",False)')
  $excel.DisplayFormulaBar = $false
  # The title bar shows the signed-in account; crop it off ($TopCrop physical pixels).
  $titleBar = $TopCrop
  foreach ($s in $sheets) {
    $ws = $wb.Worksheets.Item($s.Index)
    $ws.Activate()
    $excel.ActiveWindow.Zoom = 100
    $excel.ActiveWindow.ScrollRow = 1
    $excel.ActiveWindow.ScrollColumn = 1
    $ws.Range('A1').Select()
    [void][Win]::SetForegroundWindow([IntPtr]$excel.Hwnd)
    Start-Sleep -Milliseconds 1200
    $r = New-Object Win+RECT
    [void][Win]::GetWindowRect([IntPtr]$excel.Hwnd, [ref]$r)
    # A maximized window extends a few pixels past the screen edge; trim 8 px each side.
    $x = $r.Left + 8; $y = $r.Top + 8 + $titleBar
    $w = $r.Right - $r.Left - 16; $h = $r.Bottom - $r.Top - 16 - $titleBar
    $bmp = New-Object System.Drawing.Bitmap $w, $h
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($x, $y, 0, 0, $bmp.Size)
    $bmp.Save((Join-Path $out $s.File), [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    Write-Output "saved $($s.File) ($w x $h)"
  }
  $wb.Close($false)
} finally {
  [void]$excel.ExecuteExcel4Macro('SHOW.TOOLBAR("Ribbon",True)')
  $excel.DisplayFormulaBar = $true
  $excel.Quit()
  [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
}
