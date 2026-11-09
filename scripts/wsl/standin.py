"""Local scripted Messages API stand-in for the single-vehicle setup demo."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--port", type=int, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)


class Handler(BaseHTTPRequestHandler):
    count = 0

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 4 * 1024 * 1024:
            self.send_error(400, "Invalid request length")
            return
        try:
            request = json.loads(self.rfile.read(length))
        except (ValueError, TypeError):
            self.send_error(400, "Invalid JSON")
            return
        Handler.count += 1
        (args.output / f"request-{Handler.count}.json").write_text(json.dumps(request, indent=2))
        last = next((item.get("content", "") for item in reversed(request.get("messages", []))
                     if item.get("role") == "user"), "")
        blocks = last if isinstance(last, list) else [{"type": "text", "text": str(last)}]
        text = " ".join(item.get("text", "") for item in blocks).lower()
        reply = "This is a local scripted demo, not a live model. Type 'setup smoke goto' to propose a simulated move, then 'y' to approve."
        content = [{"type": "text", "text": reply}]
        reason = "end_turn"
        if any(item.get("type") == "tool_result" for item in blocks):
            content = [{"type": "text", "text": "The simulated command was submitted."}]
        elif "setup smoke goto" in text:
            content = [{"type": "text", "text": "Proposing a local simulated move."},
                       {"type": "tool_use", "id": f"setup-{Handler.count}", "name": "goto",
                        "input": {"x": 20, "y": -20}}]
            reason = "tool_use"
        response = {"id": f"local-{Handler.count}", "type": "message", "role": "assistant",
                    "model": "local-scripted-standin", "content": content, "stop_reason": reason,
                    "usage": {"input_tokens": 0, "output_tokens": 0}}
        data = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
