# Local patch: getLogStart() ends its string when the line ends right after the value

- **Date applied:** 2026-11-20
- **File changed:** `ivp/src/lib_logutils/LogUtils.cpp` (`getLogStart()`)
- **Patch file:** `local-patches/0004-logutils-getlogstart-terminate.patch`
- **Baseline commit at time of patch:** `f56c6907a` (merge base with upstream/main)
- **Status:** LOCAL MODIFICATION, not upstream. Re-apply after any upstream
  update that touches `getLogStart()` in `LogUtils.cpp`.

## Why

`getLogStart()` reads the timestamp from an alog's `%% LOGSTART  <value>`
header line. It copies the value into a local buffer and writes the
terminating `'\0'` only when a blank or a tab comes after the value. A
line that ends right after the value never meets one, the buffer is
left unterminated, and `atof` reads on into whatever bytes the stack
held. pLogger writes every header that way (`%% LOGSTART
8951307663.465096`, nothing after it), so every real log takes this
path. The answer is right when the next stack byte happens not to
continue a number, which is what Linux and Intel macOS have been
giving. It is wrong otherwise: a stray digit lengthens the fraction, a
stray `e` and digits would make an exponent of it.

Found on 2026-11-20, the first time the self-tests ran on macOS: the
`macos-26` (arm64) CI job failed `history_selftest`'s check "LOGSTART
read" (458 checks, 1 failure; run 44780008460), which writes a header
`%% LOGSTART           1000000.5`, loads it through
`HistoryLoad::load` and expects 1000000.5 back. Reproduced on Linux
with a small program that leaves digit characters on the stack before
the call: 1000000.577777778 came back.

Callers: `getLogStartFromFile()` in the same file, and through it
`HistoryLoad::load` in moos-ivp-history (the value becomes the history's
clock offset, which the `until` facts are resolved against), `alogcat`,
`alogmhash` and `Populator_TaskDiary`.

## The fix

One line before the `return(atof(buff))`: `buff[buffix] = '\0';`. The
string now ends where the copied characters end, whatever follows the
value. A line with a blank after the value behaves as before (the
string was already ended at the same place), and a header with no value
gives 0 instead of whatever was on the stack.

## The cost, accepted

One more upstream file carried as a local patch. Nothing else changes:
no caller, no test, no file format.

## Suggested message to upstream

> `getLogStart()` in `lib_logutils/LogUtils.cpp` terminates its buffer
> only when whitespace follows the timestamp. pLogger writes the
> `%% LOGSTART` line with nothing after the value, so `atof(buff)` reads
> past the copied characters into uninitialized stack memory. It shows
> on arm64 macOS, where a test reading `%% LOGSTART  1000000.5` got a
> different number back; elsewhere it is right by luck. Suggested fix:
> `buff[buffix] = '\0';` before the return (and a bound on `buffix`
> against `MAX_LINE_LENGTH` while there).

## Reverting / re-applying

    git -C ~/moos-ivp apply -R local-patches/0004-logutils-getlogstart-terminate.patch
    git -C ~/moos-ivp apply    local-patches/0004-logutils-getlogstart-terminate.patch
    ./build-ivp.sh

Verification: `bin/history_selftest` ends `458 checks, 0 failures` (the
count as of this patch) on every CI platform, the `macos-26` job
included; that job is the only arm64 check there is.
