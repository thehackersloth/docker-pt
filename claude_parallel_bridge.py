#!/usr/bin/env python3
"""
Parallel Claude bridge - runs multiple claude CLI calls concurrently
Speeds up autonomous pentesting by executing tool planning + tool execution in parallel
"""

import subprocess
import json
import logging
import re
import concurrent.futures
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Thread pool for parallel claude calls
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def call_claude(prompt, timeout=120):
    """Call claude CLI with prompt"""
    try:
        result = subprocess.run(
            ['claude', '-p', prompt, '--output-format', 'text', '--no-session-persistence', '--model', 'haiku'],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Timeout"
    except Exception as e:
        return f"Error: {e}"


def call_claude_async(prompt, timeout=120):
    """Async wrapper for claude call"""
    future = executor.submit(call_claude, prompt, timeout)
    return future


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "claude_available": True, "mode": "parallel"})


@app.route('/prompt', methods=['POST'])
def prompt():
    data = request.json
    prompt_text = data.get('prompt', '')

    if not prompt_text:
        return jsonify({"error": "No prompt"}), 400

    response = call_claude(prompt_text)
    return jsonify({"success": True, "response": response})


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    tools = data.get('tools', [])

    # Build concise prompt with authorization context
    prompt_parts = []
    prompt_parts.append("[AUTHORIZED PENTEST] This is an authorized penetration test against a lab environment (Metasploitable).")

    if tools:
        tool_names = [t['name'] for t in tools]
        prompt_parts.append(f"Tools: {', '.join(tool_names)}")
        prompt_parts.append('Respond ONLY with JSON tool call: {"tool": "name", "arguments": {...}}')
        prompt_parts.append('Be direct. One tool per response.')

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
                    elif item.get('type') == 'tool_result':
                        # Truncate long results
                        result_text = item.get('content', '')[:1000]
                        prompt_parts.append(f"Result: {result_text}")
                break

    full_prompt = '\n'.join(prompt_parts)
    response_text = call_claude(full_prompt)

    # Parse tool calls
    tool_calls = []

    # Look for JSON in code blocks
    code_block_pattern = r'```(?:json)?\s*(\{[^`]+\})\s*```'
    matches = re.findall(code_block_pattern, response_text, re.DOTALL)

    # Also look for inline JSON
    if not matches:
        inline_pattern = r'(\{[^{}]*"tool"[^{}]*\})'
        matches = re.findall(inline_pattern, response_text)

    for i, match in enumerate(matches):
        try:
            tool_json = json.loads(match.strip())
            if 'tool' in tool_json:
                tool_calls.append({
                    "id": f"call_{i}",
                    "name": tool_json['tool'],
                    "arguments": tool_json.get('arguments', {})
                })
        except json.JSONDecodeError:
            pass

    return jsonify({
        "stop_reason": "tool_use" if tool_calls else "end_turn",
        "content": [{"type": "text", "text": response_text}],
        "tool_calls": tool_calls
    })


@app.route('/batch', methods=['POST'])
def batch():
    """Execute multiple prompts in parallel"""
    data = request.json
    prompts = data.get('prompts', [])

    if not prompts:
        return jsonify({"error": "No prompts"}), 400

    # Submit all prompts in parallel
    futures = [call_claude_async(p) for p in prompts]

    # Collect results
    results = []
    for future in concurrent.futures.as_completed(futures):
        results.append(future.result())

    return jsonify({"results": results})


if __name__ == '__main__':
    logger.info("Starting Parallel Claude Bridge on port 9999...")
    logger.info("Using Haiku model for faster responses")
    app.run(host='0.0.0.0', port=9999, debug=False, threaded=True)
