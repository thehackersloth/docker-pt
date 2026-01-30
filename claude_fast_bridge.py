#!/usr/bin/env python3
"""
Fast Claude bridge using persistent subprocess
Keeps claude running and pipes commands to it
"""

import subprocess
import threading
import queue
import json
import time
import logging
import re
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Persistent claude process
claude_process = None
response_queue = queue.Queue()
current_response = []
response_complete = threading.Event()


def read_claude_output(proc):
    """Read output from claude process"""
    global current_response
    buffer = ""

    while True:
        try:
            char = proc.stdout.read(1)
            if not char:
                break
            buffer += char

            # Check for prompt indicating response is complete
            # Claude shows "> " when ready for input
            if buffer.endswith("\n> ") or buffer.endswith("\n❯ "):
                # Response complete
                response = buffer.rsplit("\n> ", 1)[0].rsplit("\n❯ ", 1)[0]
                current_response.append(response)
                response_complete.set()
                buffer = ""
        except Exception as e:
            logger.error(f"Read error: {e}")
            break


def start_claude():
    """Start persistent claude process"""
    global claude_process

    try:
        claude_process = subprocess.Popen(
            ['claude', '--no-session-persistence'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Start output reader thread
        reader = threading.Thread(target=read_claude_output, args=(claude_process,), daemon=True)
        reader.start()

        # Wait for initial prompt
        time.sleep(3)
        logger.info("Claude process started")
        return True
    except Exception as e:
        logger.error(f"Failed to start claude: {e}")
        return False


def send_prompt(prompt):
    """Send prompt to claude and get response"""
    global current_response

    if not claude_process or claude_process.poll() is not None:
        start_claude()

    current_response = []
    response_complete.clear()

    try:
        # Send prompt
        claude_process.stdin.write(prompt + "\n")
        claude_process.stdin.flush()

        # Wait for response (max 120 seconds)
        if response_complete.wait(timeout=120):
            return "".join(current_response)
        else:
            return "Timeout waiting for response"
    except Exception as e:
        return f"Error: {e}"


@app.route('/health', methods=['GET'])
def health():
    running = claude_process is not None and claude_process.poll() is None
    return jsonify({
        "status": "healthy",
        "claude_available": running
    })


@app.route('/prompt', methods=['POST'])
def prompt():
    data = request.json
    prompt_text = data.get('prompt', '')

    if not prompt_text:
        return jsonify({"error": "No prompt"}), 400

    response = send_prompt(prompt_text)

    return jsonify({
        "success": True,
        "response": response
    })


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    tools = data.get('tools', [])

    # Build prompt
    prompt_parts = []
    if tools:
        tool_names = [t['name'] for t in tools]
        prompt_parts.append(f"Tools: {', '.join(tool_names)}")
        prompt_parts.append('Use JSON: {"tool": "name", "arguments": {...}}')

    for msg in reversed(messages):
        if msg.get('role') == 'user':
            content = msg.get('content', '')
            if isinstance(content, str):
                prompt_parts.append(content)
                break
            elif isinstance(content, list):
                for item in content:
                    if item.get('type') == 'text':
                        prompt_parts.append(item['text'])
                        break
                break

    full_prompt = '\n'.join(prompt_parts)
    response_text = send_prompt(full_prompt)

    # Parse tool calls
    tool_calls = []
    code_block_pattern = r'```(?:json)?\s*(\{[^`]+\})\s*```'
    matches = re.findall(code_block_pattern, response_text, re.DOTALL)

    for i, match in enumerate(matches):
        try:
            tool_json = json.loads(match.strip())
            if 'tool' in tool_json:
                tool_calls.append({
                    "id": f"call_{i}",
                    "name": tool_json['tool'],
                    "arguments": tool_json.get('arguments', {})
                })
        except:
            pass

    return jsonify({
        "stop_reason": "tool_use" if tool_calls else "end_turn",
        "content": [{"type": "text", "text": response_text}],
        "tool_calls": tool_calls
    })


if __name__ == '__main__':
    if start_claude():
        logger.info("Starting Fast Claude Bridge on port 9998...")
        app.run(host='0.0.0.0', port=9998, debug=False)
    else:
        logger.error("Failed to start claude")
        exit(1)
