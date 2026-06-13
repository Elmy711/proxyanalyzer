#!/usr/bin/env python3
import asyncio
import aiohttp
import random
import time
import sys
from datetime import datetime
from collections import defaultdict, deque
import threading
from typing import List, Dict, Optional, Tuple
import os
import shutil

# ============================================
# PROXY LIST - LANGSUNG DI DALAM SCRIPT
# ============================================
PROXY_LIST = [
    "103.152.232.36:80",
    "47.91.99.55:3128", 
    "183.88.104.229:8080",
    "192.252.222.92:4145",
    "45.86.221.115:8080",
    "115.78.131.186:8080",
    "190.14.249.147:999",
    "189.240.60.170:9090",
    "177.74.112.77:8080",
    "200.54.193.147:8080",
    # Tambahkan proxy lainnya di sini
]

# ============================================
# ATAU BISA JUGA PAKAI FORMAT TEXT BLOCK
# ============================================
PROXY_TEXT = """
103.152.232.36:80
47.91.99.55:3128
183.88.104.229:8080
192.252.222.92:4145
45.86.221.115:8080
115.78.131.186:8080
190.14.249.147:999
189.240.60.170:9090
"""

# Fungsi untuk mendapatkan proxy dari embedded list
def get_proxies():
    # Opsi 1: Dari LIST
    return PROXY_LIST.copy()
    
    # Opsi 2: Dari TEXT BLOCK
    # return [p.strip() for p in PROXY_TEXT.strip().split('\n') if p.strip()]

# Banner 3 huruf "CPA" tanpa frame
def get_centered_banner():
    terminal_width = shutil.get_terminal_size().columns
    banner_lines = [
        "",
        "     ██████╗ ██████╗  █████╗     ",
        "    ██╔════╝ ██╔══██╗██╔══██╗    ",
        "    ██║      ██████╔╝███████║    ",
        "    ██║      ██╔═══╝ ██╔══██║    ",
        "    ╚██████╗ ██║     ██║  ██║    ",
        "     ╚═════╝ ╚═╝     ╚═╝  ╚═╝    ",
        "                                  ",
        "       CPA PROXY ANALYZER       ",
        "          ELANG TOOLS v1.0          ",
        ""
    ]
    
    centered_banner = []
    for line in banner_lines:
        if terminal_width > len(line):
            padding = (terminal_width - len(line)) // 2
            centered_line = " " * padding + f"\033[95m{line}\033[0m"
        else:
            centered_line = f"\033[95m{line}\033[0m"
        centered_banner.append(centered_line)
    
    return "\n".join(centered_banner)

# ============================================
# LANJUTAN MODEL-MODEL SEBELUMNYA
# ============================================

class ProxyPool:
    def __init__(self, proxies: List[str]):
        self.proxies = proxies
        self.failed_proxies = set()
        self.proxy_speeds = defaultdict(lambda: float('inf'))
        self.lock = threading.Lock()
    
    def get_best_proxy(self) -> Optional[str]:
        with self.lock:
            available = [p for p in self.proxies if p not in self.failed_proxies]
            if not available:
                return None
            best = min(available, key=lambda p: self.proxy_speeds[p])
            return best
    
    def report_result(self, proxy: str, success: bool, latency: float):
        with self.lock:
            if success:
                self.proxy_speeds[proxy] = min(self.proxy_speeds[proxy], latency)
                if proxy in self.failed_proxies:
                    self.failed_proxies.remove(proxy)
            else:
                self.failed_proxies.add(proxy)
                if len(self.failed_proxies) > len(self.proxies) * 0.5:
                    self.failed_proxies.clear()
    
    def get_alive_count(self) -> int:
        with self.lock:
            return len([p for p in self.proxies if p not in self.failed_proxies])

class RequestWorker:
    def __init__(self, worker_id: int, proxy_pool: ProxyPool, target: str):
        self.worker_id = worker_id
        self.proxy_pool = proxy_pool
        self.target = target
        self.request_count = 0
        self.success_count = 0
        self.latencies = deque(maxlen=100)
        
    async def make_request(self, session: aiohttp.ClientSession, proxy: str) -> Tuple[bool, float, int]:
        start_time = time.time()
        methods = ['GET', 'POST', 'HEAD']
        method = random.choice(methods)
        
        headers = {
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            ])
        }
        
        try:
            proxy_url = f"http://{proxy}"
            async with session.request(method, self.target, headers=headers, 
                                      proxy=proxy_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                latency = time.time() - start_time
                status = resp.status
                
                if status == 200 and latency < 1.5:
                    self.success_count += 1
                    self.latencies.append(latency)
                    return True, latency, status
                else:
                    return False, latency, status
                    
        except Exception as e:
            latency = time.time() - start_time
            return False, latency, 0
    
    async def run(self, stats: Dict, stop_event: threading.Event):
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
        async with aiohttp.ClientSession(connector=connector) as session:
            while not stop_event.is_set():
                proxy = self.proxy_pool.get_best_proxy()
                if not proxy:
                    await asyncio.sleep(0.5)
                    continue
                
                success, latency, status = await self.make_request(session, proxy)
                self.proxy_pool.report_result(proxy, success, latency)
                self.request_count += 1
                
                stats['total_requests'] += 1
                if success:
                    stats['successful_requests'] += 1
                stats['total_latency'] += latency
                
                await asyncio.sleep(random.uniform(0.3, 0.8))

class Dashboard:
    def __init__(self, target: str, proxy_pool: ProxyPool):
        self.target = target
        self.proxy_pool = proxy_pool
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'total_latency': 0,
            'start_time': time.time()
        }
        self.logs = deque(maxlen=10)
        self.info_logs = deque(maxlen=5)
        self.lock = threading.Lock()
        
    def add_log(self, status: int, method: str, latency: float):
        with self.lock:
            self.logs.appendleft({
                'status': status,
                'method': method,
                'latency': latency,
                'time': datetime.now()
            })
    
    def add_info(self, message: str):
        with self.lock:
            self.info_logs.appendleft({
                'message': message,
                'time': datetime.now()
            })
    
    def display(self):
        os.system('clear' if os.name == 'posix' else 'cls')
        print(get_centered_banner())
        print()
        
        terminal_width = shutil.get_terminal_size().columns
        
        header = "📊 LIVE DASHBOARD 📊"
        print(f"\033[96m{' ' * ((terminal_width - len(header)) // 2)}{header}\033[0m")
        print()
        
        elapsed = time.time() - self.stats['start_time']
        req_per_sec = self.stats['total_requests'] / elapsed if elapsed > 0 else 0
        success_rate = (self.stats['successful_requests'] / self.stats['total_requests'] * 100 
                       if self.stats['total_requests'] > 0 else 0)
        avg_latency = (self.stats['total_latency'] / self.stats['total_requests'] 
                      if self.stats['total_requests'] > 0 else 0)
        
        stats_data = [
            f"╔══════════════════════════════════════════════════════════════╗",
            f"║ \033[1;37mTarget:\033[0m {self.target:<55} ║",
            f"║ \033[1;37mAlive Proxies:\033[0m {self.proxy_pool.get_alive_count():<55} ║",
            f"║ \033[1;37mTotal Requests:\033[0m {self.stats['total_requests']:<55} ║",
            f"║ \033[1;37mReq/s:\033[0m {req_per_sec:.2f}{' ' * 49} ║",
            f"║ \033[1;37mSuccess Rate:\033[0m {success_rate:.1f}%{' ' * 49} ║",
            f"║ \033[1;37mAvg Latency:\033[0m {avg_latency*1000:.1f}ms{' ' * 49} ║",
            f"╚══════════════════════════════════════════════════════════════╝"
        ]
        
        for line in stats_data:
            if terminal_width > len(line):
                padding = (terminal_width - len(line)) // 2
                print(" " * padding + line)
            else:
                print(line)
        
        print()
        
        log_header = "📝 RECENT REQUESTS"
        print(f"\033[96m{' ' * ((terminal_width - len(log_header)) // 2)}{log_header}\033[0m")
        print()
        
        with self.lock:
            for log in self.logs:
                color = "\033[37m"
                if log['status'] == 200:
                    color = "\033[32m"
                elif log['status'] == 403:
                    color = "\033[31m"
                elif log['status'] == 429:
                    color = "\033[33m"
                
                log_text = f"  {color}[{log['status']}]{reset} {log['method']} | {log['latency']*1000:.0f}ms"
                reset = "\033[0m"
                log_line = f"║{log_text:<64}║"
                
                if terminal_width > len(log_line):
                    padding = (terminal_width - len(log_line)) // 2
                    print(" " * padding + log_line)
                else:
                    print(log_line)
        
        print()
        
        info_header = "ℹ️  SYSTEM INFO"
        print(f"\033[96m{' ' * ((terminal_width - len(info_header)) // 2)}{info_header}\033[0m")
        print()
        
        with self.lock:
            for log in self.info_logs:
                info_line = f"║ \033[33m{log['message']:<62}\033[0m ║"
                if terminal_width > len(info_line):
                    padding = (terminal_width - len(info_line)) // 2
                    print(" " * padding + info_line)
                else:
                    print(info_line)
        
        print()
        footer = "Press Ctrl+C to stop"
        print(f"\033[90m{' ' * ((terminal_width - len(footer)) // 2)}{footer}\033[0m")
        self.save_good_proxies()
    
    def save_good_proxies(self):
        if int(time.time()) % 10 == 0:
            with open('good_proxies.txt', 'w') as f:
                for proxy in self.proxy_pool.proxies:
                    if proxy not in self.proxy_pool.failed_proxies:
                        f.write(f"{proxy}\n")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 script.py <url>")
        print(get_centered_banner())
        return
    
    target = sys.argv[1]
    
    # Gunakan proxy dari embedded list (TIDAK PERLU FILE EKSTERNAL)
    proxies = get_proxies()
    
    if not proxies:
        print("No proxies available in script!")
        return
    
    print(f"\033[95m✓ Loaded {len(proxies)} proxies from embedded list\033[0m")
    await asyncio.sleep(1)
    
    proxy_pool = ProxyPool(proxies)
    dashboard = Dashboard(target, proxy_pool)
    stop_event = threading.Event()
    
    workers = []
    num_workers = min(50, len(proxies))
    
    for i in range(num_workers):
        worker = RequestWorker(i, proxy_pool, target)
        workers.append(worker)
    
    async def run_workers():
        tasks = [worker.run(dashboard.stats, stop_event) for worker in workers]
        await asyncio.gather(*tasks)
    
    def display_dashboard():
        while not stop_event.is_set():
            dashboard.display()
            time.sleep(0.5)
    
    display_thread = threading.Thread(target=display_dashboard)
    display_thread.start()
    
    try:
        await run_workers()
    except KeyboardInterrupt:
        print("\n\033[95mShutting down...\033[0m")
        stop_event.set()
        display_thread.join()
        print("\033[95m✓ Proxy analyzer stopped\033[0m")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\033[95mALHAMDULILLAH\033[0m")
