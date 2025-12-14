import sys
import os
import time
import subprocess
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse


app = FastAPI()

@app.get("/")
def home():
    try:
        with open("index.html", "r", encoding="utf-8") as file:
            html_content = file.read()
        
        # 正确设置响应头的方法
        response = HTMLResponse(content=html_content)
        response.headers["x-lang"] = "Python"
        response.headers["x-custom"] = "FastAPI"  # 可以添加更多自定义头
        return response
    except FileNotFoundError:
        error_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>404 - File Not Found</h1>
            <p>index.html file not found</p>
        </body>
        </html>
        """
        response = HTMLResponse(content=error_content, status_code=404)
        response.headers["x-lang"] = "Python"
        return response

@app.get("/Hello")
def hello():
    # 获取当前UTC时间
    current_time = datetime.utcnow()
    # 构建响应数据
    response_data = {
        "code": 1,
        "message": "OK",
        "data": {
            "hello": "world",
            "ts": int(current_time.timestamp() * 1000),  # UTC时间戳（毫秒）
            "date": current_time.strftime("%Y-%m-%d")    # 当前日期 yyyy-MM-dd 格式
        }
    }
    return response_data

# 添加一个测试端点来验证响应头
@app.get("/Header")
def headers():
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"message": "Header"})
    response.headers["x-lang"] = "Python"
    response.headers["x-api-version"] = "1.0"
    return response

@app.get("/Monitor")
def monitor():
    """执行监控采集并返回结果"""
    try:
        # 检查Monitor.py是否存在
        if not os.path.exists("Monitor.py"):
            error_html = "<h1>Monitor.py not found</h1>"
            response = HTMLResponse(content=error_html, status_code=500)
            response.headers["x-lang"] = "Python"
            return response
        # 执行监控脚本，设置超时时间为60秒
        result = subprocess.run(
            ["python", "Monitor.py"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=60
        )
        if result.returncode != 0:
            # 如果监控脚本执行失败
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Monitor Error</title></head>
            <body>
                <h1>监控脚本执行失败</h1>
                <p>返回码: {result.returncode}</p>
                <h3>错误输出:</h3>
                <pre>{result.stderr}</pre>
                <h3>标准输出:</h3>
                <pre>{result.stdout}</pre>
            </body>
            </html>
            """
            response = HTMLResponse(content=error_html, status_code=500)
            response.headers["x-lang"] = "Python"
            return response
        # 读取生成的Monitor.html文件
        if os.path.exists("Monitor.html"):
            with open("Monitor.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            response = HTMLResponse(content=html_content)
            response.headers["x-lang"] = "Python"
            return response
        else:
            error_html = "<h1>Monitor.html not generated</h1>"
            response = HTMLResponse(content=error_html, status_code=500)
            response.headers["x-lang"] = "Python"
            return response
    except subprocess.TimeoutExpired:
        error_html = "<h1>监控脚本执行超时（60秒）</h1>"
        response = HTMLResponse(content=error_html, status_code=504)
        response.headers["x-lang"] = "Python"
        return response
    except Exception as e:
        error_html = f"<h1>监控端点错误: {str(e)}</h1>"
        response = HTMLResponse(content=error_html, status_code=500)
        response.headers["x-lang"] = "Python"
        return response


