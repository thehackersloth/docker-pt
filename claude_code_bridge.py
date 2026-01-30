#!/usr/bin/env python3
"""
Claude Code Bridge Service
Runs on host machine to provide AI capabilities to Docker container
Uses Claude.ai OAuth tokens OR Anthropic API keys

Usage:
    pip install flask requests
    export ANTHROPIC_API_KEY=your_key_or_oauth_token
    python claude_code_bridge.py
"""

import os
import json
import logging
import requests
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# API configuration
api_key = None
use_oauth = False


def init_api():
    """Initialize API configuration"""
    global api_key, use_oauth
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        return False

    # Detect if this is an OAuth token or API key
    if api_key.startswith('sk-ant-oat'):
        use_oauth = True
        logger.info("Using Claude.ai OAuth token")
    else:
        use_oauth = False
        logger.info("Using Anthropic API key")
    return True


def call_claude_api(messages, tools=None, system=None, model="claude-sonnet-4-20250514", max_tokens=4096):
    """Call Claude API (either Claude.ai or Anthropic depending on token type)"""
    global api_key, use_oauth

    if use_oauth:
        # Claude.ai API with OAuth token
        url = "https://api.claude.ai/api/organizations/-/chat_conversations/null/completion"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "anthropic-client-platform": "web",
            "anthropic-client-version": "1.0.0",
        }

        # Convert to Claude.ai format
        payload = {
            "prompt": "",
            "parent_message_uuid": "root",
            "timezone": "America/Los_Angeles",
            "model": model,
            "max_tokens": max_tokens,
        }

        # Build the prompt from messages
        for msg in messages:
            if msg["role"] == "user":
                if isinstance(msg["content"], str):
                    payload["prompt"] = msg["content"]
                elif isinstance(msg["content"], list):
                    for item in msg["content"]:
                        if item.get("type") == "text":
                            payload["prompt"] = item["text"]

        # Note: Claude.ai API doesn't support tools in the same way
        # We'll use text-based tool simulation for OAuth tokens

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            if response.status_code == 401:
                raise Exception("OAuth token expired or invalid")
            response.raise_for_status()

            # Parse streaming response
            text = ""
            for line in response.text.split('\n'):
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if "completion" in data:
                            text += data["completion"]
                    except:
                        pass

            return {
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": text}],
                "tool_calls": []
            }
        except Exception as e:
            logger.error(f"Claude.ai API call failed: {e}")
            raise

    else:
        # Standard Anthropic API
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()

            result = {
                "stop_reason": data.get("stop_reason", "end_turn"),
                "content": [],
                "tool_calls": []
            }

            for block in data.get("content", []):
                if block["type"] == "text":
                    result["content"].append({"type": "text", "text": block["text"]})
                elif block["type"] == "tool_use":
                    result["tool_calls"].append({
                        "id": block["id"],
                        "name": block["name"],
                        "arguments": block["input"]
                    })
                    result["content"].append({
                        "type": "tool_use",
                        "id": block["id"],
                        "name": block["name"],
                        "input": block["input"]
                    })

            return result
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "anthropic_available": api_key is not None,
        "auth_type": "oauth" if use_oauth else "api_key"
    })


@app.route('/generate', methods=['POST'])
def generate():
    """Generate text using Claude"""
    if not api_key:
        return jsonify({"error": "API not initialized"}), 503

    data = request.json
    prompt = data.get('prompt', '')
    model = data.get('model', 'claude-sonnet-4-20250514')
    max_tokens = data.get('max_tokens', 4096)

    system_prompt = """You are an AI assistant integrated with a professional penetration testing platform.
You help analyze security findings, suggest exploits, plan attack paths, and provide technical security guidance.
Always provide accurate, actionable information for authorized security testing.
Respond with JSON when requested."""

    try:
        result = call_claude_api(
            messages=[{"role": "user", "content": prompt}],
            system=system_prompt,
            model=model,
            max_tokens=max_tokens
        )

        text = ""
        for item in result.get("content", []):
            if item.get("type") == "text":
                text += item.get("text", "")

        return jsonify({
            "response": text,
            "model": model
        })

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/chat', methods=['POST'])
def chat_with_tools():
    """Chat with Claude including tool use support"""
    if not api_key:
        return jsonify({"error": "API not initialized"}), 503

    data = request.json
    messages = data.get('messages', [])
    tools = data.get('tools', [])
    system = data.get('system', 'You are a penetration testing AI assistant.')
    model = data.get('model', 'claude-sonnet-4-20250514')
    max_tokens = data.get('max_tokens', 4096)

    try:
        result = call_claude_api(
            messages=messages,
            tools=tools if not use_oauth else None,  # OAuth doesn't support tools natively
            system=system,
            model=model,
            max_tokens=max_tokens
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/analyze/pentest', methods=['POST'])
def analyze_pentest():
    """Analyze pentest results and provide recommendations"""
    if not api_key:
        return jsonify({"error": "API not initialized"}), 503

    data = request.json

    prompt = f"""Analyze these penetration test results and provide strategic recommendations:

Hosts Discovered: {data.get('hosts_discovered', 0)}
Services Found: {data.get('services_discovered', 0)}
Credentials Found: {data.get('credentials_found', 0)}
Shells Obtained: {data.get('shells_obtained', 0)}

Services:
{json.dumps(data.get('services', [])[:20], indent=2)}

Findings by Severity:
{json.dumps(data.get('findings_by_severity', {}), indent=2)}

Provide a JSON response with:
{{
    "risk_level": "critical|high|medium|low",
    "priority_actions": ["action1", "action2"],
    "attack_paths": ["path1", "path2"],
    "lateral_movement_opportunities": ["opportunity1"],
    "recommended_tools": ["tool1", "tool2"],
    "executive_summary": "Brief summary for management"
}}"""

    try:
        result = call_claude_api(
            messages=[{"role": "user", "content": prompt}],
            model="claude-sonnet-4-20250514",
            max_tokens=4096
        )

        text = ""
        for item in result.get("content", []):
            if item.get("type") == "text":
                text += item.get("text", "")

        # Try to parse JSON from response
        try:
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            parsed = json.loads(text.strip())
            return jsonify(parsed)
        except:
            return jsonify({"raw_analysis": text})

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    if init_api():
        logger.info("Starting Claude Code Bridge on port 9999...")
        logger.info("Container can connect via http://host.docker.internal:9999")
        app.run(host='0.0.0.0', port=9999, debug=False)
    else:
        logger.error("Failed to initialize. Set ANTHROPIC_API_KEY environment variable.")
        exit(1)
