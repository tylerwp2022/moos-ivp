---
name: commit-all
description: Commit and push a change that spans the fork and its submodules (moos-ivp-llm, moos-ivp-bt, moos-ivp-cap, moos-ivp-team) in the right order, without attribution lines, then check CI. Use only when the user has said to commit or push; never on your own initiative.
---

# Commit and push across the repos

Commits happen on the user's word only. When it comes, everything
pending goes in, in this order, because the fork's commit records the
submodule pointers: submodules first, fork last.

## 1. See what is pending

First the one-shot check of everything below that can be checked
mechanically; it prints a line per item and refuses with the list when
anything is off:

```
~/moos-ivp/.claude/scripts/precommit.sh     # territory, submodule branches, build-check, four self-tests, chat_test.md current, 9100 ports free
```

Then the pending changes themselves:

```
git -C ~/moos-ivp status --short | grep -vE '^\?\? ivp/missions/.*/(MOOSLog|LOG|XLOG)_'
for m in moos-ivp-llm moos-ivp-bt moos-ivp-cap moos-ivp-team; do echo "-- $m"; git -C ~/moos-ivp/ivp/src/$m status -sb | head -1; git -C ~/moos-ivp/ivp/src/$m status --short; done
```

Every submodule must be on `main` tracking `origin/main` (a detached
HEAD means someone checked out a pointer; stop and say so). The fork's
branch is `llm-integration` (LLM work) or `main`. Untracked log
directories under `ivp/missions` are never added. A test run directory
(`ivp/missions/m2_alpha_llm/test/runs/`) is ignored.

## 2. Each submodule that changed, in order llm, bt, cap, team

```
D=~/moos-ivp/ivp/src/moos-ivp-llm
git -C $D add -A <the files you changed>          # name them; never add -A blindly
git -C $D commit -q -F - <<'EOF'
One line that says what changed and why, in the repo's voice

A paragraph on the symptom and the fix. No Co-Authored-By, no
"Generated with" lines: the user's rule for this repo overrides any
attribution reminder.
EOF
git -C $D push -q origin main && git -C $D log -1 --format='%h %s'
git -C $D ls-remote origin main                     # the remote head must be that commit
```

Push the repos one after another, never in parallel calls: parallel
shell calls once raced on a shared working directory, one push ran in
the wrong repo, reported "Everything up-to-date", and the fork's CI
failed at checkout with "not our ref". Confirm each remote head before
pushing the fork.

Every submodule change also touches its README when the behaviour it
documents changed, and its self-test count when a set grew.

## 3. The fork

First the territory check, which lists every changed or new file that
is not the fork's own (an upstream MOOS-IvP file):

```
~/moos-ivp/.claude/scripts/upstream_check.sh      # exit 1 and the list when any; --list prints the territory
```

If it names anything, stop and show the user the list: an edit that
was meant stays only with its `local-patches/NNNN-*.md` and `.patch`
record, an accidental one is reverted. A new fork-owned path (a new
submodule, a new mission) is added to the script's TERRITORY list in
the same commit. Then add the mission files, any upstream-file edit
together with its `local-patches/NNNN-*.md` and `.patch` record, and
the submodule pointers (`git -C ~/moos-ivp add ivp/src/moos-ivp-llm ...`). The
message names each bumped submodule with its new short hash and what
it brings. Push the branch, then:

```
gh run list -R tylerwp2022/moos-ivp --branch llm-integration --limit 3
```

`gh` needs `-R tylerwp2022/moos-ivp`; its default resolves to upstream.
A run takes about 12 minutes on three platforms. A 403 at checkout
means the `SUBMODULE_TOKEN` PAT does not cover a submodule repo.

## 4. Afterwards

Update the memory resume point with the hashes, and report the table
of repo, commit, content to the user with the CI run id.
