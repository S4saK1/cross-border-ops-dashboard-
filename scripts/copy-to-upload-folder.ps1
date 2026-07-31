# copy-to-upload-folder.ps1
# 将需上传 GitHub 的文件整理到实体文件夹（不含机密/构建产物），
# 方便直接在 GitHub 网页拖拽上传。
# 用法（在项目根目录的父级用 -File 运行）：
#   powershell -ExecutionPolicy Bypass -File scripts\copy-to-upload-folder.ps1
# 产物文件夹：%USERPROFILE%\github-upload-staging\bilingual-product-cms\

$ErrorActionPreference = 'Stop'

# 项目根 = 脚本所在目录(bilingual-product-cms\scripts)的父目录
$scriptDir = $PSScriptRoot
$root = (Get-Item $scriptDir).Parent.FullName

$stagingRoot = Join-Path $env:USERPROFILE 'github-upload-staging'
$top = Join-Path $stagingRoot 'bilingual-product-cms'

# 需要排除的目录名（不区分大小写）
$excludeDirs = @(
    '.git',
    '__pycache__',
    'node_modules',
    '.next',
    'logs',
    'temp',
    'tmp',
    'build',
    'dist',
    'eggs',
    'coverage_html',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache',
    'htmlcov',
    '.workbuddy',
    '.venv',
    'venv',
    'env',
    'temp-engineering-review'
)

# 需要排除的精确文件名
$excludeExact = @(
    '.env',
    '.env.production',
    '.env.local',
    'nul',
    'upload_files.txt',
    'generate_upload_list.py',
    'test_password_validation.py',
    'GITHUB_WEB_UPLOAD_GUIDE.md',
    'build-upload-zip.ps1',
    'copy-to-upload-folder.ps1',
    'package-for-github.bat'
)

# 需要排除的文件后缀（小写）
$excludeExt = @('.db', '.sqlite', '.sqlite3', '.pyc', '.pyo', '.pyd', '.log')

Write-Host "Scanning: $root"

$files = Get-ChildItem -Path $root -Recurse -File | Where-Object {
    $item = $_
    # 1) 路径中是否包含需排除的目录
    $parts = $item.FullName.Split([System.IO.Path]::DirectorySeparatorChar)
    foreach ($p in $parts) {
        if ($excludeDirs -contains $p) { return $false }
    }
    # 2) 精确文件名排除
    if ($excludeExact -contains $item.Name) { return $false }
    # 3) 后缀排除
    if ($excludeExt -contains $item.Extension.ToLower()) { return $false }
    # 4) init-git 临时脚本排除
    if ($item.Name -like 'init-git*') { return $false }
    return $true
}

# 清空并重建目标文件夹
if (Test-Path $top) { Remove-Item $top -Recurse -Force }
New-Item -ItemType Directory -Path $top | Out-Null

$sep = [System.IO.Path]::DirectorySeparatorChar
foreach ($f in $files) {
    $rel = $f.FullName.Substring($root.Length).TrimStart($sep)
    $dest = Join-Path $top $rel
    $destDir = Split-Path $dest -Parent
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    Copy-Item $f.FullName $dest -Force
}

Write-Host ''
Write-Host "Done. Copied $($files.Count) files to:"
Write-Host $top
