"""Create Linux working copies from Git objects already fetched on Windows."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess


def git(*args):
    return subprocess.check_output(["git", *map(str, args)], text=True).strip()


def local_path(value, parent):
    value = value.strip()
    if re.match(r"^[A-Za-z]:[/\\]", value):
        return Path(subprocess.check_output(["wslpath", "-u", value], text=True).strip())
    path = Path(value)
    return path if path.is_absolute() else (parent / path).resolve()


def git_dir(source):
    marker = source / ".git"
    if marker.is_dir():
        return marker.resolve()
    if marker.is_file():
        value = marker.read_text().strip()
        if value.startswith("gitdir: "):
            return local_path(value[len("gitdir: "):], source)
    raise RuntimeError(f"Not an initialized Git checkout: {source}")


def clone(source_objects, destination, revision):
    git(f"--git-dir={source_objects}", "cat-file", "-e", f"{revision}^{{commit}}")
    if (destination / ".git").exists():
        if git("-C", destination, "rev-parse", "HEAD") != revision:
            raise RuntimeError(f"{destination} is at another commit. Use a new InstallRoot or update that working copy explicitly; no reset was performed.")
        return
    subprocess.run(["git", "clone", "--no-hardlinks", "--no-checkout", "--config", "core.autocrlf=false",
                    "--config", "core.symlinks=true", str(source_objects), str(destination)], check=True)
    subprocess.run(["git", "-C", str(destination), "checkout", "--detach", revision], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--without-squad", action="store_true")
    parser.add_argument("--mctf-source", type=Path)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    objects = git_dir(args.source.resolve())
    common_marker = objects / "commondir"
    common = local_path(common_marker.read_text(), objects) if common_marker.exists() else objects
    revision = git(f"--git-dir={objects}", "rev-parse", "HEAD")
    modules = []
    for line in git(f"--git-dir={objects}", "ls-tree", "-r", revision).splitlines():
        metadata, path = line.split("\t", 1)
        mode, kind, commit = metadata.split()
        if mode != "160000":
            continue
        if path == "ivp/src/moos-ivp-squad" and args.without_squad:
            continue
        candidates = (objects / "modules" / path, common / "modules" / path)
        module_objects = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
        if not module_objects.exists():
            raise RuntimeError(f"Missing objects for {path}. Initialize that submodule with Windows Git first. For squad only, -WithoutSquad is available.")
        git(f"--git-dir={module_objects}", "cat-file", "-e", f"{commit}^{{commit}}")
        modules.append((path, module_objects, commit))
    if "ivp/src/moos-ivp-llm" not in {path for path, _, _ in modules}:
        raise RuntimeError("This demo requires the dev integration and its extension submodules.")
    clone(objects, root / "moos-ivp", revision)
    for path, module_objects, commit in modules:
        clone(module_objects, root / "moos-ivp" / path, commit)
    manifest = {"base": revision, "squad": not args.without_squad,
                "submodules": {path: commit for path, _, commit in modules}}
    if args.mctf_source:
        mctf_objects = git_dir(args.mctf_source.resolve())
        mctf_revision = git(f"--git-dir={mctf_objects}", "rev-parse", "HEAD")
        clone(mctf_objects, root / "moos-ivp-mctf", mctf_revision)
        manifest["mctf"] = mctf_revision
    (root / "source-manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Linux working copy: {root}")


if __name__ == "__main__":
    main()
