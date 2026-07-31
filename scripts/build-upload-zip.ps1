# build-upload-zip.ps1
# 将跨境产品资料中英对照系统整理为可上传 GitHub 的压缩包。
# 用法：在 PowerShell 中执行
#   powershell -ExecutionPolicy Bypass -File scripts\build-upload-zip.ps1
# 生成的压缩包：<项目根>\bilingual-product-cms-upload.zip

$ErrorActionPreference = 'Stop'

# 项目根 = 脚本所在目录(bilingual-product-cms\scripts)的父目录
$scriptDir = $PSScriptRoot
$root = (Get-Item $scriptDir).Parent.FullName

$outName = 'bilingual-product-cms-upload.zip'
$out = Join-Path $root $outName

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

# 复制到临时目录，保持结构，顶层统一为 bilingual-product-cms/
$tmp = Join-Path $env:TEMP ('bcms_upload_' + [System.Guid]::NewGuid().ToString('N'))
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
New-Item -ItemType Directory -Path $tmp | Out-Null

$sep = [System.IO.Path]::DirectorySeparatorChar
foreach ($f in $files) {
    $rel = $f.FullName.Substring($root.Length).TrimStart($sep)
    $dest = Join-Path $tmp ('bilingual-product-cms' + [System.IO.Path]::DirectorySeparatorChar + $rel)
    $destDir = Split-Path $dest -Parent
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    Copy-Item $f.FullName $dest -Force
}

if (Test-Path $out) { Remove-Item $out -Force }
Compress-Archive -Path (Join-Path $tmp 'bilingual-product-cms') -DestinationPath $out -Force

Write-Host ''
Write-Host "Done. Packed $($files.Count) files."
Write-Host "Zip: $out"
Write-Host "Temp: $tmp  (可手动删除)"
