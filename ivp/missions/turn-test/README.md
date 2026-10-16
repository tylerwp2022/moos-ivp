# turn-test — turn-in-place characterization rig

Single-vehicle sandbox for measuring how a rudder-steered surface craft
(V2GPM kinematics) can rotate to a commanded compass heading while
holding position. It quantifies the **speed vs. footprint** tradeoff of
several turning modalities so we can pick one before committing a
production behavior.

There is **no helm and no PID** in this mission: `pTurnInPlace` drives
`DESIRED_RUDDER` / `DESIRED_THRUST` straight into `uSimMarine`. That is
what lets it command reverse and run K-turn / shuffle maneuvers, which a
stock IvP behavior cannot (the helm's speed domain is non-negative).

## Run it

```bash
# GUI: watch the auto sweep; buttons C45/K90/S90 fire manual trials, STOP aborts
./launch.sh 10

# Headless: run the full sweep, tear down, and print/plot metrics
./launch.sh --nogui 15

# Analyze an existing log by hand
python3 analyze.py [LOG_dir | file.alog]

./clean.sh   # remove logs + generated files
```

Outputs (next to the `.alog`): `turn_metrics.csv`, and — if `matplotlib`
is installed — `turn_tradeoff.png` (footprint vs time, colored by
strategy) and `turn_paths.png` (XY tracks). Plots are skipped with a
notice if matplotlib is missing (`pip install matplotlib`).

## Strategies (`strategy=` in a TURN_REQUEST, or the config default)

- **circle** — continuous forward min-radius arc. Fastest per degree,
  largest footprint.
- **kturn** — forward arc until excursion reaches `cap`, then a reverse
  arc (rudder sign flipped so reverse rotates the *same* way), back to
  forward when excursion drops below `return_frac*cap`. Bounds footprint
  to ~`cap`.
- **shuffle** — same fwd/rev alternation but switched on a fixed
  `phase_time`; both legs rotate toward target so translation cancels →
  tightest footprint.

## Commanding a maneuver

`pTurnInPlace` acts on `TURN_REQUEST` (comma-separated key=val):

```
TURN_REQUEST = heading=90,strategy=kturn,tol=5,id=t1
TURN_REQUEST = delta=180,strategy=shuffle,phase_time=3,id=t2
```

Keys: `heading`|`delta`, `x`,`y` (station; default = pose at request
time), `strategy`, `tol`, `settle`, `fwd_thrust`, `rev_thrust`,
`rudder`, `cap`, `return_frac`, `phase_time`, `id`. On completion it
posts `TURN_RESULT` with `t_elapsed`, `max_excursion`, `bbox_diag`,
`final_pos_err`, `final_hdg_err`.

The `uTimerScript` block in `turn_test.moos` is the batch driver — edit
its `event=` lines to change the sweep (strategy × delta).

## Using it in a real (helm) mission: BHV_TurnInPlace

`turn_test.moos` is the bare characterization rig (no helm). To use
turn-in-place inside a normal helm mission, see **`turn_demo.moos` +
`turn_demo.bhv`**, and run:

```bash
./launch_demo.sh 4      # GUI: DEPLOY -> TURN180 -> auto-resume
```

Why a helper behavior instead of a pure IvP behavior: the shuffle needs
**reverse thrust** and coordinated rudder/thrust sign flips, which live
below the helm's `(course, speed)` abstraction and outside its
non-negative speed domain. A pure behavior can't express it. So:

- **`pTurnInPlace`** (the app) is the control engine. On a `TURN_REQUEST`
  it asserts `MOOS_MANUAL_OVERRIDE=true` (which parks the helm and makes
  `pMarinePID` go quiet), drives the actuators through the maneuver, then
  clears the override so the helm resumes. Set `manage_override=true`
  (default) in any helm mission; `false` in the bare rig.
- **`BHV_TurnInPlace`** (`lib/libBHV_TurnInPlace.so`) is a thin helm
  trigger: when its run conditions hold it posts one `TURN_REQUEST`,
  waits for `TURN_DONE`, then `setComplete()`s so its `endflag` fires and
  the mission resumes. It produces no objective function.

Minimal `.bhv` usage (see `turn_demo.bhv` for the full example):

```
Behavior = BHV_TurnInPlace
{
  name       = turn_in_place
  condition  = TURN = true
  perpetual  = true
  endflag    = TURN = false      // clears the trigger; prior behavior resumes

  delta       = 180              // or: heading = <abs>, or heading_var = SOME_VAR
  strategy    = shuffle          // circle | kturn | shuffle
  fwd_thrust  = 100
  rev_thrust  = -100
  phase_time  = 2
  tol         = 5
}
```

To trigger without a behavior, just post the same request from anywhere
(viewer button, uTimerScript, another app):
`TURN_REQUEST = delta=180,strategy=shuffle,fwd_thrust=100,rev_thrust=-100`.

Verified end-to-end in `turn_demo`: BHV fires -> override on -> shuffle
180 in ~0.58 m of drift -> override off -> `endflag` -> station-keep
resumes.

## IMPORTANT: sim-model dependency

Reverse rotation works only in the **legacy `uSimMarine`
(`dep_uSimMarine`)** turn model, which V2GPM uses. There, heading rate is
`rudder·(turn_rate/100)·(thrust/50)`, so negative thrust flips the yaw
direction and the K-turn / shuffle legs rotate. In **`uSimMarineV23`**,
`TurnSpeedMap.getTurnRate()` returns 0 for `speed ≤ 0`, so the vehicle
**cannot rotate while backing** — K-turns silently degrade to straight
reversing. If V2GPM is ever migrated to V23 (the direction implied by the
PlatModel/PR-104 port), this rig and any turn behavior derived from it
must be revisited.

## Findings from the initial sweep (turn_rate=10, rudder=100, thrust=±60)

| delta | circle t / footprint | shuffle t / footprint |
|------:|---------------------:|----------------------:|
|  45°  |  5.5 s / 0.7 m       |  5.6 s / 0.6 m        |
|  90°  |  9.1 s / 1.7 m       |  9.4 s / 0.6 m        |
| 135°  | 13.0 s / 2.5 m       | 13.2 s / 0.6 m        |
| 180°  | 16.7 s / 2.8 m       | 17.1 s / 0.8 m        |

- Time-to-heading is essentially strategy-independent (~0.09 s/deg); the
  turn rate is set by the forward-arc kinematics.
- **shuffle gives a ~3× smaller footprint for ~1% more time** — the clear
  "balance both" winner: a 180° reorientation in <1 m of drift.
- **kturn ≈ circle here** because the natural forward-arc footprint
  (~2.8 m at 180°) never reaches the default `cap=6`, so the reverse leg
  never triggers. Lower `cap` (e.g. 1.5) to make kturn distinct, or just
  use shuffle.
