# Alternatives for api_routes.py

```
@bp.route('/health')
def health_check():
    """Basic health check endpoint"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        result = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
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
        }
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500
```

```
def format_datetime(timestamp):
    """Format timestamp for display"""
    if timestamp is None:
        return "Never"
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
```