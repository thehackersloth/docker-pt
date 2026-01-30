"""
BloodHound tool runner
Collects and imports Active Directory data for security analysis
"""

import subprocess
import json
import logging
import zipfile
import tempfile
from typing import Dict, List, Any, Optional
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class BloodHoundRunner(BaseToolRunner):
    """BloodHound collector runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "bloodhound")
        self.output_dir = Path(f"/data/bloodhound/{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate BloodHound input"""
        config = config or {}
        # Need domain, DC IP, and credentials
        if not config.get('domain'):
            return False
        if not config.get('dc_ip'):
            return False
        if not config.get('username') or not config.get('password'):
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run BloodHound collection
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid BloodHound input - need domain, DC IP, and credentials")
        
        config = config or {}
        domain = config['domain']
        dc_ip = config['dc_ip']
        username = config['username']
        password = config['password']
        collection_methods = config.get('collection_methods', ['DCOnly', 'RPC'])
        
        # Use bloodhound.py (Python collector)
        cmd = [
            'bloodhound-python',
            '-d', domain,
            '-u', username,
            '-p', password,
            '-dc', dc_ip,
            '-c', ','.join(collection_methods),
            '--zip',
            '--output', str(self.output_dir)
        ]
        
        logger.info(f"Running BloodHound collection: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"BloodHound failed: {stderr}")
                return {"error": stderr, "success": False}
            
            # Find output zip file
            zip_files = list(self.output_dir.glob("*.zip"))
            if not zip_files:
                return {"error": "No output file generated", "success": False}
            
            output_file = zip_files[0]
            
            results = {
                "success": True,
                "output_file": str(output_file),
                "output_dir": str(self.output_dir),
                "collection_methods": collection_methods,
                "domain": domain,
                "dc_ip": dc_ip,
                "stdout": stdout,
            }
            
            return results
            
        except Exception as e:
            logger.error(f"BloodHound execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse BloodHound output"""
        # BloodHound outputs JSON files
        # This will be processed by the import service
        return {"raw_output": output}
    
    def import_to_neo4j(self, zip_file: str, clear_db: bool = False) -> Dict[str, Any]:
        """
        Import BloodHound data into Neo4j

        Args:
            zip_file: Path to BloodHound ZIP file
            clear_db: Whether to clear existing data before import
        """
        from app.core.config import settings
        from neo4j import GraphDatabase

        stats = {
            "users": 0,
            "computers": 0,
            "groups": 0,
            "domains": 0,
            "gpos": 0,
            "ous": 0,
            "containers": 0,
            "sessions": 0,
            "relationships": 0
        }

        try:
            driver = GraphDatabase.driver(
                f"bolt://{settings.NEO4J_HOST}:{settings.NEO4J_PORT}",
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )

            # Extract ZIP to temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(zip_file, 'r') as zf:
                    zf.extractall(temp_dir)

                temp_path = Path(temp_dir)

                with driver.session() as session:
                    # Clear existing data if requested
                    if clear_db:
                        session.run("MATCH (n) DETACH DELETE n")
                        logger.info("Cleared existing Neo4j data")

                    # Create indexes for performance
                    self._create_indexes(session)

                    # Import in order: domains, users, computers, groups, then relationships
                    for json_file in temp_path.glob("*_domains.json"):
                        count = self._import_domains(session, json_file)
                        stats["domains"] += count

                    for json_file in temp_path.glob("*_users.json"):
                        count = self._import_users(session, json_file)
                        stats["users"] += count

                    for json_file in temp_path.glob("*_computers.json"):
                        count = self._import_computers(session, json_file)
                        stats["computers"] += count

                    for json_file in temp_path.glob("*_groups.json"):
                        count = self._import_groups(session, json_file)
                        stats["groups"] += count

                    for json_file in temp_path.glob("*_gpos.json"):
                        count = self._import_gpos(session, json_file)
                        stats["gpos"] += count

                    for json_file in temp_path.glob("*_ous.json"):
                        count = self._import_ous(session, json_file)
                        stats["ous"] += count

                    for json_file in temp_path.glob("*_containers.json"):
                        count = self._import_containers(session, json_file)
                        stats["containers"] += count

                    # Import relationships from all files
                    for json_file in temp_path.glob("*.json"):
                        count = self._import_relationships(session, json_file)
                        stats["relationships"] += count

            driver.close()

            total_nodes = sum(v for k, v in stats.items() if k != "relationships")
            logger.info(f"BloodHound import complete: {total_nodes} nodes, {stats['relationships']} relationships")

            return {
                "success": True,
                "message": "Data imported to Neo4j",
                "stats": stats
            }

        except Exception as e:
            logger.error(f"Neo4j import failed: {e}")
            return {"success": False, "error": str(e)}

    def _create_indexes(self, session) -> None:
        """Create Neo4j indexes for BloodHound queries"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (n:User) ON (n.objectid)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Computer) ON (n.objectid)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Group) ON (n.objectid)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Domain) ON (n.objectid)",
            "CREATE INDEX IF NOT EXISTS FOR (n:GPO) ON (n.objectid)",
            "CREATE INDEX IF NOT EXISTS FOR (n:OU) ON (n.objectid)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Container) ON (n.objectid)",
            "CREATE INDEX IF NOT EXISTS FOR (n:User) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Computer) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Group) ON (n.name)",
        ]
        for idx in indexes:
            try:
                session.run(idx)
            except Exception as e:
                logger.debug(f"Index creation skipped: {e}")

    def _import_domains(self, session, json_file: Path) -> int:
        """Import domain nodes"""
        count = 0
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            domains = data.get('data', data.get('domains', []))
            if isinstance(domains, dict):
                domains = [domains]

            for domain in domains:
                props = domain.get('Properties', domain)
                object_id = props.get('objectid', props.get('objectsid', ''))

                session.run("""
                    MERGE (d:Domain {objectid: $objectid})
                    SET d.name = $name,
                        d.domain = $domain,
                        d.distinguishedname = $dn,
                        d.functionallevel = $level,
                        d.collected = true
                """,
                    objectid=object_id,
                    name=props.get('name', '').upper(),
                    domain=props.get('domain', props.get('name', '')).upper(),
                    dn=props.get('distinguishedname', ''),
                    level=props.get('functionallevel', '')
                )
                count += 1

        except Exception as e:
            logger.error(f"Domain import error: {e}")

        return count

    def _import_users(self, session, json_file: Path) -> int:
        """Import user nodes"""
        count = 0
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            users = data.get('data', data.get('users', []))

            for user in users:
                props = user.get('Properties', user)
                object_id = props.get('objectid', props.get('objectsid', ''))

                session.run("""
                    MERGE (u:User {objectid: $objectid})
                    SET u.name = $name,
                        u.domain = $domain,
                        u.distinguishedname = $dn,
                        u.enabled = $enabled,
                        u.admincount = $admincount,
                        u.hasspn = $hasspn,
                        u.dontreqpreauth = $asreproast,
                        u.unconstraineddelegation = $unconstrained,
                        u.pwdneverexpires = $pwdneverexp,
                        u.sensitive = $sensitive,
                        u.lastlogon = $lastlogon,
                        u.lastlogontimestamp = $lastlogonts,
                        u.pwdlastset = $pwdlastset,
                        u.serviceprincipalnames = $spns,
                        u.description = $description
                """,
                    objectid=object_id,
                    name=props.get('name', '').upper(),
                    domain=props.get('domain', '').upper(),
                    dn=props.get('distinguishedname', ''),
                    enabled=props.get('enabled', True),
                    admincount=props.get('admincount', False),
                    hasspn=props.get('hasspn', False),
                    asreproast=props.get('dontreqpreauth', False),
                    unconstrained=props.get('unconstraineddelegation', False),
                    pwdneverexp=props.get('pwdneverexpires', False),
                    sensitive=props.get('sensitive', False),
                    lastlogon=props.get('lastlogon', 0),
                    lastlogonts=props.get('lastlogontimestamp', 0),
                    pwdlastset=props.get('pwdlastset', 0),
                    spns=props.get('serviceprincipalnames', []),
                    description=props.get('description', '')
                )
                count += 1

        except Exception as e:
            logger.error(f"User import error: {e}")

        return count

    def _import_computers(self, session, json_file: Path) -> int:
        """Import computer nodes"""
        count = 0
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            computers = data.get('data', data.get('computers', []))

            for computer in computers:
                props = computer.get('Properties', computer)
                object_id = props.get('objectid', props.get('objectsid', ''))

                session.run("""
                    MERGE (c:Computer {objectid: $objectid})
                    SET c.name = $name,
                        c.domain = $domain,
                        c.distinguishedname = $dn,
                        c.enabled = $enabled,
                        c.unconstraineddelegation = $unconstrained,
                        c.trustedtoauth = $trustedtoauth,
                        c.haslaps = $haslaps,
                        c.operatingsystem = $os,
                        c.lastlogon = $lastlogon,
                        c.lastlogontimestamp = $lastlogonts,
                        c.pwdlastset = $pwdlastset,
                        c.serviceprincipalnames = $spns
                """,
                    objectid=object_id,
                    name=props.get('name', '').upper(),
                    domain=props.get('domain', '').upper(),
                    dn=props.get('distinguishedname', ''),
                    enabled=props.get('enabled', True),
                    unconstrained=props.get('unconstraineddelegation', False),
                    trustedtoauth=props.get('trustedtoauth', False),
                    haslaps=props.get('haslaps', False),
                    os=props.get('operatingsystem', ''),
                    lastlogon=props.get('lastlogon', 0),
                    lastlogonts=props.get('lastlogontimestamp', 0),
                    pwdlastset=props.get('pwdlastset', 0),
                    spns=props.get('serviceprincipalnames', [])
                )
                count += 1

        except Exception as e:
            logger.error(f"Computer import error: {e}")

        return count

    def _import_groups(self, session, json_file: Path) -> int:
        """Import group nodes"""
        count = 0
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            groups = data.get('data', data.get('groups', []))

            for group in groups:
                props = group.get('Properties', group)
                object_id = props.get('objectid', props.get('objectsid', ''))

                session.run("""
                    MERGE (g:Group {objectid: $objectid})
                    SET g.name = $name,
                        g.domain = $domain,
                        g.distinguishedname = $dn,
                        g.admincount = $admincount,
                        g.description = $description,
                        g.highvalue = $highvalue
                """,
                    objectid=object_id,
                    name=props.get('name', '').upper(),
                    domain=props.get('domain', '').upper(),
                    dn=props.get('distinguishedname', ''),
                    admincount=props.get('admincount', False),
                    description=props.get('description', ''),
                    highvalue=props.get('highvalue', False)
                )
                count += 1

        except Exception as e:
            logger.error(f"Group import error: {e}")

        return count

    def _import_gpos(self, session, json_file: Path) -> int:
        """Import GPO nodes"""
        count = 0
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            gpos = data.get('data', data.get('gpos', []))

            for gpo in gpos:
                props = gpo.get('Properties', gpo)
                object_id = props.get('objectid', props.get('guid', ''))

                session.run("""
                    MERGE (g:GPO {objectid: $objectid})
                    SET g.name = $name,
                        g.domain = $domain,
                        g.distinguishedname = $dn,
                        g.gpcpath = $gpcpath,
                        g.highvalue = $highvalue
                """,
                    objectid=object_id,
                    name=props.get('name', ''),
                    domain=props.get('domain', '').upper(),
                    dn=props.get('distinguishedname', ''),
                    gpcpath=props.get('gpcpath', ''),
                    highvalue=props.get('highvalue', False)
                )
                count += 1

        except Exception as e:
            logger.error(f"GPO import error: {e}")

        return count

    def _import_ous(self, session, json_file: Path) -> int:
        """Import OU nodes"""
        count = 0
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            ous = data.get('data', data.get('ous', []))

            for ou in ous:
                props = ou.get('Properties', ou)
                object_id = props.get('objectid', props.get('guid', ''))

                session.run("""
                    MERGE (o:OU {objectid: $objectid})
                    SET o.name = $name,
                        o.domain = $domain,
                        o.distinguishedname = $dn,
                        o.highvalue = $highvalue,
                        o.blocksinheritance = $blocksinheritance
                """,
                    objectid=object_id,
                    name=props.get('name', ''),
                    domain=props.get('domain', '').upper(),
                    dn=props.get('distinguishedname', ''),
                    highvalue=props.get('highvalue', False),
                    blocksinheritance=props.get('blocksinheritance', False)
                )
                count += 1

        except Exception as e:
            logger.error(f"OU import error: {e}")

        return count

    def _import_containers(self, session, json_file: Path) -> int:
        """Import container nodes"""
        count = 0
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            containers = data.get('data', data.get('containers', []))

            for container in containers:
                props = container.get('Properties', container)
                object_id = props.get('objectid', props.get('guid', ''))

                session.run("""
                    MERGE (c:Container {objectid: $objectid})
                    SET c.name = $name,
                        c.domain = $domain,
                        c.distinguishedname = $dn
                """,
                    objectid=object_id,
                    name=props.get('name', ''),
                    domain=props.get('domain', '').upper(),
                    dn=props.get('distinguishedname', '')
                )
                count += 1

        except Exception as e:
            logger.error(f"Container import error: {e}")

        return count

    def _import_relationships(self, session, json_file: Path) -> int:
        """Import relationships from BloodHound JSON"""
        count = 0

        # Relationship type mappings
        rel_types = {
            'MemberOf': 'MemberOf',
            'AdminTo': 'AdminTo',
            'HasSession': 'HasSession',
            'CanRDP': 'CanRDP',
            'CanPSRemote': 'CanPSRemote',
            'ExecuteDCOM': 'ExecuteDCOM',
            'AllowedToDelegate': 'AllowedToDelegate',
            'AddMember': 'AddMember',
            'ForceChangePassword': 'ForceChangePassword',
            'GenericAll': 'GenericAll',
            'GenericWrite': 'GenericWrite',
            'WriteOwner': 'WriteOwner',
            'WriteDacl': 'WriteDacl',
            'Owns': 'Owns',
            'DCSync': 'DCSync',
            'ReadLAPSPassword': 'ReadLAPSPassword',
            'ReadGMSAPassword': 'ReadGMSAPassword',
            'Contains': 'Contains',
            'GPLink': 'GPLink',
            'HasSIDHistory': 'HasSIDHistory',
            'TrustedBy': 'TrustedBy',
            'AllowedToAct': 'AllowedToAct',
            'AddSelf': 'AddSelf',
            'AddAllowedToAct': 'AddAllowedToAct',
            'SQLAdmin': 'SQLAdmin',
            'AllExtendedRights': 'AllExtendedRights',
        }

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            # BloodHound stores relationships in multiple places
            items = data.get('data', [])
            if isinstance(items, dict):
                items = [items]

            for item in items:
                # Process Aces (ACL entries)
                aces = item.get('Aces', [])
                for ace in aces:
                    principal_sid = ace.get('PrincipalSID', '')
                    right_name = ace.get('RightName', '')

                    if principal_sid and right_name in rel_types:
                        target_id = item.get('Properties', {}).get('objectid',
                                    item.get('ObjectIdentifier', ''))

                        if target_id:
                            self._create_relationship(
                                session,
                                principal_sid,
                                target_id,
                                rel_types[right_name]
                            )
                            count += 1

                # Process Members (group membership)
                members = item.get('Members', [])
                target_id = item.get('Properties', {}).get('objectid',
                            item.get('ObjectIdentifier', ''))

                for member in members:
                    member_id = member.get('ObjectIdentifier', member.get('MemberId', ''))
                    if member_id and target_id:
                        self._create_relationship(session, member_id, target_id, 'MemberOf')
                        count += 1

                # Process LocalAdmins
                local_admins = item.get('LocalAdmins', [])
                for admin in local_admins:
                    admin_id = admin.get('ObjectIdentifier', admin.get('MemberId', ''))
                    if admin_id and target_id:
                        self._create_relationship(session, admin_id, target_id, 'AdminTo')
                        count += 1

                # Process Sessions
                sessions = item.get('Sessions', [])
                for sess in sessions:
                    user_id = sess.get('UserId', sess.get('UserSID', ''))
                    computer_id = sess.get('ComputerId', sess.get('ComputerSID', ''))
                    if user_id and computer_id:
                        self._create_relationship(session, computer_id, user_id, 'HasSession')
                        count += 1

                # Process AllowedToDelegate
                delegates = item.get('AllowedToDelegate', [])
                source_id = item.get('Properties', {}).get('objectid',
                            item.get('ObjectIdentifier', ''))
                for delegate in delegates:
                    delegate_id = delegate.get('ObjectIdentifier', delegate)
                    if isinstance(delegate_id, str) and source_id:
                        self._create_relationship(session, source_id, delegate_id, 'AllowedToDelegate')
                        count += 1

                # Process GPLinks
                links = item.get('Links', [])
                for link in links:
                    gpo_id = link.get('GUID', link.get('ObjectIdentifier', ''))
                    if gpo_id and target_id:
                        self._create_relationship(session, gpo_id, target_id, 'GPLink')
                        count += 1

        except Exception as e:
            logger.debug(f"Relationship import from {json_file.name}: {e}")

        return count

    def _create_relationship(self, session, source_id: str, target_id: str, rel_type: str) -> None:
        """Create a relationship between two nodes"""
        try:
            session.run(f"""
                MATCH (a {{objectid: $source}})
                MATCH (b {{objectid: $target}})
                MERGE (a)-[r:{rel_type}]->(b)
            """, source=source_id, target=target_id)
        except Exception as e:
            logger.debug(f"Relationship creation failed: {e}")

    def get_attack_paths(self, start_node: str = None, target_group: str = "DOMAIN ADMINS") -> Dict[str, Any]:
        """
        Query Neo4j for attack paths to high-value targets
        """
        from app.core.config import settings
        from neo4j import GraphDatabase

        try:
            driver = GraphDatabase.driver(
                f"bolt://{settings.NEO4J_HOST}:{settings.NEO4J_PORT}",
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )

            paths = []

            with driver.session() as session:
                # Shortest paths to Domain Admins
                if start_node:
                    result = session.run("""
                        MATCH (start {name: $start})
                        MATCH (end:Group) WHERE end.name CONTAINS $target
                        MATCH path = shortestPath((start)-[*1..10]->(end))
                        RETURN path LIMIT 10
                    """, start=start_node.upper(), target=target_group.upper())
                else:
                    result = session.run("""
                        MATCH (start:User) WHERE start.enabled = true
                        MATCH (end:Group) WHERE end.name CONTAINS $target
                        MATCH path = shortestPath((start)-[*1..5]->(end))
                        RETURN path LIMIT 50
                    """, target=target_group.upper())

                for record in result:
                    path = record["path"]
                    path_nodes = [{"name": node.get("name"), "type": list(node.labels)[0]}
                                  for node in path.nodes]
                    path_rels = [type(rel).__name__ for rel in path.relationships]
                    paths.append({"nodes": path_nodes, "relationships": path_rels})

            driver.close()

            return {
                "success": True,
                "target": target_group,
                "paths_found": len(paths),
                "paths": paths
            }

        except Exception as e:
            logger.error(f"Attack path query failed: {e}")
            return {"success": False, "error": str(e)}

    def get_kerberoastable_users(self) -> Dict[str, Any]:
        """Find Kerberoastable users"""
        from app.core.config import settings
        from neo4j import GraphDatabase

        try:
            driver = GraphDatabase.driver(
                f"bolt://{settings.NEO4J_HOST}:{settings.NEO4J_PORT}",
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )

            users = []

            with driver.session() as session:
                result = session.run("""
                    MATCH (u:User)
                    WHERE u.hasspn = true AND u.enabled = true
                    RETURN u.name as name, u.serviceprincipalnames as spns,
                           u.admincount as admincount, u.description as description
                    ORDER BY u.admincount DESC
                """)

                for record in result:
                    users.append({
                        "name": record["name"],
                        "spns": record["spns"],
                        "admincount": record["admincount"],
                        "description": record["description"]
                    })

            driver.close()

            return {
                "success": True,
                "count": len(users),
                "users": users
            }

        except Exception as e:
            logger.error(f"Kerberoastable query failed: {e}")
            return {"success": False, "error": str(e)}

    def get_asreproastable_users(self) -> Dict[str, Any]:
        """Find AS-REP roastable users"""
        from app.core.config import settings
        from neo4j import GraphDatabase

        try:
            driver = GraphDatabase.driver(
                f"bolt://{settings.NEO4J_HOST}:{settings.NEO4J_PORT}",
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )

            users = []

            with driver.session() as session:
                result = session.run("""
                    MATCH (u:User)
                    WHERE u.dontreqpreauth = true AND u.enabled = true
                    RETURN u.name as name, u.admincount as admincount,
                           u.description as description
                    ORDER BY u.admincount DESC
                """)

                for record in result:
                    users.append({
                        "name": record["name"],
                        "admincount": record["admincount"],
                        "description": record["description"]
                    })

            driver.close()

            return {
                "success": True,
                "count": len(users),
                "users": users
            }

        except Exception as e:
            logger.error(f"AS-REP roastable query failed: {e}")
            return {"success": False, "error": str(e)}

    def get_unconstrained_delegation(self) -> Dict[str, Any]:
        """Find computers with unconstrained delegation"""
        from app.core.config import settings
        from neo4j import GraphDatabase

        try:
            driver = GraphDatabase.driver(
                f"bolt://{settings.NEO4J_HOST}:{settings.NEO4J_PORT}",
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )

            computers = []

            with driver.session() as session:
                result = session.run("""
                    MATCH (c:Computer)
                    WHERE c.unconstraineddelegation = true AND c.enabled = true
                    RETURN c.name as name, c.operatingsystem as os
                """)

                for record in result:
                    computers.append({
                        "name": record["name"],
                        "os": record["os"]
                    })

            driver.close()

            return {
                "success": True,
                "count": len(computers),
                "computers": computers
            }

        except Exception as e:
            logger.error(f"Unconstrained delegation query failed: {e}")
            return {"success": False, "error": str(e)}
