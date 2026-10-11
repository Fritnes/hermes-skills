---
name: git-repo-sync
description: Register and safely synchronize multiple Git repositories. Use when the user asks to add a repository, check Git status, pull, commit, or push a registered repo.
version: 1.0.0
compatibility: Requires Python 3.11+ and Git.
---

# Git Repository Sync

Manage ordinary Git repositories independently of Obsidian. This skill does not create or edit project files unless the user requests it, and note creation must never trigger a Git sync automatically.

## Repository registry

Persist the list of repositories in `~/.hermes/git-repos.toml`, outside this skills repository. Do not store credentials or access tokens there; use the user's existing SSH agent, credential manager, or Git credential helper.

Use one table per repository under `[repositories.<key>]`. The registry supports any number of repositories. Each entry has the required fields `name`, `description`, `remote`, and `local_path`; `branch` is optional.

```toml
[repositories.home-lab]
name = "home-lab"
description = "Personal home lab configuration and services"
remote = "git@github.com:user/home-lab.git"
local_path = "/home/user/projects/home-lab"
branch = "main"

[repositories.dotfiles]
name = "dotfiles"
description = "Personal workstation configuration"
remote = "git@github.com:user/dotfiles.git"
local_path = "/home/user/.dotfiles"
```

`name` is a short, unique identifier and should match the table key. `description` briefly explains what the repository is for. `remote` is the expected Git remote URL. `local_path` is the absolute path to the working copy. `branch` is optional; if omitted, use the repository's currently checked-out branch.

When registering a repository:

1. Ask for the repo name, a brief description, its remote URL, and local path. Ask for the branch only if it cannot be determined or the user wants a particular branch.
2. If the repo is already local, verify it is a Git repository and inspect its remotes and current branch. If it is not local, ask whether to clone it and confirm the destination path before cloning.
3. Show the proposed entry and get confirmation before writing it. Do not put credentials or tokens in the remote URL.
4. Preserve other registry entries. Validate the TOML after editing, then report the saved name and values, omitting any sensitive data.

For an existing repo, if its actual remote differs from the configured `remote`, or the configured remote is missing, report the mismatch and ask before changing Git remotes. Never silently rewrite a remote or branch.

## Check for updates

Run `python3 scripts/check_repos.py` from this skill's directory to check every registered repo, or add `--repo <name>` to check one. This default mode fetches and reports status without pulling or pushing.

Add `--sync` to perform two-way synchronization. If the remote is ahead, it fast-forward pulls. If local commits are ahead, it pushes them. If both sides have unique commits, it reports divergence and stops. It also skips pull and push when the worktree is dirty or the configured branch is not checked out. It never creates commits or force-pushes. Use `--config <path>` only when the registry is stored somewhere other than `~/.hermes/git-repos.toml`.

The checker reports whether a branch is up to date, behind the remote, ahead, or diverged, and whether the worktree is clean or dirty. Fetch updates Git metadata but does not change working files.

## Workflow

- If the user names a repo, resolve it from the registry. If the name is ambiguous or absent, ask which repo or register it first.
- Before any operation, verify the configured local path exists, is a Git worktree, and has the expected remote. Show the repository name, path, branch, and remote host so the user can catch a wrong target.
- When asked whether a repo needs updating, run `check_repos.py` without `--sync` and report the result.
- When asked to sync a repo, run `check_repos.py --sync` (with `--repo <name>` when specified). Explain that this may pull or push committed changes; it will not create commits.
- For status requests, run `git -C <path> status --short --branch` and report the result. Use `git -C <path> fetch` when ahead/behind information is needed; fetch does not change the working tree.
- Pull only when the working tree is clean. Show the target branch and remote first, then use `git -C <path> pull --ff-only` to avoid creating an unexpected merge commit. If it cannot fast-forward, stop and explain the situation; do not reset, rebase user changes, or resolve conflicts automatically.
- Before committing, inspect `git diff` and `git status`, summarize the files and changes, and ask for approval and a commit message. Stage only the approved changes; do not blindly stage unrelated files.
- Push manually only when the user explicitly asks. State the repository and branch before pushing. Never force-push.
- A request to "sync" authorizes the script's fast-forward pull or push of already-committed changes. Report conflicts and stop rather than guessing.
- For bulk requests, show the repository list first. Sync only the requested repos, report each result, and never create commits as part of a bulk sync.

## Safety

- Never run `reset --hard`, force-push, clean untracked files, discard changes, or resolve conflicts without explicit user direction.
- Never overwrite or delete repository files while registering, updating, or removing an entry. Removing a registry entry must not delete the local repository or remote.
- Keep the registry user-local; never commit it into this skills repo.
- Do not expose tokens, credentials, or credential-bearing remote URLs in chat or logs.
