# Components and interfaces

The components form one autonomy system. Their pinned source files define the interfaces. Some linked repositories require access; the website does not copy their private manuals.

## Component responsibilities

| Component | Responsibility | Authoritative reference |
|---|---|---|
| MOOS-IvP base | Message bus, process launcher, simulator, controller, helm, viewer | [Base source](https://github.com/tylerwp2022/moos-ivp/tree/cf3a853835e72d126b6abf8cd5a29930a34a3e0f) |
| Capability | Command definitions and field constraints | [Capability README](https://github.com/tylerwp2022/moos-ivp-cap/blob/496a6672a1a6350b65559c83efed9eb5c766cfae/README.md) |
| Behavior tree | Plan validation and execution | [Behavior-tree README](https://github.com/tylerwp2022/moos-ivp-bt/blob/45c921f80ead76b2e41bf0ad2491e826580cbd73/README.md) |
| LLM | Model protocol, conversation, tools, and approval | [LLM README](https://github.com/tylerwp2022/moos-ivp-llm/blob/8fedcbd5e95911ad9c60a67e87942fa7d1e250c1/README.md) |
| Panel | Buttons that post commands or invoke plans | [Panel README](https://github.com/tylerwp2022/moos-ivp-panel/blob/b062a90f815120cf149200d941f8df6291f3da5b/README.md) |
| Dynamics | Measured motion characteristics | [Dynamics README](https://github.com/tylerwp2022/moos-ivp-dyn/blob/fdb02cf4b3a0433a6b70c280d2ca9bf9eced1c49/README.md) |
| History | Mission events and bounded summaries | [History README](https://github.com/tylerwp2022/moos-ivp-history/blob/2c35071c51fd4b9df2d03b4b724e4cf9a635f712/README.md) |
| Squad | Fleet-level plan coordination | [Squad README](https://github.com/tylerwp2022/moos-ivp-squad/blob/376ee8bde122516451dc0e7611365df557e6b30c/README.md) |
| MCTF | Capture-the-flag rules and missions | [Mission README](https://github.com/tylerwp2022/moos-ivp-mctf/blob/776b0b482bbc646a36e794f231cdd66497fd7ea8/missions/mctf_llm/README.md) |

## Find exact contracts

The `.cap` catalog defines capability names, arguments, validation, and MOOS posts. The behavior-tree library defines supported XML nodes. The mission supplies the behaviors and variables that a capability needs.

Do not assume that a syntactically valid plan can run in every mission. Inspect the capability requirements and the mission configuration together.

Use the installed binary to inspect its interface:

```bash
pLLMAgent -i
pLLMAgent -e
pBehaviorTree -i
pBehaviorTree -e
pBehaviorTree --check=plan.xml
```

`plan.xml` is your input file. An offline validation result does not establish that a live mission supplies its required behaviors or services. Some example/help text retains legacy provider wording; use the pinned LLM reference and implementation for protocol selection.

## Important MOOS variables

| Identifier | Role in the documented workflow |
|---|---|
| `LLM_CHAT_IN` | Operator message or approval input to the agent. |
| `LLM_CHAT_OUT` | Agent transcript output. |
| `LLM_STATUS` | Agent state, including `awaiting_confirm`. |
| `BT_TREE` | Behavior-tree XML submitted to the executor. |
| `NAV_X`, `NAV_Y` | Local navigation coordinates used by the simulation. |
| `WPT_UPDATE` | Waypoint behavior update in the Alpha mission. |

These are orientation notes, not a replacement interface schema. The component reference and `-i` output remain authoritative.
