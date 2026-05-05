param(
    [string]$Version = "",
    [string]$PreviousTag = "",
    [string]$Repo = "flathack/FLAtlas",
    [switch]$SkipBuild,
    [switch]$SkipUpload
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Resolve-RepoRoot {
    $scriptDir = Split-Path -Parent $PSCommandPath
    return (Resolve-Path (Join-Path $scriptDir "..")).Path
}

function Assert-CleanWorktree {
    $status = git status --short
    if ($status) {
        throw "Worktree is dirty. Commit or stash changes before creating a release:`n$status"
    }
}

function Get-AppVersion {
    $content = Get-Content -LiteralPath "fl_atlas.py" -Raw
    $match = [regex]::Match($content, 'APP_VERSION\s*=\s*"([^"]+)"')
    if (-not $match.Success) {
        throw "Could not read APP_VERSION from fl_atlas.py"
    }
    return $match.Groups[1].Value
}

function Normalize-Version {
    param([string]$Value)
    $value = $Value.Trim()
    if (-not $value) {
        throw "Version is empty."
    }
    if ($value.StartsWith("v")) {
        return $value
    }
    return "v$value"
}

function Assert-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Get-PreviousTag {
    param([string]$Tag)
    if ($PreviousTag.Trim()) {
        return $PreviousTag.Trim()
    }
    $tags = git tag --sort=-creatordate
    foreach ($candidate in $tags) {
        $candidate = "$candidate".Trim()
        if ($candidate -and $candidate -ne $Tag) {
            return $candidate
        }
    }
    return ""
}

function Assert-PathInsideRepo {
    param([string]$Path)
    $repoRoot = (Resolve-Path ".").Path
    $full = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $Path))
    if (-not $full.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to operate outside repository: $full"
    }
    return $full
}

function Remove-GeneratedPath {
    param([string]$Path)
    $full = Assert-PathInsideRepo $Path
    if (Test-Path -LiteralPath $full) {
        Remove-Item -LiteralPath $full -Recurse -Force
    }
}

function Get-PythonLauncher {
    param([string]$Arch)
    if ($Arch -eq "x64") {
        return @("py", "-3.13")
    }
    if ($Arch -eq "arm64") {
        return @("py", "-3.13-arm64")
    }
    throw "Unsupported architecture: $Arch"
}

function Invoke-Python {
    param(
        [string]$Arch,
        [string[]]$Args
    )
    $launcher = Get-PythonLauncher $Arch
    & $launcher[0] $launcher[1] @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed for ${Arch}: $($Args -join ' ')"
    }
}

function New-ReleaseVenv {
    param([string]$Arch)
    $venv = "build\venv-release-$Arch"
    if (-not (Test-Path -LiteralPath (Join-Path $venv "Scripts\python.exe"))) {
        Invoke-Python $Arch @("-m", "venv", $venv)
    }
    $py = Join-Path $venv "Scripts\python.exe"
    & $py -m pip install --upgrade pip wheel | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "pip bootstrap failed for $Arch"
    }
    & $py -m pip install --upgrade -r requirements-build.txt | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "requirements install failed for $Arch"
    }
    return (Resolve-Path $py).Path
}

function Get-PythonPlatform {
    param([string]$Python)
    return (& $Python -c "import sysconfig; print(sysconfig.get_platform())").Trim().ToLowerInvariant()
}

function Assert-PythonArchitecture {
    param(
        [string]$Arch,
        [string]$Python
    )
    $platform = Get-PythonPlatform $Python
    if ($Arch -eq "x64" -and $platform -notlike "*amd64*") {
        throw "x64 build requires win-amd64 Python, got: $platform"
    }
    if ($Arch -eq "arm64" -and $platform -notlike "*arm64*") {
        throw "arm64 build requires win-arm64 Python, got: $platform"
    }
}

function Invoke-ReleaseBuild {
    param(
        [string]$Arch,
        [string]$Python
    )
    Write-Step "Building Windows $Arch"
    Assert-PythonArchitecture $Arch $Python

    Remove-GeneratedPath "dist-$Arch"
    Remove-GeneratedPath "dist-$Arch-updater"
    Remove-GeneratedPath "build\pyinstaller-$Arch"
    Remove-GeneratedPath "build\pyinstaller-$Arch-updater"

    $icon = (Resolve-Path "fl_editor\images\FLAtlas-Suite-Dreadnought-Front-Logo.ico").Path
    & $Python -m PyInstaller --noconfirm --clean --distpath "dist-$Arch" --workpath "build\pyinstaller-$Arch" FLAtlas.spec
    if ($LASTEXITCODE -ne 0) {
        throw "FLAtlas PyInstaller build failed for $Arch"
    }

    & $Python -m PyInstaller --noconfirm --clean --distpath "dist-$Arch-updater" --workpath "build\pyinstaller-$Arch-updater" --specpath "build\pyinstaller-$Arch-updater" --onefile --windowed --name FLAtlasUpdater --icon $icon flatlas_updater.py
    if ($LASTEXITCODE -ne 0) {
        throw "FLAtlasUpdater PyInstaller build failed for $Arch"
    }

    $targetDir = "dist-$Arch\FLAtlas"
    if (-not (Test-Path -LiteralPath $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir | Out-Null
    }
    Copy-Item -LiteralPath "dist-$Arch-updater\FLAtlasUpdater.exe" -Destination (Join-Path $targetDir "FLAtlasUpdater.exe") -Force
}

function Get-PeMachine {
    param([string]$Path)
    $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path $Path).Path)
    if ($bytes.Length -lt 64 -or $bytes[0] -ne 0x4D -or $bytes[1] -ne 0x5A) {
        throw "Not a PE file: $Path"
    }
    $peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
    if ($peOffset + 6 -gt $bytes.Length) {
        throw "Invalid PE header: $Path"
    }
    $sig = [System.Text.Encoding]::ASCII.GetString($bytes, $peOffset, 4)
    if ($sig -ne "PE$([char]0)$([char]0)") {
        throw "Invalid PE signature: $Path"
    }
    return [BitConverter]::ToUInt16($bytes, $peOffset + 4)
}

function Assert-BuildArchitecture {
    param([string]$Arch)
    $expected = if ($Arch -eq "x64") { 0x8664 } else { 0xAA64 }
    foreach ($exe in @("dist-$Arch\FLAtlas\FLAtlas.exe", "dist-$Arch\FLAtlas\FLAtlasUpdater.exe")) {
        $actual = Get-PeMachine $exe
        if ($actual -ne $expected) {
            throw "$exe has PE machine 0x$($actual.ToString('x')), expected 0x$($expected.ToString('x'))"
        }
    }
}

function New-ReleaseZip {
    param(
        [string]$Arch,
        [string]$Tag
    )
    Write-Step "Creating ZIP for Windows $Arch"
    $releaseDir = "release\$Tag"
    if (-not (Test-Path -LiteralPath $releaseDir)) {
        New-Item -ItemType Directory -Path $releaseDir | Out-Null
    }
    $zipPath = Join-Path $releaseDir "FLAtlas-$Tag-windows-$Arch.zip"
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    tar -a -cf $zipPath -C "dist-$Arch" FLAtlas
    if ($LASTEXITCODE -ne 0) {
        throw "ZIP creation failed: $zipPath"
    }
    return (Resolve-Path $zipPath).Path
}

function Get-CommitLines {
    param([string]$Range)
    if ($Range) {
        return @(git log --reverse --oneline $Range)
    }
    return @(git log --reverse --oneline)
}

function Get-IssueNumbersFromGitLog {
    param([string]$Range)
    $text = if ($Range) { git log --format=%B $Range } else { git log --format=%B }
    $numbers = New-Object System.Collections.Generic.HashSet[string]
    foreach ($line in $text) {
        foreach ($match in [regex]::Matches($line, '#(\d+)')) {
            [void]$numbers.Add($match.Groups[1].Value)
        }
    }
    return @($numbers) | Sort-Object {[int]$_}
}

function Get-ClosedIssueNumbersSinceTag {
    param(
        [string]$Tag,
        [string]$Repo
    )
    if (-not $Tag.Trim()) {
        return @()
    }
    try {
        $dateText = (git log -1 --format=%cI $Tag).Trim()
        if (-not $dateText) {
            return @()
        }
        $date = $dateText.Substring(0, 10)
        $jsonText = gh issue list --repo $Repo --state closed --search "closed:>=$date" --limit 100 --json number
        $items = $jsonText | ConvertFrom-Json
        $numbers = @()
        foreach ($item in $items) {
            if ($item.number) {
                $numbers += [string]$item.number
            }
        }
        return $numbers | Sort-Object {[int]$_} -Unique
    } catch {
        return @()
    }
}

function Merge-IssueNumbers {
    param([string[]]$Sets)
    $numbers = New-Object System.Collections.Generic.HashSet[string]
    foreach ($item in $Sets) {
        if ("$item".Trim()) {
            [void]$numbers.Add("$item")
        }
    }
    return @($numbers) | Sort-Object {[int]$_}
}

function New-ReleaseNotes {
    param(
        [string]$Tag,
        [string]$PrevTag,
        [string]$Repo
    )
    Write-Step "Generating release notes"
    $range = if ($PrevTag) { "$PrevTag..HEAD" } else { "" }
    $notesPath = "release\$Tag\release-notes.md"
    if (-not (Test-Path -LiteralPath (Split-Path -Parent $notesPath))) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $notesPath) | Out-Null
    }

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("## FLAtlas $Tag")
    $lines.Add("")

    $issueNumbers = Merge-IssueNumbers @(
        Get-IssueNumbersFromGitLog $range
        Get-ClosedIssueNumbersSinceTag $PrevTag $Repo
    )
    if ($issueNumbers.Count -gt 0) {
        $lines.Add("### Fixed / Closed Issues")
        foreach ($num in $issueNumbers) {
            $title = ""
            try {
                $json = gh issue view $num --repo $Repo --json title,state,url 2>$null | ConvertFrom-Json
                if ($json -and $json.title) {
                    $title = [string]$json.title
                }
            } catch {
                $title = ""
            }
            if ($title) {
                $lines.Add("- #$num $title")
            } else {
                $lines.Add("- #$num")
            }
        }
        $lines.Add("")
    }

    $commitLines = Get-CommitLines $range
    if ($commitLines.Count -gt 0) {
        $lines.Add("### Commits")
        foreach ($line in $commitLines) {
            $lines.Add("- ``$line``")
        }
        $lines.Add("")
    }

    if ($issueNumbers.Count -eq 0 -and $commitLines.Count -eq 0) {
        $lines.Add("No commit changes were found for this release range.")
        $lines.Add("")
    }

    Set-Content -LiteralPath $notesPath -Value $lines -Encoding UTF8
    return (Resolve-Path $notesPath).Path
}

function Assert-ReleasePrerequisites {
    param([string]$Tag)
    Assert-Command "git"
    Assert-Command "gh"
    Assert-Command "py"
    Assert-Command "tar"

    gh auth status | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub CLI is not authenticated."
    }

    $existingTag = git tag --list $Tag
    if ($existingTag) {
        throw "Tag already exists locally: $Tag"
    }
    $remoteTag = git ls-remote --tags origin $Tag
    if ($remoteTag) {
        throw "Tag already exists on origin: $Tag"
    }
    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    gh release view $Tag --repo $Repo *> $null
    $releaseViewExitCode = $LASTEXITCODE
    $ErrorActionPreference = $oldErrorActionPreference
    if ($releaseViewExitCode -eq 0) {
        throw "GitHub release already exists: $Tag"
    }
}

function Publish-Release {
    param(
        [string]$Tag,
        [string]$Repo,
        [string]$NotesPath,
        [string[]]$Assets
    )
    Write-Step "Publishing GitHub release"
    git tag $Tag
    git push origin $Tag
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to push tag $Tag"
    }

    gh release create $Tag @Assets --repo $Repo --title "FLAtlas $Tag" --notes-file $NotesPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create GitHub release $Tag"
    }

    $release = gh release view $Tag --repo $Repo --json url,assets | ConvertFrom-Json
    Write-Host "Release URL: $($release.url)"
    foreach ($asset in $release.assets) {
        Write-Host "Asset uploaded: $($asset.name) ($($asset.size) bytes)"
    }
}

$repoRoot = Resolve-RepoRoot
Set-Location $repoRoot

$appVersion = Get-AppVersion
$releaseVersionInput = if ($Version.Trim()) { $Version } else { $appVersion }
$tag = Normalize-Version $releaseVersionInput
$prevTag = Get-PreviousTag $tag
$rangeLabel = if ($prevTag) { "$prevTag..HEAD" } else { "all commits" }

Write-Step "Preparing FLAtlas release $tag"
Write-Host "Repository: $repoRoot"
Write-Host "GitHub repo: $Repo"
Write-Host "Changelog range: $rangeLabel"

Assert-CleanWorktree
Assert-ReleasePrerequisites $tag

$assets = @()
if (-not $SkipBuild) {
    foreach ($arch in @("x64", "arm64")) {
        $py = New-ReleaseVenv $arch
        Invoke-ReleaseBuild $arch $py
        Assert-BuildArchitecture $arch
    }
} else {
    Write-Step "Skipping build by request"
    foreach ($arch in @("x64", "arm64")) {
        Assert-BuildArchitecture $arch
    }
}

foreach ($arch in @("x64", "arm64")) {
    $assets += New-ReleaseZip $arch $tag
}

$notes = New-ReleaseNotes $tag $prevTag $Repo

if ($SkipUpload) {
    Write-Step "Skipping upload by request"
    Write-Host "Release notes: $notes"
    foreach ($asset in $assets) {
        Write-Host "Asset ready: $asset"
    }
    exit 0
}

Publish-Release $tag $Repo $notes $assets
