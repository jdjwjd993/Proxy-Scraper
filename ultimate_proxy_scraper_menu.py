ESET_ALL)
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
