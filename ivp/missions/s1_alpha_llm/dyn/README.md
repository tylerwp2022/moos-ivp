# dyn/

`alpha.txt` is the results file of `uDynamicsTest` (moos-ivp-dyn) for
this mission's boat: one line per measurement, appended at the end of
every run, read at launch and posted as `DYN_FACTS`, which pBehaviorTree
folds into `VEHICLE_FACTS` for pLLMAgent's prompt. Measured with the
mission's current simulator and PID tuning; re-measure after changing
either, with the helm idle: `uPokeDB alpha.moos DYN_START=1`.
