param (
    [Alias("v")]
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
$tagName = "v$Version"
$releaseName = "Encrypted Databases $tagName"
$dbDir = "database"

Write-Host "--- Starting Process for Version $Version ---" -ForegroundColor Cyan

# 1. Run Conversion
Write-Host "Step 1: Running parallel database conversion..." -ForegroundColor Yellow
uv run python convert_to_db.py
if ($LASTEXITCODE -ne 0) { throw "Database conversion failed." }

# 2. Generate Index
Write-Host "Step 2: Generating translation index..." -ForegroundColor Yellow
uv run python generate_index.py
if ($LASTEXITCODE -ne 0) { throw "Index generation failed." }

# 3. Git Commit and Tag
Write-Host "Step 3: Committing changes and tagging..." -ForegroundColor Yellow
git add bible-translations-index.json
git diff --quiet --staged
if ($LASTEXITCODE -ne 0) {
    git commit -m "chore: update index for $tagName"
    git push origin master
}
else {
    Write-Host "No changes in index to commit." -ForegroundColor Gray
}

# Check if tag exists locally and delete if it does (to allow override if needed, or just fail)
if (git tag -l $tagName) {
    Write-Host "Tag $tagName already exists. Please choose a new version or delete the tag." -ForegroundColor Red
    exit 1
}

git tag $tagName
git push origin $tagName

# 4. Create GitHub Release
Write-Host "Step 4: Creating GitHub Release $tagName..." -ForegroundColor Yellow
gh release create $tagName --title $releaseName --notes "Automated release of encrypted Bible databases for version $tagName."

# 5. Chunked Upload
Write-Host "Step 5: Uploading databases in batches of 100..." -ForegroundColor Yellow
$files = Get-ChildItem -Path $dbDir -Filter *.db
$totalFiles = $files.Count
$batchSize = 100
$batchCount = [Math]::Ceiling($totalFiles / $batchSize)

for ($i = 0; $i -lt $batchCount; $i++) {
    $start = $i * $batchSize
    $currentBatch = $files | Select-Object -Skip $start -First $batchSize
    
    $batchNames = $currentBatch.FullName
    Write-Host "Uploading batch $($i + 1) of $batchCount ($($currentBatch.Count) files) in parallel..." -ForegroundColor Cyan
    
    # Upload the batch in parallel
    $currentBatch | ForEach-Object -Parallel {
        gh release upload $using:tagName $_.FullName --clobber
    } -ThrottleLimit 10
    
    if ($i -lt ($batchCount - 1)) {
        Write-Host "Batch complete. Waiting 10 seconds for rate limits..." -ForegroundColor Gray
        Start-Sleep -Seconds 10
    }
}

Write-Host "--- All Done! Release $tagName is ready ---" -ForegroundColor Green
