# 一键部署个人网站：提交本地改动 -> 推送到 GitHub -> 等待自动部署完成
# 用法：双击 deploy.bat；或在终端运行 .\deploy.ps1 -Message "修改说明"
param([string]$Message = "")

[Console]::OutputEncoding = [Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$repo = "zwchen03/zwchen03.github.io"

function Done($code) {
  if (-not $env:DEPLOY_NO_PAUSE) { Read-Host "`n按回车关闭" | Out-Null }
  exit $code
}

Write-Host "=== 部署 zwchen.online ===" -ForegroundColor Cyan

# 1. 先同步线上的改动（例如每 6 小时自动更新的力扣数据），避免推送冲突
git pull --rebase --autostash --quiet
if ($LASTEXITCODE -ne 0) {
  Write-Host "拉取线上改动时出现冲突，请先处理冲突后再部署。" -ForegroundColor Red
  Done 1
}

# 2. 提交本地改动
git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
  Write-Host "`n本次改动的文件："
  git diff --cached --stat
  if (-not $Message) { $Message = Read-Host "`n请输入这次修改的说明（直接回车使用默认说明）" }
  if (-not $Message) { $Message = "Update site " + (Get-Date -Format "yyyy-MM-dd HH:mm") }
  $tmp = [IO.Path]::GetTempFileName()
  [IO.File]::WriteAllText($tmp, $Message, (New-Object Text.UTF8Encoding $false))
  git commit --quiet -F $tmp
  Remove-Item $tmp
} else {
  $ahead = git rev-list --count "@{u}..HEAD"
  if ($ahead -eq "0") {
    Write-Host "没有需要部署的改动。" -ForegroundColor Yellow
    Done 0
  }
}

# 3. 推送，GitHub Actions 会自动开始部署
git push --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "推送失败，请检查网络或 GitHub 登录状态。" -ForegroundColor Red; Done 1 }
Write-Host "已推送到 GitHub，正在等待自动部署..." -ForegroundColor Green

# 4. 等待部署完成（需要 GitHub CLI；没有的话就去网页上看）
if (Test-Path $gh) {
  Start-Sleep -Seconds 6
  $id = & $gh run list -R $repo --limit 1 --json databaseId --jq ".[0].databaseId"
  & $gh run watch $id -R $repo --exit-status --interval 5 | Out-Null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "`n部署成功！约 1 分钟后访问 https://zwchen.online （按 Ctrl+F5 强制刷新）" -ForegroundColor Green
    Done 0
  }
  Write-Host "`n部署失败，查看详情：https://github.com/$repo/actions" -ForegroundColor Red
  Done 1
}
Write-Host "部署进度：https://github.com/$repo/actions"
Done 0
