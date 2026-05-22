#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
 PROJET TITANIUM / V-MAX  -  SNIPER V13 "ENDURANCE"
=====================================================================
 Tout V12 (liste complete + throttle global anti-ban) PLUS :
  - Backoff PAR PAYS : un marche bloque se met en pause solo,
    les 15 autres continuent. Zero temps mort global.
  - Pauses humaines : rythme irregulier, micro-pauses aleatoires.
  - Detection de blocage repete -> recul automatique du pays.
  - Deduplication PERSISTANTE sur disque (seen_ids.json) : on ne
    regaspille pas de requetes sur du deja-vu entre deux lancements.
  - Priorite adaptative : les mots-cles qui rapportent des pepites
    sont cherches plus souvent (pondération dynamique).
 Objectif : maximum d'annonces REELLEMENT recuperees, en durant
 le plus longtemps possible sans se faire bannir.
 Arret propre : Ctrl+C (sauvegarde les seen_ids).
=====================================================================
"""

import os
import re
import time
import json
import random
import threading
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime

import requests

# ---------------------------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------------------------

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://fqwkwiikhgwiddqeoecq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_Z4R_4MOvo3C5FE7bGi6YqA_0nknnRiK")
DISCORD_WEBHOOK = os.environ.get(
    "DISCORD_WEBHOOK",
    "https://discord.com/api/webhooks/1505833503927959602/s0EgBiWrEGDu-maKPQkpAQ1NQaSmnIqmG3lS-AVnhzIgazYQz3wYH3xncOnyMw1y-BhK",
)

SEEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_ids.json")

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

MOTS_CLES_RECHERCHE = [
    "aeroswift", "run division", "phenom elite", "dri-fit adv",
    "aeroloft", "shieldrunner", "vaporweave", "cody hudson",
    "a.i.r.", "nike d.y.e", "repel uv", "therma-fit adv",
    "veste sans manche running", "berlin marathon",
]

MARQUES_CIBLES = ["nike", "under armour", "underarmour", "under armor"]

VIP_LEXIQUE = [
    "d.y.e", "do you even", "repel uv", "gilet therma-fit", "veste sans manche",
    "nike always", "artist cody", "a.i.r. cody", "berlin marathon", "running berlin",
    "aeroswift", "aeriswift", "aroswift", "aeroswift knit", "aeroswift pant", "pantalon aeroswift", "aeroswift tight", "aeroswift half tight",
    "cuissard aeroswift", "aeroswift jacket", "veste aeroswift", "aeroswift singlet", "warm-up jacket aeroswift", "aeroswift track jacket",
    "vaporweave", "next%", "breaking2", " b2 ", "tempo", "speed-wicking", "racing kit", "kipchoge", "marathon pack",
    "tokyo marathon", "chicago marathon", "debardeur marathon", "short fendu nike", "cuissard moulant running", "survetement de piste nike",
    "run division", "division running", "rundivision", "nike division", "run division pinnacle", "pinnacle elite",
    "pinnacle woven", "run division flash", "flash pack", "run division reflective", "reflective grid",
    "run division adapt", "run division transform", "transform jacket", "run division packable", "dynamic vent",
    "run division aeroloft", "run division shield", "run division storm-fit", "run division stormfit",
    "run division therma-fit adv", "run division transit", "run division engineered", "run division woven",
    "veste division sacoche", "nike division araignee", "division araignee", "running division spider", "division grid",
    "veste nike bretelles", "veste nike pliable", "division data-mapped", "division body-mapped", "run division dri-fit adv",
    "phenom elite", "phenom", "p.elite", "phenen", "phenom trail", "phenom wild run", "challenger tech", "tapered running",
    "dri-fit adv", "drifit adv", "adv running", "dri-fit adv pant", "pantalon dri-fit adv", "tech knit pant", "knit running pant",
    "dri-fit adv jacket", "tech knit jacket", "aero react", "aeroreact", "aeroreact zip", "veste running texturee",
    "therma-fit adv", "therma fit adv", "therma-fit pant", "pantalon therma-fit", "therma sphere", "winter running pant",
    "storm-fit adv", "stormfit adv", "storm-fit pant", "shield pant", "shieldrunner", "shieldrunner pant", "shield runner",
    "phenom elite shield", "zonal aeroshield jacket", "aeroshield", "zonal aeroshield", "k-way pantalon", "veste pluie running",
    "aeroloft", "impossibly light", "repel jacket", "flash jacket", "reflective jacket", "waterproof running shell",
    "run division hybrid", "run division hybride", "run division 2-in-1", "run division 2 en 1", "tech pack hybrid",
    "tech pack 2-in-1", "aeroswift hybrid", "aeroswift 2-in-1", "aeroswift bi-matiere", "trail hybrid pant", "kiger 2-in-1",
    "wildhorse hybrid", "storm-fit hybrid", "storm-fit hybride", "shield hybrid pant", "aeroloft hybrid", "aeroloft bi-matiere",
    "future fast hybrid", "futurefast hybride", "future fast 2-in-1", "always hybrid", "nsr hybrid",
    "data-mapped hybrid", "mmw hybrid pant", "matthew williams hybride", "mmw 2 en 1",
    "off-white hybrid", "off-white 2-in-1", "ekiden hybrid", "ekiden 2 en 1", "pantalon division collant", "jogging division bi-matiere",
    "k-way collant", "pantalon impermeable mollet serre", "jogging hiver bi-matiere", "pantalon running double couche",
    "pantalon ninja bi-matiere", "jogging k-way bas serre", "legging division par dessus", "short division collant integre",
    "veste division hybride", "veste k-way polaire", "k-way doudoune hybride", "jogging araignee collant", "pantalon grille bi-matiere",
    "ua storm hybrid", "under armour rush hybrid", "qualifier 2-in-1", "ua tech bi-matiere", "hybrid pant", "pantalon hybride",
    "phenom hybrid", "swift pant", "flex swift", "hybride woven", "ua unstoppable hybrid", "under armour hybrid",
    "pantalon collant", "mi jogging mi legging", "mi legging mi pantalon", "jogging bi-matiere", "bimatiere nike", "bas serre mollet",
    "2-in-1 short", "2in1 short", "2-in-1 pant", "short 2 en 1", "pantalon 2 en 1", "flex stride 2-in-1", "twin short",
    "short avec collant integre", "legging avec short par dessus", "collant avec short course", "pantalon double couche",
    "mmw", "matthew m williams", "matthew williams", "nike x mmw", "alyx", "series 001", "series 002", "series 003",
    "off-white running", "virgil abloh", "athlete in progress", "nike x off white", "track and field",
    "nike a.i.r", "artist in residence", "nathan bell", "nathan belle", "a.i.r nathan bell", "i love running", "i hate running",
    "running is a privilege", "cody hudson", "a.i.r cody hudson", "cody hudson polka dot", "kelly anna", "kelly anna london",
    "a.i.r kelly anna", "ryan willms", "run to a magical place", "chaz bundick", "toro y moi", "a.i.r ryan willms",
    "a. savage", "andrew savage", "rostarr", "a.i.r rostarr",
    "nike ekiden", "ekiden pack", "hakone", "rising sun pack", "aeroswift ekiden", "maillot nike japon", "ekiden", "rising sun",
    "br6", "brs", "blue ribbon sports", "sample", "proto", "prototype", "not for resale", "wear test", "promo sample",
    "looksee", "development", "pro issue", "player issued", "player issue", "authentic", "federation", "bowerman track club",
    "btc", "oregon project", "nop", "custom fit", "not for retail", "etiquette rouge", "red label", "maillot kenya",
    "maillot usa", "player exclusive",
    "nike trail", "terra kiger", "kiger", "kiger pant", "wildhorse", "solar chase", "lava loop", "lava loops",
    "dawn range", "juniper", "juniper trail", "trail runner", "trail running jacket", "packable", "trail gore-tex",
]

BLACKLIST = [
    "acg", "tech fleece", "nike tech", "puffer", "corteiz", "nocta", "vintage", "oversized",
    "survet foot", "coton", "cotton", "doudoune basique", "drill", "frip", "retro", "tn",
    "jogger", "jogging basique", "lifestyle", "casual",
    "teplaky", "dresy", "spodnie dresowe", "dres",
    "jeu", "plateau", "board", "game", "jouet", "puzzle", "figurine", "carte", "boite", "box",
    "chaussure", "chaussures", "sneaker", "sneakers", "basket", "baskets", "shoe", "shoes",
    "trainers", "buty", "topanky", "obuv", "scarpe", "zapatillas", "tenisky", "cipo", "cipele",
    "air max", "air force", "dunk", "jordan", "mercurial", "vapormax", "pegasus", "vomero",
    "footscape", "korki", "crampons",
    "lacoste", "stone island", "cp company", "c.p. company", "compagnie",
]
MOTS_AUTO_BAN = ["ljr", "og batch", "gx", "haul", "1:1", "pandabuy", "hoobuy", "weidian", "whatsapp"]
MOTS_SUSPECTS = ["identique au vrai", "fournisseur direct", "sans facture", "discord", "grade a"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# Heures creuses (UTC) ou on ralentit encore plus pour rester discret la nuit.
NIGHT_HOURS = set(range(0, 7))  # 00h-06h

# ---------------------------------------------------------------------------
# 2. ADAPTIVE THROTTLE GLOBAL + mode nuit
# ---------------------------------------------------------------------------


class AdaptiveThrottle:
    def __init__(self, base_delay=2.5, min_delay=2.0, max_delay=120.0):
        self.delay = base_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def _night_factor(self):
        return 1.8 if datetime.utcnow().hour in NIGHT_HOURS else 1.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            sleep_for = max(0.0, self._next_allowed - now)
            base = self.delay * self._night_factor()
            jitter = random.uniform(0, base * 0.6)
            self._next_allowed = max(now, self._next_allowed) + base + jitter
        if sleep_for > 0:
            time.sleep(sleep_for)

    def on_success(self):
        with self._lock:
            self.delay = max(self.min_delay, self.delay - 0.15)

    def on_block(self):
        with self._lock:
            self.delay = min(self.max_delay, self.delay * 1.8)
        return self.delay


THROTTLE = AdaptiveThrottle()

# Etat partage
already_sniped = set()
SNIPE_LOCK = threading.Lock()
laboratoire_ventes = {}
LAB_LOCK = threading.Lock()
STATS = {"vues": 0, "gardees": 0, "blocages": 0}
STATS_LOCK = threading.Lock()
# pondération adaptative des mots-cles (hits par mot)
KW_HITS = defaultdict(int)
KW_LOCK = threading.Lock()


def log(market, msg):
    print(f"{datetime.now().strftime('%H:%M:%S')} | {market:<4} | {msg}", flush=True)


# ---------------------------------------------------------------------------
# 3. DEDUP PERSISTANTE
# ---------------------------------------------------------------------------


def load_seen():
    global already_sniped
    try:
        with open(SEEN_FILE, "r") as f:
            data = json.load(f)
            already_sniped = set(data[-50000:])  # garde les 50k derniers
        print(f"Dedup : {len(already_sniped)} IDs deja vus charges.")
    except (FileNotFoundError, ValueError):
        already_sniped = set()
        print("Dedup : pas de fichier existant, on part de zero.")


def save_seen():
    try:
        with SNIPE_LOCK:
            data = list(already_sniped)[-50000:]
        with open(SEEN_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# 4. SCORING / PRIX
# ---------------------------------------------------------------------------


def verify_legitimacy(item, full_text, price):
    score = 10
    if item.get("photo_count", 0) <= 1:
        score -= 3
    if any(b in full_text for b in MOTS_AUTO_BAN):
        score -= 10
    for s in MOTS_SUSPECTS:
        if s in full_text:
            score -= 2
    if any(v in full_text for v in VIP_LEXIQUE):
        score += 1
    if any(k in full_text for k in ["aeroswift", "adv", "breaking2", "kipchoge"]) and price < 15.0:
        score -= 3
    return max(0, min(10, score))


def price_of(item):
    p = item.get("price")
    if isinstance(p, dict):
        p = p.get("amount") or p.get("numeric") or 0
    try:
        return float(p)
    except (TypeError, ValueError):
        return 999.0


# ---------------------------------------------------------------------------
# 5. SESSION HTTP avec backoff PAR PAYS
# ---------------------------------------------------------------------------


class MarketSession:
    def __init__(self, code, domain, country_id):
        self.code = code
        self.domain = domain
        self.country_id = country_id
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self._warmed = False
        self.local_cooldown = 0.0   # backoff specifique a ce pays
        self.consecutive_blocks = 0

    def _rotate_identity(self):
        # change d'empreinte (UA + nouvelle session) apres trop de blocages
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self._warmed = False

    def in_cooldown(self):
        return time.monotonic() < self.local_cooldown

    def _handle_block(self, status):
        THROTTLE.on_block()
        with STATS_LOCK:
            STATS["blocages"] += 1
        self.consecutive_blocks += 1
        # backoff local croissant, propre a ce pays
        penalty = min(600, 20 * (2 ** min(self.consecutive_blocks, 5)))
        self.local_cooldown = time.monotonic() + penalty
        self._warmed = False
        if self.consecutive_blocks >= 3:
            self._rotate_identity()
            log(self.code, f"HTTP {status} x{self.consecutive_blocks} - rotation UA + pause {penalty}s")
        else:
            log(self.code, f"HTTP {status} - pause locale {penalty}s")

    def warm_up(self):
        if self._warmed:
            return True
        THROTTLE.wait()
        try:
            r = self.s.get(f"https://{self.domain}/", timeout=15)
            if r.status_code == 200:
                self._warmed = True
                self.consecutive_blocks = 0
                THROTTLE.on_success()
                return True
            if r.status_code in (401, 403, 429):
                self._handle_block(r.status_code)
            return False
        except requests.RequestException as e:
            log(self.code, f"warm-up reseau: {e}")
            return False

    def search(self, keyword):
        if self.in_cooldown():
            return []
        if not self.warm_up():
            return []
        THROTTLE.wait()
        params = {
            "search_text": keyword,
            "per_page": "20",
            "order": "newest_first",
            "country_id": str(self.country_id),
        }
        url = f"https://{self.domain}/api/v2/catalog/items?" + urllib.parse.urlencode(params)
        try:
            r = self.s.get(url, timeout=15)
        except requests.RequestException as e:
            log(self.code, f"reseau: {e}")
            return []
        if r.status_code in (401, 403, 429):
            self._handle_block(r.status_code)
            return []
        if r.status_code != 200:
            log(self.code, f"HTTP {r.status_code} inattendu")
            return []
        self.consecutive_blocks = 0
        THROTTLE.on_success()
        try:
            return r.json().get("items", []) or []
        except ValueError:
            return []


# ---------------------------------------------------------------------------
# 6. SORTIES
# ---------------------------------------------------------------------------


def push_supabase(record):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates",
    }
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/annonces", headers=headers,
                      data=json.dumps(record), timeout=15)
    except requests.RequestException:
        pass


def push_discord(item):
    if not DISCORD_WEBHOOK:
        return
    payload = {"embeds": [{
        "title": f"{item['title']}"[:240],
        "url": item["direct_buy_url"],
        "color": 5763719,
        "fields": [
            {"name": "Prix", "value": f"`{item['price']}`", "inline": True},
            {"name": "Origine", "value": f"`{item['country']}`", "inline": True},
            {"name": "LC Score", "value": f"`{item['lc_score']}/10`", "inline": True},
        ],
        "image": {"url": item.get("image_url", "")},
    }]}
    try:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
    except requests.RequestException:
        pass


# ---------------------------------------------------------------------------
# 7. TRAITEMENT
# ---------------------------------------------------------------------------


def process_items(items, code, keyword):
    kept_here = 0
    for item in items:
        item_id = str(item.get("id", ""))
        if not item_id:
            continue
        with SNIPE_LOCK:
            if item_id in already_sniped:
                continue
        with STATS_LOCK:
            STATS["vues"] += 1
        title = item.get("title", "")
        full_text = f"{title} {item.get('description', '')}".lower()
        if not any(m in full_text for m in MARQUES_CIBLES):
            continue
        if any(bad in full_text for bad in BLACKLIST):
            continue
        if any(sh in full_text for sh in ["chaussure", "sneaker", "basket", "shoe", "trainers", "buty", "scarpe", "zapatillas", "air max", "jordan", "dunk", "mercurial"]):
            continue
        is_tshirt = any(kw in full_text for kw in ["t-shirt", "tshirt", "tee-shirt", "tee ", "maillot", "tricko", "koszulka"])
        if is_tshirt and not any(t in full_text for t in ["trail", "division", "aeroswift", "ekiden", "singlet", "racing"]):
            continue
        prix_val = price_of(item)
        lc = verify_legitimacy(item, full_text, prix_val)
        if lc < 7:
            continue
        is_heavy = any(kw in full_text for kw in ["therma-fit adv", "aeroloft", "storm-fit"])
        if is_heavy and prix_val > 90.0:
            continue
        if not is_heavy and prix_val > 60.0:
            continue
        url = item.get("url") or f"https://{MARKETS[code][0]}/items/{item_id}"
        if ".fr/" in url:
            continue
        photo = ""
        if item.get("photo"):
            photo = item["photo"].get("url", "")
        elif item.get("photos") and isinstance(item["photos"], list) and item["photos"]:
            photo = item["photos"][0].get("url", "")
        fiche = {
            "vinted_id": f"vinted_{item_id}",
            "title": title,
            "price": f"{prix_val} EUR",
            "size": item.get("size_title", "N/A"),
            "country": code,
            "platform": "Vinted",
            "image_url": photo,
            "direct_buy_url": url,
            "lc_score": lc,
        }
        with SNIPE_LOCK:
            if item_id in already_sniped:
                continue
            already_sniped.add(item_id)
        push_supabase(fiche)
        push_discord(fiche)
        kept_here += 1
        with STATS_LOCK:
            STATS["gardees"] += 1
        log(code, f"GARDEE [{lc}/10] {prix_val}EUR - {title[:45]}")
        with LAB_LOCK:
            laboratoire_ventes[item_id] = {"timestamp": time.time(), "text": full_text}
    if kept_here:
        with KW_LOCK:
            KW_HITS[keyword] += kept_here


def ordered_keywords():
    """Mots-cles tries : ceux qui rapportent en premier (priorite adaptative)."""
    with KW_LOCK:
        return sorted(MOTS_CLES_RECHERCHE, key=lambda k: KW_HITS.get(k, 0), reverse=True)


# ---------------------------------------------------------------------------
# 8. BOUCLE PAR MARCHE (avec pauses humaines)
# ---------------------------------------------------------------------------


def market_loop(code, domain, country_id, stop_event):
    sess = MarketSession(code, domain, country_id)
    time.sleep(random.uniform(0, 20))  # demarrage decale
    log(code, "thread demarre")
    cycles = 0
    while not stop_event.is_set():
        if sess.in_cooldown():
            time.sleep(5)
            continue
        for keyword in ordered_keywords():
            if stop_event.is_set() or sess.in_cooldown():
                break
            items = sess.search(keyword)
            if items:
                process_items(items, code, keyword)
        cycles += 1
        # pause humaine entre cycles : courte d'habitude, parfois longue
        if random.random() < 0.15:
            pause = random.uniform(120, 300)  # vraie pause "humaine" 2-5 min
            log(code, f"pause humaine {int(pause)}s")
        else:
            pause = random.uniform(20, 45)
        for _ in range(int(pause)):
            if stop_event.is_set():
                break
            time.sleep(1)


# ---------------------------------------------------------------------------
# 9. AUTO-APPRENTISSAGE + SAUVEGARDE PERIODIQUE
# ---------------------------------------------------------------------------


def apprendre_des_rejets():
    """Lit la table rejets et ajoute a la blacklist les mots recurrents de tes suppressions."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/rejets?select=title", headers=headers, timeout=15)
        if r.status_code != 200:
            return
        titres = [x.get("title", "") for x in r.json()]
    except requests.RequestException:
        return
    mots = []
    for t in titres:
        mots.extend(re.findall(r"\b[a-z]{4,}\b", (t or "").lower()))
    protege = set(MARQUES_CIBLES) | {"nike", "armour", "under", "running", "vinted", "aeroswift", "division", "phenom", "trail", "ekiden"}
    for mot, occ in Counter(mots).most_common(20):
        if occ >= 3 and mot not in BLACKLIST and mot not in protege:
            BLACKLIST.append(mot)
            log("APPRENTI", f"mot rejete ajoute blacklist: '{mot}' (vu {occ}x)")


def background_tasks(stop_event):
    last_opt = time.monotonic()
    last_save = time.monotonic()
    last_learn = time.monotonic()
    apprendre_des_rejets()
    while not stop_event.is_set():
        time.sleep(5)
        now = time.monotonic()
        if now - last_save > 300:
            save_seen()
            last_save = now
        if now - last_learn > 1800:
            apprendre_des_rejets()
            last_learn = now
        # auto-apprentissage toutes les 2h
        if now - last_opt > 7200:
            maintenant = time.time()
            mots = []
            with LAB_LOCK:
                for iid, data in list(laboratoire_ventes.items()):
                    if maintenant - data["timestamp"] > 14400:
                        del laboratoire_ventes[iid]
                    else:
                        mots.extend(re.findall(r"\b[a-z]{4,}\b", data["text"].lower()))
            for mot, occ in Counter([m for m in mots if m not in BLACKLIST]).most_common(3):
                if occ > 20 and mot not in VIP_LEXIQUE:
                    VIP_LEXIQUE.append(mot)
                    log("IA", f"mot ajoute au lexique: '{mot}'")
            last_opt = now


# ---------------------------------------------------------------------------
# 10. MAIN
# ---------------------------------------------------------------------------


def self_test_discord():
    if not DISCORD_WEBHOOK:
        return
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": "SNIPER V13 'ADAPTIVE' demarre - veille en cours."}, timeout=10)
        print("Test Discord envoye.")
    except requests.RequestException as e:
        print(f"Test Discord echoue: {e}")


def main():
    print("=" * 60)
    print(" SNIPER V13 'ADAPTIVE' - PROJET TITANIUM")
    print(f" {len(MARKETS)} marches | {len(MOTS_CLES_RECHERCHE)} termes | {len(VIP_LEXIQUE)} mots VIP")
    print(" Backoff par pays | pauses humaines | dedup persistante | mode nuit")
    print("=" * 60)
    load_seen()
    self_test_discord()
    stop_event = threading.Event()
    for code, (domain, cid) in MARKETS.items():
        threading.Thread(target=market_loop, args=(code, domain, cid, stop_event), daemon=True).start()
    threading.Thread(target=background_tasks, args=(stop_event,), daemon=True).start()

    last = time.monotonic()
    try:
        while True:
            time.sleep(2)
            if time.monotonic() - last > 60:
                with STATS_LOCK:
                    print(f"--- STATS | vues:{STATS['vues']} gardees:{STATS['gardees']} "
                          f"blocages:{STATS['blocages']} | throttle:{THROTTLE.delay:.1f}s ---", flush=True)
                last = time.monotonic()
    except KeyboardInterrupt:
        print("\nArret demande (Ctrl+C). Sauvegarde...")
        stop_event.set()
        save_seen()
        time.sleep(2)
        print("Bot arrete proprement. Dedup sauvegardee.")


if __name__ == "__main__":
    main()
