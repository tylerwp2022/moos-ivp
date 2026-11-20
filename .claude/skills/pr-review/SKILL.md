---
name: pr-review
description: Review a pull request someone else opened against the fork or one of its submodules - find the linked pair, read the whole diff, build the pull request's tree in scratch without touching the working tree, compare its self-test and its startup with the current build, check what it says about an outside API against the vendor's own docs, and report findings with a merge recommendation. Use when the user says a pull request came in, asks for a PR to be reviewed, or names a PR number or URL.
---

# Reviewing a pull request

The author's description is a list of claims. Each one ends the review
either checked, with how, or named as not checked. Three rules hold
throughout:

- The pull request's branch is never checked out in the working tree:
  the owner usually has uncommitted work there. Everything is built
  and run from the session scratchpad.
- Nothing is posted to GitHub (a comment, a review, a merge) without
  the owner's word.
- Reading says what the code does; a run says what happens. Report
  which of the two each statement rests on.

## 1. Find what was submitted

A change to a submodule arrives as a pair: the real pull request on
the submodule's repository and a one-line pointer bump on the fork.
Look in both places:

```
gh pr list --repo tylerwp2022/moos-ivp --state open
for r in moos-ivp-llm moos-ivp-bt moos-ivp-cap moos-ivp-squad moos-ivp-dyn moos-ivp-panel moos-ivp-history moos-ivp-tak moos-ivp-mctf; do
  gh pr list --repo tylerwp2022/$r --state open; done
gh pr view <n> --repo tylerwp2022/<repo> --json title,body,author,baseRefName,headRefName,headRefOid,commits,files,mergeable,statusCheckRollup
gh api repos/tylerwp2022/<repo>/commits/<headRefOid> --jq '[.parents[].sha]'   # does it sit on the current head?
```

Read `statusCheckRollup` for what actually ran. The submodule
repositories have no CI of their own, so the fork's pull request is
the only automated build. A green Docker job means the commit compiled
on Ubuntu; only the `CMake Build` workflow runs `build-check.sh`, the
unit tests, the self-tests and macOS, and only for the branches its
`pull_request:` line names.

## 2. Read the diff, then lay out exactly what was read

```
S=<scratchpad>/pr ; mkdir -p $S/tree
gh pr diff <n> --repo tylerwp2022/<sub> > $S/pr.diff        # read all of it, not the summary
git -C ivp/src/<sub> archive HEAD | tar -x -C $S/tree        # when the submodule's HEAD is the PR's parent
git -C $S/tree apply $S/pr.diff
```

The tree built this way is the base plus the diff that was read, line
for line. When the submodule's HEAD is not the pull request's parent,
`git -C ivp/src/<sub> fetch origin <headRefName>` and archive
`FETCH_HEAD` instead (a fetch adds objects and changes no file).

The owner's uncommitted work against it:

```
git -C ivp/src/<sub> diff > $S/local.diff
cp -r $S/tree $S/tree_local && git -C $S/tree_local apply --check $S/local.diff
```

## 3. Build it, and count the self-test

```
.claude/skills/pr-review/pr_build.sh <sub> $S/tree $S/overlay     # about a minute for moos-ivp-llm
$S/overlay/bin/llm_selftest | tail -1 ;  bin/llm_selftest | tail -1
```

`pr_build.sh` builds in an overlay: a folder of links to `ivp/src` with
the one submodule pointing at the scratch tree, CMake run with the
settings of the build in `build/ivp`, outputs in `$S/overlay/bin` and
`lib`. It builds every library and executable the pull request's CMake
files declare and prints the compiler's diagnostics in the pull
request's own files (the tree builds with `-Wall -Wextra -pedantic`
and `-std=c++11`; a new warning is a finding). Nothing in the
repository is written.

Compare the self-test's count with the current binary's and with the
number the author gives: the difference is the number of checks the
pull request adds. The five self-tests are `llm_selftest`,
`bt_selftest`, `cap_selftest`, `squad_selftest`, `history_selftest`;
run the ones whose libraries the change touches.

A pull request that edits the fork's own source (pMarineViewer,
`ivp/src/CMakeLists.txt`) is not a submodule tree: the overlay does not
fit it. Rely on the fork's CI run for the build, or make a
`git worktree` outside the repository and run `./build.sh` there.

## 4. Start it next to the current build

```
.claude/skills/pr-review/pr_startup.sh pLLMAgent ivp/missions/s1_alpha_llm/alpha.moos $S/overlay/bin $S/run \
   'openai=s|^( *)confirm_default = true|\1confirm_default = true\n\1provider = openai|' \
   'no_ttl=/^ *cache_ttl *=/d'
```

It copies the mission's folder to scratch, starts one MOOSDB on 9100,
and starts the current app and the pull request's app on the file as
it is and on each named variant (a `sed -E` script), with every API key
out of the environment so nothing can be sent. Give it one variant per
configuration line the pull request reads, and one per case the pull
request says it refuses. It says "up" or how the app died, with a
backtrace when it died on a signal, and shuts the MOOSDB down.

What this is for: a shipped mission must start exactly as before, and
a refused configuration must be refused in words the operator sees.
In this MOOS, `OnStartUp` returning false tears the app down under its
reader thread: the process aborts and the reason, held in the appcast,
is never shown. The tree's convention is `reportConfigWarning` and
carry on; an early `return false` there is a finding.

For more than a startup (a chat turn, a plan, a boat moving), the
headless-fleet and chat-test skills apply; they launch apps by name
from `PATH`, so they run the current build unless `$S/overlay/bin` is
put first in `PATH` (not yet tried).

## 5. Two checks that run in the background

- `/code-review <the pull request's URL>` for the line-by-line read.
  Give the URL, not the number: a number alone does not say whether
  the fork or a submodule is meant. It takes about twenty minutes; do
  steps 2 to 4 meanwhile and do not repeat its reading. Its findings
  are a second reader's: check the ones that decide the recommendation
  against the code before passing them on.
- When the change talks to an outside service, list every fact it
  relies on (model names, field names, allowed values, prices, limits)
  and have an agent check each against the vendor's own documentation,
  fetched that day: confirmed, contradicted or could not verify, with
  the URL and the quoted line. Never from memory; these change faster
  than anything a model was trained on.

## 6. Follow the pull request's safety claims through the code

A claim such as "a refused or cut-off reply cannot run a tool" is
checked at the place the thing happens: find the one call that runs
tools, the condition on it, and what the new code feeds that
condition. Ask too what is left behind in stored state (the
conversation, a file) when the unusual case happens, and whether the
next request can still be built from it.

## 7. Report

In the fix-review skill's plain terms, in this order:

1. The recommendation: merge, or request changes, in one line.
2. What holds up, each with how it was checked.
3. Fix before merge: numbered, each with the file and line in the pull
   request's version, what the operator would see, and whether the
   owner's own missions run into it.
4. What needs a live run by the author (anything that takes a key or
   an account the review did not have).
5. Minor points, at the author's discretion.
6. Faults already in the tree that the review came across: reported as
   the tree's, not held against the pull request.
7. What was not verified.
8. Merging: the submodule's pull request first, as a merge commit and
   not a squash, so the commit the fork's pointer names still exists;
   after a squash or a rebase the pointer is moved first.

Posting is a separate step the owner asks for:
`gh pr review <n> --repo tylerwp2022/<repo> --request-changes --body-file <file>`.
Name the commit the review covers in its first lines, and look at
`headRefOid` again just before posting: an author keeps pushing while a
review is under way (the first one here grew two commits, a new title
and a different scope in half an hour). When the head has moved, read
the new commits (`gh api repos/.../compare/<reviewed>...<head>` with
`Accept: application/vnd.github.diff`), repeat steps 2 to 4 on the new
tree, redo the report, and show the owner the new text before it goes.
If the owner would rather fix a finding here than send it back, that
is the fix-review skill, one fix at a time.

## 8. Leave nothing behind

Everything made is in the scratchpad. Check that no MOOSDB is left on
9100 (the Stop hook does too) and that the submodule's working tree
and branch are as they were (`git -C ivp/src/<sub> status -sb`).
