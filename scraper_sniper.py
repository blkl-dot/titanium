#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TITANIUM — Collecteur multi-sources (tout-en-un)
================================================
Un seul script qui :
  1) contient le CATALOGUE des sites par pays (neuf + occasion) ;
  2) applique EXACTEMENT les memes regles que le sniper Vinted
     (anti-chaussures, anti junior/femme, marque, type, collection) ;
  3) calcule un score "bonne affaire" (remise + modele tendance) ;
  4) ecrit dans la meme table Supabase `annonces` avec un champ `etat`
     ('neuf' / 'occasion') et `source` (nom du site) ;
  5) regule le rythme (AdaptiveThrottle) pour ne pas se faire bloquer.

IMPORTANT — a lire avant de lancer :
  * Chaque site a une STRUCTURE HTML differente. Le framework est pret,
    mais le PARSER de chaque site doit etre calibre (selecteurs). Un
    parser generique "best-effort" est fourni en repli + un exemple
    concret (idealo). Active un site quand son parser est valide.
  * Pour INSERER dans Supabase il faut la cle SERVICE (secrete), pas la
    cle publishable (lecture seule). Mets-la dans la variable
    d'environnement SUPABASE_KEY.

Dependances : requests, beautifulsoup4
    pip install requests beautifulsoup4 --break-system-packages
"""

import os, re, time, json, random, hashlib, unicodedata
import requests
from bs4 import BeautifulSoup

# =====================================================================
# CONFIG
# =====================================================================
SB_URL  = os.environ.get("SUPABASE_URL", "https://fqwkwiikhgwiddqeoecq.supabase.co")
SB_KEY  = os.environ.get("SUPABASE_KEY", "")          # cle SERVICE pour insert
DISCORD = os.environ.get("DISCORD_WEBHOOK", "")        # optionnel
TABLE   = "annonces"

# Termes de recherche par defaut (repli si la table `lexique` est vide).
# Idealement le bot lit ta table `lexique` (kind in recherche/signature/vip).
SEARCH_TERMS = [
    "nike dri-fit adv", "nike aeroswift", "nike phenom elite",
    "nike run division", "nike windrunner", "nike storm-fit",
    "nike challenger short", "nike stride short", "nike aeroloft",
    "nike tech fleece", "under armour launch", "under armour qualifier",
]

# Modeles "tendance du moment" -> bonus de score (revue chaque semaine).
TREND_TERMS = [
    "aeroswift", "phenom", "dri-fit adv", "drifit adv", "storm-fit",
    "run division", "windrunner", "aeroloft", "tech fleece", "vaporfly kit",
]

PRICE_MAX = float(os.environ.get("PRICE_MAX", "45"))   # plafond "pas cher"
MIN_SCORE = float(os.environ.get("MIN_SCORE", "6"))    # seuil pour garder

# =====================================================================
# CATALOGUE DES SITES PAR PAYS  (neuf + occasion)
# ---------------------------------------------------------------------
# etat : 'neuf' | 'occasion'
# kind : 'comparator' | 'outlet' | 'marketplace'
# url  : gabarit de recherche ; {q}=requete (url-encodee), {min},{max}=prix
# parser : nom de la fonction de parsing (voir PARSERS). 'generic' = repli.
# active : False tant que le parser n'est pas valide en conditions reelles.
# =====================================================================
SITES = [
    # ---------------- FRANCE ----------------
    {"name":"idealo.fr","country":"FR","etat":"neuf","kind":"comparator",
     "url":"https://www.idealo.fr/prixcomparaison/MainSearchProductCategory.html?q={q}","parser":"idealo","active":True},
    {"name":"sport-outlet.fr","country":"FR","etat":"neuf","kind":"outlet",
     "url":"https://www.sport-outlet.fr/recherche?controller=search&s={q}","parser":"generic","active":False},
    {"name":"courir.fr","country":"FR","etat":"neuf","kind":"outlet",
     "url":"https://www.courir.com/fr/recherche/?q={q}","parser":"generic","active":False},
    {"name":"leboncoin.fr","country":"FR","etat":"occasion","kind":"marketplace",
     "url":"https://www.leboncoin.fr/recherche?text={q}","parser":"generic","active":False},
    {"name":"videdressing.fr","country":"FR","etat":"occasion","kind":"marketplace",
     "url":"https://www.videdressing.com/recherche/?q={q}","parser":"generic","active":False},

    # ---------------- ESPAGNE ----------------
    {"name":"misterrunning.es","country":"ES","etat":"neuf","kind":"outlet",
     "url":"https://www.misterrunning.com/es/buscar?controller=search&s={q}","parser":"generic","active":False},
    {"name":"deporte-outlet.es","country":"ES","etat":"neuf","kind":"outlet",
     "url":"https://www.deporte-outlet.es/buscar?q={q}","parser":"generic","active":False},
    {"name":"outlet-sport.es","country":"ES","etat":"neuf","kind":"outlet",
     "url":"https://www.outlet-sport.es/buscar?controller=search&s={q}","parser":"generic","active":False},
    {"name":"maspormenos.net","country":"ES","etat":"neuf","kind":"outlet",
     "url":"https://maspormenos.net/buscar?controller=search&s={q}","parser":"generic","active":False},
    {"name":"wallapop.es","country":"ES","etat":"occasion","kind":"marketplace",
     "url":"https://es.wallapop.com/app/search?keywords={q}","parser":"generic","active":False},

    # ---------------- ITALIE ----------------
    {"name":"misterrunning.it","country":"IT","etat":"neuf","kind":"outlet",
     "url":"https://www.misterrunning.com/it/cerca?controller=search&s={q}","parser":"generic","active":False},
    {"name":"jdsports.it","country":"IT","etat":"neuf","kind":"outlet",
     "url":"https://www.jdsports.it/ricerca/{q}/","parser":"generic","active":False},
    {"name":"trovaprezzi.it","country":"IT","etat":"neuf","kind":"comparator",
     "url":"https://www.trovaprezzi.it/cerca.aspx?libera={q}","parser":"generic","active":False},
    {"name":"subito.it","country":"IT","etat":"occasion","kind":"marketplace",
     "url":"https://www.subito.it/annunci-italia/vendita/usato/?q={q}","parser":"generic","active":False},

    # ---------------- ALLEMAGNE ----------------
    {"name":"idealo.de","country":"DE","etat":"neuf","kind":"comparator",
     "url":"https://www.idealo.de/preisvergleich/MainSearchProductCategory.html?q={q}","parser":"idealo","active":True},
    {"name":"outdoordeals.de","country":"DE","etat":"neuf","kind":"comparator",
     "url":"https://www.outdoordeals.de/suche/?q={q}","parser":"generic","active":False},
    {"name":"sportscheck.com","country":"DE","etat":"neuf","kind":"outlet",
     "url":"https://www.sportscheck.com/search/?q={q}","parser":"generic","active":False},
    {"name":"kleinanzeigen.de","country":"DE","etat":"occasion","kind":"marketplace",
     "url":"https://www.kleinanzeigen.de/s-{q}/k0","parser":"generic","active":False},

    # ---------------- POLOGNE ----------------
    {"name":"sklepbiegacza.pl","country":"PL","etat":"neuf","kind":"outlet",
     "url":"https://sklepbiegacza.pl/szukaj?q={q}","parser":"generic","active":False},
    {"name":"runexpert.pl","country":"PL","etat":"neuf","kind":"outlet",
     "url":"https://www.runexpert.pl/szukaj?controller=search&s={q}","parser":"generic","active":False},
    {"name":"50style.pl","country":"PL","etat":"neuf","kind":"outlet",
     "url":"https://50style.pl/szukaj?q={q}","parser":"generic","active":False},
    {"name":"olx.pl","country":"PL","etat":"occasion","kind":"marketplace",
     "url":"https://www.olx.pl/oferty/q-{q}/","parser":"generic","active":False},

    # ---------------- MULTI-PAYS (streetwear/occasion premium) ----------------
    {"name":"grailed.com","country":"INT","etat":"occasion","kind":"marketplace",
     "url":"https://www.grailed.com/shop?query={q}","parser":"generic","active":False},
    {"name":"depop.com","country":"INT","etat":"occasion","kind":"marketplace",
     "url":"https://www.depop.com/search/?q={q}","parser":"generic","active":False},
    {"name":"sportsdirect.com","country":"INT","etat":"neuf","kind":"outlet",
     "url":"https://www.sportsdirect.com/SearchResults.aspx?searchText={q}","parser":"generic","active":False},
]

# =====================================================================
# FILTRES — portage exact de la logique du dashboard (index.html)
# =====================================================================
def _norm(t):
    t = (t or "").lower()
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")

SHOE_RX = re.compile(_norm(
    "chaussure|sneaker|basket|shoe|trainers|scarpe|zapatillas|tenisky|buty|"
    "air max|air force|jordan|dunk|mercurial|vapormax|pegasus|vomero|footscape|"
    "korki|crampon|alphafly|vaporfly"))
KIDW_RX = re.compile(_norm(
    "junior|enfant|kid|kids|boy|girl|garcon|fille|youth|jr|"
    "femme|woman|women|damski|damen|mujer|donna|wmns|dziecie|detsk|nino|nina|bimbo"))

def is_shoe(t):      return bool(SHOE_RX.search(_norm(t)))
def is_kid_woman(t): return bool(KIDW_RX.search(_norm(t)))

def brand_of(t):
    t = t.lower()
    if re.search(r"under ?armou?r", t) or re.search(r"\bua\b", t): return "Under Armour"
    if "nike" in t: return "Nike"
    return "Autre"

def type_of(t):
    t = t.lower()
    if re.search(r"(pant|pantalon|tight|collant|jogging|legging|cuissard)", t): return "Pantalon"
    if re.search(r"(veste|jacket|blouson|coupe|windbreaker|gilet|vest|smanicat)", t): return "Veste/Gilet"
    if "short" in t: return "Short"
    if re.search(r"(t-shirt|tshirt|tee|maillot|singlet|debardeur|top|shirt|koszulk|maglia|camiseta)", t): return "Haut/T-shirt"
    if re.search(r"(ensemble|survetement|tuta|dres)", t): return "Ensemble"
    return "Autre"

def coll_of(t):
    t = t.lower()
    table = [("aeroswift","Aeroswift"),("division","Run Division"),("phenom","Phenom Elite"),
             ("therma","Therma-FIT"),("aeroloft","Aeroloft"),("ekiden","Ekiden"),
             ("dri-fit adv","Dri-FIT ADV"),("drifit adv","Dri-FIT ADV"),("storm-fit","Storm-FIT"),
             ("windrunner","Windrunner"),("rush","UA Rush"),("flow","UA Flow"),
             ("qualifier","UA Qualifier"),("unstoppable","UA Unstoppable"),("tech fleece","Tech Fleece")]
    for k, v in table:
        if k in t: return v
    return "Autre"

def is_trend(t):
    n = _norm(t)
    return any(_norm(x) in n for x in TREND_TERMS)

# =====================================================================
# SCORE "bonne affaire" 0..10
#   base remise (0..6) + tendance (+2) + collection connue (+1) + UA cible (+1)
# =====================================================================
def deal_score(item):
    s = 0.0
    disc = item.get("discount", 0) or 0           # 0..1
    s += min(6.0, disc * 8.0)                      # -75% -> 6 pts
    if is_trend(item["name"]): s += 2.0
    if coll_of(item["name"]) != "Autre": s += 1.0
    if brand_of(item["name"]) == "Under Armour": s += 0.5
    if item.get("price", 999) <= PRICE_MAX * 0.6: s += 1.0
    return round(min(10.0, s), 1)

# =====================================================================
# ANTI-BAN — un seul regulateur de rythme partage
# =====================================================================
class AdaptiveThrottle:
    def __init__(self, base=4.0, lo=2.0, hi=45.0):
        self.delay, self.lo, self.hi = base, lo, hi
    def ok(self):
        self.delay = max(self.lo, self.delay * 0.92)
    def blocked(self):
        self.delay = min(self.hi, self.delay * 1.8)
    def wait(self):
        time.sleep(self.delay + random.uniform(0, self.delay * 0.4))

THROTTLE = AdaptiveThrottle()
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
]
def fetch_html(url):
    h = {"User-Agent": random.choice(UA_POOL), "Accept-Language": "fr,en;q=0.8"}
    r = requests.get(url, headers=h, timeout=20)
    if r.status_code in (403, 429, 503):
        THROTTLE.blocked(); raise RuntimeError("blocked %s" % r.status_code)
    r.raise_for_status(); THROTTLE.ok()
    return r.text

# =====================================================================
# PARSERS  (un par site ; 'generic' = repli best-effort)
# Chaque parser renvoie une liste de dicts :
#   {name, price, old_price, image, url}
# =====================================================================
def _to_float(s):
    if not s: return None
    s = s.replace("\xa0", " ")
    m = re.search(r"(\d[\d.\s]*),(\d{2})|\d[\d.,]*", s)
    if not m: return None
    val = m.group(0).replace(" ", "").replace(".", "").replace(",", ".")
    try: return float(re.sub(r"[^\d.]", "", val))
    except: return None

def parse_idealo(html, base):
    """Exemple concret (a verifier en conditions reelles)."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for card in soup.select("[class*=offerList-item], [class*=resultlist] a, div.sr-resultList__item"):
        a = card.select_one("a[href]")
        title = card.get("title") or (a and a.get_text(" ", strip=True))
        if not title: continue
        price = _to_float(card.get_text(" ", strip=True))
        img = card.select_one("img")
        out.append({"name": title.strip(), "price": price, "old_price": None,
                    "image": (img.get("src") if img else ""),
                    "url": (a.get("href") if a else base)})
    return out

def parse_generic(html, base):
    """Repli : tente de reperer cartes produit (lien + prix + image)."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    cands = soup.select("[class*=product], [class*=card], li[class*=item], article")
    for c in cands[:60]:
        a = c.select_one("a[href]")
        if not a: continue
        title = a.get("title") or a.get_text(" ", strip=True)
        if not title or len(title) < 6: continue
        txt = c.get_text(" ", strip=True)
        if "nike" not in txt.lower() and "armour" not in txt.lower(): continue
        price = _to_float(txt)
        img = c.select_one("img")
        href = a.get("href", "")
        if href and href.startswith("/"):
            href = re.match(r"https?://[^/]+", base).group(0) + href
        out.append({"name": title.strip()[:140], "price": price, "old_price": None,
                    "image": (img.get("src") or img.get("data-src") if img else ""),
                    "url": href or base})
    return out

PARSERS = {"idealo": parse_idealo, "generic": parse_generic}

# =====================================================================
# SUPABASE (REST)
# =====================================================================
def sb_headers():
    return {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
            "Content-Type": "application/json", "Prefer": "resolution=ignore-duplicates"}

def already_seen(uid):
    try:
        r = requests.get(SB_URL + "/rest/v1/%s?select=vinted_id&vinted_id=eq.%s" % (TABLE, uid),
                         headers=sb_headers(), timeout=15)
        return r.ok and len(r.json()) > 0
    except: return False

def insert_annonce(row):
    try:
        r = requests.post(SB_URL + "/rest/v1/" + TABLE, headers=sb_headers(),
                          data=json.dumps(row), timeout=15)
        return r.status_code in (200, 201, 204)
    except Exception as e:
        print("   ! insert err", e); return False

def notify(item, site):
    if not DISCORD: return
    try:
        requests.post(DISCORD, json={"content":
            "**%s** — %s€ (score %s) · %s [%s]\n%s" %
            (item["name"][:80], item.get("price"), item["sc"], site["name"], site["etat"], item["url"])},
            timeout=10)
    except: pass

# =====================================================================
# PIPELINE
# =====================================================================
def make_uid(site, item):
    raw = site["name"] + "|" + item["url"]
    return site["country"].lower() + "-" + hashlib.md5(raw.encode()).hexdigest()[:16]

def keep(item):
    n = item["name"]
    if is_shoe(n) or is_kid_woman(n): return False
    if brand_of(n) == "Autre": return False
    if item.get("price") is None or item["price"] > PRICE_MAX: return False
    return True

def process_site(site, terms):
    if not site.get("active"):
        print(" - %s (%s/%s) : parser non valide -> ignore" % (site["name"], site["country"], site["etat"]))
        return 0
    parser = PARSERS.get(site["parser"], parse_generic)
    found = 0
    for term in terms:
        q = requests.utils.quote(term)
        url = site["url"].format(q=q, min=0, max=int(PRICE_MAX))
        THROTTLE.wait()
        try:
            html = fetch_html(url)
        except Exception as e:
            print("   x %s '%s' : %s" % (site["name"], term, e)); continue
        for it in parser(html, url):
            if not it.get("name"): continue
            if it.get("old_price") and it.get("price"):
                it["discount"] = max(0.0, 1 - it["price"] / it["old_price"])
            else:
                it["discount"] = 0.0
            if not keep(it): continue
            it["sc"] = deal_score(it)
            if it["sc"] < MIN_SCORE: continue
            uid = make_uid(site, it)
            if already_seen(uid): continue
            row = {
                "vinted_id": uid, "title": it["name"], "price": it["price"],
                "country": site["country"], "image_url": it.get("image", ""),
                "direct_buy_url": it["url"], "lc_score": it["sc"],
                "etat": site["etat"], "source": site["name"],
            }
            if insert_annonce(row):
                found += 1; notify(it, site)
                print("   + [%s] %s %s€ (%s)" % (site["etat"], it["name"][:60], it["price"], it["sc"]))
    return found

def load_terms():
    """Lit la table `lexique` (kind recherche/signature/vip) sinon repli."""
    if not SB_KEY: return SEARCH_TERMS
    try:
        r = requests.get(SB_URL + "/rest/v1/lexique?select=mot,kind", headers=sb_headers(), timeout=15)
        rows = r.json() if r.ok else []
        terms = [x["mot"] for x in rows if x.get("kind") in ("recherche", "signature", "vip")]
        return terms or SEARCH_TERMS
    except: return SEARCH_TERMS

def main():
    if not SB_KEY:
        print("!! SUPABASE_KEY manquante (cle SERVICE). export SUPABASE_KEY=...  -> insertion desactivee\n")
    terms = load_terms()
    print("Termes:", len(terms), "| Sites:", len(SITES), "| actifs:",
          sum(1 for s in SITES if s.get("active")), "\n")
    total = 0
    for site in SITES:
        total += process_site(site, terms)
    print("\nTermine. %d nouvelle(s) annonce(s) ajoutee(s)." % total)

if __name__ == "__main__":
    main()
