#!/usr/bin/env python3
import requests
import concurrent.futures
import time

def fetch_proxies_from_api():
    """Ambil proxy dari berbagai API"""
    print("📡 Mengambil proxy dari internet...")
    
    apis = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/ProxifyPE/Proxify/main/ProxyLists/http.txt",
    ]
    
    all_proxies = set()
    
    for url in apis:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                proxies = [p.strip() for p in r.text.split('\n') if p.strip() and ':' in p]
                all_proxies.update(proxies[:50])  # Ambil 50 dari tiap sumber
                print(f"  ✅ {len(proxies)} proxy dari {url[:50]}...")
        except:
            print(f"  ❌ Gagal ambil dari {url[:50]}...")
    
    return list(all_proxies)

def test_proxy(proxy):
    """Test proxy ke target"""
    try:
        proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
        start = time.time()
        r = requests.get('http://ip.jsontest.com', proxies=proxies, timeout=5)
        latency = time.time() - start
        
        if r.status_code == 200:
            return proxy, True, latency
    except:
        pass
    return proxy, False, 0

def main():
    print("="*60)
    print("     PROXY TESTER & VALIDATOR")
    print("="*60)
    
    # Ambil proxy
    proxies = fetch_proxies_from_api()
    
    if not proxies:
        print("\n❌ Gagal mengambil proxy!")
        return
    
    print(f"\n📊 Total proxy diambil: {len(proxies)}")
    print(f"🔍 Menguji proxy ke http://ip.jsontest.com...")
    print("-"*60)
    
    # Test proxy
    working = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        results = executor.map(test_proxy, proxies)
        
        for proxy, success, latency in results:
            if success:
                print(f"✅ {proxy} - {latency:.2f}s")
                working.append(proxy)
            else:
                print(f"❌ {proxy}")
    
    print("-"*60)
    print(f"\n📈 HASIL: {len(working)}/{len(proxies)} proxy WORKING")
    
    if working:
        with open('working_proxies.txt', 'w') as f:
            for proxy in working:
                f.write(f"{proxy}\n")
        print(f"✅ Disimpan ke: working_proxies.txt")
        print(f"\n🚀 Gunakan proxy ini untuk attack:")
        print(f"   python3 script.py https://target.com working_proxies.txt")
    else:
        print("\n⚠️ TIDAK ADA PROXY YANG BERFUNGSI!")
        print("   Coba lagi nanti atau gunakan proxy berbayar")

if __name__ == "__main__":
    main()
