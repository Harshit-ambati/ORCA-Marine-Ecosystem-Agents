$ErrorActionPreference = 'Stop'
$repo = 'Harshit-ambati/ORCA-Marine-Ecosystem-Agents'
$root = $PSScriptRoot

# Expected remote blob IDs from the public main branch when this update was prepared.
$files = @(
    @{ Path = 'evaluation/run.py'; Sha = '73dd63ab52b9694dcce9f3743698acea98db9f9d' },
    @{ Path = 'README.md'; Sha = 'ff3d7a2af42a24ef76cf3eb1242403e53ab793fa' },
    @{ Path = 'SUBMISSION.md'; Sha = 'dad09303118a5c14ed17c362375c59d4e25016f3' },
    @{ Path = 'tests/test_evaluation.py'; Sha = $null }
)

gh auth status | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI authentication is not available in this terminal.' }

foreach ($file in $files) {
    $path = $file.Path
    $localPath = Join-Path $root $path
    if (-not (Test-Path -LiteralPath $localPath -PathType Leaf)) { throw "Missing local file: $path" }
    $endpoint = "repos/$repo/contents/$path"
    $remoteJson = $null
    $status = 1
    try {
        $remoteJson = gh api $endpoint 2>$null
        $status = $LASTEXITCODE
    } catch {
        # A missing new file returns 404; PUT below creates it. Existing files still fail safely.
        if ($file.Sha) { throw }
    }
    $remote = if ($status -eq 0) { $remoteJson | ConvertFrom-Json } else { $null }
    if ($file.Sha) {
        if (-not $remote) { throw "Cannot read existing remote file: $path" }
        if ($remote.sha -ne $file.Sha) {
            $remoteText = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(($remote.content -replace '\s', '')))
            $localText = [IO.File]::ReadAllText($localPath, [Text.Encoding]::UTF8)
            if ($remoteText -ceq $localText) { Write-Host "Already current: $path"; continue }
            throw "Remote file changed since review: $path. Stop and inspect before overwriting."
        }
    } elseif ($remote) {
        $remoteText = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(($remote.content -replace '\s', '')))
        $localText = [IO.File]::ReadAllText($localPath, [Text.Encoding]::UTF8)
        if ($remoteText -ceq $localText) { Write-Host "Already current: $path"; continue }
        throw "Remote file already exists with different content: $path"
    }

    $payload = @{ message = 'Improve evaluation scoring and review outputs'; branch = 'main';
        content = [Convert]::ToBase64String([IO.File]::ReadAllBytes($localPath)) }
    if ($file.Sha) { $payload.sha = $file.Sha }
    $tempFile = Join-Path $env:TEMP ("orca-publish-" + [guid]::NewGuid().ToString('N') + '.json')
    try {
        [IO.File]::WriteAllText($tempFile, ($payload | ConvertTo-Json -Compress), [Text.UTF8Encoding]::new($false))
        gh api $endpoint -X PUT --input $tempFile | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "GitHub rejected update: $path" }
        Write-Host "Published: $path"
    } finally {
        Remove-Item -LiteralPath $tempFile -ErrorAction SilentlyContinue
    }
}

Write-Host "Verified target: https://github.com/$repo"
