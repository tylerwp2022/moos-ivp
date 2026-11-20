# V2GPM development instructions

- `dev` is the source of truth for our project work. Make changes on feature branches and submit pull requests targeting `dev`; do not push directly to `dev` unless explicitly requested.
- Tyler owns `main`. Do not push to or merge into `main` unless the user explicitly requests it.
- The V2GPM component repositories also use `dev`. Merge component changes through pull requests into their `dev` branches before updating their pinned commits in this repository through a pull request.
- Submodule branch settings identify development branches; normal checkout and builds must still use the exact committed submodule pins.
- Attribute our changes and work-history entries to Timeo Williams; do not add separate agent attribution.
- Preserve existing author/license notices. Add or update source-file modification comments with Timeo Williams and the actual modification date (`YYYY-MM-DD`).
- Add selective comments in the owner's direct, plainspoken voice to explain non-obvious changes; avoid narrating obvious code or commenting every edit.
