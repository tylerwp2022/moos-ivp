# ADR 001: Publish the researcher handbook from dev

Status: accepted by owner instruction, November 20, 2026.

## Context

The workspace documentation mixes local setup, component references, proposed work, and dated evidence. Researchers need one browser entry point and a reproducible first task. Tyler maintains `main`; our source of truth is `dev`.

## Decision

Maintain the handbook as Markdown under `docs/handbook`. Build it with pinned MkDocs tooling. Publish its static output through GitHub Actions and GitHub Pages from `dev`.

Use the four Diátaxis purposes. Keep current guidance, decisions, and evidence separate. Link component contracts at exact revisions. Do not copy private component manuals into the public site.

The website build checks out only this repository. It does not fetch submodules or require a model key. Include the CSS, search index, and diagrams in the build output.

## Consequences

The site can build before runtime dependencies are available. GitHub repository access is still required for some component references and the runtime installation.

A repository owner or maintainer must enable Pages. The owner must allow `dev` in the `github-pages` environment. The build can succeed while publication remains disabled.

This decision does not establish that the site is deployed, that a fresh-machine installation passed, or that the prose fully complies with ASD-STE100.
