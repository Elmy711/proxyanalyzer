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

# Banner 3 huruf "CPA" tanpa frame
def get_centered_banner():
    """Menghasilkan banner CPA tanpa frame yang selalu terpusat di tengah layar"""
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
        "           ELANG TOOLS V1.0          ",
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

# ProxyPool dengan pengelolaan dinamis
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

# RequestWorker dengan load balancing
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

# Dashboard tanpa frame
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
        """Menampilkan dashboard tanpa frame"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # Tampilkan banner
        print(get_centered_banner())
        print()
        
        terminal_width = shutil.get_terminal_size().columns
        
        # Header
        header = "📊 LIVE DASHBOARD 📊"
        print(f"\033[1;36m{' ' * ((terminal_width - len(header)) // 2)}{header}\033[0m")
        print()
        
        # Statistics - tanpa frame
        elapsed = time.time() - self.stats['start_time']
        req_per_sec = self.stats['total_requests'] / elapsed if elapsed > 0 else 0
        success_rate = (self.stats['successful_requests'] / self.stats['total_requests'] * 100 
                       if self.stats['total_requests'] > 0 else 0)
        avg_latency = (self.stats['total_latency'] / self.stats['total_requests'] 
                      if self.stats['total_requests'] > 0 else 0)
        
        # Format statistik dengan rapi
        stats_text = f"""
\033[1;37m┌────────────────────────────────────────────────────────────────┐\033[0m
\033[1;37m│\033[0m \033[36mTARGET:\033[0m {self.target}
\033[1;37m│\033[0m 
\033[1;37m│\033[0m \033[36mPROXY STATUS:\033[0m
\033[1;37m│\033[0m   ├─ \033[33mAlive Proxies:\033[0m {self.proxy_pool.get_alive_count()}
\033[1;37m│\033[0m   └─ \033[33mDead Proxies:\033[0m {len(self.proxy_pool.proxies) - self.proxy_pool.get_alive_count()}
\033[1;37m│\033[0m 
\033[1;37m│\033[0m \033[36mREQUEST STATS:\033[0m
\033[1;37m│\033[0m   ├─ \033[33mTotal Requests:\033[0m {self.stats['total_requests']}
\033[1;37m│\033[0m   ├─ \033[33mRequests/sec:\033[0m {req_per_sec:.2f}
\033[1;37m│\033[0m   ├─ \033[33mSuccess Rate:\033[0m {success_rate:.1f}%
\033[1;37m│\033[0m   └─ \033[33mAvg Latency:\033[0m {avg_latency*1000:.1f}ms
\033[1;37m└────────────────────────────────────────────────────────────────┘\033[0m
"""
        
        # Pusatkan statistik
        for line in stats_text.split('\n'):
            if line.strip():
                if terminal_width > len(line):
                    padding = (terminal_width - len(line)) // 2
                    print(" " * padding + line)
                else:
                    print(line)
        
        print()
        
        # Recent Requests section
        log_header = "📝 RECENT REQUESTS"
        print(f"\033[1;36m{' ' * ((terminal_width - len(log_header)) // 2)}{log_header}\033[0m")
        print()
        
        with self.lock:
            for i, log in enumerate(self.logs):
                # Warna berdasarkan status
                if log['status'] == 200:
                    status_color = "\033[32m"  # Hijau
                    status_icon = "✓"
                elif log['status'] == 403:
                    status_color = "\033[31m"  # Merah
                    status_icon = "✗"
                elif log['status'] == 429:
                    status_color = "\033[33m"  # Kuning
                    status_icon = "⚠"
                else:
                    status_color = "\033[37m"  # Abu-abu
                    status_icon = "•"
                
                log_text = f"{status_color}{status_icon}\033[0m [{log['status']}] \033[36m{log['method']}\033[0m | \033[33m{log['latency']*1000:.0f}ms\033[0m"
                
                if terminal_width > len(log_text):
                    padding = (terminal_width - len(log_text)) // 2
                    print(" " * padding + log_text)
                else:
                    print(log_text)
        
        print()
        
        # System Info section
        info_header = "ℹ️  SYSTEM INFO"
        print(f"\033[1;36m{' ' * ((terminal_width - len(info_header)) // 2)}{info_header}\033[0m")
        print()
        
        with self.lock:
            for log in self.info_logs:
                info_text = f"\033[33m→\033[0m {log['message']}"
                if terminal_width > len(info_text):
                    padding = (terminal_width - len(info_text)) // 2
                    print(" " * padding + info_text)
                else:
                    print(info_text)
        
        print()
        
        # Running time
        running_time = time.time() - self.stats['start_time']
        hours = int(running_time // 3600)
        minutes = int((running_time % 3600) // 60)
        seconds = int(running_time % 60)
        
        time_text = f"\033[90m⏱ Running: {hours:02d}:{minutes:02d}:{seconds:02d}\033[0m"
        if terminal_width > len(time_text):
            padding = (terminal_width - len(time_text)) // 2
            print(" " * padding + time_text)
        else:
            print(time_text)
        
        print()
        
        footer = "Press \033[91mCtrl+C\033[0m to stop"
        if terminal_width > len(footer):
            padding = (terminal_width - len(footer)) // 2
            print(" " * padding + footer)
        else:
            print(footer)
        
        # Save good proxies
        self.save_good_proxies()
    
    def save_good_proxies(self):
        """Menyimpan proxy yang bagus ke file"""
        if int(time.time()) % 10 == 0:
            with open('good_proxies.txt', 'w') as f:
                for proxy in self.proxy_pool.proxies:
                    if proxy not in self.proxy_pool.failed_proxies:
                        f.write(f"{proxy}\n")

async def main():
    if len(sys.argv) < 3:
        print("Usage: python3 script.py <url> <proxy.txt>")
        print(get_centered_banner())
        return
    
    target = sys.argv[1]
    proxy_file = sys.argv[2]
    
    # Load proxies dari file
    try:
        with open(proxy_file, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"File {proxy_file} not found!")
        print("\nContoh format proxy.txt:")
        print("103.152.232.36:80")
        print("47.91.99.55:3128")
        return
    
    if not proxies:
        print("No proxies loaded!")
        return
    
    print(f"\033[95m✓ Loaded {len(proxies)} proxies\033[0m")
    await asyncio.sleep(1)
    
    # Initialize components
    proxy_pool = ProxyPool(proxies)
    dashboard = Dashboard(target, proxy_pool)
    stop_event = threading.Event()
    
    # Start workers
    workers = []
    num_workers = min(50, len(proxies))
    
    for i in range(num_workers):
        worker = RequestWorker(i, proxy_pool, target)
        workers.append(worker)
    
    # Run workers asynchronously
    async def run_workers():
        tasks = [worker.run(dashboard.stats, stop_event) for worker in workers]
        await asyncio.gather(*tasks)
    
    # Start dashboard display thread
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
