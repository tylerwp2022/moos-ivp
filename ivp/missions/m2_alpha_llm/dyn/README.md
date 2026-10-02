# dyn/

One results file per vehicle from `uDynamicsTest` (moos-ivp-dyn): one
line per measurement, appended at the end of every run, read at launch.
The vehicle's uDynamicsTest posts the statistics as `DYN_FACTS`,
pBehaviorTree folds them into `VEHICLE_FACTS`, the bridge carries them
to the shoreside, and pLLMAgent's prompt reads them out per speed. The
files here were measured on the simulated boats with the mission's
current uSimMarineV22 and pMarinePIDV22 tuning; re-measure after
changing either, with the helm idle:

    uPokeDB targ_abe.moos DYN_START=1      # one sequence of the five speeds
