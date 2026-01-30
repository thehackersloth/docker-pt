"""
AI service layer
Abstraction for multiple AI providers
"""

import logging
import requests
from typing import Dict, Optional, Any, List
from app.core.config import settings
from app.services.ai.providers.ollama_provider import OllamaProvider
from app.services.ai.providers.openai_provider import OpenAIProvider
from app.services.ai.providers.whiterabbit_neo_provider import WhiteRabbitNeoProvider
from app.services.ai.providers.anthropic_provider import AnthropicProvider
from app.services.ai.providers.gemini_provider import GeminiProvider
from app.services.ai.providers.github_copilot_provider import GitHubCopilotProvider

# Try to import Claude Code bridge provider
try:
    from app.services.ai.providers.claude_code_bridge_provider import ClaudeCodeBridgeProvider
    CLAUDE_CODE_BRIDGE_AVAILABLE = True
except ImportError:
    CLAUDE_CODE_BRIDGE_AVAILABLE = False

logger = logging.getLogger(__name__)


class AIService:
    """AI service with provider abstraction"""
    
    def __init__(self):
        self.providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available AI providers"""

        # PRIORITY 1: Claude Code Bridge (auto-detect on host)
        if CLAUDE_CODE_BRIDGE_AVAILABLE and self._detect_claude_code():
            try:
                provider = ClaudeCodeBridgeProvider()
                if provider.is_available():
                    self.providers['claude_code'] = provider
                    logger.info("Claude Code detected and connected!")
            except Exception as e:
                logger.debug(f"Claude Code bridge not available: {e}")

        # Local AI providers (priority for privacy)
        if settings.WHITERABBIT_NEO_ENABLED:
            try:
                self.providers['whiterabbit_neo'] = WhiteRabbitNeoProvider()
                logger.info("WhiteRabbit Neo provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize WhiteRabbit Neo: {e}")

        if settings.OLLAMA_ENABLED:
            try:
                self.providers['ollama'] = OllamaProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama: {e}")

        # Cloud AI providers (only if not local-only)
        if settings.OPENAI_ENABLED and not settings.AI_LOCAL_ONLY:
            try:
                self.providers['openai'] = OpenAIProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")

        if settings.ANTHROPIC_ENABLED and not settings.AI_LOCAL_ONLY:
            try:
                self.providers['anthropic'] = AnthropicProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic: {e}")

        if settings.GEMINI_ENABLED and not settings.AI_LOCAL_ONLY:
            try:
                self.providers['gemini'] = GeminiProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")

        if settings.GITHUB_COPILOT_ENABLED and not settings.AI_LOCAL_ONLY:
            try:
                self.providers['github_copilot'] = GitHubCopilotProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize GitHub Copilot: {e}")

    def _detect_claude_code(self) -> bool:
        """Auto-detect if Claude Code bridge is running on host"""
        try:
            bridge_url = getattr(settings, 'CLAUDE_CODE_BRIDGE_URL', 'http://host.docker.internal:9999')
            response = requests.get(f"{bridge_url}/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get('anthropic_available'):
                    logger.info(f"Claude Code bridge detected at {bridge_url}")
                    return True
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            logger.debug(f"Claude Code detection failed: {e}")
        return False

    def list_available_providers(self) -> List[Dict[str, Any]]:
        """List all available AI providers for UI selection"""
        available = []

        for name, provider in self.providers.items():
            is_available = False
            if hasattr(provider, 'is_available'):
                try:
                    is_available = provider.is_available()
                except:
                    pass

            provider_info = {
                "name": name,
                "display_name": self._get_display_name(name),
                "available": is_available,
                "type": self._get_provider_type(name),
                "description": self._get_provider_description(name)
            }
            available.append(provider_info)

        # Also check for Claude Code even if not initialized
        if 'claude_code' not in self.providers:
            claude_detected = self._detect_claude_code()
            available.append({
                "name": "claude_code",
                "display_name": "Claude Code (Host)",
                "available": claude_detected,
                "type": "bridge",
                "description": "Connect to Claude Code running on host machine"
            })

        return available

    def _get_display_name(self, name: str) -> str:
        """Get human-readable provider name"""
        names = {
            "claude_code": "Claude Code (Host)",
            "anthropic": "Anthropic Claude API",
            "openai": "OpenAI GPT",
            "ollama": "Ollama (Local)",
            "whiterabbit_neo": "WhiteRabbit Neo",
            "gemini": "Google Gemini",
            "github_copilot": "GitHub Copilot"
        }
        return names.get(name, name.title())

    def _get_provider_type(self, name: str) -> str:
        """Get provider type (local/cloud/bridge)"""
        local = ["ollama", "whiterabbit_neo", "llama_cpp"]
        bridge = ["claude_code"]
        if name in local:
            return "local"
        elif name in bridge:
            return "bridge"
        return "cloud"

    def _get_provider_description(self, name: str) -> str:
        """Get provider description"""
        descriptions = {
            "claude_code": "Uses Claude Code on your host machine for AI-powered analysis",
            "anthropic": "Direct Anthropic API - requires API key",
            "openai": "OpenAI GPT models - requires API key",
            "ollama": "Local LLM via Ollama - private, no API needed",
            "whiterabbit_neo": "Security-focused local AI model",
            "gemini": "Google Gemini models - requires API key",
            "github_copilot": "GitHub Copilot - requires subscription"
        }
        return descriptions.get(name, "")
    
    def get_provider(self, preferred: Optional[str] = None):
        """
        Get AI provider based on preferences and availability
        Priority: Claude Code > Anthropic > OpenAI > Local
        """
        # Use preferred provider if specified and available
        if preferred and preferred in self.providers:
            provider = self.providers[preferred]
            if hasattr(provider, 'is_available'):
                if provider.is_available():
                    return provider
            else:
                return provider

        # Priority order for automatic selection
        priority_order = [
            'claude_code',      # Best: Claude Code on host
            'anthropic',        # Direct API
            'openai',           # Alternative API
            'whiterabbit_neo',  # Local security AI
            'ollama',           # Local general AI
            'gemini',
            'github_copilot'
        ]

        for provider_name in priority_order:
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                if hasattr(provider, 'is_available'):
                    try:
                        if provider.is_available():
                            return provider
                    except:
                        continue
                else:
                    return provider

        # Fallback to any available
        for provider in self.providers.values():
            if hasattr(provider, 'is_available'):
                try:
                    if provider.is_available():
                        return provider
                except:
                    continue
            else:
                return provider

        return None

    def set_preferred_provider(self, provider_name: str) -> bool:
        """Set the preferred AI provider"""
        if provider_name in self.providers:
            provider = self.providers[provider_name]
            if hasattr(provider, 'is_available') and provider.is_available():
                self._preferred_provider = provider_name
                logger.info(f"AI provider set to: {provider_name}")
                return True
        return False
    
    def get_fallback_provider(self, primary_provider_name: str):
        """Get fallback provider if primary fails"""
        provider_names = list(self.providers.keys())
        
        try:
            current_index = provider_names.index(primary_provider_name)
            # Try next providers
            for provider_name in provider_names[current_index + 1:]:
                provider = self.providers[provider_name]
                if hasattr(provider, 'is_available') and provider.is_available():
                    return provider
        except ValueError:
            pass
        
        # Fallback to any available
        return self.get_provider()
    
    def generate_text(self, prompt: str, model: Optional[str] = None, provider_name: Optional[str] = None, **kwargs) -> Optional[str]:
        """Generate text using AI with fallback"""
        provider = self.get_provider(provider_name)
        if not provider:
            logger.error("No AI provider available")
            return None

        try:
            result = provider.generate_text(prompt, model, **kwargs)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Primary AI provider failed: {e}")

        # Try fallback provider
        if provider_name:
            fallback = self.get_fallback_provider(provider_name)
            if fallback and fallback != provider:
                try:
                    logger.info(f"Using fallback provider: {fallback.name}")
                    return fallback.generate_text(prompt, model, **kwargs)
                except Exception as e:
                    logger.error(f"Fallback provider also failed: {e}")

        return None

    def analyze_vulnerability(self, description: str, tool: str = None, context: Dict = None) -> Optional[Dict[str, Any]]:
        """
        Analyze a vulnerability finding using AI

        Args:
            description: Vulnerability description from tool output
            tool: Name of the tool that found the vulnerability
            context: Additional context (target, port, service, etc.)

        Returns:
            Dict with severity, exploitation difficulty, remediation, etc.
        """
        context = context or {}

        prompt = f"""Analyze this security vulnerability finding and provide a structured assessment:

Tool: {tool or 'Unknown'}
Finding: {description}
Target: {context.get('target', 'Unknown')}
Service: {context.get('service', 'Unknown')}
Port: {context.get('port', 'Unknown')}

Provide a JSON response with the following structure:
{{
    "severity": "critical|high|medium|low|info",
    "cvss_score": 0.0-10.0,
    "exploitation_difficulty": "trivial|easy|moderate|difficult|very_difficult",
    "confirmed": true/false,
    "title": "Brief vulnerability title",
    "description": "Detailed vulnerability description",
    "impact": "What could an attacker do with this vulnerability",
    "remediation": "How to fix this vulnerability",
    "references": ["CVE-XXXX-XXXX", "relevant URLs"],
    "exploit_available": true/false,
    "exploit_type": "remote|local|web|network"
}}

Only respond with valid JSON, no markdown or explanation."""

        try:
            result = self.generate_text(prompt)
            if result:
                import json
                # Try to extract JSON from response
                result = result.strip()
                if result.startswith('```'):
                    result = result.split('```')[1]
                    if result.startswith('json'):
                        result = result[4:]
                return json.loads(result)
        except Exception as e:
            logger.error(f"Failed to analyze vulnerability: {e}")

        # Return basic analysis if AI fails
        return {
            "severity": self._estimate_severity(description),
            "title": description[:100] if len(description) > 100 else description,
            "description": description,
            "remediation": "Review and remediate based on tool output",
            "confirmed": False
        }

    def _estimate_severity(self, description: str) -> str:
        """Estimate severity based on keywords when AI is unavailable"""
        description_lower = description.lower()

        critical_keywords = ['rce', 'remote code execution', 'sql injection', 'command injection',
                            'unauthenticated', 'root', 'admin', 'arbitrary code', 'backdoor']
        high_keywords = ['xss', 'cross-site', 'lfi', 'rfi', 'ssrf', 'xxe', 'deserialization',
                        'privilege escalation', 'authentication bypass', 'password']
        medium_keywords = ['csrf', 'open redirect', 'information disclosure', 'sensitive data',
                          'misconfiguration', 'weak', 'deprecated']
        low_keywords = ['verbose', 'banner', 'version', 'header', 'cookie']

        for keyword in critical_keywords:
            if keyword in description_lower:
                return 'critical'
        for keyword in high_keywords:
            if keyword in description_lower:
                return 'high'
        for keyword in medium_keywords:
            if keyword in description_lower:
                return 'medium'
        for keyword in low_keywords:
            if keyword in description_lower:
                return 'low'

        return 'info'

    def generate_metasploit_module(self, title: str, description: str, target: str,
                                   vuln_type: str = None) -> Optional[Dict[str, Any]]:
        """
        Generate or suggest Metasploit module for exploitation

        Args:
            title: Vulnerability title
            description: Vulnerability description
            target: Target IP/hostname
            vuln_type: Type of vulnerability (rce, sqli, etc.)

        Returns:
            Dict with module path, options, and usage instructions
        """
        prompt = f"""Based on this vulnerability, suggest the most appropriate Metasploit module for exploitation:

Vulnerability: {title}
Description: {description}
Target: {target}
Type: {vuln_type or 'Unknown'}

Provide a JSON response with:
{{
    "module_path": "exploit/linux/http/example",
    "module_type": "exploit|auxiliary|post",
    "options": {{
        "RHOSTS": "{target}",
        "RPORT": "port_number",
        "other_required_options": "values"
    }},
    "payload_suggestion": "linux/x64/meterpreter/reverse_tcp",
    "usage_instructions": "Step by step instructions",
    "alternative_modules": ["module1", "module2"],
    "manual_exploit": "If no module exists, describe manual exploitation steps",
    "confidence": 0.0-1.0
}}

Only respond with valid JSON."""

        try:
            result = self.generate_text(prompt)
            if result:
                import json
                result = result.strip()
                if result.startswith('```'):
                    result = result.split('```')[1]
                    if result.startswith('json'):
                        result = result[4:]
                return json.loads(result)
        except Exception as e:
            logger.error(f"Failed to generate Metasploit module suggestion: {e}")

        return None

    def suggest_next_steps(self, scan_results: Dict, findings: list) -> Optional[Dict[str, Any]]:
        """
        Analyze scan results and suggest next steps for the pentester

        Args:
            scan_results: Results from completed scans
            findings: List of findings discovered

        Returns:
            Dict with prioritized next steps and reasoning
        """
        findings_summary = "\n".join([
            f"- {f.get('title', 'Unknown')}: {f.get('severity', 'unknown')} severity"
            for f in findings[:20]  # Limit to top 20
        ])

        prompt = f"""Based on these penetration testing findings, suggest the next steps:

Findings:
{findings_summary}

Provide a JSON response with:
{{
    "priority_targets": ["target1", "target2"],
    "next_tools": ["tool1", "tool2"],
    "exploitation_order": [
        {{"finding": "finding_title", "reason": "why exploit this first"}}
    ],
    "additional_reconnaissance": ["what else to scan for"],
    "lateral_movement_opportunities": ["potential paths"],
    "post_exploitation_suggestions": ["what to do after gaining access"],
    "report_highlights": ["key findings for the report"]
}}

Only respond with valid JSON."""

        try:
            result = self.generate_text(prompt)
            if result:
                import json
                result = result.strip()
                if result.startswith('```'):
                    result = result.split('```')[1]
                    if result.startswith('json'):
                        result = result[4:]
                return json.loads(result)
        except Exception as e:
            logger.error(f"Failed to suggest next steps: {e}")

        return None

    def generate_report_section(self, section_type: str, data: Dict) -> Optional[str]:
        """
        Generate a report section using AI

        Args:
            section_type: Type of section (executive_summary, technical_details, remediation)
            data: Data to include in the section

        Returns:
            Generated report text
        """
        prompts = {
            "executive_summary": f"""Write an executive summary for a penetration test report based on this data:
{data}

The summary should be professional, non-technical, and highlight key business risks.
Keep it under 300 words.""",

            "technical_details": f"""Write a technical details section for a penetration test report:
{data}

Include technical specifics, evidence references, and reproduction steps.
Format with clear headers and bullet points.""",

            "remediation": f"""Write a remediation section based on these findings:
{data}

Provide prioritized, actionable remediation steps.
Include both quick wins and long-term improvements.""",

            "risk_assessment": f"""Write a risk assessment based on these penetration testing findings:
{data}

Include likelihood, impact, and overall risk ratings.
Reference industry standards where appropriate."""
        }

        prompt = prompts.get(section_type, prompts["technical_details"])

        try:
            return self.generate_text(prompt)
        except Exception as e:
            logger.error(f"Failed to generate report section: {e}")
            return None
