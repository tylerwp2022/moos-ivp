# Local patch: IvPContactBehavior::applyAbleFilter() accepts action=able

- **Date applied:** 2026-09-30
- **File changed:** `ivp/src/lib_behaviors/IvPContactBehavior.cpp` (`applyAbleFilter()`, Part 2)
- **Patch file:** `local-patches/0002-contactbehavior-able-filter-able.patch`
- **Baseline commit at time of patch:** `f56c6907a` (upstream/main as merged)
- **Status:** LOCAL MODIFICATION, not upstream. Re-apply after any upstream
  update that touches `IvPContactBehavior.cpp`.

## Why

The helm's `BHV_ABLE_FILTER` variable carries four actions. Three go to the
behaviors (`disable`, `enable`, `expunge`, applied per contact, behavior
type or source). The fourth, `able`, is handled by the helm itself:
`BehaviorSet::applyAbleFilterMsg()` (`lib_helmivp/BehaviorSet.cpp`) keeps a
blacklist of contact names that were disabled, so that an instance spawned
later for that contact starts out disabled, and `action=able,contact=X`
is the only way to take X off that list. But the same function first hands
every message to every behavior's `applyAbleFilter()`, whose syntax check
rejects any action other than the three it knows, so `able` always comes
back as a failure and pHelmIvP posts the sticky run warning
`Unhandled BHV_ABLE_FILTER` while doing the right thing underneath.

The fork's `avoid_heed` capability (`moos-ivp-cap/capabilities/contact/`)
undoes a per-contact avoidance exemption with `enable` (live instances)
followed by `able` (the blacklist, for later spawns); without the second
post the exemption silently returned the first time the contact left
`completed_dist` and came back. With the warning the operator sees a red
warning count on the vehicle for a post that worked.

## The fix

`applyAbleFilter()` returns true for `action=able` before its action check:
well-formed, nothing for a behavior to do. Six lines, comment included.

## Suggested message to upstream

> `BHV_ABLE_FILTER = action=able,contact=X` (the blacklist clear added to
> `BehaviorSet::applyAbleFilterMsg` in Sep 2025) is rejected by every
> `IvPContactBehavior::applyAbleFilter()`, so `addAbleFilterMsg` returns
> false and pHelmIvP reports "Unhandled BHV_ABLE_FILTER" although the
> blacklist was updated. Suggested fix: accept `able` in the behavior's
> syntax check as a no-op.

## Reverting / re-applying

    git -C ~/moos-ivp apply -R local-patches/0002-contactbehavior-able-filter-able.patch
    git -C ~/moos-ivp apply    local-patches/0002-contactbehavior-able-filter-able.patch
    ./build-ivp.sh pHelmIvP

Verification: on a vehicle with the two avoidance templates, post
`BHV_ABLE_FILTER = action=able,contact=ben` and check the pHelmIvP appcast
shows no run warning.
