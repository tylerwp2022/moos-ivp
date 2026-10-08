# Local patch: IvPContactBehavior::updatePlatformInfo() is quiet about a contact with no information when on_no_contact_ok

- **Date applied:** 2026-10-08
- **File changed:** `ivp/src/lib_behaviors/IvPContactBehavior.cpp` (`updatePlatformInfo()`, Part 1B)
- **Patch file:** `local-patches/0003-contactbehavior-nav-warning-quiet.patch`
- **Baseline commit at time of patch:** `f56c6907a` (merge base with upstream/main)
- **Status:** LOCAL MODIFICATION, not upstream. Re-apply after any upstream
  update that touches `IvPContactBehavior.cpp`.

## Why

A contact behavior names the vehicle it works against and reads that
vehicle's position from the helm's ledger on every iteration, in the idle
state too (`BHV_AvoidCollision::onIdleState`, `BHV_AvdColregsV22`
likewise call `updatePlatformInfo()`). When the name has no information
the function posts the warning `<contact> x/y/heading/speed info not
found` on every call when `on_no_contact_ok = true`, and the helm's
appcast counts every post as a run warning for the rest of the run: a
retraction clears the active list, not the count, and pMarineViewer
paints a vehicle red while the count is above zero. A behavior that
exists from helm start with a fixed contact, as the mctf_llm mission's
avoidance instances do (one per other boat, so that live range updates
stick), posted the warning four times a second until the shoreside
relayed the other boats' first node reports: 500 to 2300 warnings per
boat at every launch, every boat red in the viewer over nothing. A
spawned template never shows this, since it spawns only when the contact
is already known. A first version of this patch posted the warning once
per gap; twelve retracted warnings per boat still left every vehicle red,
so the owner asked for them gone (2026-10-08).

## The fix

With `on_no_contact_ok = true`, a contact with no information is not
warned about at all: the behavior idles until the contact reports, which
is what the parameter says. The error branch (`on_no_contact_ok = false`)
is unchanged and still reports a missing contact loudly.

## The cost, accepted

A contact name that never resolves (a typo in a hand-written block, a
plan naming a boat that does not exist) is not pointed at by a warning
under the ok setting; the behavior simply never acts. In the fork's
missions the contact names come from the launcher's roster, the agent's
tools and uFldSquad, all checked against the roster before posting, and
the plan checker reads plan files against it too, so the hint was not
load-bearing there.

## Suggested message to upstream

> `IvPContactBehavior::updatePlatformInfo()` posts the "x/y/heading/speed
> info not found" warning on every call while a named contact has no
> ledger information, even with `on_no_contact_ok = true`. A behavior
> configured at helm start with a contact that reports later (fixed
> instances rather than spawned templates) posts thousands before the
> first report, and the appcast count never comes down. Suggested fix:
> under `on_no_contact_ok` post nothing (or at most once, gated by the
> `m_nav_warning_posted` flag the retraction already assumes).

## Reverting / re-applying

    git -C ~/moos-ivp apply -R local-patches/0003-contactbehavior-nav-warning-quiet.patch
    git -C ~/moos-ivp apply    local-patches/0003-contactbehavior-nav-warning-quiet.patch
    ./build-ivp.sh

Verification: launch mctf_llm headless and count `BHV_WARNING` posts per
boat: none from the avoidance instances, every helm appcast at zero run
warnings.
