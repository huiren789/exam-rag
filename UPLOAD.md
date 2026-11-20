# 把 ExamRAG 上传到 GitHub——手把手指南

这份指南假设你**已有一个 GitHub 账号**，但还没有这个项目的仓库。
按从上到下的顺序做即可；遇到报错看最后的「常见问题」。

---

## 0. 当前状态（我已帮你做完的部分）

在项目目录里，我已经完成：

```bash
git init
git config --local user.name  "hrh666"
git config --local user.email "<你的 GitHub 邮箱>"
git branch -M main
git add .
git commit -m "feat: ExamRAG 可溯源课程复习 RAG 工具（零依赖 + 测试 + CI）"
```

也就是说：**本地仓库已经建好、身份已配置、首次提交已完成**。
提交作者邮箱使用的是 GitHub 的 noreply 地址，不会把真实邮箱写进提交历史。
你只需要做「在网页上建仓库」+「推送」两步。

> 想核对状态，在该目录打开终端运行 `git status` 和 `git log --oneline -1`。

**安全检查**：仓库里没有 `.env`（已被 `.gitignore` 忽略），源码里也没有真实 API Key。
如果你之后创建了 `.env`，它不会被提交；千万不要把含真实密钥的文件 `git add` 进去。

---

## 1. 在 GitHub 网页上新建仓库

1. 浏览器打开 <https://github.com>，登录你的账号 `hrh666`。
2. 点右上角 **+** → **New repository**。
3. 按下面填写：
   - **Repository name**：`exam-rag`
   - **Description**（可选，建议填）：
     `有据可依的复习搭档——零依赖、可溯源的课程 RAG 命令行工具`
   - **Public / Private**：选 **Public**（作品集展示建议公开；以后也能在 Settings 改）。
   - **不要勾选** Add a README file、Add .gitignore、Choose a license
     ——本地已有这些文件，勾了会产生冲突。
4. 点 **Create repository**。页面会显示一段远程仓库地址，形如
   `https://github.com/hrh666/exam-rag.git`。

---

## 2. 推送到 GitHub

在项目目录打开终端（Git Bash / PowerShell / CMD 都行），依次执行：

```bash
cd <项目目录>

git remote add origin https://github.com/hrh666/exam-rag.git
git push -u origin main
```

第一次推送会要求登录 GitHub：

- 用户名填：`hrh666`
- 密码处**不要填登录密码**，要填 Personal Access Token（见下一步）。

如果推送时没有提示输入（某些环境会弹网页登录窗口），按提示完成即可。

---

## 3. 生成 Personal Access Token（推送需要它）

GitHub 从 2021 年起不再允许用账号密码推送代码，要用 Token：

1. 打开 <https://github.com/settings/tokens>。
2. 点 **Generate new token** → **Generate new token (classic)**。
3. 填写：
   - **Note**：`exam-rag-push`
   - **Expiration**：`90 days`（或 No expiration，但更要注意保管）
   - 权限勾选 **`repo`**（勾这一项会自动勾上它的子项）
4. 拉到最底部点 **Generate token**。
5. **立刻复制**那串 `ghp_...` 开头的字符——页面关闭后就看不到了。
6. 回到终端重新执行 `git push -u origin main`，用户名填 `hrh666`，密码处粘贴 Token。

> Token 等同于密码，不要截图发人、不要写进项目文件。

---

## 4.（可选）改用 SSH，以后不用每次输 Token

```bash
# 生成密钥，一路回车即可
ssh-keygen -t ed25519 -C "<你的 GitHub 邮箱>"

# 查看并复制公钥内容
cat ~/.ssh/id_ed25519.pub
```

然后到 GitHub → 头像 → **Settings** → **SSH and GPG keys** → **New SSH key**，
标题随意，把刚才复制的公钥粘贴进去并保存。最后在本地执行：

```bash
git remote set-url origin git@github.com:hrh666/exam-rag.git
git push -u origin main
```

---

## 5. 推送完成后检查

1. 刷新 `https://github.com/hrh666/exam-rag`，确认能看到
   `examrag/`、`data/`、`tests/`、`README.md`、`UPLOAD.md` 等文件。
2. 点仓库上方的 **Actions** 标签，确认 `tests` 工作流跑完并显示绿色对勾
   （首次可能要等 1–2 分钟）。
3. README 顶部的 CI 徽章开始显示状态。
4. 再确认一次：仓库里**没有** `.env`、没有 `sk-` 开头的真实密钥。

至此，项目就正式成为你的公开 GitHub 作品了。简历里可以直接放仓库链接。

---

## 常见问题

**`fatal: remote origin already exists`**
说明已经添加过远程地址。执行
`git remote set-url origin https://github.com/hrh666/exam-rag.git` 再推送。

**`error: failed to push some refs` / `Updates were rejected`**
通常是建仓库时勾了「Add a README」导致远端有本地没有的提交。执行：

```bash
git pull --rebase origin main
git push -u origin main
```

**推送时认证一直失败**
确认密码框里填的是第 3 步生成的 Token（不是 GitHub 登录密码），且 Token 勾选了 `repo` 权限、还没过期。

**想改成私有仓库**
GitHub 仓库页面 → Settings → 拉到最底部 Danger Zone → Change visibility → Make private。

**误传了 API Key**
立刻去硅基流动后台吊销/重置该 Key，然后从仓库中删除该文件并处理提交历史
（可用 `git filter-repo`），不要只删最新一次提交。

---

## 附：以后更新代码怎么提交

```bash
cd <项目目录>
# 修改文件后……
python -m unittest discover -s tests -v   # 先跑测试
git add .
git commit -m "fix: 简要说明改了什么"
git push
```
