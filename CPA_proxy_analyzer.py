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
import signal

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

def show_usage():
    """Menampilkan cara penggunaan script"""
    print(get_centered_banner())
    print("\n\033[1;33m" + "="*60 + "\033[0m")
    print("\033[1;36mCARA PENGGUNAAN:\033[0m")
    print("\033[93m1. Minimal:\033[0m python3 script.py <url> <proxy.txt>")
    print("\033[93m2. Dengan durasi (detik):\033[0m python3 script.py <url> <proxy.txt> <duration>")
    print("\033[93m3. Dengan durasi & request:\033[0m python3 script.py <url> <proxy.txt> <duration> <max_requests>")
    print("\n\033[1;33m" + "="*60 + "\033[0m")
    print("\033[36mCONTOH:\033[0m")
    print("  python3 script.py https://example.com proxy.txt")
    print("  python3 script.py https://example.com proxy.txt 60")
    print("  python3 script.py https://example.com proxy.txt 300 1000")
    print("\n\033[90mKeterangan:\033[0m")
    print("  - duration: waktu berjalan dalam detik (0 = unlimited)")
    print("  - max_requests: batas maksimal request (0 = unlimited)")
    print("  - Tekan Ctrl+C kapan saja untuk menghentikan program\033[0m")
    print("\033[1;33m" + "="*60 + "\033[0m\n")

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

# Dashboard tanpa frame dengan timer
class Dashboard:
    def __init__(self, target: str, proxy_pool: ProxyPool, duration: int = 0, max_requests: int = 0):
        self.target = target
        self.proxy_pool = proxy_pool
        self.duration = duration  # 0 = unlimited
        self.max_requests = max_requests  # 0 = unlimited
        self.start_time = time.time()
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'total_latency': 0,
            'start_time': self.start_time
        }
        self.logs = deque(maxlen=10)
        self.info_logs = deque(maxlen=5)
        self.lock = threading.Lock()
        self.stop_reason = None
        
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
    
    def check_stop_conditions(self, stop_event: threading.Event) -> bool:
        """Memeriksa apakah program harus berhenti"""
        if stop_event.is_set():
            return True
            
        # Cek durasi
        if self.duration > 0:
            elapsed = time.time() - self.start_time
            if elapsed >= self.duration:
                self.stop_reason = f"Waktu habis ({self.duration} detik)"
                stop_event.set()
                return True
        
        # Cek maksimal request
        if self.max_requests > 0:
            if self.stats['total_requests'] >= self.max_requests:
                self.stop_reason = f"Mencapai batas request ({self.max_requests})"
                stop_event.set()
                return True
        
        return False
    
    def display(self, stop_event: threading.Event):
        """Menampilkan dashboard tanpa frame"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # Tampilkan banner
        print(get_centered_banner())
        print()
        
        terminal_width = shutil.get_terminal_size().columns
        
        # Header dengan informasi durasi
        if self.duration > 0 or self.max_requests > 0:
            limits = []
            if self.duration > 0:
                limits.append(f"⏱ Time Limit: {self.duration}s")
            if self.max_requests > 0:
                limits.append(f"📊 Request Limit: {self.max_requests}")
            limit_text = " | ".join(limits)
            print(f"\033[90m{' ' * ((terminal_width - len(limit_text)) // 2)}{limit_text}\033[0m")
            print()
        
        header = "📊 LIVE DASHBOARD 📊"
        print(f"\033[1;36m{' ' * ((terminal_width - len(header)) // 2)}{header}\033[0m")
        print()
        
        # Statistics
        elapsed = time.time() - self.stats['start_time']
        req_per_sec = self.stats['total_requests'] / elapsed if elapsed > 0 else 0
        success_rate = (self.stats['successful_requests'] / self.stats['total_requests'] * 100 
                       if self.stats['total_requests'] > 0 else 0)
        avg_latency = (self.stats['total_latency'] / self.stats['total_requests'] 
                      if self.stats['total_requests'] > 0 else 0)
        
        # Sisa waktu jika ada durasi
        remaining_time = ""
        if self.duration > 0:
            remaining = max(0, self.duration - elapsed)
            remaining_time = f"\033[1;37m│\033[0m \033[36mSisa Waktu:\033[0m {remaining:.0f} detik"
        
        # Sisa request jika ada batas
        remaining_requests = ""
        if self.max_requests > 0:
            remaining_req = max(0, self.max_requests - self.stats['total_requests'])
            remaining_requests = f"\033[1;37m│\033[0m \033[36mSisa Request:\033[0m {remaining_req}"
        
        stats_text = f"""
\033[1;37m┌────────────────────────────────────────────────────────────────┐\033[0m
\033[1;37m│\033[0m \033[36mTARGET:\033[0m {self.target}
{remaining_time}
{remaining_requests}
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
                if log['status'] == 200:
                    status_color = "\033[32m"
                    status_icon = "✓"
                elif log['status'] == 403:
                    status_color = "\033[31m"
                    status_icon = "✗"
                elif log['status'] == 429:
                    status_color = "\033[33m"
                    status_icon = "⚠"
                else:
                    status_color = "\033[37m"
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
        
        # Tampilkan pesan stop jika ada
        if self.stop_reason and stop_event.is_set():
            print()
            stop_text = f"\033[91m⛔ {self.stop_reason}, program berhenti...\033[0m"
            if terminal_width > len(stop_text):
                padding = (terminal_width - len(stop_text)) // 2
                print(" " * padding + stop_text)
            else:
                print(stop_text)
        
        print()
        
        # Running time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        
        time_text = f"\033[90m⏱ Running: {hours:02d}:{minutes:02d}:{seconds:02d}\033[0m"
        if terminal_width > len(time_text):
            padding = (terminal_width - len(time_text)) // 2
            print(" " * padding + time_text)
        else:
            print(time_text)
        
        print()
        
        if not self.stop_reason:
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
                f.write(f"# Proxy hasil filter - {datetime.now()}\n")
                f.write(f"# Total: {self.proxy_pool.get_alive_count()} proxies alive\n\n")
                for proxy in self.proxy_pool.proxies:
                    if proxy not in self.proxy_pool.failed_proxies:
                        f.write(f"{proxy}\n")

async def main():
    # Parsing parameter
    if len(sys.argv) < 3:
        show_usage()
        return
    
    target = sys.argv[1]
    proxy_file = sys.argv[2]
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    max_requests = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    
    # Load proxies
    try:
        with open(proxy_file, 'r') as f:
            proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print(f"\033[91m✗ File {proxy_file} tidak ditemukan!\033[0m")
        print("\n\033[93mBuat file proxy.txt dengan format:\033[0m")
        print("  103.152.232.36:80")
        print("  47.91.99.55:3128")
        print("  183.88.104.229:8080\n")
        return
    
    if not proxies:
        print("\033[91m✗ Tidak ada proxy yang ditemukan di file!\033[0m")
        return
    
    # Tampilkan konfigurasi
    print(get_centered_banner())
    print(f"\n\033[92m✓ Loaded {len(proxies)} proxies\033[0m")
    print(f"\033[36m✓ Target:\033[0m {target}")
    if duration > 0:
        print(f"\033[36m✓ Durasi:\033[0m {duration} detik")
    else:
        print(f"\033[36m✓ Durasi:\033[0m Unlimited (sampai Ctrl+C)")
    if max_requests > 0:
        print(f"\033[36m✓ Maks Request:\033[0m {max_requests}")
    else:
        print(f"\033[36m✓ Maks Request:\033[0m Unlimited")
    print(f"\n\033[33mMemulai dalam 3 detik...\033[0m")
    await asyncio.sleep(3)
    
    # Initialize components
    proxy_pool = ProxyPool(proxies)
    dashboard = Dashboard(target, proxy_pool, duration, max_requests)
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
            dashboard.display(stop_event)
            
            # Cek kondisi stop
            if dashboard.check_stop_conditions(stop_event):
                break
                
            time.sleep(0.5)
        
        # Tampilkan ringkasan akhir
        if dashboard.stop_reason:
            time.sleep(1)
            dashboard.display(stop_event)
            print(f"\n\033[92m✓ {dashboard.stop_reason}\033[0m")
    
    display_thread = threading.Thread(target=display_dashboard)
    display_thread.start()
    
    try:
        await run_workers()
    except KeyboardInterrupt:
        print("\n\033[93m⚠ Menerima interrupt signal...\033[0m")
        stop_event.set()
        display_thread.join(timeout=2)
        print("\033[92m✓ Program dihentikan oleh user\033[0m")
    finally:
        # Tampilkan ringkasan akhir
        elapsed = time.time() - dashboard.start_time
        success_rate = (dashboard.stats['successful_requests'] / dashboard.stats['total_requests'] * 100 
                       if dashboard.stats['total_requests'] > 0 else 0)
        
        print("\n\033[1;33m" + "="*60 + "\033[0m")
        print("\033[1;36m📊 RINGKASAN AKHIR:\033[0m")
        print(f"  ⏱ Total Waktu: {elapsed:.2f} detik")
        print(f"  📊 Total Request: {dashboard.stats['total_requests']}")
        print(f"  ✓ Success: {dashboard.stats['successful_requests']}")
        print(f"  ✗ Failed: {dashboard.stats['total_requests'] - dashboard.stats['successful_requests']}")
        print(f"  📈 Success Rate: {success_rate:.1f}%")
        print(f"  🌐 Proxy Alive: {proxy_pool.get_alive_count()}/{len(proxies)}")
        print(f"  💾 Good proxies saved to: good_proxies.txt")
        print("\033[1;33m" + "="*60 + "\033[0m")
        print("\n\033[95mGoodbye!\033[0m")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\033[95mALHAMDULILLAH\033[0m")
