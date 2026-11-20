# Terminology

Use these terms consistently. Preserve exact commands, UI labels, fields, and filenames. This project list does not replace the ASD-STE100 dictionary.

| Term | Meaning and use |
|---|---|
| V2GPM | Project name used in correspondence and this handbook. |
| `V2PGM` | Existing workspace/path spelling. Do not change it inside executable examples. |
| MOOSDB | The message database used by applications to exchange named values. Technical noun. |
| MOOS variable | A named value published through MOOSDB. Technical noun. |
| capability | A permitted command defined by a `.cap` file. |
| behavior tree | An XML plan executed by `pBehaviorTree`. Technical noun. |
| helm | The autonomy process that selects vehicle behavior outputs. |
| operator approval | The operator's acceptance of a proposed tool action. It is not proof that the action is safe in every setting. |
| scripted stand-in | A local endpoint with fixed responses used for a test. Do not call it a live model. |
| simulation | A run that uses a simulated vehicle. It does not establish field behavior. |
| replay | Execution or analysis of retained inputs. Distinguish it from regenerating a plan with a model. |
| source manifest | A record of source commit identities and selected components. |
| validation evidence | Dated commands, inputs, observations, failures, and limits. |
| `dev` | Our development source branch. |
| `main` | Tyler's maintained branch. |
| build, clone, commit, deploy | Software technical verbs, used for their defined software operations. |

The last row records project usage; its classification still needs a full-standard editorial review. Do not use a technical-term list to excuse ambiguous ordinary prose.
