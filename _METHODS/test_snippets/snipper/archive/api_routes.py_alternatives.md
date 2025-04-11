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

Explanation of Selection:
- **Best Version**: The `admin_required` decorator is selected as the most important and unique snippet because it encapsulates a custom authentication mechanism, including error handling, logging, and token validation. It's reusable, central to securing routes, and demonstrates best practices for decorators in Flask.
- **Alternatives**: The `/health` route is chosen as an alternative because it provides a practical, system-monitoring feature using `psutil`, which is unique in its integration of system metrics. It's important for API health checks but is less reusable than the decorator. Other similar routes (e.g., `/dashboard/api/status`) were omitted as they are redundant with this one.