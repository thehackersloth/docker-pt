#!/usr/bin/env python3
"""
Simple bridge that calls Claude Code CLI on the host
Container calls this HTTP server, which executes 'claude' commands
"""

import subprocess
import json
import logging
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health():
    """Check if claude CLI is available"""
    try:
        result = subprocess.run(['claude', '--version'], capture_output=True, text=True, timeout=5)
        available = result.returncode == 0
    except:
        available = False

    return jsonify({
        "status": "healthy",
        "claude_available": available
    })


@app.route('/prompt', methods=['POST'])
def prompt():
    """Send a prompt to Claude Code CLI"""
    data = request.json
    prompt_text = data.get('prompt', '')

    if not prompt_text:
        return jsonify({"error": "No prompt provided"}), 400

    try:
        # Call claude CLI with the prompt (no session persistence for speed)
        result = subprocess.run(
            ['claude', '-p', prompt_text, '--output-format', 'text', '--no-session-persistence'],
            capture_output=True,
            text=True,
            timeout=300
        )

        return jsonify({
            "success": result.returncode == 0,
            "response": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Command timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/chat', methods=['POST'])
def chat():
    """Chat with tools - converts to prompt format for CLI"""
    data = request.json
    messages = data.get('messages', [])
    tools = data.get('tools', [])
    system = data.get('system', '')

    # Build a concise prompt
    prompt_parts = []

    # Simplified tool list - just names
    if tools:
        tool_names = [t['name'] for t in tools]
        prompt_parts.append(f"Tools available: {', '.join(tool_names)}\n")
        prompt_parts.append("To use: respond with {\"tool\": \"name\", \"arguments\": {...}}\n\n")

    # Get the last user message as the main task
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
                    elif item.get('type') == 'tool_result':
                        prompt_parts.append(f"Previous result: {item['content'][:500]}\n")
                break

    full_prompt = ''.join(prompt_parts)

    try:
        result = subprocess.run(
            ['claude', '-p', full_prompt, '--output-format', 'text', '--no-session-persistence'],
            capture_output=True,
            text=True,
            timeout=300
        )

        response_text = result.stdout.strip()

        # Try to detect tool calls in response
        tool_calls = []
        import re

        # First, extract JSON from code blocks
        code_block_pattern = r'```(?:json)?\s*(\{[^`]+\})\s*```'
        code_matches = re.findall(code_block_pattern, response_text, re.DOTALL)

        # Also look for bare JSON objects with "tool" key
        bare_json_pattern = r'(\{[^{}]*"tool"[^{}]*\})'
        bare_matches = re.findall(bare_json_pattern, response_text)

        all_matches = code_matches + bare_matches

        for i, match in enumerate(all_matches):
            try:
                tool_json = json.loads(match.strip())
                if 'tool' in tool_json:
                    tool_calls.append({
                        "id": f"call_{i}_{hash(match) % 10000}",
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

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Command timed out"}), 504
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    logger.info("Starting Claude Host Bridge on port 9999...")
    logger.info("This calls the 'claude' CLI on the host machine")
    app.run(host='0.0.0.0', port=9999, debug=False)
