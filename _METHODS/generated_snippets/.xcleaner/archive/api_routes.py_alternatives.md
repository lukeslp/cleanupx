# Alternatives for api_routes.py

Here are other notable snippets that are important but slightly less central than the best version. They include unique implementations like the health check route (for system monitoring) and the API documentation serving route (for serving static files securely).

1. **Health Check Route**: This snippet is unique because it integrates system metrics (e.g., CPU, memory, disk usage) using the `psutil` library, providing a robust way to monitor API health. It's essential for operational awareness in production environments.
   
   ```python
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

2. **API Documentation Serving Route**: This is a unique snippet for securely serving static documentation files, protected by the `@admin_required` decorator. It's important for maintaining API usability and is a good example of file handling in a Flask app.
   
   ```python
   @bp.route('/admin/docs')
   @admin_required
   def api_docs():
       """Serve API documentation"""
       try:
           docs_path = BASE_DIR / 'API_DOCUMENTATION.md'
           if docs_path.exists():
               return send_file(str(docs_path), mimetype='text/markdown')
           else:
               return jsonify({"error": "Documentation not found"}), 404
       except Exception as e:
           logger.error(f"Error serving documentation: {str(e)}")
           return jsonify({"error": str(e)}), 500
   ```