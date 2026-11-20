# Configure a model endpoint

Use this guide to prepare the `pLLMAgent` configuration for a compatible service. It is a configuration procedure, not a verified live-service deployment procedure.

The WSL `Demo` and `Verify` actions always select a local scripted endpoint. Changing the source mission does not turn those actions into live-model launchers.

## Supply the endpoint information

Obtain the wire protocol, complete request URL, model ID, authentication method, and permitted data use from the service operator.

Use the [pinned LLM reference](https://github.com/tylerwp2022/moos-ivp-llm/blob/8fedcbd5e95911ad9c60a67e87942fa7d1e250c1/README.md#configurable-api-endpoints) for exact fields and defaults. Repository access can be required.

## Prepare the mission block

1. Make a separate copy of the mission configuration.
2. In its `pLLMAgent` block, remove any conflicting legacy `provider` selection.
3. Select an explicit protocol, URL, and model.
4. Start with `tools_enabled = false`.
5. Name the credential environment variable. Keep its value outside the mission file.

This example is a template. Replace the URL and model ID before use:

```text
api_protocol = chat_completions
api_url = "https://your-server.example/v1/chat/completions"
model = your-model-id
api_auth = bearer
api_key_env = LLM_API_KEY
tools_enabled = false
confirm_default = true
```

Quote URLs that contain `//`; otherwise the MOOS parser can treat the rest as a comment. Explicit protocols require an explicit URL and model.

## Review the configuration

Compare the block with the pinned reference. Use `pLLMAgent -e` and `pLLMAgent -i` to inspect the binary's example and MOOS interface. These commands do not prove that a service accepts the configuration.

Restart the agent through the mission's controlled launch procedure after a configuration change. The existing Alpha `launch.sh` still checks `ANTHROPIC_API_KEY`; it is not a generic provider launcher. A complete generic live launch-and-stop procedure remains unverified.

Before enabling control tools, verify a native read-only tool call and its result round trip. Text that resembles a command does not establish native tool support.

For non-Anthropic protocols, cost estimates require explicit rates. The budget is advisory. Model availability, pricing, service access, and live operation are not established by the local stand-in tests.
