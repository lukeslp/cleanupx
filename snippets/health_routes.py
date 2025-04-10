from flask import Blueprint, jsonify, render_template
import psutil
import socket
from datetime import datetime
import logging
import os
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('health', __name__)

@bp.route('/', methods=['GET'])
def health_check():
    """
    Main health check endpoint
    """
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Check services health
        services = check_services()

        return jsonify({
            "status": "healthy",
            "timestamp": str(datetime.now()),
            "server": {
                "hostname": hostname,
                "ip": ip,
                "uptime": str(datetime.now() - datetime.fromtimestamp(psutil.boot_time()))
            },
            "services": services,
            "system": {
                "cpu_usage": f"{cpu_percent}%",
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": f"{memory.percent}%"
                },
                "disk": {
                    "total": disk.total,
                    "free": disk.free,
                    "percent": f"{disk.percent}%"
                }
            }
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": str(datetime.now())
        }), 500

def check_services():
    """
    Check status of core services
    """
    services = {}
    
    # Example service checks - customize as needed
    services["database"] = check_database_connection()
    services["cache"] = check_cache_connection()
    services["external_api"] = check_external_api()
    
    return services

def check_database_connection():
    """
    Check database connection
    """
    try:
        # This is a placeholder - implement actual database check
        # Example: if using SQLAlchemy, check db.engine.execute("SELECT 1")
        return "healthy"
    except Exception as e:
        logger.error(f"Database check failed: {str(e)}")
        return "unhealthy"

def check_cache_connection():
    """
    Check cache service connection
    """
    try:
        # This is a placeholder - implement actual cache check
        # Example: if using Redis, check redis_client.ping()
        return "not_configured"
    except Exception as e:
        logger.error(f"Cache check failed: {str(e)}")
        return "unhealthy"

def check_external_api():
    """
    Check external API connectivity
    """
    try:
        # This is a placeholder - implement actual API check
        import requests
        response = requests.get("https://api.openai.com/v1/models", timeout=5)
        return "healthy" if response.status_code == 200 else "degraded"
    except Exception as e:
        logger.error(f"External API check failed: {str(e)}")
        return "unhealthy"

@bp.route('/services', methods=['GET'])
def service_health():
    """
    Check status of all required services
    """
    try:
        services = check_services()
        
        # Check processes running status
        services.update({
            "web_server": check_process("nginx") or check_process("apache2"),
            "app_server": check_process("gunicorn") or check_process("uwsgi")
        })
        
        # Return 200 even if some services are down, let frontend handle display
        all_healthy = all(status == "healthy" for status in services.values())
        status = "healthy" if all_healthy else "degraded"
        
        return jsonify({
            "status": status,
            "timestamp": str(datetime.now()),
            "services": services
        }), 200
    except Exception as e:
        logger.error(f"Service health check failed: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": str(datetime.now())
        }), 500

def check_process(process_name):
    """
    Check if a process is running
    """
    try:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == process_name:
                return "healthy"
        return "not_running"
    except Exception as e:
        logger.error(f"Error checking process {process_name}: {str(e)}")
        return "error"

@bp.route('/dashboard', methods=['GET'])
def dashboard():
    """
    Serve the server status dashboard
    """
    try:
        return render_template('health/dashboard.html')
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500

@bp.route('/detailed', methods=['GET'])
def detailed_status():
    """
    Get detailed system status
    """
    try:
        # Get CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_times = psutil.cpu_times()
        
        # Get memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Get disk metrics
        disk_partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_partitions.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "usage": {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    }
                })
            except (PermissionError, FileNotFoundError):
                pass
        
        # Get network metrics
        network_io = psutil.net_io_counters()
        
        # Get process metrics
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort processes by memory usage
        processes = sorted(processes, key=lambda p: p.get('memory_percent', 0), reverse=True)[:10]
        
        return jsonify({
            "status": "healthy",
            "timestamp": str(datetime.now()),
            "hostname": socket.gethostname(),
            "cpu": {
                "percent": cpu_percent,
                "times": {
                    "user": cpu_times.user,
                    "system": cpu_times.system,
                    "idle": cpu_times.idle
                }
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent,
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percent": swap.percent
                }
            },
            "disk": {
                "partitions": disk_partitions
            },
            "network": {
                "bytes_sent": network_io.bytes_sent,
                "bytes_recv": network_io.bytes_recv,
                "packets_sent": network_io.packets_sent,
                "packets_recv": network_io.packets_recv
            },
            "top_processes": processes
        }), 200
    except Exception as e:
        logger.error(f"Error in detailed status: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": str(datetime.now())
        }), 500 