# 推送到 GitHub —— 只剩这一步

本地仓库已经完整构建并提交好了（`D:\DSH\github\bg3-knuckle-dusters`，84 个文件 / 32.3 MB，
分支 `main`，首次提交 `4f895d2`）。**剩下的只是需要你的 GitHub 凭据**，我没有也不该有。

---

## 方式 A：用 GitHub CLI（推荐，一条命令全搞定）

```powershell
winget install --id GitHub.cli -e
gh auth login                     # 选 GitHub.com -> HTTPS -> 浏览器登录
cd D:\DSH\github\bg3-knuckle-dusters
gh repo create bg3-knuckle-dusters --public --source . --push
```

`gh` 会自动建仓库、加 remote、推送，不用手点任何东西。

---

## 方式 B：网页建库 + 一条 push

1. 打开 https://github.com/new
2. 仓库名填 `bg3-knuckle-dusters`，选 **Public**，**不要**勾 README / .gitignore / licence（否则首推会冲突）
3. 然后在 PowerShell 里跑：

```powershell
cd D:\DSH\github\bg3-knuckle-dusters
.\push-to-github.ps1
```

第一次推送会弹浏览器让你登录 GitHub，登录完成后自动推上去。

---

## 方式 C：给我一个令牌，我来推

在 https://github.com/settings/tokens?type=beta 新建 fine-grained token，
只勾 **Repository permissions → Contents: Read and write**，有效期设 7 天，
仓库范围选 All repositories（或先建好空库再单选它），把令牌发给我，我执行推送后你立刻吊销。

> 令牌等同于密码，仅在你自己机器上使用；用完请马上 revoke。

---

## 推完要做的两件事

1. 确认仓库地址，我把 Nexus 描述里的链接改成实际地址（现在写的是
   `github.com/RelyonBigBlueFatWhale/bg3-knuckle-dusters`，用户名不对就告诉我）。
2. 在 Nexus 每个文件的 **Permissions** 里把 `Modification permission` 设成
   **"You are allowed to modify my files and release bug fixes or improve on the features
   without asking me first"**，与 MIT + CC BY 4.0 的承诺保持一致。