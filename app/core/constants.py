
# These match exactly what's in the Wanaware frontend
from typing import Literal


ASSET_TYPES = Literal[
    # Circuit - Internet types (different connection technologies)
    "Circuit-Internet-Cable Broadband",
    "Circuit-Internet-Fiber Broadband",
    "Circuit-Internet-Copper Broadband",
    "Circuit-Internet-Wireless Broadband",
    "Circuit-Internet-Wireless 4G Broadband",
    "Circuit-Internet-Wireless 5G Broadband",
    "Circuit-Internet-Satellite Broadband",
    "Circuit-Internet-Dedicated Internet Access",
    # Circuit - Enterprise connection types
    "Circuit-MPLS",
    "Circuit-Private Line",
    "Circuit-PRI",
    "Circuit-POTS",
    "Circuit-SIP",
    # Network Assets (physical/virtual network equipment)
    "Network Asset-IP Block",
    "Network Asset-Router",
    "Network Asset-SD-WAN",
    "Network Asset-Switch",
    "Network Asset-Wireless Access Point (WAP)",
    "Network Asset-Load Balancer",
    # Security Assets (security infrastructure)
    "Security Asset-Firewall",
    "Security Asset-Intrusion Detection System (IDS)",
    "Security Asset-Intrusion Prevention System (IPS)",
    "Security Asset-Network Detection & Response (NDR)",
    "Security Asset-Web Application Firewall (WAF)",
    # Compute Assets (servers and endpoints)
    "Compute Asset-Server",
    "Compute Asset-Laptop",
    "Compute Asset-Desktop",
    # Storage Assets
    "Storage Asset-Storage Area Network (SAN)",
]
