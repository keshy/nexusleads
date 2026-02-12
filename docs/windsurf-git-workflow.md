# Windsurf Git Workflow (OSS + Private)

This workflow assumes two worktrees with different identities and push targets.

## One-time Setup

1. Ensure the two remotes exist in the main worktree.
   - `origin-private` -> `git@github-keshy:keshy/nexusleads.git`
   - `origin-oss` -> `git@github-krishna2:krishna2_cisco/nexusleads.git`
2. Ensure SSH host aliases map to the correct keys.
   - `github-keshy` uses `~/.ssh/p_github`
   - `github-krishna2` uses `~/.ssh/c_github`
3. Enable per-worktree config once in the main worktree.
   - `git config extensions.worktreeConfig true`
4. Create the OSS worktree (from the main worktree).
   - `git worktree add ../nexusleads-oss oss-main`
5. Set identities per worktree.
   - Private worktree:
     - `git config user.name "Krishnan"`
     - `git config user.email "krishna2@cisco.com"`
     - `git config commit.gpgsign true`
     - `git config remote.pushDefault origin-private`
   - OSS worktree:
     - `git config user.name "Krishnan"`
     - `git config user.email "keshi8086@gmail.com"`
     - `git config commit.gpgsign true`
     - `git config remote.pushDefault origin-oss`

## Daily Workflow (Windsurf)

1. Open two Windsurf windows, one per worktree.
   - Private: `/Users/krishnan/code/plg-lead-sourcer`
   - OSS: `/Users/krishnan/code/nexusleads-oss`
2. Before coding, confirm identity and branch.
   - `git status -sb`
   - `git config user.email`
3. Develop and commit in the private worktree first.
   - `git add -A`
   - `git commit -m "Your message"`
4. Push private.
   - `git push`
5. Bring changes into OSS worktree.
   - `git fetch origin-private`
   - `git merge origin-private/main`
6. Confirm no private-only content is present, then commit in OSS worktree if needed.
   - `git add -A`
   - `git commit -m "Your message"`
7. Push OSS.
   - `git push`

## If You Prefer Syncing by Branch Name

1. From private worktree, push `main`.
2. From OSS worktree, rebase or merge from private remote.
   - `git fetch origin-private`
   - `git rebase origin-private/main`
3. Push OSS branch.

## Troubleshooting

1. Wrong GitHub identity used.
   - `ssh -T git@github-keshy`
   - `ssh -T git@github-krishna2`
2. Verify remote URLs.
   - `git remote -v`
3. Force the correct key for a single push.
   - `GIT_SSH_COMMAND="ssh -i ~/.ssh/p_github -o IdentitiesOnly=yes" git push origin-private main`
   - `GIT_SSH_COMMAND="ssh -i ~/.ssh/c_github -o IdentitiesOnly=yes" git push origin-oss oss-main`

## Optional Convenience

1. Push both from the private worktree.
   - `git push origin-private main`
   - `git push origin-oss oss-main`
2. Add aliases.
   - `git config alias.pushboth "!git push origin-private main && git push origin-oss oss-main"`
