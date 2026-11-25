# Configure a model endpoint

Use this guide to prepare the `pLLMAgent` configuration for a compatible service. It is a configuration procedure, not a verified live-service deployment procedure.

The WSL `Demo` and `Verify` actions select a local scripted endpoint. The [live Alpha launch](../tutorials/first-command.md#run-live-alpha) reads the checked-in OpenAI mission.

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

For OpenAI Responses, use `api_protocol = openai_responses`, `api_url = "https://api.openai.com/v1/responses"`, and `api_key_env = OPENAI_API_KEY`. Set the model ID to one available to your project.

For WIRE, use the `chat_completions` template above with the full endpoint URL, deployed model ID, and authentication settings provided by West Point. Start with `tools_enabled = false`. Run the shared Alpha tutorial against its local stand-in to verify the viewer workflow from either site.

## Review the configuration

Compare the block with the pinned reference. Use `pLLMAgent -e` and `pLLMAgent -i` to inspect the binary's example and MOOS interface. These commands do not prove that a service accepts the configuration.

Restart the agent through the mission's controlled launch procedure after a configuration change. The checked-in Alpha launcher expects `OPENAI_API_KEY` for its OpenAI profile. For a different provider, follow the launch procedure for the mission you configured.

Before enabling control tools, verify a native read-only tool call and its result round trip. Text that resembles a command does not establish native tool support.

For non-Anthropic protocols, cost estimates require explicit rates. The budget is advisory. Model availability, pricing, service access, and live operation are not established by the local stand-in tests.
