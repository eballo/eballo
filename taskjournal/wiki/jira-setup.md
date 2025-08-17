# 🔑 Generate a Jira API Token

## 1. Go to the API token page

👉 [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

## 2. Click **"Create API token"**

## 3. Set up your token

- **Label**: Give it a descriptive name (e.g. `taskjournal-cli` or `local-dev`).
- **Permissions**: Jira API tokens inherit your account’s permissions.
  > No need to select scopes — if your account can do it in Jira, the token will allow it.

## 4. Copy the token

Copy the generated token to your clipboard.
It will look like: `abcd1234efgh5678ijklmnopqrstuvwx`

Then add it to your `~/.config/taskjournal/.env` file as `JIRA_API_TOKEN`.

```shell
# JIRA configuration
JIRA_ORGANIZATION="my-organization"
JIRA_API_TOKEN="jira-key"
JIRA_EMAIL="jira-email"
JIRA_BOARD_ID="jira-board-id"
```
