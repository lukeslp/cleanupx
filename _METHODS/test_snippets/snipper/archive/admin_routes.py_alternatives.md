# Alternatives for admin_routes.py

1. **Health Check Route**: This snippet is unique for its use of psutil to monitor system resources and service status, providing a comprehensive health overview. It's important for real-time admin monitoring.
   
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

2. **Get Open Ports Function**: This is a unique utility for network monitoring, filtering and processing network connections with psutil. It's important for security and diagnostics in an admin context.
   
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