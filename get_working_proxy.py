#!/usr/bin/env python3
import requests
import concurrent.futures
import time
import json

def get_proxies_from_sources():
    """Ambil proxy dari multiple sources"""
    print("📡 Mengambil proxy dari internet...")
    
    sources = [
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/ProxifyPE/Proxify/main/ProxyLists/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all"
    ]
    
    all_proxies = set()
    
    for url in sources:
        try:
            print(f"  Mengambil dari {url[:50]}...")
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                proxies = [p.strip() for p in r.text.split('\n') if p.strip() and ':' in p and not p.startswith('#')]
                for p in proxies[:100]:  # Ambil 100 dari tiap sumber
                    all_proxies.add(p)
                print(f"    ✅ Mendapat {len(proxies)} proxy")
        except Exception as e:
            print(f"    ❌ Gagal: {str(e)[:50]}")
    
    return list(all_proxies)

def test_proxy(proxy, target="http://ip.jsontest.com"):
    """Test proxy ke target sederhana"""
    try:
        start = time.time()
        proxies = {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }
        r = requests.get(target, proxies=proxies, timeout=5)
        latency = time.time() - start
        
        if r.status_code == 200:
            # Coba parse response
            try:
                data = r.json()
                return proxy, True, latency, data.get('ip', 'unknown')
            except:
                return proxy, True, latency, r.text[:50]
        else:
            return proxy, False, latency, f"HTTP {r.status_code}"
    except requests.exceptions.Timeout:
        return proxy, False, 0, "Timeout"
    except requests.exceptions.ProxyError as e:
        return proxy, False, 0, "Proxy Error"
    except Exception as e:
        return proxy, False, 0, str(e)[:30]

def main():
    print("="*70)
    print("     🚀 PROXY FINDER & TESTER - Cari Proxy Yang Bekerja")
    print("="*70)
    
    # Ambil proxy
    proxies = get_proxies_from_sources()
    
    if not proxies:
        print("\n❌ Gagal mengambil proxy! Cek koneksi internet.")
        return
    
    print(f"\n📊 Total proxy unik: {len(proxies)}")
    print(f"\n🔍 Menguji proxy ke http://ip.jsontest.com...")
    print("   (Hanya proxy yang merespon < 3 detik yang akan dipakai)")
    print("-"*70)
    
    # Test dengan threading
    working_proxies = []
    tested = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        future_to_proxy = {executor.submit(test_proxy, p): p for p in proxies[:150]}
        
        for future in concurrent.futures.as_completed(future_to_proxy):
            proxy, success, latency, info = future.result()
            tested += 1
            
            if success and latency < 3:  # Hanya yang cepat
                print(f"✅ {proxy:<20} | {latency:.2f}s | {info}")
                working_proxies.append(proxy)
            else:
                print(f"❌ {proxy:<20} | Gagal: {info}")
            
            # Progress
            if tested % 20 == 0:
                print(f"   Progress: {tested}/{min(150, len(proxies))}")
    
    print("-"*70)
    print(f"\n📈 HASIL: {len(working_proxies)} proxy WORKING (dari {tested} yang dites)")
    
    if working_proxies:
        # Simpan ke file
        with open('WORKING_PROXIES.txt', 'w') as f:
            for proxy in working_proxies:
                f.write(f"{proxy}\n")
        
        print(f"\n✅ Proxy bekerja disimpan ke: WORKING_PROXIES.txt")
        print(f"\n📋 Contoh proxy yang bekerja:")
        for proxy in working_proxies[:5]:
            print(f"   {proxy}")
        
        print(f"\n🚀 SEKARANG GUNAKAN PROXY INI:")
        print(f"   python3 CPA_proxy_analyzer.py https://www.nes.co.il WORKING_PROXIES.txt 60")
        
        # Test ke target asli dengan 1 proxy
        print(f"\n🔍 Test ke target asli dengan 1 proxy...")
        test_proxy_to_target(working_proxies[0], "https://www.nes.co.il")
        
    else:
        print("\n⚠️ TIDAK ADA PROXY YANG BEKERJA!")
        print("\n💡 SOLUSI:")
        print("1. Jalankan ulang script (mungkin dapat proxy baru)")
        print("2. Coba menggunakan VPN")
        print("3. Gunakan proxy berbayar seperti BrightData, Oxylabs")
        print("4. Target mungkin memiliki proteksi anti-proxy")

def test_proxy_to_target(proxy, target):
    """Test proxy ke target asli"""
    try:
        proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(target, proxies=proxies, headers=headers, timeout=10)
        if r.status_code == 200:
            print(f"   ✅ Proxy BEKERJA! Status: {r.status_code}")
            print(f"   📝 Response length: {len(r.text)} characters")
        else:
            print(f"   ⚠️ Proxy response: HTTP {r.status_code}")
    except Exception as e:
        print(f"   ❌ Gagal: {str(e)[:80]}")

if __name__ == "__main__":
    main()
