# 一键把本仓库推上 GitHub
# 用法：在 PowerShell 里运行  .\push-to-github.ps1
# 前提：已在 GitHub 网页端建好空仓库（不要勾选 README），仓库名建议 bg3-knuckle-dusters

param(
    [string]$User = "RelyonBigBlueFatWhale",
    [string]$RepoName = "bg3-knuckle-dusters",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (git remote) -or -not ((git remote) -contains "origin")) {
    git remote add origin "https://github.com/$User/$RepoName.git"
} else {
    git remote set-url origin "https://github.com/$User/$RepoName.git"
}

git branch -M $Branch
Write-Host "推送到 https://github.com/$User/$RepoName (分支 $Branch) ..." -ForegroundColor Cyan
git push -u origin $Branch

Write-Host ""
Write-Host "完成。仓库地址：https://github.com/$User/$RepoName" -ForegroundColor Green