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

# Banner 3 huruf "CPA" warna magenta
BANNER = """
\033[95m
   ╔══════════════════════════════════════════════════════════╗
   ║                                                          ║
   ║     ██████╗ ██████╗  █████╗                              ║
   ║    ██╔════╝ ██╔══██╗██╔══██╗                             ║
   ║    ██║      ██████╔╝███████║                             ║
   ║    ██║      ██╔═══╝ ██╔══██║                             ║
   ║    ╚██████╗ ██║     ██║  ██║                             ║
   ║     ╚═════╝ ╚═╝     ╚═╝  ╚═╝                             ║
   ║                                                          ║
   ║              CYBER PROXY ANALYZER                        ║
   ║                   v2.0 - Python                          ║
   ╚══════════════════════════════════════════════════════════╝
\033[0m
"""
# Model 1: ProxyPool dengan pengelolaan dinamis
class ProxyPool:
    def __init__(self, proxies: List[str]):
        self.proxies = proxies
        self.failed_proxies = set()
        self.proxy_speeds = defaultdict(lambda: float('inf'))
        self.lock = threading.Lock()
    
    def get_best_proxy(self) -> Optional[str]:
        """Mengambil proxy tercepat yang tersedia"""
        with self.lock:
            available = [p for p in self.proxies if p not in self.failed_proxies]
            if not available:
                return None
            
            # Pilih proxy tercepat berdasarkan history
            best = min(available, key=lambda p: self.proxy_speeds[p])
            return best
    
    def report_result(self, proxy: str, success: bool, latency: float):
        """Melaporkan hasil penggunaan proxy"""
        with self.lock:
            if success:
                self.proxy_speeds[proxy] = min(self.proxy_speeds[proxy], latency)
                if proxy in self.failed_proxies:
                    self.failed_proxies.remove(proxy)
            else:
                self.failed_proxies.add(proxy)
                if len(self.failed_proxies) > len(self.proxies) * 0.5:
                    # Reset jika terlalu banyak gagal
                    self.failed_proxies.clear()
    
    def get_alive_count(self) -> int:
        with self.lock:
            return len([p for p in self.proxies if p not in self.failed_proxies])

# Model 2: RequestWorker dengan load balancing
class RequestWorker:
    def __init__(self, worker_id: int, proxy_pool: ProxyPool, target: str):
        self.worker_id = worker_id
        self.proxy_pool = proxy_pool
        self.target = target
        self.request_count = 0
        self.success_count = 0
        self.latencies = deque(maxlen=100)
        
    async def make_request(self, session: aiohttp.ClientSession, proxy: str) -> Tuple[bool, float, int]:
        """Melakukan request HTTP dengan proxy"""
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
        """Worker utama untuk menjalankan request"""
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
                
                # Update statistics
                stats['total_requests'] += 1
                if success:
                    stats['successful_requests'] += 1
                stats['total_latency'] += latency
                
                # Rate limiting
                await asyncio.sleep(random.uniform(0.3, 0.8))

# Model 3: Dashboard dengan live monitoring
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
        """Menambahkan log request"""
        with self.lock:
            self.logs.appendleft({
                'status': status,
                'method': method,
                'latency': latency,
                'time': datetime.now()
            })
    
    def add_info(self, message: str):
        """Menambahkan info log"""
        with self.lock:
            self.info_logs.appendleft({
                'message': message,
                'time': datetime.now()
            })
    
    def display(self):
        """Menampilkan dashboard"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # Tampilkan banner CPA
        print(BANNER)
        
        width = 60
        print("\033[95m╔" + "═" * width + "╗\033[0m")
        
        # Statistics
        elapsed = time.time() - self.stats['start_time']
        req_per_sec = self.stats['total_requests'] / elapsed if elapsed > 0 else 0
        success_rate = (self.stats['successful_requests'] / self.stats['total_requests'] * 100 
                       if self.stats['total_requests'] > 0 else 0)
        avg_latency = (self.stats['total_latency'] / self.stats['total_requests'] 
                      if self.stats['total_requests'] > 0 else 0)
        
        print(f"\033[95m║\033[0m \033[1;37mTarget:\033[0m {self.target:<50} \033[95m║\033[0m")
        print(f"\033[95m║\033[0m \033[1;37mAlive Proxies:\033[0m {self.proxy_pool.get_alive_count():<50} \033[95m║\033[0m")
        print(f"\033[95m║\033[0m \033[1;37mTotal Requests:\033[0m {self.stats['total_requests']:<50} \033[95m║\033[0m")
        print(f"\033[95m║\033[0m \033[1;37mReq/s:\033[0m {req_per_sec:.2f}{' ' * 44} \033[95m║\033[0m")
        print(f"\033[95m║\033[0m \033[1;37mSuccess Rate:\033[0m {success_rate:.1f}%{' ' * 44} \033[95m║\033[0m")
        print(f"\033[95m║\033[0m \033[1;37mAvg Latency:\033[0m {avg_latency*1000:.1f}ms{' ' * 42} \033[95m║\033[0m")
        
        print("\033[95m╠" + "═" * width + "╣\033[0m")
        
        # Recent logs
        print("\033[95m║\033[0m \033[1;37mRecent Requests:\033[0m{' ' * 42}\033[95m║\033[0m")
        with self.lock:
            for log in self.logs:
                color = "\033[37m"
                if log['status'] == 200:
                    color = "\033[32m"
                elif log['status'] == 403:
                    color = "\033[31m"
                elif log['status'] == 429:
                    color = "\033[33m"
                    
                log_text = f"[{log['status']}] {log['method']} {self.target} ({log['latency']*1000:.0f}ms)"
                print(f"\033[95m║\033[0m {color}{log_text:<58}\033[95m║\033[0m")
        
        print("\033[95m╠" + "═" * width + "╣\033[0m")
        
        # Info logs
        print("\033[95m║\033[0m \033[1;37mSystem Info:\033[0m{' ' * 48}\033[95m║\033[0m")
        with self.lock:
            for log in self.info_logs:
                print(f"\033[95m║\033[0m \033[33m{log['message']:<58}\033[95m║\033[0m")
        
        print("\033[95m╚" + "═" * width + "╝\033[0m")
        
        # Save good proxies periodically
        self.save_good_proxies()
    
    def save_good_proxies(self):
        """Menyimpan proxy yang bagus ke file"""
        if int(time.time()) % 10 == 0:  # Every 10 seconds
            with open('good_proxies.txt', 'w') as f:
                for proxy in self.proxy_pool.proxies:
                    if proxy not in self.proxy_pool.failed_proxies:
                        f.write(f"{proxy}\n")

async def main():
    if len(sys.argv) < 3:
        print("Usage: python3 proxy_analyzer.py <url> <proxy.txt>")
        print(BANNER)
        return
    
    target = sys.argv[1]
    proxy_file = sys.argv[2]
    
    # Load proxies
    try:
        with open(proxy_file, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"File {proxy_file} not found!")
        return
    
    if not proxies:
        print("No proxies loaded!")
        return
    
    print(f"\033[95m✓ Loaded {len(proxies)} proxies\033[0m")
    time.sleep(1)
    
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
        print("\n\033[95mGoodbye!\033[0m")
