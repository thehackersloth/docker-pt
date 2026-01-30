"""
MCP Client for Pentest Platform
Allows AI to autonomously control pentests via any AI API with tool use
Supports: Anthropic, OpenAI, DeepSeek, Ollama, and any OpenAI-compatible API
"""

import json
import logging
import subprocess
import requests
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"  # Any OpenAI-compatible API


@dataclass
class Tool:
    """Tool definition for AI"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable


class BaseAIClient(ABC):
    """Abstract base for AI clients"""

    @abstractmethod
    def chat_with_tools(self, messages: List[dict], tools: List[dict]) -> dict:
        """Send chat with tools, return response with tool calls if any"""
        pass


class AnthropicClient(BaseAIClient):
    """Anthropic Claude client"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def chat_with_tools(self, messages: List[dict], tools: List[dict], system: str = None) -> dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system or "You are a penetration testing AI assistant.",
            tools=tools,
            messages=messages
        )

        result = {
            "stop_reason": response.stop_reason,
            "content": [],
            "tool_calls": []
        }

        for block in response.content:
            if block.type == "text":
                result["content"].append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                result["tool_calls"].append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input
                })
                result["content"].append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })

        return result


class OpenAICompatibleClient(BaseAIClient):
    """OpenAI-compatible client (works with OpenAI, DeepSeek, Ollama, etc.)"""

    def __init__(self, api_key: str, model: str = "gpt-4",
                 base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _convert_tools_to_openai_format(self, tools: List[dict]) -> List[dict]:
        """Convert Anthropic-style tools to OpenAI function format"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            }
            for tool in tools
        ]

    def chat_with_tools(self, messages: List[dict], tools: List[dict], system: str = None) -> dict:
        # Convert messages to OpenAI format
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})

        for msg in messages:
            if msg["role"] == "user":
                if isinstance(msg["content"], list):
                    # Tool results
                    for item in msg["content"]:
                        if item.get("type") == "tool_result":
                            openai_messages.append({
                                "role": "tool",
                                "tool_call_id": item["tool_use_id"],
                                "content": item["content"]
                            })
                else:
                    openai_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                if isinstance(msg["content"], list):
                    # Assistant message with tool calls
                    text_content = ""
                    tool_calls = []
                    for item in msg["content"]:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                text_content += item.get("text", "")
                            elif item.get("type") == "tool_use":
                                tool_calls.append({
                                    "id": item["id"],
                                    "type": "function",
                                    "function": {
                                        "name": item["name"],
                                        "arguments": json.dumps(item["input"])
                                    }
                                })
                        elif hasattr(item, "type"):
                            if item.type == "text":
                                text_content += item.text
                            elif item.type == "tool_use":
                                tool_calls.append({
                                    "id": item.id,
                                    "type": "function",
                                    "function": {
                                        "name": item.name,
                                        "arguments": json.dumps(item.input)
                                    }
                                })

                    assistant_msg = {"role": "assistant", "content": text_content or None}
                    if tool_calls:
                        assistant_msg["tool_calls"] = tool_calls
                    openai_messages.append(assistant_msg)
                else:
                    openai_messages.append({"role": "assistant", "content": msg["content"]})

        # Make API call
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": openai_messages,
            "tools": self._convert_tools_to_openai_format(tools),
            "tool_choice": "auto",
            "max_tokens": 4096
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=300
        )
        response.raise_for_status()
        data = response.json()

        # Parse response
        result = {
            "stop_reason": data["choices"][0]["finish_reason"],
            "content": [],
            "tool_calls": []
        }

        message = data["choices"][0]["message"]

        if message.get("content"):
            result["content"].append({"type": "text", "text": message["content"]})

        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                result["tool_calls"].append({
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "arguments": json.loads(tc["function"]["arguments"])
                })
                result["content"].append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "input": json.loads(tc["function"]["arguments"])
                })

        # Normalize stop reason
        if result["stop_reason"] == "tool_calls":
            result["stop_reason"] = "tool_use"

        return result


class ClaudeCodeBridgeClient(BaseAIClient):
    """Client that routes through Claude Code bridge on host"""

    def __init__(self, bridge_url: str = "http://host.docker.internal:9999", model: str = "claude-sonnet-4-20250514"):
        self.bridge_url = bridge_url.rstrip("/")
        self.model = model

    def chat_with_tools(self, messages: List[dict], tools: List[dict], system: str = None) -> dict:
        response = requests.post(
            f"{self.bridge_url}/chat",
            json={
                "messages": messages,
                "tools": tools,
                "system": system or "You are a penetration testing AI assistant.",
                "model": self.model,
                "max_tokens": 4096
            },
            timeout=300
        )
        response.raise_for_status()
        return response.json()


class OllamaClient(BaseAIClient):
    """Ollama local client"""

    def __init__(self, model: str = "llama2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def chat_with_tools(self, messages: List[dict], tools: List[dict], system: str = None) -> dict:
        # Ollama doesn't have native tool support, so we embed tools in the prompt
        tools_desc = "\n".join([
            f"- {t['name']}: {t['description']}\n  Parameters: {json.dumps(t['input_schema'])}"
            for t in tools
        ])

        system_with_tools = f"""{system or 'You are a penetration testing AI.'}

You have access to these tools:
{tools_desc}

To use a tool, respond with JSON in this exact format:
{{"tool": "tool_name", "arguments": {{"param1": "value1"}}}}

Only use one tool at a time. After receiving tool results, continue with next steps or provide final answer."""

        # Convert messages
        ollama_messages = [{"role": "system", "content": system_with_tools}]

        for msg in messages:
            if msg["role"] == "user":
                if isinstance(msg["content"], list):
                    # Tool results
                    content = "Tool results:\n"
                    for item in msg["content"]:
                        if item.get("type") == "tool_result":
                            content += f"{item['content']}\n"
                    ollama_messages.append({"role": "user", "content": content})
                else:
                    ollama_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                text = ""
                if isinstance(msg["content"], list):
                    for item in msg["content"]:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text += item.get("text", "")
                else:
                    text = msg["content"]
                if text:
                    ollama_messages.append({"role": "assistant", "content": text})

        # Make API call
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": ollama_messages,
                "stream": False
            },
            timeout=300
        )
        response.raise_for_status()
        data = response.json()

        content = data["message"]["content"]

        result = {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": content}],
            "tool_calls": []
        }

        # Try to parse tool call from response
        try:
            # Look for JSON tool call in response
            if "{" in content and "tool" in content:
                start = content.index("{")
                end = content.rindex("}") + 1
                tool_json = json.loads(content[start:end])

                if "tool" in tool_json:
                    tool_id = f"call_{hash(content) % 10000}"
                    result["tool_calls"].append({
                        "id": tool_id,
                        "name": tool_json["tool"],
                        "arguments": tool_json.get("arguments", {})
                    })
                    result["content"].append({
                        "type": "tool_use",
                        "id": tool_id,
                        "name": tool_json["tool"],
                        "input": tool_json.get("arguments", {})
                    })
                    result["stop_reason"] = "tool_use"
        except (json.JSONDecodeError, ValueError):
            pass

        return result


def create_ai_client(provider: str, api_key: str = None, model: str = None,
                     base_url: str = None) -> BaseAIClient:
    """Factory function to create AI client based on provider"""

    provider = provider.lower()

    if provider == "anthropic":
        return AnthropicClient(
            api_key=api_key,
            model=model or "claude-sonnet-4-20250514"
        )

    elif provider == "claude_code" or provider == "claude_code_bridge":
        # Route through Claude Code bridge running on host
        return ClaudeCodeBridgeClient(
            bridge_url=base_url or "http://host.docker.internal:9999",
            model=model or "claude-sonnet-4-20250514"
        )

    elif provider == "openai":
        return OpenAICompatibleClient(
            api_key=api_key,
            model=model or "gpt-4",
            base_url=base_url or "https://api.openai.com/v1"
        )

    elif provider == "deepseek":
        return OpenAICompatibleClient(
            api_key=api_key,
            model=model or "deepseek-chat",
            base_url=base_url or "https://api.deepseek.com/v1"
        )

    elif provider == "ollama":
        return OllamaClient(
            model=model or "llama2",
            base_url=base_url or "http://localhost:11434"
        )

    elif provider == "openai_compatible":
        if not base_url:
            raise ValueError("base_url required for openai_compatible provider")
        return OpenAICompatibleClient(
            api_key=api_key or "not-needed",
            model=model or "default",
            base_url=base_url
        )

    else:
        raise ValueError(f"Unknown provider: {provider}. Supported: anthropic, claude_code, openai, deepseek, ollama, openai_compatible")


class PentestMCPClient:
    """
    MCP-style client that lets any AI control the pentest platform
    Supports multiple AI providers
    """

    def __init__(self, provider: str = "anthropic", api_key: str = None,
                 model: str = None, base_url: str = None,
                 platform_url: str = "http://localhost:8000"):
        self.ai_client = create_ai_client(provider, api_key, model, base_url)
        self.provider = provider
        self.platform_url = platform_url
        self.api_token = None
        self.tools = self._register_tools()
        self.conversation_history = []
        self.max_iterations = 8  # Keep it fast - 8 iterations max

    def _register_tools(self) -> List[Tool]:
        """Register all available pentest tools"""
        return [
            Tool(
                name="login",
                description="Login to pentest platform",
                input_schema={
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string"}
                    },
                    "required": ["username", "password"]
                },
                handler=self._tool_login
            ),
            Tool(
                name="start_full_pentest",
                description="Start a full automated penetration test against targets. This runs recon, vulnerability scanning, credential attacks, exploitation, and post-exploitation.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name for this pentest"},
                        "targets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Target IPs, hostnames, or CIDR ranges"
                        }
                    },
                    "required": ["name", "targets"]
                },
                handler=self._tool_start_pentest
            ),
            Tool(
                name="get_scan_status",
                description="Get current status and results of a scan",
                input_schema={
                    "type": "object",
                    "properties": {
                        "scan_id": {"type": "string"}
                    },
                    "required": ["scan_id"]
                },
                handler=self._tool_get_scan_status
            ),
            Tool(
                name="list_scans",
                description="List all scans",
                input_schema={
                    "type": "object",
                    "properties": {}
                },
                handler=self._tool_list_scans
            ),
            Tool(
                name="get_findings",
                description="Get security findings/vulnerabilities discovered",
                input_schema={
                    "type": "object",
                    "properties": {
                        "scan_id": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low", "info"]
                        }
                    },
                    "required": ["scan_id"]
                },
                handler=self._tool_get_findings
            ),
            Tool(
                name="run_nmap",
                description="Run nmap port scan",
                input_schema={
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"},
                        "ports": {"type": "string", "description": "Port spec like '22,80,443' or '1-1000'"},
                        "options": {"type": "string", "description": "Additional nmap options"}
                    },
                    "required": ["target"]
                },
                handler=self._tool_run_nmap
            ),
            Tool(
                name="run_hydra",
                description="Run Hydra credential brute force",
                input_schema={
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"},
                        "service": {"type": "string", "enum": ["ssh", "ftp", "telnet", "smb", "rdp", "mysql"]},
                        "port": {"type": "integer"},
                        "usernames": {"type": "array", "items": {"type": "string"}},
                        "passwords": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["target", "service"]
                },
                handler=self._tool_run_hydra
            ),
            Tool(
                name="run_exploit",
                description="Run a Metasploit exploit module",
                input_schema={
                    "type": "object",
                    "properties": {
                        "module": {"type": "string", "description": "MSF module path"},
                        "target": {"type": "string"},
                        "port": {"type": "integer"},
                        "payload": {"type": "string"},
                        "options": {"type": "object"}
                    },
                    "required": ["module", "target"]
                },
                handler=self._tool_run_exploit
            ),
            Tool(
                name="list_sessions",
                description="List active shell sessions",
                input_schema={
                    "type": "object",
                    "properties": {}
                },
                handler=self._tool_list_sessions
            ),
            Tool(
                name="session_command",
                description="Execute command in a shell session",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "command": {"type": "string"}
                    },
                    "required": ["session_id", "command"]
                },
                handler=self._tool_session_command
            ),
            Tool(
                name="generate_report",
                description="Generate pentest report",
                input_schema={
                    "type": "object",
                    "properties": {
                        "scan_id": {"type": "string"},
                        "format": {"type": "string", "enum": ["pdf", "html", "json"]}
                    },
                    "required": ["scan_id"]
                },
                handler=self._tool_generate_report
            ),
            Tool(
                name="shell_command",
                description="Execute a shell command directly in the pentest container",
                input_schema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to execute"}
                    },
                    "required": ["command"]
                },
                handler=self._tool_shell_command
            ),
            Tool(
                name="task_complete",
                description="Signal that the pentest task is complete",
                input_schema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "Summary of what was accomplished"},
                        "findings_count": {"type": "integer"},
                        "critical_findings": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["summary"]
                },
                handler=self._tool_task_complete
            )
        ]

    def _api_call(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make API call to pentest platform"""
        url = f"{self.platform_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=60)
            elif method == "POST":
                resp = requests.post(url, json=data, headers=headers, timeout=300)
            else:
                return {"error": f"Unknown method: {method}"}
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    # Tool handlers
    def _tool_login(self, username: str, password: str) -> str:
        result = self._api_call("POST", "/api/v1/auth/login", {
            "username": username,
            "password": password
        })
        if "access_token" in result:
            self.api_token = result["access_token"]
            return json.dumps({"success": True, "message": "Logged in"})
        return json.dumps(result)

    def _tool_start_pentest(self, name: str, targets: List[str]) -> str:
        result = self._api_call("POST", "/api/v1/scans?auto_start=true&full_automation=true", {
            "name": name,
            "targets": targets,
            "scan_type": "network"
        })
        return json.dumps(result)

    def _tool_get_scan_status(self, scan_id: str) -> str:
        result = self._api_call("GET", f"/api/v1/scans/{scan_id}")
        return json.dumps(result)

    def _tool_list_scans(self) -> str:
        result = self._api_call("GET", "/api/v1/scans")
        return json.dumps(result)

    def _tool_get_findings(self, scan_id: str, severity: str = None) -> str:
        endpoint = f"/api/v1/findings?scan_id={scan_id}"
        if severity:
            endpoint += f"&severity={severity}"
        result = self._api_call("GET", endpoint)
        return json.dumps(result)

    def _tool_run_nmap(self, target: str, ports: str = "1-1000", options: str = "") -> str:
        import shlex
        import re
        # Sanitize target - only allow IPs, hostnames, CIDR
        if not re.match(r'^[a-zA-Z0-9\.\-\_\/\:]+$', target):
            return json.dumps({"error": "Invalid target format"})
        # Sanitize ports - only allow digits, commas, dashes
        if not re.match(r'^[0-9,\-]+$', ports):
            return json.dumps({"error": "Invalid port format"})
        # Sanitize options - block shell metacharacters
        if options and re.search(r'[;&|`$(){}]', options):
            return json.dumps({"error": "Invalid characters in options"})
        cmd = f"nmap {options} -p {ports} {shlex.quote(target)}"
        return self._tool_shell_command(cmd)

    def _tool_run_hydra(self, target: str, service: str, port: int = None,
                        usernames: List[str] = None, passwords: List[str] = None) -> str:
        import shlex
        import re
        # Sanitize target
        if not re.match(r'^[a-zA-Z0-9\.\-\_]+$', target):
            return json.dumps({"error": "Invalid target format"})
        # Sanitize service name
        if not re.match(r'^[a-zA-Z0-9\-]+$', service):
            return json.dumps({"error": "Invalid service format"})
        # Sanitize port
        if port is not None and not isinstance(port, int):
            return json.dumps({"error": "Port must be integer"})

        users = usernames or ["admin", "root", "user"]
        passes = passwords or ["admin", "password", "123456"]

        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as uf:
            uf.write('\n'.join(users))
            user_file = uf.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as pf:
            pf.write('\n'.join(passes))
            pass_file = pf.name

        port_opt = f"-s {port}" if port else ""
        cmd = f"hydra -L {shlex.quote(user_file)} -P {shlex.quote(pass_file)} {port_opt} -f -t 4 {shlex.quote(target)} {shlex.quote(service)}"
        return self._tool_shell_command(cmd)

    def _tool_run_exploit(self, module: str, target: str, port: int = None,
                          payload: str = None, options: dict = None) -> str:
        result = self._api_call("POST", "/api/v1/metasploit/exploit", {
            "module": module,
            "target": target,
            "port": port,
            "payload": payload,
            "options": options or {}
        })
        return json.dumps(result)

    def _tool_list_sessions(self) -> str:
        result = self._api_call("GET", "/api/v1/metasploit/sessions")
        return json.dumps(result)

    def _tool_session_command(self, session_id: str, command: str) -> str:
        result = self._api_call("POST", f"/api/v1/metasploit/sessions/{session_id}/command", {
            "command": command
        })
        return json.dumps(result)

    def _tool_generate_report(self, scan_id: str, format: str = "pdf") -> str:
        result = self._api_call("POST", "/api/v1/reports/generate", {
            "scan_id": scan_id,
            "format": format
        })
        return json.dumps(result)

    # Allowed command prefixes for shell execution
    ALLOWED_COMMANDS = [
        "nmap", "masscan", "nikto", "sqlmap", "hydra", "gobuster", "dirb",
        "enum4linux", "smbclient", "rpcclient", "crackmapexec", "netexec",
        "whatweb", "wpscan", "searchsploit", "msfconsole", "msfvenom",
        "curl", "wget", "ping", "traceroute", "dig", "nslookup", "whois",
        "cat", "ls", "head", "tail", "grep", "find", "wc", "sort", "uniq",
        "python3", "ruby", "perl", "nc", "openssl",
    ]

    def _tool_shell_command(self, command: str) -> str:
        """Execute shell command directly (runs inside container)"""
        import re
        # Block dangerous shell operators
        if re.search(r'[;&|`\$]', command.split('#')[0]):
            # Allow pipes specifically for grep/sort/etc
            parts = command.split('|')
            for part in parts:
                stripped = part.strip().split()[0] if part.strip() else ""
                if stripped and stripped not in self.ALLOWED_COMMANDS:
                    return json.dumps({"error": f"Command not allowed: {stripped}"})
        else:
            # Validate the base command
            base_cmd = command.strip().split()[0] if command.strip() else ""
            if base_cmd not in self.ALLOWED_COMMANDS:
                return json.dumps({"error": f"Command not allowed: {base_cmd}. Allowed: {', '.join(self.ALLOWED_COMMANDS[:10])}..."})

        try:
            result = subprocess.run(
                ["bash", "-c", command],
                capture_output=True,
                text=True,
                timeout=300
            )
            return json.dumps({
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:1000],
                "returncode": result.returncode
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _tool_task_complete(self, summary: str, findings_count: int = 0,
                            critical_findings: List[str] = None) -> str:
        return json.dumps({
            "complete": True,
            "summary": summary,
            "findings_count": findings_count,
            "critical_findings": critical_findings or []
        })

    def _get_tool_schemas(self) -> List[dict]:
        """Get tool schemas"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            }
            for tool in self.tools
        ]

    def _execute_tool(self, name: str, input_data: dict) -> str:
        """Execute a tool by name"""
        for tool in self.tools:
            if tool.name == name:
                try:
                    import inspect
                    sig = inspect.signature(tool.handler)
                    params = {k: v for k, v in input_data.items() if k in sig.parameters}
                    return tool.handler(**params)
                except Exception as e:
                    return json.dumps({"error": str(e)})
        return json.dumps({"error": f"Unknown tool: {name}"})

    def run_autonomous_pentest(self, task: str, auto_login: bool = True) -> Dict[str, Any]:
        """
        Run an autonomous pentest based on natural language task

        Args:
            task: Natural language description of what to do
            auto_login: Automatically login first

        Returns:
            Dict with results, findings, and summary
        """
        logger.info(f"Starting autonomous pentest with {self.provider}: {task}")

        if auto_login:
            import os
            auto_user = os.environ.get("PENTEST_AUTO_USER", "admin")
            auto_pass = os.environ.get("PENTEST_AUTO_PASS", "")
            if auto_pass:
                self._tool_login(auto_user, auto_pass)
            else:
                logger.warning("No PENTEST_AUTO_PASS set, skipping auto-login")

        system_prompt = """You are an autonomous penetration testing AI. Execute efficiently - each response costs time.

RULES:
1. Call ONE tool per response - be decisive
2. After 3-5 tool calls, use task_complete with summary
3. Don't explain - just execute tools
4. Focus on quick wins: vsftpd backdoor, default creds, known CVEs

Respond ONLY with a tool call JSON:
{"tool": "tool_name", "arguments": {...}}

Start with run_nmap to find services, then exploit the easiest target."""

        self.conversation_history = [
            {"role": "user", "content": task}
        ]

        results = {
            "task": task,
            "provider": self.provider,
            "iterations": 0,
            "tool_calls": [],
            "complete": False,
            "summary": None
        }

        for iteration in range(self.max_iterations):
            results["iterations"] = iteration + 1
            logger.info(f"Iteration {iteration + 1}")

            # Call AI with tools
            response = self.ai_client.chat_with_tools(
                messages=self.conversation_history,
                tools=self._get_tool_schemas(),
                system=system_prompt
            )

            # Check if we need to execute tools
            if response.get("tool_calls"):
                tool_results = []

                for tool_call in response["tool_calls"]:
                    tool_name = tool_call["name"]
                    tool_input = tool_call["arguments"]
                    tool_id = tool_call["id"]

                    logger.info(f"Executing tool: {tool_name}")
                    result = self._execute_tool(tool_name, tool_input)

                    results["tool_calls"].append({
                        "tool": tool_name,
                        "input": tool_input,
                        "output": result[:500]
                    })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result
                    })

                    # Check if task is complete
                    if tool_name == "task_complete":
                        result_data = json.loads(result)
                        results["complete"] = True
                        results["summary"] = result_data.get("summary")
                        results["findings_count"] = result_data.get("findings_count", 0)
                        results["critical_findings"] = result_data.get("critical_findings", [])
                        return results

                # Add to history
                self.conversation_history.append({"role": "assistant", "content": response["content"]})
                self.conversation_history.append({"role": "user", "content": tool_results})

            else:
                # No tool calls - AI is done
                final_text = ""
                for item in response.get("content", []):
                    if item.get("type") == "text":
                        final_text += item.get("text", "")

                results["final_message"] = final_text
                if not results["complete"]:
                    results["summary"] = final_text
                break

        return results


def get_supported_providers() -> List[Dict[str, str]]:
    """Get list of supported AI providers"""
    return [
        {"name": "claude_code", "display": "Claude Code (Host)", "requires_key": False},
        {"name": "anthropic", "display": "Anthropic Claude", "requires_key": True},
        {"name": "openai", "display": "OpenAI GPT", "requires_key": True},
        {"name": "deepseek", "display": "DeepSeek", "requires_key": True},
        {"name": "ollama", "display": "Ollama (Local)", "requires_key": False},
        {"name": "openai_compatible", "display": "OpenAI-Compatible API", "requires_key": False}
    ]
