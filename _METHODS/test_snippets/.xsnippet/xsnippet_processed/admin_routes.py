from flask import Blueprint, jsonify, render_template, send_file, request
import psutil
import subprocess
from datetime import datetime
import logging
import os
from pathlib import Path
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__, 
              template_folder='../templates',
              static_folder='../static')

# Constants
MONITORED_PORTS = [80, 443, 5000, 5001, 5002, 8000]
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'default_token')

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            logger.warning("No authorization header provided")
            return jsonify({"error": "No authorization header"}), 401
        
        try:
            token_type, token = auth_header.split(' ')
            if token_type.lower() != 'bearer':
                logger.warning("Invalid authorization type")
                return jsonify({"error": "Invalid authorization type"}), 401
            
            if token != ADMIN_TOKEN:
                logger.warning("Invalid admin token provided")
                return jsonify({"error": "Unauthorized"}), 403
                
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Auth error: {str(e)}")
            return jsonify({"error": "Invalid authorization header"}), 401
            
    return decorated_function

@bp.route('/')
@admin_required
def dashboard():
    """Serve the admin dashboard"""
    logger.info("Serving admin dashboard")
    return render_template('admin/dashboard.html')

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

def check_service_status(service_name):
    """Check if a service is running"""
    # This is a placeholder - implement your service checks here
    return "not_configured"

@bp.route('/docs')
@admin_required
def api_docs():
    """Serve API documentation"""
    try:
        docs_path = Path(__file__).parent.parent / 'API_DOCUMENTATION.md'
        if docs_path.exists():
            return send_file(docs_path, mimetype='text/markdown')
        else:
            return jsonify({"error": "Documentation not found"}), 404
    except Exception as e:
        logger.error(f"Error serving documentation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/system', methods=['GET'])
@admin_required
def system_status():
    """
    Get detailed system status
    """
    try:
        # Get system metrics
        memory = get_memory_usage()
        cpu = get_cpu_usage()
        disk = get_disk_usage()
        uptime = get_system_uptime()
        
        # Get port usage
        port_traffic = get_port_traffic()
        open_ports = get_open_ports()
        
        # Get high resource consumers
        high_consumers = get_high_resource_consumers()

        return jsonify({
            "status": "healthy",
            "timestamp": str(datetime.now()),
            "system": {
                "memory": memory,
                "cpu": cpu,
                "disk": disk,
                "uptime": uptime
            },
            "network": {
                "open_ports": open_ports,
                "port_traffic": port_traffic
            },
            "processes": high_consumers
        }), 200
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": str(datetime.now())
        }), 500

def get_memory_usage():
    """
    Get memory usage statistics
    """
    memory = psutil.virtual_memory()
    return {
        "total": memory.total,
        "available": memory.available,
        "used": memory.used,
        "percent": memory.percent
    }

def get_cpu_usage():
    """
    Get CPU usage statistics
    """
    cpu_percent = psutil.cpu_percent(interval=0.1)
    return {
        "used_percent": cpu_percent,
        "free_percent": 100 - cpu_percent
    }

def get_disk_usage():
    """
    Get disk usage statistics
    """
    disk = psutil.disk_usage('/')
    return {
        "total": disk.total,
        "used": disk.used,
        "free": disk.free,
        "percent": disk.percent
    }

def get_system_uptime():
    """
    Get system uptime information
    """
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    return {
        "since": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
        "uptime": str(uptime)
    }

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

def get_port_traffic():
    """
    Get port traffic statistics
    """
    traffic_summary = {port: {"connections": 0} for port in MONITORED_PORTS}
    
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port in MONITORED_PORTS:
                traffic_summary[conn.laddr.port]["connections"] += 1
        
        return [{"port": port, "connections": data["connections"]} 
                for port, data in traffic_summary.items()]
    except Exception as e:
        logger.error(f"Error getting port traffic: {str(e)}")
        return []

def get_high_resource_consumers():
    """
    Get processes using high system resources
    """
    processes = []
    for proc in psutil.process_iter(["pid", "name", "username", "cmdline"]):
        try:
            process_info = proc.info
            process_info['cpu_percent'] = proc.cpu_percent(interval=0.1)
            process_info['memory_percent'] = proc.memory_percent()
            process_info['cmdline'] = ' '.join(proc.cmdline())
            processes.append(process_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # Sort and get top consumers
    top_cpu = sorted(processes, key=lambda p: p["cpu_percent"], reverse=True)[:10]
    top_memory = sorted(processes, key=lambda p: p["memory_percent"], reverse=True)[:10]
    
    return {
        "cpu": top_cpu,
        "memory": top_memory
    }

@bp.route('/logs', methods=['GET'])
@admin_required
def get_logs():
    """
    Get recent log entries
    """
    try:
        log_dir = Path(os.getenv('LOG_DIR', 'logs'))
        logs = []
        
        if not log_dir.exists():
            return jsonify({
                "success": False,
                "error": "Log directory not found"
            }), 404
        
        for log_file in log_dir.glob("*.log"):
            try:
                with open(log_file, 'r') as f:
                    # Get last 100 lines
                    lines = f.readlines()[-100:]
                    logs.append({
                        "file": log_file.name,
                        "entries": lines
                    })
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {str(e)}")
        
        return jsonify({
            "success": True,
            "logs": logs
        }), 200
    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@bp.route('/cleanup', methods=['POST'])
@admin_required
def cleanup_system():
    """
    Perform system cleanup tasks
    """
    try:
        temp_dir = Path(os.getenv('TEMP_DIR', 'temp'))
        log_dir = Path(os.getenv('LOG_DIR', 'logs'))
        
        results = {
            "temp_files_deleted": 0,
            "logs_rotated": 0
        }
        
        # Clean temp files
        if temp_dir.exists():
            current_time = datetime.now()
            for file_path in temp_dir.glob('*'):
                if file_path.is_file():
                    file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_age.total_seconds() > 3600:  # 1 hour
                        file_path.unlink()
                        results["temp_files_deleted"] += 1
        
        # Rotate logs
        if log_dir.exists():
            current_time = datetime.now()
            for log_file in log_dir.glob("*.log.*"):
                file_age = current_time - datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_age.total_seconds() > 7 * 24 * 3600:  # 7 days
                    log_file.unlink()
                    results["logs_rotated"] += 1
        
        return jsonify({
            "success": True,
            "results": results
        }), 200
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500 