"""Manage an isolated local simulator with a scripted LLM endpoint, no API key."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(os.environ.get("MOOS_IVP_WSL_ROOT", Path.home() / "Projects/moos-ivp-wsl"))
BASE = ROOT / "moos-ivp"
RUNS = ROOT / "runs"
STATE = RUNS / "current.json"
PORT = int(os.environ.get("MOOS_IVP_WSL_PORT", "19841"))
API_PORT = PORT + 1


def env():
    result = os.environ.copy()
    result["PATH"] = f"{BASE}/bin:{ROOT}/moos-ivp-mctf/bin:" + result["PATH"]
    result["IVP_BEHAVIOR_DIRS"] = f"{BASE}/lib:{ROOT}/moos-ivp-mctf/lib"
    result["LD_LIBRARY_PATH"] = str(BASE / "build/MOOS/MOOSGeodesy/lib")
    result["ANTHROPIC_API_KEY"] = "local-stand-in-only"
    result["MOOSIVP_IMAGE_DIR"] = str(BASE / "ivp/data")
    return result


def stamp(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().split()[21]
    except (FileNotFoundError, IndexError):
        return None


def current():
    return json.loads(STATE.read_text()) if STATE.exists() else None


def ports_available(ports):
    for port in ports:
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                return False
    return True


def stop():
    state = current()
    if not state:
        print("No setup demo has been started.")
        return
    for item in reversed(state["processes"]):
        pid = item["pid"]
        try:
            if item["start"] is not None and stamp(pid) == item["start"] and os.getpgid(pid) == pid:
                os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 5
    while not ports_available(state.get("ports", [PORT, API_PORT])):
        if time.monotonic() >= deadline:
            raise RuntimeError("Demo ports are still occupied; state was retained. Check the logs and retry Stop.")
        time.sleep(0.05)
    STATE.unlink(missing_ok=True)
    print(f"Stopped setup demo; logs retained in {state['directory']}")


def query(directory, condition, seconds=15):
    return subprocess.run(
        [str(BASE / "bin/uQueryDB"), "alpha.moos", f"--condition={condition}",
         f"--wait={seconds * 5}"], cwd=directory, env=env(),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=seconds + 15)


def poke(directory, *values):
    result = subprocess.run([str(BASE / "bin/uPokeDB"), "alpha.moos", *values],
                            cwd=directory, env=env(), capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)


def start(headless=False):
    if current() and any(stamp(p["pid"]) == p["start"] for p in current()["processes"]):
        raise RuntimeError("A setup demo is already running. Stop it first.")
    for port in (PORT, API_PORT):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))
    RUNS.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=time.strftime("alpha-%Y%m%d-%H%M%S-"), dir=RUNS))
    shutil.copytree(BASE / "ivp/missions/s1_alpha_llm", directory, dirs_exist_ok=True)
    mission = directory / "alpha.moos"
    text = mission.read_text()
    text = re.sub(r"(?m)^ServerPort\s*=.*$", f"ServerPort = {PORT}", text)
    text = re.sub(r"(?m)^MOOSTimeWarp\s*=.*$", "MOOSTimeWarp = 5", text)
    text, configured = re.subn(r"(?m)^(ProcessConfig\s*=\s*pLLMAgent\s*\n\s*\{)",
                              rf"\1\n  api_url = localhost:{API_PORT}/v1/messages", text)
    if configured != 1:
        raise RuntimeError("Expected one pLLMAgent block; refusing to launch without a local API override.")
    text = re.sub(r"(?m)^\s*api_url\s*=.*$", f"  api_url = localhost:{API_PORT}/v1/messages", text)
    if headless:
        text = re.sub(r"(?m)^\s*Run\s*=\s*(pMarineViewer|uButtonPanel)\b.*$", "", text)
    mission.write_text(text)
    processes = []
    state = {"directory": str(directory), "headless": headless, "ports": [PORT, API_PORT], "processes": processes}
    try:
        commands = [
            ("standin.log", [sys.executable, str(Path(__file__).with_name("standin.py")),
                             "--port", str(API_PORT), "--output", str(directory / "standin")]),
            ("antler.log", [str(BASE / "bin/pAntler"), str(mission)]),
        ]
        for log, command in commands:
            with (directory / log).open("w") as stream:
                process = subprocess.Popen(command, cwd=directory, env=env(), stdin=subprocess.DEVNULL,
                                           stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            processes.append({"pid": process.pid, "start": stamp(process.pid)})
            STATE.parent.mkdir(parents=True, exist_ok=True)
            STATE.write_text(json.dumps(state, indent=2))
        result = query(directory, "LLM_STATUS = idle", 25)
        (directory / "startup-query.log").write_text(result.stdout)
        if result.returncode:
            raise RuntimeError(f"Simulator did not become ready. See {directory}/antler.log")
    except BaseException:
        stop()
        raise
    print(f"Started {'headless' if headless else 'GUI'} simulator: {directory}")
    print(f"MOOSDB: localhost:{PORT}; LLM endpoint: local stand-in only")
    return directory


def verify(output):
    existing = current()
    if existing and any(stamp(item["pid"]) == item["start"] for item in existing["processes"]):
        print("Stop the active demo before running Verify; it has been left running.", file=sys.stderr)
        return 2
    output.mkdir(parents=True, exist_ok=True)
    results = []
    names = ["cap_selftest", "field_selftest", "bt_selftest", "dyn_selftest",
             "history_selftest", "llm_selftest"]
    for optional in ("intercept_selftest", "return_selftest", "testmode_selftest"):
        if (ROOT / "moos-ivp-mctf/bin" / optional).is_file():
            names.append(optional)
    for name in names:
        started = time.monotonic()
        completed = subprocess.run([name], cwd=output, env=env(), capture_output=True, text=True, timeout=180)
        (output / f"{name}.log").write_text(completed.stdout + completed.stderr)
        results.append({"name": name, "pass": completed.returncode == 0,
                        "exit_code": completed.returncode, "seconds": round(time.monotonic() - started, 2)})
        print(f"{'PASS' if completed.returncode == 0 else 'FAIL'} {name}", flush=True)
    owns_demo = False
    try:
        directory = start(headless=True)
        owns_demo = True
        for name, condition, action in (
            ("simulator publishes position", "NAV_X >= 0", None),
            ("LLM asks for confirmation", "LLM_STATUS = awaiting_confirm",
             lambda: poke(directory, "LLM_CHAT_IN:=setup smoke goto")),
            ("approved command moves the simulated boat", "NAV_X > 3",
             lambda: poke(directory, "LLM_CHAT_IN:=y")),
            ("behavior tree executes through MOOSDB", "SETUP_BT = passed",
             lambda: poke(directory, 'BT_TREE:=<root BTCPP_format="4" main_tree_to_execute="MainTree"><BehaviorTree ID="MainTree"><Sequence><Wait sec="1"/><Post var="SETUP_BT" val="passed"/></Sequence></BehaviorTree></root>')),
        ):
            if action:
                action()
            checked = query(directory, condition)
            (output / f"smoke-{len(results)}.log").write_text(checked.stdout)
            results.append({"name": name, "pass": checked.returncode == 0,
                            "exit_code": checked.returncode, "condition": condition})
            print(f"{'PASS' if checked.returncode == 0 else 'FAIL'} {name}", flush=True)
            if checked.returncode:
                break
    except Exception as error:
        results.append({"name": "live simulator", "pass": False, "error": str(error)})
        print(f"FAIL live simulator: {error}", flush=True)
    finally:
        if owns_demo:
            stop()
        (output / "verification.json").write_text(json.dumps(results, indent=2))
    return 0 if all(row["pass"] for row in results) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "stop", "status", "verify"))
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "verification")
    args = parser.parse_args()
    if args.action == "start":
        start(args.headless)
    elif args.action == "stop":
        stop()
    elif args.action == "status":
        print(json.dumps(current(), indent=2))
    else:
        return verify(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
