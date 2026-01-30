"""
LDAP Search - LDAP enumeration tool runner
Queries LDAP/Active Directory for users, groups, computers, and more
"""

import subprocess
import re
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class LdapSearchRunner(BaseToolRunner):
    """LDAP search and enumeration runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "ldapsearch")
        self.output_dir = Path(f"/tmp/ldapsearch_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate LDAP search input"""
        if not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run LDAP search

        Config options:
            - base_dn: Base DN for search (e.g., DC=domain,DC=local)
            - bind_dn: Bind DN (username) for authentication
            - password: Password for authentication
            - search_filter: LDAP filter (default: (objectClass=*))
            - attributes: Attributes to retrieve (default: all)
            - scope: Search scope - base, one, sub (default: sub)
            - port: LDAP port (default: 389, or 636 for SSL)
            - ssl: Use LDAPS (default: False)
            - anonymous: Try anonymous bind (default: False)
            - query_type: Predefined query types:
                - users: Enumerate users
                - groups: Enumerate groups
                - computers: Enumerate computers
                - admins: Find admin users
                - spns: Service Principal Names (Kerberoasting)
                - asreproast: Users without preauth
                - domain_info: Get domain information
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid LDAP search input - target required")

        config = config or {}
        target = targets[0]
        query_type = config.get('query_type', 'users')

        # Get predefined query based on type
        if query_type == 'users':
            return self._query_users(target, config)
        elif query_type == 'groups':
            return self._query_groups(target, config)
        elif query_type == 'computers':
            return self._query_computers(target, config)
        elif query_type == 'admins':
            return self._query_admins(target, config)
        elif query_type == 'spns':
            return self._query_spns(target, config)
        elif query_type == 'asreproast':
            return self._query_asreproast(target, config)
        elif query_type == 'domain_info':
            return self._query_domain_info(target, config)
        else:
            return self._query_custom(target, config)

    def _build_base_cmd(self, target: str, config: Dict) -> List[str]:
        """Build base ldapsearch command"""
        bind_dn = config.get('bind_dn')
        password = config.get('password')
        base_dn = config.get('base_dn', '')
        port = config.get('port', 389)
        ssl = config.get('ssl', False)
        anonymous = config.get('anonymous', False)

        cmd = ['ldapsearch']

        # Host
        if ssl:
            cmd.extend(['-H', f'ldaps://{target}:{port}'])
        else:
            cmd.extend(['-H', f'ldap://{target}:{port}'])

        # Authentication
        if anonymous:
            cmd.append('-x')  # Simple auth
        elif bind_dn and password:
            cmd.extend(['-x', '-D', bind_dn, '-w', password])
        else:
            cmd.append('-x')  # Try simple auth

        # Base DN
        if base_dn:
            cmd.extend(['-b', base_dn])

        return cmd

    def _query_users(self, target: str, config: Dict) -> Dict[str, Any]:
        """Query for all users"""
        cmd = self._build_base_cmd(target, config)
        cmd.extend([
            '(objectClass=user)',
            'sAMAccountName', 'cn', 'mail', 'memberOf', 'userAccountControl',
            'lastLogon', 'pwdLastSet', 'description'
        ])

        return self._execute_query(cmd, target, 'users', config)

    def _query_groups(self, target: str, config: Dict) -> Dict[str, Any]:
        """Query for all groups"""
        cmd = self._build_base_cmd(target, config)
        cmd.extend([
            '(objectClass=group)',
            'cn', 'description', 'member', 'memberOf'
        ])

        return self._execute_query(cmd, target, 'groups', config)

    def _query_computers(self, target: str, config: Dict) -> Dict[str, Any]:
        """Query for all computers"""
        cmd = self._build_base_cmd(target, config)
        cmd.extend([
            '(objectClass=computer)',
            'cn', 'dNSHostName', 'operatingSystem', 'operatingSystemVersion',
            'lastLogon', 'servicePrincipalName'
        ])

        return self._execute_query(cmd, target, 'computers', config)

    def _query_admins(self, target: str, config: Dict) -> Dict[str, Any]:
        """Query for admin users"""
        cmd = self._build_base_cmd(target, config)
        # Query members of Domain Admins, Administrators, Enterprise Admins
        cmd.extend([
            '(|(memberOf=CN=Domain Admins,*)(memberOf=CN=Administrators,*)(memberOf=CN=Enterprise Admins,*))',
            'sAMAccountName', 'cn', 'memberOf', 'description'
        ])

        return self._execute_query(cmd, target, 'admins', config)

    def _query_spns(self, target: str, config: Dict) -> Dict[str, Any]:
        """Query for Service Principal Names (Kerberoasting targets)"""
        cmd = self._build_base_cmd(target, config)
        cmd.extend([
            '(&(objectClass=user)(servicePrincipalName=*))',
            'sAMAccountName', 'cn', 'servicePrincipalName', 'memberOf'
        ])

        return self._execute_query(cmd, target, 'spns', config)

    def _query_asreproast(self, target: str, config: Dict) -> Dict[str, Any]:
        """Query for users without Kerberos pre-authentication"""
        cmd = self._build_base_cmd(target, config)
        # DONT_REQUIRE_PREAUTH = 0x400000 (4194304)
        cmd.extend([
            '(&(objectClass=user)(userAccountControl:1.2.840.113556.1.4.803:=4194304))',
            'sAMAccountName', 'cn', 'userAccountControl'
        ])

        return self._execute_query(cmd, target, 'asreproast', config)

    def _query_domain_info(self, target: str, config: Dict) -> Dict[str, Any]:
        """Query domain information"""
        cmd = self._build_base_cmd(target, config)
        cmd.extend([
            '(objectClass=domain)',
            'dc', 'distinguishedName', 'objectSid', 'whenCreated',
            'ms-DS-MachineAccountQuota', 'minPwdLength', 'lockoutThreshold'
        ])

        return self._execute_query(cmd, target, 'domain_info', config)

    def _query_custom(self, target: str, config: Dict) -> Dict[str, Any]:
        """Execute custom LDAP query"""
        cmd = self._build_base_cmd(target, config)

        search_filter = config.get('search_filter', '(objectClass=*)')
        attributes = config.get('attributes', '*')

        cmd.append(search_filter)
        if isinstance(attributes, list):
            cmd.extend(attributes)
        else:
            cmd.append(attributes)

        return self._execute_query(cmd, target, 'custom', config)

    def _execute_query(self, cmd: List[str], target: str, query_type: str, config: Dict) -> Dict[str, Any]:
        """Execute LDAP query and parse results"""
        output_file = self.output_dir / f"{query_type}_{target.replace('.', '_')}.ldif"

        logger.info(f"Running LDAP query ({query_type}): {' '.join(cmd[:5])}...")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=120)

            # Save output
            with open(output_file, 'w') as f:
                f.write(stdout)

            # Parse LDIF output
            entries = self._parse_ldif(stdout)

            return {
                "success": True,
                "target": target,
                "query_type": query_type,
                "entries": entries,
                "entries_count": len(entries),
                "output_file": str(output_file),
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "LDAP query timed out", "success": False}
        except Exception as e:
            logger.error(f"LDAP query error: {e}")
            return {"error": str(e), "success": False}

    def _parse_ldif(self, ldif_output: str) -> List[Dict]:
        """Parse LDIF format output"""
        entries = []
        current_entry = {}

        for line in ldif_output.split('\n'):
            line = line.strip()

            if not line:
                # Empty line marks end of entry
                if current_entry:
                    entries.append(current_entry)
                    current_entry = {}
                continue

            if line.startswith('#'):
                continue

            if ':' in line:
                # Handle multi-value attributes and base64
                if ':: ' in line:
                    # Base64 encoded value
                    key, value = line.split(':: ', 1)
                    try:
                        import base64
                        value = base64.b64decode(value).decode('utf-8', errors='ignore')
                    except:
                        pass
                else:
                    parts = line.split(': ', 1)
                    if len(parts) == 2:
                        key, value = parts
                    else:
                        continue

                key = key.lower()

                # Handle multi-value attributes
                if key in current_entry:
                    if isinstance(current_entry[key], list):
                        current_entry[key].append(value)
                    else:
                        current_entry[key] = [current_entry[key], value]
                else:
                    current_entry[key] = value

        # Don't forget the last entry
        if current_entry:
            entries.append(current_entry)

        return entries

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse LDAP search output"""
        return {"entries": self._parse_ldif(output)}
