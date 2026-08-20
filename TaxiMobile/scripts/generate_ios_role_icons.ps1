[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Add-Type -AssemblyName System.Drawing

function New-RoundedRectanglePath {
    param(
        [Parameter(Mandatory = $true)]
        [System.Drawing.RectangleF]$Rectangle,
        [Parameter(Mandatory = $true)]
        [float]$Radius
    )

    $diameter = $Radius * 2
    $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $path.AddArc($Rectangle.Left, $Rectangle.Top, $diameter, $diameter, 180, 90)
    $path.AddArc($Rectangle.Right - $diameter, $Rectangle.Top, $diameter, $diameter, 270, 90)
    $path.AddArc($Rectangle.Right - $diameter, $Rectangle.Bottom - $diameter, $diameter, $diameter, 0, 90)
    $path.AddArc($Rectangle.Left, $Rectangle.Bottom - $diameter, $diameter, $diameter, 90, 90)
    $path.CloseFigure()
    return $path
}

function New-TaxiMobileIcon {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Destination,
        [Parameter(Mandatory = $true)]
        [bool]$DriverBadge
    )

    $bitmap = [System.Drawing.Bitmap]::new(
        1024,
        1024,
        [System.Drawing.Imaging.PixelFormat]::Format24bppRgb
    )
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

    $navy950 = [System.Drawing.ColorTranslator]::FromHtml("#071426")
    $navy900 = [System.Drawing.ColorTranslator]::FromHtml("#0B1F3A")
    $navy700 = [System.Drawing.ColorTranslator]::FromHtml("#163A63")
    $accent500 = [System.Drawing.ColorTranslator]::FromHtml("#D6A800")
    $white = [System.Drawing.Color]::White
    $graphics.Clear($navy900)

    $bodyBrush = [System.Drawing.SolidBrush]::new($white)
    $windowBrush = [System.Drawing.SolidBrush]::new($navy700)
    $darkBrush = [System.Drawing.SolidBrush]::new($navy950)
    $accentBrush = [System.Drawing.SolidBrush]::new($accent500)
    $whitePen = [System.Drawing.Pen]::new($white, 22)
    $whitePen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $whitePen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round

    try {
        $body = New-RoundedRectanglePath ([System.Drawing.RectangleF]::new(126, 546, 772, 260)) 66
        $graphics.FillPath($bodyBrush, $body)
        $body.Dispose()

        $roof = [System.Drawing.PointF[]]@(
            [System.Drawing.PointF]::new(238, 550),
            [System.Drawing.PointF]::new(318, 350),
            [System.Drawing.PointF]::new(378, 300),
            [System.Drawing.PointF]::new(646, 300),
            [System.Drawing.PointF]::new(706, 350),
            [System.Drawing.PointF]::new(786, 550)
        )
        $graphics.FillPolygon($bodyBrush, $roof)

        $leftWindow = [System.Drawing.PointF[]]@(
            [System.Drawing.PointF]::new(336, 386),
            [System.Drawing.PointF]::new(390, 342),
            [System.Drawing.PointF]::new(492, 342),
            [System.Drawing.PointF]::new(492, 516),
            [System.Drawing.PointF]::new(278, 516)
        )
        $rightWindow = [System.Drawing.PointF[]]@(
            [System.Drawing.PointF]::new(532, 342),
            [System.Drawing.PointF]::new(634, 342),
            [System.Drawing.PointF]::new(688, 386),
            [System.Drawing.PointF]::new(746, 516),
            [System.Drawing.PointF]::new(532, 516)
        )
        $graphics.FillPolygon($windowBrush, $leftWindow)
        $graphics.FillPolygon($windowBrush, $rightWindow)

        $light = New-RoundedRectanglePath ([System.Drawing.RectangleF]::new(442, 230, 140, 70)) 18
        $graphics.FillPath($accentBrush, $light)
        $light.Dispose()

        $graphics.FillEllipse($accentBrush, 184, 638, 78, 54)
        $graphics.FillEllipse($accentBrush, 762, 638, 78, 54)
        $graphics.FillRectangle($windowBrush, 320, 650, 384, 38)

        $graphics.FillEllipse($darkBrush, 222, 746, 150, 150)
        $graphics.FillEllipse($darkBrush, 652, 746, 150, 150)
        $graphics.FillEllipse($accentBrush, 268, 792, 58, 58)
        $graphics.FillEllipse($accentBrush, 698, 792, 58, 58)

        if ($DriverBadge) {
            $graphics.FillEllipse($accentBrush, 690, 94, 246, 246)
            $centerX = 813.0
            $centerY = 217.0
            foreach ($angle in 0, 45, 90, 135) {
                $radians = $angle * [Math]::PI / 180.0
                $dx = [Math]::Cos($radians) * 82
                $dy = [Math]::Sin($radians) * 82
                $graphics.DrawLine(
                    $whitePen,
                    [float]($centerX - $dx),
                    [float]($centerY - $dy),
                    [float]($centerX + $dx),
                    [float]($centerY + $dy)
                )
            }
            $graphics.FillEllipse($darkBrush, 768, 172, 90, 90)
        }

        $directory = Split-Path -Parent $Destination
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
        $bitmap.Save($Destination, [System.Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $whitePen.Dispose()
        $accentBrush.Dispose()
        $darkBrush.Dispose()
        $windowBrush.Dispose()
        $bodyBrush.Dispose()
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

$assetRoot = Join-Path (Split-Path -Parent $PSScriptRoot) "iosApp\iosApp\Assets.xcassets"
New-TaxiMobileIcon `
    -Destination (Join-Path $assetRoot "AppIcon.appiconset\app-icon-1024.png") `
    -DriverBadge $false
New-TaxiMobileIcon `
    -Destination (Join-Path $assetRoot "DriverAppIcon.appiconset\driver-app-icon-1024.png") `
    -DriverBadge $true

Write-Host "Generated TaxiMobile passenger and driver iOS icons."
