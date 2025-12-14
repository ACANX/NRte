#!/usr/bin/env python3
"""
监控信息采集模块 - Docker容器适配版
所有监控逻辑都封装在此文件中
"""

import os
import sys
import json
import platform
import subprocess
import psutil
import socket
import datetime
from pathlib import Path

def collect_system_info():
    """收集所有系统监控信息"""
    try:
        info = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "host_info": get_host_info(),
            "cpu_info": get_cpu_info(),
            "memory_info": get_memory_info(),
            "disk_info": get_disk_info(),
            "network_info": get_network_info(),
            "os_info": get_os_info(),
            "processes": get_process_info(),
            "system_status": get_system_status(),
            "container_info": get_container_info()
        }
        return info
    except Exception as e:
        return {"error": f"收集系统信息失败: {str(e)}"}

def get_host_info():
    """获取主机基本信息"""
    try:
        return {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "fqdn": socket.getfqdn() if hasattr(socket, 'getfqdn') else "未知"
        }
    except:
        return {"error": "无法获取主机信息"}

def get_cpu_info():
    """获取CPU信息"""
    try:
        cpu_data = {}
        
        # 基础CPU信息
        cpu_data["physical_cores"] = psutil.cpu_count(logical=False)
        cpu_data["logical_cores"] = psutil.cpu_count(logical=True)
        cpu_data["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        
        # CPU频率
        try:
            freq = psutil.cpu_freq()
            if freq:
                cpu_data["current_freq"] = f"{freq.current:.2f} MHz"
                cpu_data["max_freq"] = f"{freq.max:.2f} MHz" if freq.max > 0 else "未知"
        except:
            pass
        
        return cpu_data
    except Exception as e:
        return {"error": f"获取CPU信息失败: {str(e)}"}

def get_memory_info():
    """获取内存信息"""
    try:
        memory_data = {}
        virtual_memory = psutil.virtual_memory()
        
        # 修正内存使用率计算
        memory_data["total"] = f"{virtual_memory.total / (1024**3):.2f} GB"
        memory_data["available"] = f"{virtual_memory.available / (1024**3):.2f} GB"
        memory_data["used"] = f"{virtual_memory.used / (1024**3):.2f} GB"
        
        # 确保使用率是百分比数值
        memory_data["percent"] = virtual_memory.percent
        memory_data["percent_str"] = f"{virtual_memory.percent}%"
        
        return memory_data
    except Exception as e:
        return {"error": f"获取内存信息失败: {str(e)}"}

def get_disk_info():
    """获取磁盘信息 - 适配容器环境"""
    try:
        disk_data = {"partitions": []}
        
        # 在容器中，只检查重要的挂载点
        important_mounts = ["/", "/tmp", "/home", "/var", "/usr", "/etc"]
        
        for partition in psutil.disk_partitions():
            try:
                # 过滤掉奇怪的挂载点（如/etc/hosts）
                mountpoint = partition.mountpoint
                device = partition.device
                
                # 跳过特殊文件挂载
                if mountpoint.startswith("/etc/") and os.path.isfile(mountpoint):
                    continue
                    
                if mountpoint.startswith("/dev/"):
                    continue
                    
                # 只检查目录挂载点
                if not os.path.isdir(mountpoint):
                    continue
                
                usage = psutil.disk_usage(mountpoint)
                partition_info = {
                    "device": device,
                    "mountpoint": mountpoint,
                    "total": f"{usage.total / (1024**3):.2f} GB",
                    "used": f"{usage.used / (1024**3):.2f} GB",
                    "free": f"{usage.free / (1024**3):.2f} GB",
                    "percent": usage.percent,
                    "percent_str": f"{usage.percent}%"
                }
                disk_data["partitions"].append(partition_info)
                
                # 限制显示数量
                if len(disk_data["partitions"]) >= 5:
                    break
                    
            except (PermissionError, OSError):
                continue
            except:
                continue
        
        # 如果没有找到分区，至少显示根目录
        if not disk_data["partitions"]:
            try:
                usage = psutil.disk_usage("/")
                disk_data["partitions"].append({
                    "device": "root",
                    "mountpoint": "/",
                    "total": f"{usage.total / (1024**3):.2f} GB",
                    "used": f"{usage.used / (1024**3):.2f} GB",
                    "free": f"{usage.free / (1024**3):.2f} GB",
                    "percent": usage.percent,
                    "percent_str": f"{usage.percent}%"
                })
            except:
                pass
        
        return disk_data
    except Exception as e:
        return {"error": f"获取磁盘信息失败: {str(e)}"}

def get_network_info():
    """获取网络信息 - 适配容器环境"""
    try:
        network_data = {"interfaces": []}
        
        # 获取内网IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            internal_ip = s.getsockname()[0]
            s.close()
        except:
            # 备选方法获取IP
            try:
                internal_ip = socket.gethostbyname(socket.gethostname())
            except:
                internal_ip = "无法获取"
        
        network_data["internal_ip"] = internal_ip
        
        # 尝试获取网络接口信息
        try:
            for interface, addrs in psutil.net_if_addrs().items():
                iface_info = {
                    "interface": interface,
                    "addresses": []
                }
                
                for addr in addrs:
                    addr_info = {
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask if hasattr(addr, 'netmask') else None,
                    }
                    iface_info["addresses"].append(addr_info)
                
                network_data["interfaces"].append(iface_info)
                
                # 限制显示数量
                if len(network_data["interfaces"]) >= 3:
                    break
        except:
            # 如果无法获取接口信息，至少显示IP
            network_data["interfaces"] = [{
                "interface": "eth0",
                "addresses": [{
                    "family": "AF_INET",
                    "address": internal_ip,
                    "netmask": "255.255.255.0"
                }]
            }]
        
        # 获取网络IO统计
        try:
            net_io = psutil.net_io_counters()
            network_data["io_stats"] = {
                "bytes_sent": f"{net_io.bytes_sent / (1024**2):.2f} MB",
                "bytes_recv": f"{net_io.bytes_recv / (1024**2):.2f} MB",
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        except:
            pass
        
        return network_data
    except Exception as e:
        return {"error": f"获取网络信息失败: {str(e)}"}

def get_os_info():
    """获取操作系统信息"""
    try:
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.architecture()[0]
        }
    except Exception as e:
        return {"error": f"获取OS信息失败: {str(e)}"}

def get_process_info():
    """获取进程信息"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username', 'status']):
            try:
                proc_info = proc.info
                processes.append(proc_info)
                if len(processes) >= 30:  # 获取前30个进程
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # 按CPU使用率排序
        processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        return processes[:15]  # 返回前15个进程
    except Exception as e:
        return [{"error": f"获取进程信息失败: {str(e)}"}]

def get_system_status():
    """获取系统当前状态"""
    try:
        status = {}
        
        # CPU使用率
        status["cpu_usage"] = psutil.cpu_percent(interval=0.5)
        
        # 内存使用率
        memory = psutil.virtual_memory()
        status["memory_usage"] = memory.percent
        
        # 系统启动时间
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        status["boot_time"] = boot_time.strftime("%Y-%m-%d %H:%M:%S")
        status["uptime"] = str(datetime.datetime.now() - boot_time).split('.')[0]  # 去除微秒部分
        
        # 当前用户
        try:
            status["current_user"] = psutil.Process().username()
        except:
            status["current_user"] = os.getenv("USER", "未知")
        
        # 负载平均值（如果有）
        if hasattr(os, 'getloadavg'):
            try:
                load = os.getloadavg()
                status["load_average"] = {
                    "1min": load[0],
                    "5min": load[1],
                    "15min": load[2]
                }
            except:
                pass
        
        return status
    except Exception as e:
        return {"error": f"获取系统状态失败: {str(e)}"}

def get_container_info():
    """获取容器环境信息"""
    try:
        container_info = {}
        
        # 检查是否在容器中运行
        container_info["is_container"] = False
        
        # 检查常见的容器标识文件
        container_markers = [
            "/.dockerenv",
            "/run/.containerenv",
            "/proc/1/cgroup"
        ]
        
        for marker in container_markers:
            if os.path.exists(marker):
                container_info["is_container"] = True
                break
        
        # 如果在容器中，尝试获取容器信息
        if container_info["is_container"]:
            # 检查cgroup信息
            try:
                with open("/proc/1/cgroup", "r") as f:
                    cgroup_content = f.read()
                    if "docker" in cgroup_content:
                        container_info["container_type"] = "Docker"
                    elif "kubepods" in cgroup_content:
                        container_info["container_type"] = "Kubernetes"
                    else:
                        container_info["container_type"] = "Container"
            except:
                container_info["container_type"] = "未知"
            
            # 获取环境变量中的容器信息
            container_info["container_id"] = os.getenv("HOSTNAME", "未知")
            container_info["image_name"] = os.getenv("CONTAINER_IMAGE", "未知")
        
        return container_info
    except:
        return {"is_container": False, "container_type": "未知"}

def generate_html_report(system_info, output_file="Monitor.html"):
    """生成HTML报告"""
    try:
        # 提取各个部分的数据
        timestamp = system_info.get('timestamp', '未知')
        container_info = system_info.get('container_info', {})
        is_container = container_info.get('is_container', False)
        container_type = container_info.get('container_type', '未知')
        
        # 系统状态数据
        system_status = system_info.get('system_status', {})
        if isinstance(system_status, dict) and 'error' not in system_status:
            cpu_usage = system_status.get('cpu_usage', 0)
            memory_usage = system_status.get('memory_usage', 0)
            uptime = system_status.get('uptime', '未知')
            boot_time = system_status.get('boot_time', '未知')
            current_user = system_status.get('current_user', '未知')
        else:
            cpu_usage = 0
            memory_usage = 0
            uptime = '未知'
            boot_time = '未知'
            current_user = '未知'
        
        # CPU信息数据
        cpu_info = system_info.get('cpu_info', {})
        if isinstance(cpu_info, dict) and 'error' not in cpu_info:
            physical_cores = cpu_info.get('physical_cores', '未知')
            logical_cores = cpu_info.get('logical_cores', '未知')
            current_freq = cpu_info.get('current_freq', '未知')
            max_freq = cpu_info.get('max_freq', '未知')
            cpu_percent = cpu_info.get('cpu_percent', 0)
        else:
            physical_cores = '未知'
            logical_cores = '未知'
            current_freq = '未知'
            max_freq = '未知'
            cpu_percent = 0
        
        # 内存信息数据
        memory_info = system_info.get('memory_info', {})
        if isinstance(memory_info, dict) and 'error' not in memory_info:
            memory_total = memory_info.get('total', '未知')
            memory_used = memory_info.get('used', '未知')
            memory_available = memory_info.get('available', '未知')
            memory_percent = memory_info.get('percent', 0)
        else:
            memory_total = '未知'
            memory_used = '未知'
            memory_available = '未知'
            memory_percent = 0
        
        # 磁盘信息
        disk_info = system_info.get('disk_info', {})
        partitions = []
        if isinstance(disk_info, dict) and 'error' not in disk_info:
            partitions = disk_info.get('partitions', [])
        
        # 生成磁盘信息表格行
        disk_rows = ""
        if isinstance(partitions, list):
            for part in partitions[:5]:  # 只显示前5个分区
                if isinstance(part, dict):
                    mountpoint = part.get("mountpoint", "未知")
                    device = part.get("device", "未知")
                    total = part.get("total", "未知")
                    used = part.get("used", "未知")
                    free = part.get("free", "未知")
                    percent_num = part.get("percent", 0)
                    
                    disk_rows += f'''
                    <tr>
                        <td>{mountpoint}</td>
                        <td>{device}</td>
                        <td>{total}</td>
                        <td>{used}</td>
                        <td>{free}</td>
                        <td>
                            {percent_num}%
                            <div class="progress-bar">
                                <div class="progress-fill {"warning" if percent_num > 70 else "danger" if percent_num > 90 else ""}" 
                                     style="width: {percent_num}%"></div>
                            </div>
                        </td>
                    </tr>
                    '''
        
        # 网络信息
        network_info = system_info.get('network_info', {})
        if isinstance(network_info, dict) and 'error' not in network_info:
            internal_ip = network_info.get('internal_ip', '未知')
            interfaces = network_info.get('interfaces', [])
            io_stats = network_info.get('io_stats', {})
        else:
            internal_ip = '未知'
            interfaces = []
            io_stats = {}
        
        # 生成网络接口信息
        interface_html = ""
        if isinstance(interfaces, list):
            for iface in interfaces[:3]:  # 只显示前3个接口
                if isinstance(iface, dict):
                    interface_name = iface.get("interface", "未知")
                    addresses = iface.get("addresses", [])
                    ip_addresses = []
                    if isinstance(addresses, list):
                        for addr in addresses:
                            if isinstance(addr, dict):
                                # 检查是否是IPv4地址
                                family = str(addr.get('family', ''))
                                if 'AF_INET' in family or 'AddressFamily.AF_INET' in family:
                                    ip_addresses.append(addr.get('address', ''))
                    
                    if ip_addresses:
                        interface_html += f'''
                        <div class="info-item">
                            <strong>{interface_name}:</strong><br>
                            {"<br>".join(ip_addresses)}
                        </div>
                        '''
        
        # 操作系统信息
        os_info = system_info.get('os_info', {})
        if isinstance(os_info, dict) and 'error' not in os_info:
            os_system = os_info.get('system', '未知')
            os_release = os_info.get('release', '未知')
            os_architecture = os_info.get('architecture', '未知')
        else:
            os_system = '未知'
            os_release = '未知'
            os_architecture = '未知'
        
        # 进程信息
        processes = system_info.get('processes', [])
        
        # 生成进程信息表格行
        process_rows = ""
        if isinstance(processes, list):
            for proc in processes[:10]:  # 只显示前10个进程
                if isinstance(proc, dict):
                    pid = proc.get("pid", "未知")
                    name = str(proc.get("name", "未知"))[:25]
                    cpu_percent_proc = proc.get("cpu_percent", 0)
                    memory_percent = proc.get("memory_percent", 0)
                    
                    process_rows += f'''
                    <tr>
                        <td>{pid}</td>
                        <td title="{proc.get('name', '未知')}">{name}</td>
                        <td>{cpu_percent_proc}%</td>
                        <td>{memory_percent:.1f}%</td>
                    </tr>
                    '''
        
        # 主机信息
        host_info = system_info.get('host_info', {})
        hostname = host_info.get('hostname', '未知') if isinstance(host_info, dict) and 'error' not in host_info else '未知'
        
        # 准备网络IO统计HTML
        io_stats_html = ""
        if io_stats:
            io_stats_html = f'''
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{io_stats.get("bytes_sent", "0 MB")}</div>
                    <div class="stat-label">发送总量</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{io_stats.get("bytes_recv", "0 MB")}</div>
                    <div class="stat-label">接收总量</div>
                </div>
            </div>
            '''
        
        # 准备容器标识HTML
        container_badge_html = f'<span class="container-badge">{container_type} 容器</span>' if is_container else ''
        
        # 确定进度条CSS类
        cpu_progress_class = "warning" if cpu_percent > 70 else "danger" if cpu_percent > 90 else ""
        memory_progress_class = "warning" if memory_percent > 70 else "danger" if memory_percent > 90 else ""
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统监控信息 - 容器版</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .section {{
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 5px solid #007bff;
        }}
        .section h2 {{
            color: #495057;
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 1.5em;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
        }}
        .info-item {{
            padding: 12px;
            background: white;
            border-radius: 6px;
            border-left: 4px solid #28a745;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        .info-item.warning {{
            border-left-color: #ffc107;
        }}
        .info-item.danger {{
            border-left-color: #dc3545;
        }}
        .timestamp {{
            color: #6c757d;
            font-style: italic;
            margin-bottom: 20px;
            font-size: 0.9em;
        }}
        .progress-bar {{
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 8px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.5s ease;
        }}
        .progress-fill.warning {{
            background: linear-gradient(90deg, #ffc107, #fd7e14);
        }}
        .progress-fill.danger {{
            background: linear-gradient(90deg, #dc3545, #c82333);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 0.9em;
        }}
        th, td {{
            padding: 10px;
            border: 1px solid #dee2e6;
            text-align: left;
        }}
        th {{
            background: #007bff;
            color: white;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        tr:hover {{
            background: #e9ecef;
        }}
        .container-badge {{
            display: inline-block;
            padding: 4px 12px;
            background: #17a2b8;
            color: white;
            border-radius: 20px;
            font-size: 0.8em;
            margin-left: 10px;
            font-weight: 600;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }}
        .stat-item {{
            background: white;
            padding: 10px;
            border-radius: 6px;
            text-align: center;
            border: 1px solid #dee2e6;
        }}
        .stat-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #007bff;
        }}
        .stat-label {{
            font-size: 0.8em;
            color: #6c757d;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 系统监控信息 
            {container_badge_html}
        </h1>
        <div class="timestamp">采集时间: {timestamp} | 运行环境: {f"{container_type} 容器" if is_container else "物理机/虚拟机"}</div>
        
        <!-- 系统状态 -->
        <div class="section">
            <h2>🔄 系统状态</h2>
            <div class="info-grid">
                <div class="info-item">
                    <strong>CPU使用率:</strong> {cpu_percent}%
                    <div class="progress-bar">
                        <div class="progress-fill {cpu_progress_class}" 
                             style="width: {cpu_percent}%"></div>
                    </div>
                </div>
                <div class="info-item">
                    <strong>内存使用率:</strong> {memory_percent}%
                    <div class="progress-bar">
                        <div class="progress-fill {memory_progress_class}" 
                             style="width: {memory_percent}%"></div>
                    </div>
                </div>
                <div class="info-item">
                    <strong>系统运行时间:</strong> {uptime}
                </div>
                <div class="info-item">
                    <strong>启动时间:</strong> {boot_time}
                </div>
                <div class="info-item">
                    <strong>当前用户:</strong> {current_user}
                </div>
                <div class="info-item">
                    <strong>主机名:</strong> {hostname}
                </div>
            </div>
        </div>
        
        <!-- CPU信息 -->
        <div class="section">
            <h2>💻 CPU信息</h2>
            <div class="info-grid">
                <div class="info-item">
                    <strong>物理核心:</strong> {physical_cores}
                </div>
                <div class="info-item">
                    <strong>逻辑核心:</strong> {logical_cores}
                </div>
                <div class="info-item">
                    <strong>当前频率:</strong> {current_freq}
                </div>
                <div class="info-item">
                    <strong>最大频率:</strong> {max_freq}
                </div>
            </div>
        </div>
        
        <!-- 内存信息 -->
        <div class="section">
            <h2>🧠 内存信息</h2>
            <div class="info-grid">
                <div class="info-item">
                    <strong>总内存:</strong> {memory_total}
                </div>
                <div class="info-item">
                    <strong>已使用:</strong> {memory_used}
                </div>
                <div class="info-item">
                    <strong>可用内存:</strong> {memory_available}
                </div>
                <div class="info-item">
                    <strong>使用率:</strong> {memory_percent}%
                </div>
            </div>
        </div>
        
        <!-- 磁盘信息 -->
        <div class="section">
            <h2>💾 磁盘信息</h2>
            <table>
                <thead>
                    <tr>
                        <th>挂载点</th>
                        <th>设备</th>
                        <th>总空间</th>
                        <th>已用空间</th>
                        <th>可用空间</th>
                        <th>使用率</th>
                    </tr>
                </thead>
                <tbody>
                    {disk_rows if disk_rows else '<tr><td colspan="6" style="text-align:center;">无磁盘信息</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <!-- 网络信息 -->
        <div class="section">
            <h2>🌐 网络信息</h2>
            <div class="info-item">
                <strong>内网IP:</strong> {internal_ip}
            </div>
            <h3>网络接口:</h3>
            <div class="info-grid">
                {interface_html if interface_html else '<div class="info-item">使用容器默认网络</div>'}
            </div>
            {io_stats_html}
        </div>
        
        <!-- 操作系统信息 -->
        <div class="section">
            <h2>🖥️ 操作系统信息</h2>
            <div class="info-grid">
                <div class="info-item">
                    <strong>系统:</strong> {os_system}
                </div>
                <div class="info-item">
                    <strong>版本:</strong> {os_release}
                </div>
                <div class="info-item">
                    <strong>架构:</strong> {os_architecture}
                </div>
            </div>
        </div>
        
        <!-- 进程信息 -->
        <div class="section">
            <h2>⚙️ 进程信息 (前10个)</h2>
            <table>
                <thead>
                    <tr>
                        <th>PID</th>
                        <th>名称</th>
                        <th>CPU%</th>
                        <th>内存%</th>
                    </tr>
                </thead>
                <tbody>
                    {process_rows if process_rows else '<tr><td colspan="4" style="text-align:center;">无进程信息</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("HTML报告生成成功")
        return True
        
    except Exception as e:
        print(f"生成HTML报告失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def run_monitor():
    """执行监控采集并生成报告"""
    try:
        print("开始采集系统监控信息...")
        system_info = collect_system_info()
        print("信息采集完成")
        
        if generate_html_report(system_info):
            print("HTML报告生成成功")
            return True
        else:
            print("HTML报告生成失败")
            return False
    except Exception as e:
        print(f"监控采集失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 当直接运行此脚本时执行监控采集
    success = run_monitor()
    sys.exit(0 if success else 1)
