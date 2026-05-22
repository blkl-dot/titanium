cd ~/v-max-dashboard
rm -f sniper_*.py vmax_*.pycat > scraper_sniper.py <<'#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SNIPER V12 STEADY - liste complete V-MAX 8.2 + anti-ban global."""

import os, re, time, json, random, threading, urllib.parse
from collections import Counter
from datetime import datetime
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://fqwkwiikhgwiddqeoecq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_Z4R_4MOvo3C5FE7bGi6YqA_0nknnRiK")
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "https://discord.com/api/webhooks/1505833503927959602/s0EgBiWrEGDu-maKPQkpAQ1NQaSmnIqmG3lS-AVnhzIgazYQz3wYH3xncOnyMw1y-BhK")

MARKETS = {
    "PL": ("www.vinted.pl", 17), "UK": ("www.vinted.co.uk", 9),
    "IT": ("www.vinted.it", 16), "CZ": ("www.vinted.cz", 23),
    "ES": ("www.vinted.es", 8),  "PT": ("www.vinted.pt", 22),
    "NL": ("www.vinted.nl", 5),  "BE": ("www.vinted.be", 2),
    "LU": ("www.vinted.lu", 4),  "SE": ("www.vinted.se", 21),
    "SK": ("www.vinted.sk", 24), "RO": ("www.vinted.ro", 30),
    "HU": ("www.vinted.hu", 29), "LT": ("www.vinted.lt", 32),
    "HR": ("www.vinted.hr", 31), "GR": ("www.vinted.gr", 35),
}

MOTS_CLES_RECHERCHE = ["aeroswift", "run division", "phenom elite", "dri-fit adv", "aeroloft", "shieldrunner", "vaporweave", "cody hudson", "a.i.r.", "nike d.y.e", "repel uv", "therma-fit adv", "veste sans manche running", "berlin marathon"]
MARQUES_CIBLES = ["nike", "under armour", "underarmour", "under armor"]

VIP_LEXIQUE = ["d.y.e", "do you even", "repel uv", "gilet therma-fit", "veste sans manche", "nike always", "artist cody", "a.i.r. cody", "berlin marathon", "running berlin", "aeroswift", "aeriswift", "aroswift", "aeroswift knit", "aeroswift pant", "pantalon aeroswift", "aeroswift tight", "aeroswift half tight", "cuissard aeroswift", "aeroswift jacket", "veste aeroswift", "aeroswift singlet", "warm-up jacket aeroswift", "aeroswift track jacket", "vaporweave", "next%", "breaking2", " b2 ", "tempo", "speed-wicking", "racing kit", "kipchoge", "marathon pack", "tokyo marathon", "chicago marathon", "debardeur marathon", "short fendu nike", "cuissard moulant running", "survetement de piste nike", "run division", "division running", "rundivision", "nike division", "run division pinnacle", "pinnacle elite", "pinnacle woven", "run division flash", "flash pack", "run division reflective", "reflective grid", "run division adapt", "run division transform", "transform jacket", "run division packable", "dynamic vent", "run division aeroloft", "run division shield", "run division storm-fit", "run division stormfit", "run division therma-fit adv", "run division transit", "run division engineered", "run division woven", "veste division sacoche", "nike division araignee", "division araignee", "running division spider", "division grid", "veste nike bretelles", "veste nike pliable", "division data-mapped", "division body-mapped", "run division dri-fit adv", "phenom elite", "phenom", "p.elite", "phenen", "phenom trail", "phenom wild run", "challenger tech", "tapered running", "dri-fit adv", "drifit adv", "adv running", "dri-fit adv pant", "pantalon dri-fit adv", "tech knit pant", "knit running pant", "dri-fit adv jacket", "tech knit jacket", "aero react", "aeroreact", "aeroreact zip", "veste running texturee", "therma-fit adv", "therma fit adv", "therma-fit pant", "pantalon therma-fit", "therma sphere", "winter running pant", "storm-fit adv", "stormfit adv", "storm-fit pant", "shield pant", "shieldrunner", "shieldrunner pant", "shield runner", "phenom elite shield", "zonal aeroshield jacket", "aeroshield", "zonal aeroshield", "k-way pantalon", "veste pluie running", "aeroloft", "impossibly light", "repel jacket", "flash jacket", "reflective jacket", "waterproof running shell", "run division hybrid", "run division hybride", "run division 2-in-1", "run division 2 en 1", "tech pack hybrid", "tech pack 2-in-1", "aeroswift hybrid", "aeroswift 2-in-1", "aeroswift bi-matiere", "trail hybrid pant", "kiger 2-in-1", "wildhorse hybrid", "storm-fit hybrid", "storm-fit hybride", "shield hybrid pant", "aeroloft hybrid", "aeroloft bi-matiere", "future fast hybrid", "futurefast hybride", "future fast 2-in-1", "always hybrid", "nsr hybrid", "data-mapped hybrid", "mmw hybrid pant", "matthew williams hybride", "mmw 2 en 1", "off-white hybrid", "off-white 2-in-1", "ekiden hybrid", "ekiden 2 en 1", "pantalon division collant", "jogging division bi-matiere", "k-way collant", "pantalon impermeable mollet serre", "jogging hiver bi-matiere", "pantalon running double couche", "pantalon ninja bi-matiere", "jogging k-way bas serre", "legging division par dessus", "short division collant integre", "veste division hybride", "veste k-way polaire", "k-way doudoune hybride", "jogging araignee collant", "pantalon grille bi-matiere", "ua storm hybrid", "under armour rush hybrid", "qualifier 2-in-1", "ua tech bi-matiere", "hybrid pant", "pantalon hybride", "phenom hybrid", "swift pant", "flex swift", "hybride woven", "ua unstoppable hybrid", "under armour hybrid", "pantalon collant", "mi jogging mi legging", "mi legging mi pantalon", "jogging bi-matiere", "bimatiere nike", "bas serre mollet", "2-in-1 short", "2in1 short", "2-in-1 pant", "short 2 en 1", "pantalon 2 en 1", "flex stride 2-in-1", "twin short", "short avec collant integre", "legging avec short par dessus", "collant avec short course", "pantalon double couche", "mmw", "matthew m williams", "matthew williams", "nike x mmw", "alyx", "series 001", "series 002", "series 003", "off-white running", "virgil abloh", "athlete in progress", "nike x off white", "track and field", "nike a.i.r", "artist in residence", "nathan bell", "nathan belle", "a.i.r nathan bell", "i love running", "i hate running", "running is a privilege", "cody hudson", "a.i.r cody hudson", "cody hudson polka dot", "kelly anna", "kelly anna london", "a.i.r kelly anna", "ryan willms", "run to a magical place", "chaz bundick", "toro y moi", "a.i.r ryan willms", "a. savage", "andrew savage", "rostarr", "a.i.r rostarr", "nike ekiden", "ekiden pack", "hakone", "rising sun pack", "aeroswift ekiden", "maillot nike japon", "ekiden", "rising sun", "br6", "brs", "blue ribbon sports", "sample", "proto", "prototype", "not for resale", "wear test", "promo sample", "looksee", "development", "pro issue", "player issued", "player issue", "authentic", "federation", "bowerman track club", "btc", "oregon project", "nop", "custom fit", "not for retail", "etiquette rouge", "red label", "maillot kenya", "maillot usa", "player exclusive", "nike trail", "terra kiger", "kiger", "kiger pant", "wildhorse", "solar chase", "lava loop", "lava loops", "dawn range", "juniper", "juniper trail", "trail runner", "trail running jacket", "packable", "trail gore-tex"]

BLACKLIST = ["acg", "tech fleece", "nike tech", "puffer", "corteiz", "nocta", "vintage", "oversized", "survet foot", "coton", "cotton", "doudoune basique", "drill", "frip", "retro", "sneaker", "tn", "jogger", "jogging basique", "lifestyle", "casual", "teplaky", "dresy", "spodnie dresowe", "dres", "jeu", "plateau", "board", "game", "jouet", "puzzle", "figurine", "carte", "boite", "box"]
MOTS_AUTO_BAN = ["ljr", "og batch", "gx", "haul", "1:1", "pandabuy", "hoobuy", "weidian", "whatsapp"]
MOTS_SUSPECTS = ["identique au vrai", "fournisseur direct", "sans facture", "discord", "grade a"]

USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"]


class AdaptiveThrottle:
    def __init__(self, base_delay=2.5, min_delay=2.0, max_delay=90.0):
        self.delay = base_delay; self.min_delay = min_delay; self.max_delay = max_delay
        self._lock = threading.Lock(); self._next_allowed = 0.0
    def wait(self):
        with self._lock:
            now = time.monotonic(); sleep_for = max(0.0, self._next_allowed - now)
            jitter = random.uniform(0, self.delay * 0.5)
            self._next_allowed = max(now, self._next_allowed) + self.delay + jitter
        if sleep_for > 0: time.sleep(sleep_for)
    def on_success(self):
        with self._lock: self.delay = max(self.min_delay, self.delay - 0.15)
    def on_block(self):
        with self._lock: self.delay = min(self.max_delay, self.delay * 1.8)
        return self.delay


THROTTLE = AdaptiveThrottle()
already_sniped = set(); SNIPE_LOCK = threading.Lock()
laboratoire_ventes = {}; LAB_LOCK = threading.Lock()
STATS = {"vues": 0, "gardees": 0, "blocages": 0}; STATS_LOCK = threading.Lock()


def log(market, msg):
    print(f"{datetime.now().strftime('%H:%M:%S')} | {market:<4} | {msg}", flush=True)


def verify_legitimacy(item, full_text, price):
    score = 10
    if item.get("photo_count", 0) <= 1: score -= 3
    if any(b in full_text for b in MOTS_AUTO_BAN): score -= 10
    for s in MOTS_SUSPECTS:
        if s in full_text: score -= 2
    if any(v in full_text for v in VIP_LEXIQUE): score += 1
    if any(k in full_text for k in ["aeroswift", "adv", "breaking2", "kipchoge"]) and price < 15.0: score -= 3
    return max(0, min(10, score))


def price_of(item):
    p = item.get("price")
    if isinstance(p, dict): p = p.get("amount") or p.get("numeric") or 0
    try: return float(p)
    except (TypeError, ValueError): return 999.0


class MarketSession:
    def __init__(self, code, domain, country_id):
        self.code = code; self.domain = domain; self.country_id = country_id
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": random.choice(USER_AGENTS), "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9"})
        self._warmed = False
    def warm_up(self):
        if self._warmed: return True
        THROTTLE.wait()
        try:
            r = self.s.get(f"https://{self.domain}/", timeout=15)
            if r.status_code == 200:
                self._warmed = True; THROTTLE.on_success(); return True
            if r.status_code in (401, 403, 429):
                d = THROTTLE.on_block()
                with STATS_LOCK: STATS["blocages"] += 1
                log(self.code, f"HTTP {r.status_code} (warm-up) - throttle {d:.1f}s")
            return False
        except requests.RequestException as e:
            log(self.code, f"warm-up reseau: {e}"); return False
    def search(self, keyword):
        if not self.warm_up(): return []
        THROTTLE.wait()
        params = {"search_text": keyword, "per_page": "20", "order": "newest_first", "country_id": str(self.country_id)}
        url = f"https://{self.domain}/api/v2/catalog/items?" + urllib.parse.urlencode(params)
        try: r = self.s.get(url, timeout=15)
        except requests.RequestException as e:
            log(self.code, f"reseau: {e}"); return []
        if r.status_code in (401, 403, 429):
            d = THROTTLE.on_block()
            with STATS_LOCK: STATS["blocages"] += 1
            log(self.code, f"HTTP {r.status_code} - backoff, throttle {d:.1f}s")
            self._warmed = False; return []
        if r.status_code != 200:
            log(self.code, f"HTTP {r.status_code} inattendu"); return []
        THROTTLE.on_success()
        try: return r.json().get("items", []) or []
        except ValueError: return []


def push_supabase(record):
    if not SUPABASE_URL or not SUPABASE_KEY: return
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "resolution=ignore-duplicates"}
    try: requests.post(f"{SUPABASE_URL}/rest/v1/annonces", headers=headers, data=json.dumps(record), timeout=15)
    except requests.RequestException: pass


def push_discord(item):
    if not DISCORD_WEBHOOK: return
    payload = {"embeds": [{"title": f"{item['title']}"[:240], "url": item["direct_buy_url"], "color": 5763719, "fields": [{"name": "Prix", "value": f"`{item['price']}`", "inline": True}, {"name": "Origine", "value": f"`{item['country']}`", "inline": True}, {"name": "LC Score", "value": f"`{item['lc_score']}/10`", "inline": True}], "image": {"url": item.get("image_url", "")}}]}
    try: requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
    except requests.RequestException: pass


def process_items(items, code):
    for item in items:
        item_id = str(item.get("id", ""))
        if not item_id: continue
        with SNIPE_LOCK:
            if item_id in already_sniped: continue
        with STATS_LOCK: STATS["vues"] += 1
        title = item.get("title", "")
        full_text = f"{title} {item.get('description', '')}".lower()
        if not any(m in full_text for m in MARQUES_CIBLES): continue
        if any(bad in full_text for bad in BLACKLIST): continue
        is_tshirt = any(kw in full_text for kw in ["t-shirt", "tshirt", "tee-shirt", "tee ", "maillot", "tricko", "koszulka"])
        if is_tshirt and not any(t in full_text for t in ["trail", "division", "aeroswift", "ekiden", "singlet", "racing"]): continue
        prix_val = price_of(item)
        lc = verify_legitimacy(item, full_text, prix_val)
        if lc < 7: continue
        is_heavy = any(kw in full_text for kw in ["therma-fit adv", "aeroloft", "storm-fit"])
        if is_heavy and prix_val > 90.0: continue
        if not is_heavy and prix_val > 60.0: continue
        url = item.get("url") or f"https://{MARKETS[code][0]}/items/{item_id}"
        if ".fr/" in url: continue
        photo = ""
        if item.get("photo"): photo = item["photo"].get("url", "")
        elif item.get("photos") and isinstance(item["photos"], list) and item["photos"]: photo = item["photos"][0].get("url", "")
        fiche = {"vinted_id": f"vinted_{item_id}", "title": title, "price": f"{prix_val} EUR", "size": item.get("size_title", "N/A"), "country": code, "platform": "Vinted", "image_url": photo, "direct_buy_url": url, "lc_score": lc}
        with SNIPE_LOCK:
            if item_id in already_sniped: continue
            already_sniped.add(item_id)
        push_supabase(fiche); push_discord(fiche)
        with STATS_LOCK: STATS["gardees"] += 1
        log(code, f"GARDEE [{lc}/10] {prix_val}EUR - {title[:45]}")
        with LAB_LOCK: laboratoire_ventes[item_id] = {"timestamp": time.time(), "text": full_text}


def market_loop(code, domain, country_id, stop_event):
    sess = MarketSession(code, domain, country_id)
    time.sleep(random.uniform(0, 15))
    log(code, "thread demarre")
    while not stop_event.is_set():
        for keyword in MOTS_CLES_RECHERCHE:
            if stop_event.is_set(): break
            items = sess.search(keyword)
            if items: process_items(items, code)
        for _ in range(25):
            if stop_event.is_set(): break
            time.sleep(1)


def self_optimize(stop_event):
    while not stop_event.is_set():
        for _ in range(7200):
            if stop_event.is_set(): return
            time.sleep(1)
        maintenant = time.time(); mots = []
        with LAB_LOCK:
            for iid, data in list(laboratoire_ventes.items()):
                if maintenant - data["timestamp"] > 14400: del laboratoire_ventes[iid]
                else: mots.extend(re.findall(r"\b[a-z]{4,}\b", data["text"].lower()))
        for mot, occ in Counter([m for m in mots if m not in BLACKLIST]).most_common(3):
            if occ > 20 and mot not in VIP_LEXIQUE:
                VIP_LEXIQUE.append(mot); log("IA", f"mot ajoute: '{mot}'")


def self_test_discord():
    if not DISCORD_WEBHOOK: return
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": "SNIPER V12 'STEADY' demarre - veille en cours."}, timeout=10)
        print("Test Discord envoye.")
    except requests.RequestException as e:
        print(f"Test Discord echoue: {e}")


def main():
    print("=" * 60)
    print(" SNIPER V12 'STEADY' - PROJET TITANIUM")
    print(f" {len(MARKETS)} marches | {len(MOTS_CLES_RECHERCHE)} termes | {len(VIP_LEXIQUE)} mots VIP")
    print(" Anti-ban : throttle global partage. France exclue.")
    print("=" * 60)
    self_test_discord()
    stop_event = threading.Event()
    for code, (domain, cid) in MARKETS.items():
        threading.Thread(target=market_loop, args=(code, domain, cid, stop_event), daemon=True).start()
    threading.Thread(target=self_optimize, args=(stop_event,), daemon=True).start()
    last = time.monotonic()
    try:
        while True:
            time.sleep(2)
            if time.monotonic() - last > 60:
                with STATS_LOCK:
                    print(f"--- STATS | vues:{STATS['vues']} gardees:{STATS['gardees']} blocages:{STATS['blocages']} | throttle:{THROTTLE.delay:.1f}s ---", flush=True)
                last = time.monotonic()
    except KeyboardInterrupt:
        print("\nArret demande (Ctrl+C).")
        stop_event.set(); time.sleep(2); print("Bot arrete proprement.")


if __name__ == "__main__":
    main()'

