# Alternatives for admin_routes.py

Here are other notable snippets that are important and unique but serve as alternatives. I selected these based on their role in system monitoring, health checks, and documentation. Each provides value in different contexts, such as runtime monitoring or logging.

1. **Health Check Route**: This is a key route for API health monitoring. It's unique due to its integration of system metrics (e.g., CPU, memory, disk) and service status checks, making it essential for operational awareness.
   
   ```python
   @bp.route('/health')
   @admin_required
   def health():
       """Get API health status"""
       try:
           # Check system health
           memory = psutil.virtual_memory()
           disk = psutil.disk_usage('/')
           cpu_percent = psutil.cpu_percent(interval=0.1)
           
           # Check service health
           services_status = {
               "server": "healthy",
               "database": check_service_status("database"),
               "cache": check_service_status("cache"),
               "storage": check_service_status("storage")
           }
           
           return jsonify({
               "status": "healthy",
               "timestamp": datetime.now().isoformat(),
               "services": services_status,
               "system": {
                   "cpu_usage": f"{cpu_percent}%",
                   "memory": {
                       "total": memory.total,
                       "used": memory.used,
                       "free": memory.available,
                       "percent": memory.percent
                   },
                   "disk": {
                       "total": disk.total,
                       "used": disk.used,
                       "free": disk.free,
                       "percent": disk.percent
                   }
               }
           }), 200
       except Exception as e:
           logger.error(f"Health check failed: {str(e)}")
           return jsonify({
               "status": "unhealthy",
               "error": str(e),
               "timestamp": datetime.now().isoformat()
           }), 500
   ```

2. **System Status Helper Function (e.g., get_open_ports)**: This function is unique for its network monitoring capabilities, specifically checking open ports from a predefined list. It's part of a larger set of helper functions and demonstrates how the code interacts with system resources.
   
   ```python
   def get_open_ports():
       """
       Get information about open ports
       """
       try:
           connections = psutil.net_connections(kind='inet')
           open_ports = []
           
           for conn in connections:
               if conn.laddr and conn.laddr.port in MONITORED_PORTS:
                   try:
                       if conn.pid:
                           process = psutil.Process(conn.pid)
                           port_data = {
                               "port": conn.laddr.port,
                               "pid": conn.pid,
                               "process_name": process.name(),
                               "status": conn.status,
                               "local_address": f"{conn.laddr.ip}:{conn.laddr.port}",
                               "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "None"
                           }
                           open_ports.append(port_data)
                   except (psutil.NoSuchProcess, psutil.AccessDenied):
                       continue
           
           return open_ports
       except Exception as e:
           logger.error(f"Error getting open ports: {str(e)}")
           return []
   ```

3. **Documentation Segment from System Status Route**: This docstring provides clear documentation for the `/system` route, explaining its purpose and what it returns. It's unique as it outlines the structure of the response, which is helpful for API users.
   
   ```
   @bp.route('/system', methods=['GET'])
   @admin_required
   def system_status():
       """
       Get detailed system status
       """
       # [Function body omitted for brevity]
   ```
   (The full docstring describes the route's output, including system metrics, network info, and processes, making it a strong documentation example.)