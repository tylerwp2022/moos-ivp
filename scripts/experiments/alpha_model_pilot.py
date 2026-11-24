#!/usr/bin/env python3
"""Compare text-to-plan drafts against the single-vehicle alpha simulator.

Timeo Williams, 2026-11-24: Added the alpha model pilot runner.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import statistics
import subprocess
import time
from urllib import error, request
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MISSION = REPO / "ivp/missions/s1_alpha_llm"
MODELS = {
    "gpt-5-nano-2025-08-07": (0.05, 0.40),
    "gpt-6-luna": (0.10, 0.50),
    "gpt-6.1-sol": (2.00, 10.00),
    "gpt-6.2-astra": (8.00, 40.00),
}
NANO_FALLBACK = "gpt-5.4-nano-2026-03-17"
RATES = {**MODELS, NANO_FALLBACK: (0.20, 1.25)}
WARP = 5
INPUT_LIMIT = 2048
MAX_OUTPUT = 4000
BUDGET = 2.0
GRACE = 3.0  # Simulation seconds allowed for mail and helm tick scheduling.

BRIEF = """Draft a plan for the offline, single-boat alpha simulator. Distances are local meters,
headings degrees, durations seconds, and speeds m/s. Home is the launch position (0,-20).
The default waypoint speed is 2 m/s. There are no peripherals or location aliases.
Reply with one JSON object with exactly keys status, xml, message and no Markdown.
Use status plan with an XML string and null message, or status clarify or unsupported
with null xml and a specific question or explanation in message. For an unsupported
capability, explain what alpha cannot do. Ask when required information is missing.
For XML use <root BTCPP_format="4" main_tree_to_execute="MainTree"> containing one
<BehaviorTree ID="MainTree">. Use Sequence for ordered steps and Fallback to try
children in order until one succeeds. The allowed leaves and attributes are:
  Goto x y [timeout], blocks until arrival at the default 2 m/s.
  Wait sec, waits for that duration.
  Ask msg [timeout], blocks and succeeds on yes, fails on no or timeout.
  Say msg, emits a message and succeeds.
  Loiter x y radius clockwise speed, StationKeep x y, HoldHeading heading speed,
  start drivers immediately. Use true or false for clockwise. Follow them with Wait
  when a duration is required. Return [timeout] goes home and blocks until arrival.
  Goto waypoint legs, Loiter, StationKeep and HoldHeading supersede the prior driver.
No other tags, variables or attributes. Supply literal numbers. Never assume a
missing location or capability. The following user request is the whole task."""

# Restrict only generated drafts. The repository's saved control plans are trusted fixtures.
XML_ATTRS = {
    "root": {"BTCPP_format", "main_tree_to_execute"}, "BehaviorTree": {"ID"},
    "Sequence": set(), "Fallback": set(), "Goto": {"x", "y", "timeout"},
    "Wait": {"sec"}, "Ask": {"msg", "timeout"}, "Say": {"msg"},
    "Loiter": {"x", "y", "radius", "clockwise", "speed"}, "StationKeep": {"x", "y"},
    "HoldHeading": {"heading", "speed"}, "Return": {"timeout"},
}
BOUNDS = {
    "x": (-100, 120), "y": (-150, 0), "speed": (0.1, 2),
    "radius": (5, 30), "heading": (0, 360), "timeout": (1, 600), "sec": (0, 120),
}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    pending.replace(path)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_commit(path):
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def freeze(output):
    path = output / "protocol.json"
    if path.exists():
        return read_json(path)
    fixtures = read_json(HERE / "alpha_cases.json")
    hashes = {str(path.relative_to(MISSION)): sha256(path) for path in MISSION.rglob("*") if path.is_file()}
    protocol = {
        **fixtures, "brief": BRIEF, "model_ids": list(MODELS), "reasoning_effort": "low",
        "max_output_tokens": MAX_OUTPUT, "input_limit": INPUT_LIMIT, "spend_limit_usd": BUDGET,
        "mission_file_sha256": hashes, "repository_commit": git_commit(REPO),
        "runner_sha256": sha256(Path(__file__)), "time_warp": WARP,
        "human_owner": "Timeo Williams", "acting_agent": "Cline/ChatGPT",
    }
    write_json(path, protocol)
    return protocol


def plain_response(body):
    parts = [part for item in body.get("output", []) for part in item.get("content", [])]
    if any(part.get("type") == "refusal" for part in parts):
        raise ValueError("API refusal")
    return "".join(part["text"] for part in parts if part.get("type") == "output_text")


def draft_response(text):
    try:
        draft = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Response is not a JSON object") from exc
    if not isinstance(draft, dict) or draft.keys() != {"status", "xml", "message"}:
        raise ValueError("Response does not match the requested fields")
    if draft["status"] == "plan" and isinstance(draft["xml"], str) and draft["xml"].strip() and draft["message"] is None:
        return draft
    if draft["status"] in ("clarify", "unsupported") and draft["xml"] is None:
        if isinstance(draft["message"], str) and draft["message"].strip():
            return draft
    raise ValueError("Response fields do not match its status")


def permitted_xml(xml):
    if len(xml) > 16_000 or re.search(r"<!DOCTYPE|<!ENTITY", xml, re.I):
        raise ValueError("XML size limit or document declaration")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML at {exc.position}") from exc
    if root.tag != "root" or root.attrib != {"BTCPP_format": "4", "main_tree_to_execute": "MainTree"}:
        raise ValueError("Expected the alpha MainTree root declaration")
    if len(root) != 1 or root[0].tag != "BehaviorTree" or root[0].attrib != {"ID": "MainTree"} or len(root[0]) != 1:
        raise ValueError("Expected exactly one MainTree with one root node")
    for index, node in enumerate(root.iter()):
        if index >= 40 or node.tag not in XML_ATTRS or node.attrib.keys() - XML_ATTRS[node.tag]:
            raise ValueError(f"Node outside the alpha pilot grammar: {node.tag}")
        if node.tag not in {"root", "BehaviorTree", "Sequence", "Fallback"} and len(node):
            raise ValueError(f"Unexpected children under {node.tag}")
        for name, value in node.attrib.items():
            if name in BOUNDS:
                low, high = BOUNDS[name]
                try:
                    number = float(value)
                except ValueError as exc:
                    raise ValueError(f"{name} must be a literal number") from exc
                if not math.isfinite(number) or not low <= number <= high:
                    raise ValueError(f"{name} outside the alpha pilot limits")
            if name == "msg" and (len(value) > 160 or any(c in value for c in "\n\r")):
                raise ValueError("Message exceeds the alpha pilot limits")
            if name == "clockwise" and value not in {"true", "false"}:
                raise ValueError("Clockwise must be true or false")


def cost(model, input_tokens, output_tokens):
    input_rate, output_rate = RATES[model]
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000


def call_model(key, model, protocol, case):
    payload = {
        "model": model, "store": False, "service_tier": "default",
        "max_output_tokens": protocol["max_output_tokens"],
        "reasoning": {"effort": protocol["reasoning_effort"]},
        "instructions": protocol["brief"], "input": case["request"],
    }
    if len((payload["instructions"] + payload["input"]).encode("utf-8")) > INPUT_LIMIT - 128:
        raise ValueError("Prompt exceeded the pilot's conservative input allowance")
    call = request.Request("https://api.openai.com/v1/responses", data=json.dumps(payload).encode(),
                           headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    started = time.monotonic()
    result = {"requested_model": model, "case": case["id"], "request": payload}
    try:
        with request.urlopen(call, timeout=150) as response:
            result.update(http=response.status, body=json.load(response))
    except error.HTTPError as exc:
        with exc:
            try:
                body = json.load(exc)
            except ValueError:
                body = {}
        api_error = body.get("error") if isinstance(body, dict) else None
        result.update(http=exc.code, api_code=(api_error or {}).get("code"),
                      failure="HTTP error " + str(exc.code))
    except (error.URLError, TimeoutError, ValueError) as exc:
        result["failure"] = "Transport or response error: " + type(exc).__name__
        result["billable_limit"] = cost(model, INPUT_LIMIT, MAX_OUTPUT)
    result["latency_seconds"] = round(time.monotonic() - started, 3)
    body = result.get("body", {})
    if body.get("usage"):
        tokens = body["usage"]
        result["estimated_cost_usd"] = cost(model, tokens["input_tokens"], tokens["output_tokens"])
        writes = tokens.get("input_tokens_details", {}).get("cache_write_tokens", 0)
        result["estimated_cost_usd"] += cost(model, writes * 0.25, 0)
    if result.get("http") == 200:
        if body.get("status") != "completed":
            result["failure"] = "API status " + str(body.get("status"))
        try:
            result["draft"] = draft_response(plain_response(body))
        except ValueError as exc:
            result["format_error"] = str(exc)
    return result


def model_results(output):
    return [read_json(path) for path in sorted((output / "responses").glob("*/*.json"))]


def generate(output, protocol):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("Load the existing project key into OPENAI_API_KEY for this process.")
    for slot in protocol["model_ids"]:
        selected = slot
        for case in protocol["cases"]:
            path = output / "responses" / slot / (case["id"] + ".json")
            if path.exists():
                selected = read_json(path)["requested_model"]
                continue
            existing = model_results(output)
            spent = sum(row.get("estimated_cost_usd", row.get("billable_limit", 0)) for row in existing)
            reserve = max(cost(selected, INPUT_LIMIT * 1.25, MAX_OUTPUT), cost(NANO_FALLBACK, INPUT_LIMIT * 1.25, MAX_OUTPUT))
            if spent + reserve > protocol["spend_limit_usd"]:
                print("Stopped at the reserved API spend limit.", flush=True)
                return
            result = call_model(key, selected, protocol, case)
            if selected == "gpt-5-nano-2025-08-07" and result.get("http") in (403, 404) and result.get("api_code") == "model_not_found":
                selected = NANO_FALLBACK
                first_attempt = result
                result = call_model(key, selected, protocol, case)
                result["fallback_from"] = first_attempt
            result["model_slot"] = slot
            write_json(path, result)
            print(f"{selected} {case['id']}: {result.get('failure', result.get('format_error', 'response received'))}", flush=True)
            if result.get("http") in (401, 429) or "billable_limit" in result:
                print("Stopped after a project, rate-limit, or transport error. Existing responses were saved.", flush=True)
                return


def tool_env(base):
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env.pop("ANTHROPIC_API_KEY", None)
    env["PATH"] = str(base / "bin") + os.pathsep + env["PATH"]
    env["IVP_BEHAVIOR_DIRS"] = str(base / "lib")
    env["LD_LIBRARY_PATH"] = str(base / "build/MOOS/MOOSGeodesy/lib") + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    return env


def invoke(base, cwd, command, *args, timeout=20):
    return subprocess.run([str(base / "bin" / command), *args], cwd=cwd, env=tool_env(base),
                          capture_output=True, text=True, timeout=timeout, check=False)


def prepare_mission(directory, port):
    shutil.copytree(MISSION, directory, dirs_exist_ok=True)
    config = directory / "alpha.moos"
    text = config.read_text(encoding="utf-8")
    replacements = {"ServerPort": port, "MOOSTimeWarp": WARP}
    for key, value in replacements.items():
        text, count = re.subn(rf"(?m)^{key}\s*=.*$", f"{key} = {value}", text)
        if count != 1:
            raise ValueError(f"Expected one {key} entry")
    enabled = {"MOOSDB", "pLogger", "uSimMarineV22", "pMarinePIDV22", "pHelmIvP", "pBehaviorTree", "uDynamicsTest"}
    text = re.sub(r"(?m)^[ \t]*Run\s*=\s*(\w+)[^\n]*\n",
                  lambda match: match[0] if match[1] in enabled else "", text)
    logger = "\n".join(f"  Log = {var} @ 0 NOSYNC" for var in
                       ("BT_CHAT", "BT_STATE", "BT_EVENT", "BT_REPLY", "TASK", "RETURN", "WPT_UPDATE"))
    text = text.replace("  LogAuxSrc = true", logger + "\n  LogAuxSrc = true", 1)
    config.write_text(text, encoding="utf-8")


@contextmanager
def simulator(base, directory):
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        prepare_mission(directory, reserve.getsockname()[1])
    with (directory / "antler.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([str(base / "bin/pAntler"), "alpha.moos"], cwd=directory,
                                   env=tool_env(base), stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            yield
        finally:
            # Stop only the process group created for this replay.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)


def query(base, directory, label, condition, duration):
    result = invoke(base, directory, "uQueryDB", "alpha.moos", "--unique",
                    f"--condition={condition}", f"--wait={duration}", timeout=duration / WARP + 18)
    (directory / f"{label}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    return result.returncode == 0


def poke(base, directory, *args):
    result = invoke(base, directory, "uPokeDB", "alpha.moos", *args)
    with (directory / "operator.log").open("a", encoding="utf-8") as log:
        log.write(result.stdout + result.stderr)
    if result.returncode != 0:
        raise RuntimeError("uPokeDB failed; see operator.log")


def trace(directory):
    logs = sorted(directory.rglob("*.alog"))
    if len(logs) != 1:
        raise ValueError(f"Expected one alpha alog; found {len(logs)}")
    wanted = {"BT_CHAT", "BT_STATE", "BT_EVENT", "BT_REPLY", "BT_TREE_FILE", "MISSION",
              "NAV_X", "NAV_Y", "TASK", "RETURN", "WPT_UPDATE", "LOITER_UPDATE",
              "STATION_UPDATE", "HEADING_UPDATE", "HEADING_SPEED_UPDATE"}
    events = {}
    with logs[0].open(encoding="utf-8", errors="replace") as lines:
        for line in lines:
            fields = line.split(maxsplit=3)
            if len(fields) == 4 and fields[1] in wanted:
                stamp, name, source, value = fields
                event = (float(stamp), source, value.strip())
                if event not in events.setdefault(name, {}):
                    events[name][event] = None
    return {name: sorted(values) for name, values in events.items()}


def timed(events, name, value):
    return [stamp for stamp, _, payload in events.get(name, []) if payload == value]


def score_trace(case, answer, events):
    errors = []
    start = next(iter(timed(events, "BT_STATE", "running")), -1)
    finish = next(iter(timed(events, "BT_STATE", "success")), -1)
    home = [t for t in timed(events, "MISSION", "return_complete") if start <= t <= finish]
    if start < 0 or finish < 0 or not home:
        return ["The plan did not reach executor success and fresh return_complete"]
    x, y, positions = None, None, []
    for stamp, axis, value in sorted((entry[0], axis, float(entry[2])) for axis in ("NAV_X", "NAV_Y")
                                    for entry in events.get(axis, [])):
        if axis == "NAV_X":
            x = value
        else:
            y = value
        if start <= stamp <= finish and x is not None and y is not None:
            positions.append((stamp, x, y))
    points = case.get("waypoints", [])
    after = start
    reached = []
    asks = [t for t, src, _ in events.get("BT_CHAT", []) if "ask," in src and start <= t <= finish]
    replies = [t for t in timed(events, "BT_REPLY", answer) if start <= t <= finish] if answer else []
    for index, (px, py) in enumerate(points):
        matches = [t for t, x, y in positions if t >= after and math.hypot(x - px, y - py) <= 12]
        if answer == "no" and index == 1:
            if matches or any(re.search(r"points\s*=\s*80(?:\.0+)?\s*,\s*-60(?:\.0+)?(?:\D|$)", value)
                              for stamp, _, value in events.get("WPT_UPDATE", []) if start <= stamp <= finish):
                errors.append("The second waypoint was commanded or visited after no")
            break
        if not matches:
            errors.append(f"The trace missed waypoint {index + 1} at ({px}, {py}) in order")
            break
        reached.append(matches[0])
        after = matches[0]
    if answer and (not reached or len(asks) != 1 or len(replies) != 1 or not reached[0] <= asks[0] <= replies[0] <= home[0]):
        errors.append("Missing or out-of-order permission question/reply evidence")
    if answer == "yes" and len(reached) == 2 and replies and reached[1] < replies[0]:
        errors.append("The boat reached the second waypoint before yes")
    returns = [t for t in timed(events, "RETURN", "true") if start <= t <= finish]
    waypoint_done = [t for t in timed(events, "MISSION", "goto_complete") if start <= t <= finish]
    if case.get("hold") and (not returns or not waypoint_done or abs(returns[0] - waypoint_done[-1] - case["hold"]) > GRACE):
        errors.append("The hold between the survey completing and return was outside 15 ± 3 seconds")
    if case.get("drivers"):
        transitions = []
        for stamp, _, value in events.get("TASK", []):
            if start - GRACE <= stamp <= finish and value in {name for name, _ in case["drivers"]}:
                if not transitions or value != transitions[-1][1]:
                    transitions.append((stamp, value))
        if [name for _, name in transitions] != [name for name, _ in case["drivers"]] or not returns:
            errors.append("The three helm drivers did not activate in the requested order")
        else:
            ends = [stamp for stamp, _ in transitions[1:]] + [returns[0]]
            for (stamp, driver), end, (_, duration) in zip(transitions, ends, case["drivers"]):
                if abs(end - stamp - duration) > GRACE:
                    errors.append(f"{driver} lasted {end - stamp:.1f} s, expected {duration} s")
        for variable, settings in case["driver_mail"].items():
            values = [re.sub(r"(?<=\d)\.0+(?=\D|$)", "", value) for stamp, _, value in events.get(variable, [])
                      if start - GRACE <= stamp <= finish]
            if not any(all(re.search(r"(?:^|[,#\s])" + re.escape(setting) + r"(?=$|[,#\s])", value)
                           for setting in settings) for value in values):
                errors.append(f"{variable} did not carry the requested parameters")
    return errors


def replay_one(base, directory, case, answer, xml, control):
    directory.mkdir(parents=True, exist_ok=True)
    file = directory / "candidate.xml"
    file.write_text(xml, encoding="utf-8")
    outcome = {"case": case["id"], "answer": answer, "phase": "validation"}
    try:
        if not control:
            permitted_xml(xml)
        validation = invoke(base, directory, "pBehaviorTree", "--check=candidate.xml")
        (directory / "validation.log").write_text(validation.stdout + validation.stderr, encoding="utf-8")
        if validation.returncode != 0:
            raise ValueError("pBehaviorTree rejected the XML")
        outcome["phase"] = "simulator"
        with simulator(base, directory):
            if not query(base, directory, "ready", "(NAV_X >= -1000) and (BT_STATE = idle)", 100):
                raise RuntimeError("The simulator did not report ready")
            # The saved raw-waypoint tree assumes the waypoint driver is selected.
            poke(base, directory, "TASK=waypoint", "BT_TREE_FILE:=candidate.xml")
            if answer:
                if not query(base, directory, "question", 'BT_CHAT != ""', case["timeout"]):
                    raise RuntimeError("The simulator did not publish a chat line")
                deadline = time.monotonic() + case["timeout"] / WARP
                while time.monotonic() < deadline:
                    try:
                        if any("ask," in src for _, src, _ in trace(directory).get("BT_CHAT", [])):
                            break
                    except ValueError:
                        pass
                    time.sleep(0.25)
                else:
                    raise RuntimeError("No executor question was logged")
                poke(base, directory, f"BT_REPLY:={answer}")
            if not query(base, directory, "terminal", "((BT_STATE = success) or ((BT_STATE = failure) or (BT_STATE = halted)))", case["timeout"]):
                raise RuntimeError("The executor did not reach a terminal state within the replay window")
            time.sleep(1)
        outcome["phase"] = "scoring"
        outcome["errors"] = score_trace(case, answer, trace(directory))
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        outcome["errors"] = [str(exc)]
    outcome["passed"] = not outcome["errors"]
    write_json(directory / "result.json", outcome)
    print(f"{'PASS' if outcome['passed'] else 'FAIL'} {directory.parent.name}/{directory.name}: {'; '.join(outcome['errors'])}", flush=True)
    return outcome


def run_replays(output, protocol, base, controls, jobs):
    for program in ("pBehaviorTree", "pAntler", "MOOSDB", "uQueryDB", "uPokeDB"):
        if not os.access(base / "bin" / program, os.X_OK):
            raise SystemExit(f"Missing executable {base / 'bin' / program}")
    for relative, digest in protocol["mission_file_sha256"].items():
        if sha256(MISSION / relative) != digest:
            raise SystemExit(f"Mission changed after the protocol was frozen: {relative}")
    runtime_path = output / "runtime.json"
    runtime = {"repository_commit": git_commit(base), "pBehaviorTree_sha256": sha256(base / "bin/pBehaviorTree"),
               "pAntler_sha256": sha256(base / "bin/pAntler")}
    if runtime_path.exists() and read_json(runtime_path) != runtime:
        raise SystemExit("Simulator runtime changed since this pilot started")
    write_json(runtime_path, runtime)
    cases = {case["id"]: case for case in protocol["cases"]}
    work = []
    if controls:
        for case in cases.values():
            if "reference" in case:
                xml = (MISSION / "plans" / case["reference"]).read_text(encoding="utf-8")
                if case.get("reference_loiter_attributes"):
                    # The checked-in tour omits inputs required by the installed Loiter leaf.
                    root = ET.fromstring(xml)
                    node = root.find(".//Loiter")
                    for name, value in case["reference_loiter_attributes"].items():
                        node.attrib.setdefault(name, value)
                    xml = ET.tostring(root, encoding="unicode")
                work.extend(("controls", case, answer, xml) for answer in case["answers"])
    else:
        for result in model_results(output):
            case = cases[result["case"]]
            draft = result.get("draft", {})
            if not result.get("failure") and draft.get("status") == case["expected"] == "plan":
                work.extend(("replays/" + result["model_slot"], case, answer, draft["xml"]) for answer in case["answers"])
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = []
        for stage, case, answer, xml in work:
            directory = output / stage / (case["id"] + ("-" + answer if answer else ""))
            if (directory / "result.json").exists():
                continue
            if directory.exists():
                raise SystemExit(f"Partial replay exists at {directory}; preserve it before retrying.")
            futures.append(pool.submit(replay_one, base, directory, case, answer, xml, controls))
        for future in futures:
            future.result()


def report(output, protocol):
    controls = [read_json(path) for path in sorted(output.glob("controls/*/result.json"))]
    results = model_results(output)
    rows = []
    for slot in protocol["model_ids"]:
        for case in protocol["cases"]:
            result = next((result for result in results if result["model_slot"] == slot and result["case"] == case["id"]), {})
            draft = result.get("draft", {})
            model = result.get("requested_model", slot)
            validation = None
            status = result.get("failure") or result.get("format_error")
            passed = None
            if not result:
                status = "no response"
            elif not status and draft.get("status") != case["expected"]:
                passed, status = False, "expected " + case["expected"] + "; got " + str(draft.get("status"))
            elif not status and case["expected"] == "plan":
                directories = [output / "replays" / slot / (case["id"] + ("-" + answer if answer else ""))
                               for answer in case["answers"]]
                replays = [read_json(path / "result.json") for path in directories if (path / "result.json").exists()]
                if len(replays) == len(directories):
                    validation = all(replay["phase"] != "validation" for replay in replays)
                    errors = [error for replay in replays for error in replay["errors"]]
                    passed, status = not errors, "; ".join(dict.fromkeys(errors)) or "executed as requested"
                else:
                    status = "simulator replay pending"
            elif not status:
                message = draft["message"].lower()
                passed = any(term in message for term in case["message_terms"])
                status = draft["message"]
            usage = result.get("body", {}).get("usage", {})
            rows.append({"model": model, "case": case["id"], "expected": case["expected"],
                         "passed": passed, "validated": validation, "detail": status,
                         "api_completed": result.get("body", {}).get("status") == "completed",
                         "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
                         "latency_seconds": result.get("latency_seconds"),
                         "estimated_cost_usd": result.get("estimated_cost_usd")})
    models = []
    for model in dict.fromkeys(row["model"] for row in rows):
        selected = [row for row in rows if row["model"] == model]
        times = [row["latency_seconds"] for row in selected if row["api_completed"]]
        models.append({"model": model, "planned_cases": len(selected),
                       "api_completed": sum(row["api_completed"] for row in selected),
                       "valid_drafts": sum(row["validated"] is True for row in selected),
                       "missions_as_requested": sum(row["passed"] is True and row["expected"] == "plan" for row in selected),
                       "correct_clarify_or_unsupported": sum(row["passed"] is True and row["expected"] != "plan" for row in selected),
                       "median_api_seconds": round(statistics.median(times), 3) if times else None,
                       "input_tokens": sum(row["input_tokens"] or 0 for row in selected),
                       "output_tokens": sum(row["output_tokens"] or 0 for row in selected),
                       "estimated_cost_usd": round(sum(row["estimated_cost_usd"] or 0 for row in selected), 6)})
    write_json(output / "summary.json", {"controls": controls, "models": models, "cases": rows,
               "reporter_sha256": sha256(Path(__file__))})
    print(json.dumps(models, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("controls", "generate", "replay", "report"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base", type=Path, help="Built MOOS-IvP checkout in Linux/WSL")
    parser.add_argument("--jobs", type=int, default=3, choices=range(1, 5))
    args = parser.parse_args()
    output = args.output.resolve()
    protocol = freeze(output)
    if args.stage in {"controls", "replay"}:
        if not args.base or os.name != "posix":
            parser.error("Simulator stages require Linux/WSL and --base")
        run_replays(output, protocol, args.base.resolve(), args.stage == "controls", args.jobs)
    elif args.stage == "generate":
        generate(output, protocol)
    else:
        report(output, protocol)


if __name__ == "__main__":
    main()
