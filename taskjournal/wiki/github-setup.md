# 🔑 Generate a Classic GitHub Token

## 1. Go to the token page

👉 [https://github.com/settings/tokens](https://github.com/settings/tokens)
(then click **"Personal access tokens → Tokens (classic)"** in the left sidebar).

## 2. Click "Generate new token (classic)"

## 3. Set up your token

- **Note**: Give it a descriptive name (e.g. `taskjournal-cli`).
- **Expiration**: Choose how long it should last (shorter is safer, you can always regenerate).

## 4. Select the scopes (permissions)

For most CLI tools that only need to read repos and commits, you can check:

- `repo` → full control of private repositories (if you only need read, you can narrow it, but GitHub’s classic token
  scopes are broad).
- `read:org` → if you want to read org info.
- `user:email` → if you need access to your email (optional).

👉 If you’re just fetching commit stats from your org (like in your `GithubService`), **`repo` + `read:org` is enough**.

## 5. Click "Generate token"

## 6. Copy the token

It will look like: `ghp_abcd1234efgh5678ijklmnopqrstuvwx`

then click **"Copy"** to copy it to your clipboard.
and add it to your `~/.config/taskjournal/.env`

```shell
# GitHub configuration
GIT_HUB_ORGANIZATION_NAME = "my-github-org"
GIT_HUB_TOKEN="gh-key"
```
