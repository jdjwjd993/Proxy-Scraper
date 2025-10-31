#!/usr/bin/env python3
"""
ultimate_proxy_scraper_menu.py — THE ULTIMATE PROXY SCRAPER (Interactive Menu Edition)

Interactive menu edition — shows a friendly menu first so you can choose:
- which protocols to scrape (HTTP/HTTPS/SOCKS4/SOCKS5)
- whether to validate (quick validation)
- worker count, timeouts, and other performance settings
- whether to fetch all sources or a limited set

Defaults are tuned for **maximum performance**, but you can easily lower them.
Made with ❤️ by 47_di — enjoy and modify as you like.

Usage:
    python ultimate_proxy_scraper_menu.py
"""

from __future__ import annotations
import asyncio
import aiohttp
import argparse
import time
import sys
import os
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional
import re

try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init(autoreset=True)
except Exception:
    class _C:
        RESET=""; RED=""; GREEN=""; YELLOW=""; CYAN=""; MAGENTA=""; WHITE=""
    Fore = _C(); Style = _C()

# ---------------- CONFIG (editable) ----------------
# SOURCES dict lists many public proxy list endpoints. You can add or remove sources freely.
SOURCES: Dict[str, List[str]] = {
    "http": [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        "https://www.proxy-list.download/api/v1/get?type=http",
    ],
    "https": [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=https&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/https.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        "https://www.proxy-list.download/api/v1/get?type=https",
    ],
    "socks4": [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=10000&country=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
        "https://www.proxy-list.download/api/v1/get?type=socks4",
    ],
    "socks5": [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        "https://www.proxy-list.download/api/v1/get?type=socks5",
    ],
}

IPPORT_RE = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3}:\d{1,5})")
OUT_DIR = Path("results_ultimate_scraper")
VALIDATE_HTTP_URL = "http://httpbin.org/ip"
VALIDATE_HTTPS_URL = "https://httpbin.org/ip"

# Max-performance defaults (you can lower these in the interactive menu)
DEFAULT_WORKERS = 800
DEFAULT_TIMEOUT = 6.0
FETCH_TIMEOUT = 14.0

# ---------------------------------------------------

def banner():
    clear()
    print(Fore.CYAN + r"""
   ___  _  _  _   _    _   _ ___    _  _ _  _   _  _ 
  | _ \| || || | | |  /_\ | | _ \  | \| | \| | | \| |
  |  _/| __ || |_| | / _ \| |  _/  | .` | .` | | .` |
  |_|  |_||_| \___/ /_/ \_\ |_|    |_|\_|_|\_| |_|\_|
    ULTIMATE PROXY SCRAPER — Interactive Menu (47_di)
    """ + Style.RESET_ALL)
    print(Fore.MAGENTA + "Made with ❤️ by 47_di — The World's Best Proxy Scraper" + Style.RESET_ALL)
    print(Fore.YELLOW + "Support: DM me on Discord -> 47_di" + Style.RESET_ALL)
    print(Fore.CYAN + "─" * 72 + Style.RESET_ALL)

def clear():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass

def eprint(*a, **k):
    print(*a, file=sys.stderr, **k)

def prompt_yesno(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    while True:
        ans = input(Fore.CYAN + f"{prompt} [{d}]: " + Style.RESET_ALL).strip().lower()
        if ans == "" and default:
            return True
        if ans == "" and not default:
            return False
        if ans in ("y","yes"):
            return True
        if ans in ("n","no"):
            return False
        print(Fore.RED + "Please enter y or n." + Style.RESET_ALL)

def prompt_int(prompt: str, default: int, minv: int = 1, maxv: int = 10000) -> int:
    while True:
        s = input(Fore.CYAN + f"{prompt} (default {default}): " + Style.RESET_ALL).strip()
        if s == "":
            return default
        try:
            v = int(s)
            if v < minv or v > maxv:
                print(Fore.RED + f"Enter a number between {minv} and {maxv}." + Style.RESET_ALL)
                continue
            return v
        except Exception:
            print(Fore.RED + "Invalid number." + Style.RESET_ALL)

def prompt_float(prompt: str, default: float, minv: float = 0.1, maxv: float = 60.0) -> float:
    while True:
        s = input(Fore.CYAN + f"{prompt} (default {default}): " + Style.RESET_ALL).strip()
        if s == "":
            return default
        try:
            v = float(s)
            if v < minv or v > maxv:
                print(Fore.RED + f"Enter a number between {minv} and {maxv}." + Style.RESET_ALL)
                continue
            return v
        except Exception:
            print(Fore.RED + "Invalid number." + Style.RESET_ALL)

def extract_proxies_from_text(text: str) -> Set[str]:
    proxies = set()
    for m in IPPORT_RE.finditer(text):
        proxies.add(m.group(1).strip())
    normalized = set()
    for p in proxies:
        p = p.strip()
        for pref in ("http://","https://","socks4://","socks5://"):
            if p.startswith(pref):
                p = p.split("://",1)[1]
                break
        normalized.add(p)
    return normalized

async def fetch_text(session: aiohttp.ClientSession, url: str, timeout: float = FETCH_TIMEOUT) -> str:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            return await resp.text(errors="ignore")
    except Exception:
        return ""

async def scrape_sources(selected_protocols: List[str], use_all_sources: bool, verbose: bool = True) -> Dict[str, List[str]]:
    out: Dict[str, Set[str]] = {k: set() for k in SOURCES.keys()}
    conn = aiohttp.TCPConnector(limit=100, ssl=False)
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = []
        # decide which urls to fetch based on user selection
        for proto, urls in SOURCES.items():
            if proto not in selected_protocols:
                continue
            chosen = urls if use_all_sources else urls[:1]  # if not use_all_sources, fetch only first source per proto
            for url in chosen:
                tasks.append((proto, url, asyncio.create_task(fetch_text(session, url))))
        if verbose:
            print(Fore.YELLOW + f"Fetching {len(tasks)} source lists..." + Style.RESET_ALL)
        for proto, url, task in tasks:
            try:
                txt = await task
                if not txt:
                    if verbose:
                        eprint(Fore.RED + f"Failed to fetch: {url}" + Style.RESET_ALL)
                    continue
                found = extract_proxies_from_text(txt)
                out[proto].update(found)
                if verbose:
                    print(Fore.GREEN + f"Found {len(found)} entries from {url} for {proto.upper()}" + Style.RESET_ALL)
            except Exception:
                continue
    return {k: sorted(list(v)) for k, v in out.items()}

def save_lists(lists: Dict[str, List[str]], out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    all_set = set()
    for proto, lst in lists.items():
        all_set.update(lst)
        p = out_dir / f"proxies_{proto}.txt"
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lst))
    all_list = sorted(list(all_set))
    with open(out_dir / "proxies_all.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(all_list))
    print(Fore.CYAN + f"Saved results to {out_dir.resolve()}" + Style.RESET_ALL)

# ----------------- Lightweight validation -----------------
async def probe_proxy_http(session: aiohttp.ClientSession, proxy: str, use_https: bool, timeout: float) -> bool:
    proxy_url = f"http://{proxy}"
    test_url = VALIDATE_HTTPS_URL if use_https else VALIDATE_HTTP_URL
    try:
        async with session.get(test_url, proxy=proxy_url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            return resp.status == 200
    except Exception:
        return False

async def validate_proxies(proxies: List[str], proto_hint: Optional[str], workers: int, timeout: float, verbose: bool = True) -> List[str]:
    valid: List[str] = []
    sem = asyncio.Semaphore(workers)
    conn = aiohttp.TCPConnector(limit_per_host=max(10, min(workers, 500)), limit=max(50, min(workers*2, 2500)), ssl=False)
    async with aiohttp.ClientSession(connector=conn) as session:
        async def probe_wrapper(p):
            async with sem:
                if proto_hint in ("socks4", "socks5"):
                    return await validate_tcp_connect(p, timeout)
                else:
                    ok = await probe_proxy_http(session, p, use_https=(proto_hint=="https"), timeout=timeout)
                    return p if ok else None
        tasks = [asyncio.create_task(probe_wrapper(p)) for p in proxies]
        if verbose:
            print(Fore.YELLOW + f"Validating {len(tasks)} proxies with {workers} workers..." + Style.RESET_ALL)
        for coro in asyncio.as_completed(tasks):
            try:
                res = await coro
                if res:
                    valid.append(res)
                    if verbose and len(valid) % 50 == 0:
                        print(Fore.GREEN + f"Validated: {len(valid)}" + Style.RESET_ALL, end="\r")
            except Exception:
                continue
    return valid

async def validate_tcp_connect(proxy: str, timeout: float) -> Optional[str]:
    parts = proxy.split(":")
    if len(parts) < 2:
        return None
    host = parts[0]
    try:
        port = int(parts[1])
    except Exception:
        return None
    loop = asyncio.get_running_loop()
    try:
        fut = loop.run_in_executor(None, _tcp_connect_blocking, host, port, timeout)
        ok = await fut
        return proxy if ok else None
    except Exception:
        return None

def _tcp_connect_blocking(host: str, port: int, timeout: float) -> bool:
    import socket
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        try:
            if s: s.close()
        except Exception:
            pass
        return False

# ----------------- Interactive Menu & Runner -----------------
def interactive_menu():
    banner()
    print(Fore.MAGENTA + "Interactive setup — configure your perfect scrape run." + Style.RESET_ALL)
    # Protocols
    print()
    print(Fore.CYAN + "Select protocols to scrape (enter numbers separated by comma, default = all):" + Style.RESET_ALL)
    proto_map = {"1":"http", "2":"https", "3":"socks4", "4":"socks5"}
    print(Fore.YELLOW + "  1) HTTP\n  2) HTTPS\n  3) SOCKS4\n  4) SOCKS5\n  5) ALL\n" + Style.RESET_ALL)
    sel = input(Fore.CYAN + "Your choice (e.g. 1,2 or 5): " + Style.RESET_ALL).strip()
    if sel == "" or "5" in sel:
        selected = ["http","https","socks4","socks5"]
    else:
        chosen = set(x.strip() for x in sel.split(",") if x.strip())
        selected = [proto_map.get(c) for c in chosen if c in proto_map]
        selected = [s for s in selected if s]
        if not selected:
            selected = ["http","https","socks4","socks5"]
    # sources depth
    use_all_sources = prompt_yesno("Fetch ALL configured sources per protocol? (recommended=yes, may be slower)", True)
    # validation
    do_validate = prompt_yesno("Run quick validation after scraping? (recommended)", True)
    # workers & timeout
    default_workers = DEFAULT_WORKERS
    workers = prompt_int("Validation worker count (higher = faster, more CPU/RAM)", default_workers, minv=10, maxv=5000)
    timeout = prompt_float("Validation timeout in seconds (shorter = faster, may miss slow proxies)", DEFAULT_TIMEOUT, minv=1.0, maxv=30.0)
    # fetch timeout
    fetch_timeout = prompt_float("Source fetch timeout in seconds", FETCH_TIMEOUT, minv=5.0, maxv=60.0)
    # output folder
    out_dir = input(Fore.CYAN + f"Output folder (default: {OUT_DIR}): " + Style.RESET_ALL).strip() or str(OUT_DIR)
    # sanity confirm
    print()
    print(Fore.MAGENTA + "Summary:" + Style.RESET_ALL)
    print(Fore.GREEN + f"  Protocols: {', '.join(selected)}" + Style.RESET_ALL)
    print(Fore.GREEN + f"  Fetch all sources: {'Yes' if use_all_sources else 'No (first source per proto)'}" + Style.RESET_ALL)
    print(Fore.GREEN + f"  Validate after scraping: {'Yes' if do_validate else 'No'}" + Style.RESET_ALL)
    print(Fore.GREEN + f"  Workers: {workers}" + Style.RESET_ALL)
    print(Fore.GREEN + f"  Timeout: {timeout}s" + Style.RESET_ALL)
    print(Fore.GREEN + f"  Fetch timeout: {fetch_timeout}s" + Style.RESET_ALL)
    print(Fore.GREEN + f"  Output folder: {out_dir}" + Style.RESET_ALL)
    go = prompt_yesno("Start scraping now?", True)
    if not go:
        print(Fore.YELLOW + "Aborted by user. Exiting." + Style.RESET_ALL)
        raise SystemExit(0)
    return selected, use_all_sources, do_validate, workers, timeout, fetch_timeout, Path(out_dir)

async def main_async(selected, use_all_sources, do_validate, workers, timeout, fetch_timeout, out_dir):
    # adjust global fetch timeout temporarily
    global FETCH_TIMEOUT
    FETCH_TIMEOUT = fetch_timeout
    start = time.time()
    print(Fore.MAGENTA + "Scraping sources..." + Style.RESET_ALL)
    lists = await scrape_sources(selected, use_all_sources, verbose=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    save_lists(lists, out_dir)
    # create combined ordered master list
    all_proxies = []
    for proto in ("http","https","socks4","socks5"):
        if proto in selected:
            all_proxies.extend(lists.get(proto, []))
    seen = set(); final_all = []
    for p in all_proxies:
        if p not in seen:
            seen.add(p); final_all.append(p)
    with open(out_dir / "proxies_all.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(final_all))
    elapsed = time.time() - start
    print(Fore.CYAN + f"\nScraped total: {len(final_all)} unique proxies in {elapsed:.2f}s" + Style.RESET_ALL)

    if not do_validate:
        print(Fore.YELLOW + "Skipping validation as requested." + Style.RESET_ALL)
        return

    print(Fore.MAGENTA + "\nStarting validation phase (quick/lightweight)..." + Style.RESET_ALL)
    validated_master = []
    for proto in selected:
        proto_list = lists.get(proto, [])
        if not proto_list:
            continue
        print(Fore.MAGENTA + f"\nValidating {len(proto_list)} {proto.upper()} proxies..." + Style.RESET_ALL)
        valid = await validate_proxies(proto_list, proto, workers=workers, timeout=timeout, verbose=True)
        ppath = out_dir / f"valid_{proto}.txt"
        with open(ppath, "w", encoding="utf-8") as f:
            f.write("\n".join(valid))
        print(Fore.GREEN + f"Saved {len(valid)} valid {proto.upper()} proxies to {ppath}" + Style.RESET_ALL)
        validated_master.extend(valid)
    vm = []
    seen = set()
    for x in validated_master:
        if x not in seen:
            seen.add(x); vm.append(x)
    with open(out_dir / "valid_proxies_all.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(vm))
    print(Fore.CYAN + f"\nValidation complete. {len(vm)} proxies validated across selected protocols." + Style.RESET_ALL)

def main():
    try:
        selected, use_all_sources, do_validate, workers, timeout, fetch_timeout, out_dir = interactive_menu()
    except SystemExit:
        return
    try:
        asyncio.run(main_async(selected, use_all_sources, do_validate, workers, timeout, fetch_timeout, out_dir))
    except KeyboardInterrupt:
        print(Fore.RED + "\nInterrupted by user." + Style.RESET_ALL)
        raise SystemExit(0)

if __name__ == "__main__":
    main()
