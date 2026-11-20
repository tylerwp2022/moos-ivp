# Publish and maintain this site

The handbook source is on `dev`. GitHub Actions builds it without submodules or model credentials. Until Pages is enabled, the workflow retains a downloadable preview and skips deployment.

## Enable Pages — Tyler's setup steps

These steps require repository-owner access for the deployment environment. GitHub Pages source configuration requires admin or maintainer permission.

1. Open [Settings → Pages](https://github.com/tylerwp2022/moos-ivp/settings/pages) in `tylerwp2022/moos-ivp`.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**. Keep the repository's default branch as `main`.
3. Open [Settings → Environments](https://github.com/tylerwp2022/moos-ivp/settings/environments). Select `github-pages`. If it is absent, select **New environment**, enter `github-pages`, and select **Configure environment**.
4. Under **Deployment branches and tags**, choose **Selected branches and tags**. Select **Add deployment branch or tag rule**. Set **Ref type** to **Branch**, enter `dev`, and select **Add rule**. Retain any required-reviewer policy you intend to use.
5. Open [Actions → Documentation website](https://github.com/tylerwp2022/moos-ivp/actions/workflows/docs.yml). Open the latest run for `dev`. Select **Re-run all jobs**, then confirm **Re-run jobs**. If a dropdown appears, choose **Re-run all jobs** rather than only failed jobs.
6. If the environment requires review, approve the pending deployment. Wait for both `build` and `deploy` to pass.
7. Open [the handbook](https://tylerwp2022.github.io/moos-ivp/). Confirm the landing page, tutorial, search, and architecture diagram load.

The initial workflow can pass its build while `deploy` is skipped. Re-running all jobs after setup repeats the Pages-configuration check.

The workflow exists on `dev`; do not depend on a **Run workflow** button appearing while `main` lacks that file. Use the existing push-triggered run. GitHub permits re-runs within 30 days. If that run is too old, push the next reviewed handbook change to `dev` to trigger a new run.

No personal access token or `SUBMODULE_TOKEN` is needed for this workflow. Its scoped `GITHUB_TOKEN` handles artifact publication.

Official guidance: [Pages source configuration](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site), [custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages), [environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments), and [workflow re-runs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs).

## Build and preview locally

Use Python 3.12 or later and Git. From the repository root, run:

```powershell
python -m venv .venv-docs
.\.venv-docs\Scripts\python.exe -m pip install -r requirements-docs.txt
.\.venv-docs\Scripts\python.exe -m mkdocs build --strict
.\.venv-docs\Scripts\python.exe scripts/docs/check_site.py site
.\.venv-docs\Scripts\python.exe -m http.server 8000 --directory site
```

Open `http://localhost:8000` in a browser. Stop the preview server with `Ctrl+C`.

On Linux, use `.venv-docs/bin/python` for the same module commands. The website does not need a runtime build.

The validator checks rendered local links, anchors, image text, the search index, and artifact symlinks. It writes `site/build-info.json` with the source commit and dirty status. It does not certify external links, technical correctness, or ASD-STE100 compliance.

## Review and update

Edit the authoritative Markdown page. Update `mkdocs.yml` when navigation changes. Preserve old anchors or add a migration entry when moving content. Run the strict build and link validator. Inspect desktop and narrow layouts, keyboard focus, search, code blocks, and diagrams.

Normally, use a feature branch and a pull request targeting `dev`. Direct pushes require the owner's explicit instruction. A qualifying push to `dev` rebuilds the site. Pull requests build a preview but do not deploy.

Keep runtime evidence dates unchanged for prose edits. Add a dated evidence record only when new checks establish a new result.

## Recover from a publication failure

If the workflow skips deployment, confirm **Source = GitHub Actions**, then re-run all jobs. If deployment is rejected for its branch, permit `dev` in the environment. If a build fails, fix the reported document or link before re-running.

To restore earlier site content, revert the relevant documentation commit through the normal `dev` review process. Do not rewrite `main` or force-push a deployment branch.
