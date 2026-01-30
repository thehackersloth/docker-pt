"""
Network utility functions
"""

import socket
import struct
from ipaddress import ip_address, ip_network, IPv4Network, IPv6Network
from typing import List, Tuple, Optional, Generator
import logging

logger = logging.getLogger(__name__)


def expand_cidr(cidr: str) -> List[str]:
    """Expand CIDR notation to list of IP addresses"""
    try:
        network = ip_network(cidr, strict=False)
        # Limit expansion to prevent memory issues
        if network.num_addresses > 65536:
            raise ValueError(f"CIDR {cidr} too large (max 65536 addresses)")
        return [str(ip) for ip in network.hosts()]
    except Exception as e:
        logger.error(f"Failed to expand CIDR {cidr}: {e}")
        return []


def expand_cidr_generator(cidr: str) -> Generator[str, None, None]:
    """Expand CIDR notation to generator of IP addresses (memory efficient)"""
    try:
        network = ip_network(cidr, strict=False)
        for ip in network.hosts():
            yield str(ip)
    except Exception as e:
        logger.error(f"Failed to expand CIDR {cidr}: {e}")


def ip_to_int(ip: str) -> int:
    """Convert IP address to integer"""
    return int(ip_address(ip))


def int_to_ip(ip_int: int) -> str:
    """Convert integer to IP address"""
    return str(ip_address(ip_int))


def get_ip_range(start_ip: str, end_ip: str) -> List[str]:
    """Get list of IPs between start and end (inclusive)"""
    start = ip_to_int(start_ip)
    end = ip_to_int(end_ip)

    if start > end:
        start, end = end, start

    if end - start > 65536:
        raise ValueError("IP range too large (max 65536 addresses)")

    return [int_to_ip(i) for i in range(start, end + 1)]


def is_private_ip(ip: str) -> bool:
    """Check if IP is private/RFC1918"""
    try:
        ip_obj = ip_address(ip)
        return ip_obj.is_private
    except Exception:
        return False


def is_loopback(ip: str) -> bool:
    """Check if IP is loopback"""
    try:
        ip_obj = ip_address(ip)
        return ip_obj.is_loopback
    except Exception:
        return False


def resolve_hostname(hostname: str) -> Optional[str]:
    """Resolve hostname to IP address"""
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


def reverse_dns(ip: str) -> Optional[str]:
    """Perform reverse DNS lookup"""
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except socket.herror:
        return None


def check_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a port is open on a host"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def get_common_ports() -> List[int]:
    """Get list of common ports to scan"""
    return [
        20, 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
        993, 995, 1433, 1521, 1723, 3306, 3389, 5432, 5900, 5985, 5986,
        6379, 8080, 8443, 8888, 9000, 9090, 27017
    ]


def get_port_service(port: int) -> str:
    """Get common service name for port"""
    services = {
        20: 'ftp-data', 21: 'ftp', 22: 'ssh', 23: 'telnet',
        25: 'smtp', 53: 'dns', 80: 'http', 110: 'pop3',
        111: 'rpcbind', 135: 'msrpc', 139: 'netbios-ssn',
        143: 'imap', 443: 'https', 445: 'microsoft-ds',
        993: 'imaps', 995: 'pop3s', 1433: 'ms-sql-s',
        1521: 'oracle', 1723: 'pptp', 3306: 'mysql',
        3389: 'rdp', 5432: 'postgresql', 5900: 'vnc',
        5985: 'winrm', 5986: 'winrm-ssl', 6379: 'redis',
        8080: 'http-proxy', 8443: 'https-alt', 27017: 'mongodb'
    }
    return services.get(port, 'unknown')


def parse_nmap_ports(port_spec: str) -> List[int]:
    """Parse nmap-style port specification"""
    ports = set()

    for part in port_spec.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = part.split('-', 1)
                for p in range(int(start), int(end) + 1):
                    if 1 <= p <= 65535:
                        ports.add(p)
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if 1 <= p <= 65535:
                    ports.add(p)
            except ValueError:
                continue

    return sorted(ports)


def get_network_info(ip: str) -> dict:
    """Get network information for an IP"""
    try:
        ip_obj = ip_address(ip)
        return {
            "ip": str(ip_obj),
            "version": ip_obj.version,
            "is_private": ip_obj.is_private,
            "is_global": ip_obj.is_global,
            "is_loopback": ip_obj.is_loopback,
            "is_multicast": ip_obj.is_multicast,
            "is_reserved": ip_obj.is_reserved,
            "is_link_local": ip_obj.is_link_local,
        }
    except Exception as e:
        return {"error": str(e)}


def calculate_network_stats(cidr: str) -> dict:
    """Calculate network statistics for a CIDR"""
    try:
        network = ip_network(cidr, strict=False)
        return {
            "network_address": str(network.network_address),
            "broadcast_address": str(network.broadcast_address),
            "netmask": str(network.netmask),
            "hostmask": str(network.hostmask),
            "num_addresses": network.num_addresses,
            "num_hosts": max(0, network.num_addresses - 2),
            "prefix_length": network.prefixlen,
            "is_private": network.is_private,
        }
    except Exception as e:
        return {"error": str(e)}
