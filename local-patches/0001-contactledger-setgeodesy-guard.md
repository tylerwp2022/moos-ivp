# Local patch: ContactLedger::setGeodesy() datum-unchanged guard

- **Date applied:** 2026-08-14 (verified same day: blue_one steady after shoreside relaunch)
- **File changed:** `ivp/src/lib_geodaid/ContactLedger.cpp` (both `setGeodesy()` overloads)
- **Patch file:** `local-patches/0001-contactledger-setgeodesy-guard.patch`
- **Baseline commit at time of patch:** `048db6fa1` (merge of upstream/main)
- **Status:** LOCAL MODIFICATION — not upstream. Re-apply after any upstream
  update that touches `ContactLedger.cpp` (git will refuse the merge or the
  patch will conflict; see "Reverting / re-applying" below).

## Symptom

In pMarineViewer (24.8), a vehicle icon constantly jumps back and forth
between two positions ~3 m apart several times per second, even though the
NODE_REPORT stream for that vehicle is completely steady (verified: single
source, monotonic INDEX, cm-level position drift, fixed heading, clocks
synchronized to 1 ms). Observed with real vehicles (SeaRobotics Surveyor,
vehicle `blue_one`) at the Popolopen site; not observed in pure simulation.

## Root cause

`PMV_MOOSApp::Iterate()` (`ivp/src/pMarineViewer/PMV_MOOSApp.cpp:139`) calls
`m_gui->mviewer->updateMOOSGeodesy()` on every app iteration (AppTick=4).
That forwards to `ContactLedger::setGeodesy()` (`PMV_Viewer.h:50`), which
unconditionally calls `updateLocalCoords()`, recomputing every contact's
x/y from its lat/lon with the viewer's geodesy — overwriting the x/y that
arrived in the node report. Each incoming NODE_REPORT then restores the
vehicle's own reported x/y, so the drawn position alternates between:

1. the x/y computed **on the vehicle** from its GPS fix, and
2. the x/y computed **by the viewer** from the report's lat/lon.

When the two conversions agree (e.g., simulation, where lat/lon is derived
from ground-truth x/y with the same geodesy), the overwrite is invisible.
They disagree here: the shoreside build has `USE_UTM=ON`, so the ledger
converts via `LatLong2LocalUTM`, while the vehicle's reported x/y matches a
flat-earth/LocalGrid-style conversion. At ~300 m from the datum
(41.34928, -74.063645), for a fix at (41.350303, -74.06017433):

| Representation                  | x (m)  | y (m)  |
|---------------------------------|--------|--------|
| Vehicle-reported X/Y            | 289.60 | 113.71 |
| Viewer UTM conversion of lat/lon| 289.12 | 116.71 |
| Flat-earth conversion of lat/lon| 290.46 | 113.62 |

The ~3 m discrepancy (mostly north-south) is dominated by UTM grid
convergence (~0.6 degrees at 0.94 degrees from the zone-18 central
meridian); it grows with distance from the datum. Result: a 3 m
back-and-forth jump at up to 4 Hz.

The per-iteration overwrite arrived with upstream commit `331518296`
("Major mod to uFldNodeComms to integrate ContactLedger"). `uFldNodeComms`
shares `ContactLedger`, so it carries the same latent behavior.

## The fix

Make `ContactLedger::setGeodesy()` a no-op when the datum is unchanged.
A genuine datum change still triggers `updateLocalCoords()`, which is that
function's intended purpose ("After a datum update, all X/Y values stored
with any contact are updated..."). Exact double comparison is appropriate
because the same parsed config value is passed on every call.

See `0001-contactledger-setgeodesy-guard.patch` for the exact diff.

Note this makes the viewer consistently trust the *vehicle-reported* x/y.
The deeper inconsistency — vehicles and shoreside converting lat/lon to
local grid differently (UTM vs LocalGrid / `USE_UTM` divergence) — still
exists and would surface anywhere else x/y and lat/lon are mixed. Upstream
has signaled x/y in NODE_REPORT will eventually be deprecated in favor of
lat/lon-only, which would also resolve this class of problem.

## Suggested message to upstream (mikerb / moos-ivp issue)

> pMarineViewer 24.8: vehicle icons jump back and forth for real vehicles
> whose onboard lat/lon->x/y conversion differs from the viewer's (e.g.,
> viewer built with USE_UTM=ON, vehicle publishing LocalGrid-style x/y; ~3 m
> apart 300 m from our datum, from UTM grid convergence). Cause:
> PMV_MOOSApp::Iterate() calls updateMOOSGeodesy() every iteration, and
> ContactLedger::setGeodesy() unconditionally runs updateLocalCoords(),
> overwriting reported x/y with a re-conversion of lat/lon; each new
> NODE_REPORT restores the reported x/y, so the drawn position ping-pongs at
> AppTick rate. Introduced in 331518296 (ContactLedger integration);
> uFldNodeComms shares the code path. Suggested fix (patch attached): early
> return in both setGeodesy() overloads when the datum origin is unchanged,
> preserving the re-localize-on-datum-change behavior.

## Scope: shoreside only

Only pMarineViewer calls `setGeodesy()` repeatedly (from `Iterate()`), so
only machines running pMarineViewer need this patch. The other ContactLedger
users — pContactMgrV20 (ContactMgrV20.cpp:203), pHelmIvP (HelmIvP.cpp:1332),
uFldNodeComms (FldNodeComms.cpp:222) — call it once in OnStartUp() and are
unaffected. The boats (searobot fleet) do not need this fix, though the
patch is a harmless no-op if it propagates there via normal rebuilds.

## Reverting / re-applying

The change is uncommitted in the working tree of `~/moos-ivp` (kept that way
deliberately so `git status`/`git diff` always show it).

Revert:

    cd ~/moos-ivp
    git checkout -- ivp/src/lib_geodaid/ContactLedger.cpp
    ./build-ivp.sh          # rebuild, then relaunch shoreside

(Equivalent: `git apply -R local-patches/0001-contactledger-setgeodesy-guard.patch`.)

Re-apply (e.g., after an upstream pull wiped it):

    cd ~/moos-ivp
    git apply local-patches/0001-contactledger-setgeodesy-guard.patch
    ./build-ivp.sh

If `git apply` conflicts after an upstream update, upstream touched
`ContactLedger.cpp` — check whether they fixed the issue before re-applying
by hand.

Verification after revert or re-apply: launch the shoreside mission with a
real vehicle reporting; patched behavior is a steady icon at the
vehicle-reported x/y, unpatched behavior is the ~3 m oscillation.
