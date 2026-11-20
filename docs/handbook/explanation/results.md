# What a result establishes

A result is useful when its claim matches its evidence. Keep the source, inputs, environment, and observation together.

## Different levels of evidence

| Statement | Evidence needed |
|---|---|
| Implemented | The behavior exists in identified source. |
| Available | Required components and access are present in the stated environment. |
| Locally verified | A stated check passed with recorded inputs and observations. |
| Independently reproduced | Another reader completed the documented procedure and retained the result and interventions. |
| Field demonstrated | Identified hardware and operating conditions produced the recorded observation. |
| Planned | A proposal or decision exists; implementation or validation is not established. |

An accepted decision does not prove implementation. A build does not establish operational readiness. A passing example does not establish general correctness.

## Simulation and model results

The local stand-in tests software integration. It cannot measure model reasoning, service reliability, or provider compatibility. The simulator cannot establish real vehicle dynamics, communication behavior, or recovery performance.

Replaying a retained plan and asking a model to generate a new plan are different experiments. Model generation can vary. State which path supplied each result.

## Experiment limits

For an experiment, retain actual sampled inputs as well as seed labels. State planned, attempted, completed, and excluded trial counts. Retain failure reasons. Do not score an incomplete run as a zero result.

A successful single-vehicle tutorial does not qualify the full MCTF match, an energy model, a UUV deployment, or an entire mission family. Those workflows need their own prerequisites and evidence.

For the current bounded result, read the [November 20 record](../evidence/2026-11-20-dev.md).
