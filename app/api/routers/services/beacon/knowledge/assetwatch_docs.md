# AssetWatch Documentation

## What is AssetWatch?

AssetWatch is a network infrastructure monitoring platform that helps you track the health and performance of your network assets. Think of it as a simplified version of enterprise monitoring tools like Wanaware.

## Core Concepts

### Assets

Assets are the network/compute/security infrastructure you want to monitor. They represent physical or virtual devices in your network.

#### Asset Categories

1. **Circuit-Internet** - Internet connection types
   - Cable Broadband
   - Fiber Broadband
   - Copper Broadband
   - Wireless Broadband (4G, 5G)
   - Satellite Broadband
   - Dedicated Internet Access (DIA)

2. **Circuit-Enterprise** - Business connectivity
   - MPLS (Multi-Protocol Label Switching)
   - Private Line
   - PRI (Primary Rate Interface)
   - POTS (Plain Old Telephone Service)
   - SIP (Session Initiation Protocol)

3. **Network Assets** - Infrastructure devices
   - IP Block
   - Router
   - SD-WAN
   - Switch
   - Wireless Access Point (WAP)
   - Load Balancer

4. **Security Assets** - Security infrastructure
   - Firewall
   - IDS (Intrusion Detection System)
   - IPS (Intrusion Prevention System)
   - NDR (Network Detection & Response)
   - WAF (Web Application Firewall)

5. **Compute Assets** - Endpoints and servers
   - Server
   - Laptop
   - Desktop

6. **Storage Assets** - Storage infrastructure
   - Storage Area Network (SAN)

### Monitors

Monitors are attached to assets to collect data. Each asset can have multiple monitors. There are two types:

#### 1. Performance Monitor

Tracks system resource usage:
- **CPU Usage (%)** - How busy the processor is
- **Memory Usage (%)** - RAM utilization
- **Disk I/O (MB/s)** - Storage read/write speed
- **Latency (ms)** - Network response time

**Configuration:**
- Protocol: ICMP (ping), HTTP, or HTTPS
- Check Intervals: 1 minute, 5 minutes, or 15 minutes

#### 2. Availability Monitor

Tracks uptime and connectivity:
- **Status** - UP or DOWN
- **Response Time (ms)** - How long to get a response
- **Uptime (%)** - Percentage of time the asset was available
- **Packet Loss (%)** - Percentage of failed ping attempts

**Configuration:**
- Circuit Type: DIA (Dedicated Internet Access) or Broadband
- Check Intervals: 30 seconds, 1 minute, 5 minutes, or 15 minutes

### Metrics

Metrics are the data points collected by monitors over time. They're stored historically so you can:
- View trends
- Analyze performance patterns
- Track uptime history
- Identify issues

## How to Use AssetWatch

### Creating an Asset

1. Go to the Assets page
2. Click "Add Asset" or the + button
3. Enter:
   - **Name**: A friendly name (e.g., "Main Office Router")
   - **Type**: Select from the asset categories
   - **Description**: Optional details

### Adding a Monitor

1. Go to your asset's detail page
2. Click "Add Monitor"
3. Choose monitor type (Performance or Availability)
4. Configure:
   - **Target**: IP address or hostname to monitor
   - **Target Type**: IP or Hostname
   - **Port**: Optional port number
   - **Protocol/Circuit Type**: Based on monitor type
   - **Check Interval**: How often to check

### Viewing Data

- **Dashboard**: Overview of all assets and their status
- **Asset Detail**: Detailed view of a single asset and its monitors
- **Metrics**: Historical charts and data for analysis

### Understanding Status

- **UP** (Green): Asset is reachable and responding
- **DOWN** (Red): Asset is not responding
- **Unknown** (Gray): No checks performed yet

## Common Tasks

### Check if an Asset is Online
Look at the monitor status. UP means online, DOWN means offline.

### View Historical Data
Go to the asset detail page and select the time range (1 day, 7 days, 30 days, etc.)

### Get Uptime Percentage
Check the Availability monitor's uptime_percentage field or view the dashboard summary.

### Find Problem Assets
- Dashboard shows recent alerts (DOWN events)
- Look for assets with DOWN status
- Check assets_down count in dashboard stats

## Tips

1. **Start Simple**: Add one asset with one availability monitor to learn
2. **Use Meaningful Names**: "HQ-Firewall-01" is better than "Device1"
3. **Set Appropriate Intervals**: Critical assets = shorter intervals
4. **Check Dashboard Daily**: Quick overview of your infrastructure health

## Troubleshooting

### Monitor Shows "Unknown" Status
- The monitor hasn't run yet
- Wait for the check interval to pass
- Manually trigger a collection if available

### Asset Shows "DOWN" but is Working
- Check if the target IP/hostname is correct
- Verify network connectivity between AssetWatch and the target
- Check if firewalls are blocking ICMP/HTTP traffic

### No Metrics Data
- Ensure monitors are active (is_active = true)
- Wait for check intervals to collect data
- Check if the target is reachable
