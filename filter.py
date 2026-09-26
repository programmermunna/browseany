#!/usr/bin/env python3
"""Filter DB/*.js URL lists down to sites that will actually render in an iframe.

Checks per URL (first failure wins):
  NO_RESPONSE           - connection / timeout error
  HTTP_<code>           - non-200 final status code
  REDIRECT_DOMAIN       - redirects to a different registered domain
  XFO                   - X-Frame-Options header present (any value)
  CSP_FRAME_ANCESTORS   - CSP frame-ancestors restricting embedding
                          (frame-ancestors with a * wildcard is allowed)
  FRAME_BUSTER_JS       - page contains frame-busting JavaScript patterns
  CONTENT_BLOCKED       - "Access denied" / JS-challenge page title
  PARKED                - parked / domain-for-sale page signals
  SPAM                  - gambling / SEO-spam page signals

Usage:
    python3 filter.py                  # filter every DB/*.js file in place
    python3 filter.py news.js games.js # filter specific files
"""

import argparse
import concurrent.futures
import os
import re
import sys

import requests
from urllib.parse import urlparse
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

DB_DIR = "DB"
MAX_WORKERS = 50
TIMEOUT = 12
BODY_LIMIT = 600_000

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# Common multi-label public suffixes so domain dedupe / redirect checks work
# for co.uk, com.au, co.jp, ... without requiring a PSL dependency.
MULTI_PART_SUFFIXES = {
    "ac.uk", "co.uk", "gov.uk", "ltd.uk", "me.uk", "net.uk", "nhs.uk",
    "org.uk", "plc.uk", "sch.uk",
    "ac.in", "co.in", "edu.in", "firm.in", "gen.in", "gov.in", "ind.in",
    "net.in", "nic.in", "org.in", "res.in",
    "ac.jp", "co.jp", "ed.jp", "go.jp", "gr.jp", "lg.jp", "ne.jp", "or.jp",
    "ac.kr", "co.kr", "go.kr", "ne.kr", "or.kr", "pe.kr", "re.kr",
    "ac.nz", "co.nz", "geek.nz", "gen.nz", "govt.nz", "iwi.nz", "maori.nz",
    "net.nz", "org.nz", "school.nz",
    "ac.za", "co.za", "edu.za", "gov.za", "net.za", "org.za", "web.za",
    "asn.au", "com.au", "edu.au", "gov.au", "id.au", "net.au", "org.au",
    "com.bd", "edu.bd", "gov.bd", "net.bd", "org.bd",
    "com.br", "edu.br", "gov.br", "net.br", "org.br",
    "com.cn", "edu.cn", "gov.cn", "net.cn", "org.cn",
    "com.co", "edu.co", "gov.co", "net.co", "nom.co", "org.co",
    "ac.id", "co.id", "go.id", "my.id", "net.id", "or.id", "sch.id",
    "co.il", "gov.il", "net.il", "org.il",
    "ac.ir", "co.ir", "gov.ir", "net.ir", "org.ir",
    "co.ke", "go.ke", "ne.ke", "or.ke",
    "com.mx", "edu.mx", "gob.mx", "net.mx", "org.mx",
    "com.my", "edu.my", "gov.my", "net.my", "org.my",
    "ac.th", "co.th", "go.th", "in.th", "net.th", "or.th",
    "com.tr", "edu.tr", "gov.tr", "net.tr", "org.tr",
    "com.tw", "edu.tw", "gov.tw", "net.tw", "org.tw",
    "com.hk", "edu.hk", "gov.hk", "net.hk", "org.hk",
    "com.sg", "edu.sg", "gov.sg", "net.sg", "org.sg",
    "com.ph", "edu.ph", "gov.ph", "net.ph", "org.ph",
    "com.pk", "edu.pk", "gov.pk", "net.pk", "org.pk",
    "com.ar", "edu.ar", "gob.ar", "net.ar", "org.ar",
    "com.pe", "edu.pe", "gob.pe", "net.pe", "org.pe",
    "com.ve", "edu.ve", "gob.ve", "net.ve", "org.ve",
    "com.uy", "edu.uy", "gub.uy", "net.uy", "org.uy",
    "com.ng", "edu.ng", "gov.ng", "net.ng", "org.ng",
    "com.gh", "edu.gh", "gov.gh", "net.gh", "org.gh",
    "com.eg", "edu.eg", "gov.eg", "net.eg", "org.eg",
    "com.sa", "edu.sa", "gov.sa", "net.sa", "org.sa",
    "com.ae", "edu.ae", "gov.ae", "net.ae", "org.ae",
    "com.qa", "edu.qa", "gov.qa", "net.qa", "org.qa",
    "com.np", "edu.np", "gov.np", "net.np", "org.np",
    "com.lk", "edu.lk", "gov.lk", "net.lk", "org.lk",
    "com.pl", "edu.pl", "gov.pl", "net.pl", "org.pl",
    "com.ru", "edu.ru", "gov.ru", "net.ru", "org.ru",
    "com.vn", "edu.vn", "gov.vn", "net.vn", "org.vn",
    "com.do", "edu.do", "gob.do", "net.do", "org.do",
    "com.gt", "edu.gt", "gob.gt", "net.gt", "org.gt",
    "com.sv", "edu.sv", "gob.sv", "net.sv", "org.sv",
    "com.hn", "edu.hn", "gob.hn", "net.hn", "org.hn",
    "com.ni", "edu.ni", "gob.ni", "net.ni", "org.ni",
    "com.pa", "edu.pa", "gob.pa", "net.pa", "org.pa",
    "com.ec", "edu.ec", "gob.ec", "net.ec", "org.ec",
    "com.py", "edu.py", "gov.py", "net.py", "org.py",
    "com.bo", "edu.bo", "gob.bo", "net.bo", "org.bo",
    "com.cu", "edu.cu", "gob.cu", "net.cu", "org.cu",
    "com.zw", "co.zw", "org.zw", "gov.zw",
    "gob.cl", "gov.cl",
    "com.ua", "edu.ua", "gov.ua", "net.ua", "org.ua",
    "com.kz", "edu.kz", "gov.kz", "net.kz", "org.kz",
    "com.by", "edu.by", "gov.by", "net.by", "org.by",
    "com.az", "edu.az", "gov.az", "net.az", "org.az",
    "com.ge", "edu.ge", "gov.ge", "net.ge", "org.ge",
    "com.am", "edu.am", "gov.am", "net.am", "org.am",
    "com.kg", "edu.kg", "gov.kg", "net.kg", "org.kg",
    "com.tj", "edu.tj", "gov.tj", "net.tj", "org.tj",
    "com.uz", "edu.uz", "gov.uz", "net.uz", "org.uz",
    "com.tm", "edu.tm", "gov.tm", "net.tm", "org.tm",
    "com.mn", "edu.mn", "gov.mn", "net.mn", "org.mn",
    "com.mm", "edu.mm", "gov.mm", "net.mm", "org.mm",
    "com.kh", "edu.kh", "gov.kh", "net.kh", "org.kh",
    "com.la", "edu.la", "gov.la", "net.la", "org.la",
    "com.bn", "edu.bn", "gov.bn", "net.bn", "org.bn",
    "com.jm", "edu.jm", "gov.jm", "net.jm", "org.jm",
    "com.tt", "co.tt", "edu.tt", "gov.tt", "net.tt", "org.tt",
    "com.bb", "edu.bb", "gov.bb", "net.bb", "org.bb",
    "com.bs", "edu.bs", "gov.bs", "net.bs", "org.bs",
    "com.bz", "edu.bz", "gov.bz", "net.bz", "org.bz",
    "com.gy", "edu.gy", "gov.gy", "net.gy", "org.gy",
    "com.sr", "edu.sr", "gov.sr", "net.sr", "org.sr",
    "com.fj", "edu.fj", "gov.fj", "net.fj", "org.fj",
    "com.pg", "edu.pg", "gov.pg", "net.pg", "org.pg",
    "com.sb", "edu.sb", "gov.sb", "net.sb", "org.sb",
    "com.vu", "edu.vu", "gov.vu", "net.vu", "org.vu",
    "com.ws", "edu.ws", "gov.ws", "net.ws", "org.ws",
    "com.to", "edu.to", "gov.to", "net.to", "org.to",
    "com.ki", "edu.ki", "gov.ki", "net.ki", "org.ki",
    "com.tv", "edu.tv", "gov.tv", "net.tv", "org.tv",
    "com.fm", "edu.fm", "gov.fm", "net.fm", "org.fm",
    "com.mh", "edu.mh", "gov.mh", "net.mh", "org.mh",
    "com.pw", "edu.pw", "gov.pw", "net.pw", "org.pw",
    "com.nr", "edu.nr", "gov.nr", "net.nr", "org.nr",
    "com.km", "edu.km", "gov.km", "net.km", "org.km",
    "com.sc", "edu.sc", "gov.sc", "net.sc", "org.sc",
    "com.mu", "edu.mu", "gov.mu", "net.mu", "org.mu",
    "com.mv", "edu.mv", "gov.mv", "net.mv", "org.mv",
    "com.ls", "edu.ls", "gov.ls", "net.ls", "org.ls",
    "com.bw", "edu.bw", "gov.bw", "net.bw", "org.bw",
    "com.na", "edu.na", "gov.na", "net.na", "org.na",
    "com.mz", "edu.mz", "gov.mz", "net.mz", "org.mz",
    "com.zm", "edu.zm", "gov.zm", "net.zm", "org.zm",
    "com.mw", "edu.mw", "gov.mw", "net.mw", "org.mw",
    "com.rw", "edu.rw", "gov.rw", "net.rw", "org.rw",
    "com.ug", "edu.ug", "gov.ug", "net.ug", "org.ug",
    "com.tz", "edu.tz", "gov.tz", "net.tz", "org.tz",
    "com.et", "edu.et", "gov.et", "net.et", "org.et",
    "com.so", "edu.so", "gov.so", "net.so", "org.so",
    "com.sd", "edu.sd", "gov.sd", "net.sd", "org.sd",
    "com.ly", "edu.ly", "gov.ly", "net.ly", "org.ly",
    "com.tn", "edu.tn", "gov.tn", "net.tn", "org.tn",
    "com.dz", "edu.dz", "gov.dz", "net.dz", "org.dz",
    "com.ma", "edu.ma", "gov.ma", "net.ma", "org.ma",
    "com.sn", "edu.sn", "gov.sn", "net.sn", "org.sn",
    "com.ci", "edu.ci", "gov.ci", "net.ci", "org.ci",
    "com.ml", "edu.ml", "gov.ml", "net.ml", "org.ml",
    "com.bf", "edu.bf", "gov.bf", "net.bf", "org.bf",
    "com.ne", "edu.ne", "gov.ne", "net.ne", "org.ne",
    "com.td", "edu.td", "gov.td", "net.td", "org.td",
    "com.cm", "edu.cm", "gov.cm", "net.cm", "org.cm",
    "com.ga", "edu.ga", "gov.ga", "net.ga", "org.ga",
    "com.cg", "edu.cg", "gov.cg", "net.cg", "org.cg",
    "com.gq", "edu.gq", "gov.gq", "net.gq", "org.gq",
    "com.cf", "edu.cf", "gov.cf", "net.cf", "org.cf",
    "com.st", "edu.st", "gov.st", "net.st", "org.st",
    "com.gw", "edu.gw", "gov.gw", "net.gw", "org.gw",
    "com.gn", "edu.gn", "gov.gn", "net.gn", "org.gn",
    "com.sl", "edu.sl", "gov.sl", "net.sl", "org.sl",
    "com.lr", "edu.lr", "gov.lr", "net.lr", "org.lr",
    "com.gm", "edu.gm", "gov.gm", "net.gm", "org.gm",
    "com.cv", "edu.cv", "gov.cv", "net.cv", "org.cv",
    "com.er", "edu.er", "gov.er", "net.er", "org.er",
    "com.dj", "edu.dj", "gov.dj", "net.dj", "org.dj",
    "com.ye", "edu.ye", "gov.ye", "net.ye", "org.ye",
    "com.om", "edu.om", "gov.om", "net.om", "org.om",
    "com.bh", "edu.bh", "gov.bh", "net.bh", "org.bh",
    "com.kw", "edu.kw", "gov.kw", "net.kw", "org.kw",
    "com.iq", "edu.iq", "gov.iq", "net.iq", "org.iq",
    "com.ps", "edu.ps", "gov.ps", "net.ps", "org.ps",
    "com.lb", "edu.lb", "gov.lb", "net.lb", "org.lb",
    "com.jo", "edu.jo", "gov.jo", "net.jo", "org.jo",
    "com.sy", "edu.sy", "gov.sy", "net.sy", "org.sy",
}

BUST_PATTERNS = [
    r"top\.location",
    r"top\s*!=\s*self",
    r"top\s*!==\s*self",
    r"window\.top\s*!=",
    r"self\.top\s*!==",
    r"parent\.location",
    r"frameElement",
    r"framebust",
    r"breakout",
    r"window\.self\s*!==\s*window\.top",
]
BUST_RE = re.compile("|".join(BUST_PATTERNS), re.IGNORECASE)

PARKED_SIGNALS = [
    "domain for sale", "domain is for sale", "buy this domain",
    "this domain may be for sale", "make an offer", "inquire now",
    "sedo.com", "afternic.com", "hugedomains.com", "parkingcrew",
    "dan.com", "undeveloped.com", "bodis.com", "above.com",
    "the domain name", "is available for purchase", "parked free",
]
SPAM_SIGNALS = [
    "gacor", "judi", "togel", "slot online", "situs slot",
    "casino", "poker online", "betting", "sportsbook",
]
BLOCKED_TITLE_SIGNALS = [
    "attention required", "just a moment", "access denied",
    "pardon our interruption", "error 403", "request blocked",
    "verify you are human", "are you a robot", "captcha",
    "cloudflare", "security check",
]
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def registered_domain(host):
    host = host.lower().split(":")[0]
    parts = host.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in MULTI_PART_SUFFIXES:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def filter_unique_domains(urls):
    seen_domains = set()
    unique_urls = []
    for url in urls:
        try:
            domain = registered_domain(urlparse(url).netloc)
            if domain and domain not in seen_domains:
                seen_domains.add(domain)
                unique_urls.append(url)
        except Exception:
            unique_urls.append(url)
    return unique_urls


def check_url(url):
    """Return (verdict, detail). verdict 'OK' means keep."""
    try:
        r = requests.get(
            url, timeout=TIMEOUT, allow_redirects=True, verify=False,
            headers={"User-Agent": UA}, stream=True)
        chunks, size = [], 0
        for chunk in r.iter_content(65536):
            chunks.append(chunk)
            size += len(chunk)
            if size >= BODY_LIMIT:
                break
        body = b"".join(chunks)
        r.close()
    except requests.RequestException:
        return "NO_RESPONSE", ""

    if r.status_code != 200:
        return f"HTTP_{r.status_code}", ""

    orig_dom = registered_domain(urlparse(url).netloc)
    final_dom = registered_domain(urlparse(r.url).netloc)
    if orig_dom != final_dom:
        return f"REDIRECT_DOMAIN({final_dom})", ""

    h = {k.lower(): v for k, v in r.headers.items()}
    if "x-frame-options" in h:
        return "XFO", h["x-frame-options"][:80]
    csp = h.get("content-security-policy", "")
    if "frame-ancestors" in csp.lower():
        m = re.search(r"frame-ancestors([^;]*)", csp, re.IGNORECASE)
        fa = m.group(1).strip() if m else ""
        if "*" not in fa:
            return "CSP_FRAME_ANCESTORS", fa[:120]

    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        text = ""
    low = text.lower()

    m = BUST_RE.search(text)
    if m:
        return "FRAME_BUSTER_JS", m.group(0)

    title_m = TITLE_RE.search(text)
    title = title_m.group(1).strip() if title_m else ""

    if any(t in title.lower() for t in BLOCKED_TITLE_SIGNALS):
        return "CONTENT_BLOCKED", title[:80]

    if any(s in low for s in PARKED_SIGNALS):
        matched = next(s for s in PARKED_SIGNALS if s in low)
        return "PARKED", matched

    spam_hits = sum(1 for s in SPAM_SIGNALS if s in low)
    title_spam = any(s in title.lower() for s in SPAM_SIGNALS)
    if spam_hits >= 3 or title_spam:
        return "SPAM", title[:80]

    return "OK", ""


def process_file(file_path):
    print(f"\nProcessing file: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    var_match = re.search(r'(var|const|let)\s+(\w+)\s*=\s*\[', content)
    if not var_match:
        print(f"Could not find JS array variable in {file_path}. Skipping...")
        return None

    var_declaration = var_match.group(1)
    var_name = var_match.group(2)

    urls = re.findall(r'"(https?://.*?)"', content)
    if not urls:
        print(f"No URLs found in {file_path}.")
        return None

    print(f"Found {len(urls)} URLs. Filtering unique domains...")
    urls = filter_unique_domains(urls)
    print(f"After unique domain filter: {len(urls)} URLs. "
          "Checking live status, iframe headers, frame-busters, parked/spam...")

    keep_urls = []
    filtered_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = zip(urls, executor.map(check_url, urls))
        for url, (verdict, detail) in results:
            if verdict == "OK":
                print(f"[OK]            {url}")
                keep_urls.append(url)
            else:
                tag = f"[{verdict}]" if verdict else "[FILTERED]"
                print(f"{tag:15} {url} {detail}")
                filtered_count += 1

    new_content = f"{var_declaration} {var_name} = [\n"
    for url in keep_urls:
        new_content += f'  "{url}",\n'
    new_content += "];\n"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Done! {file_path} updated. Kept: {len(keep_urls)} / {len(urls)}")

    return {
        "file": os.path.basename(file_path),
        "total": len(urls),
        "kept": len(keep_urls),
        "filtered": filtered_count,
    }


def main():
    parser = argparse.ArgumentParser(description="Filter URLs in DB files")
    parser.add_argument("files", nargs="*",
                        help="Specific DB file names to filter "
                             "(e.g., news.js games.js)")
    args = parser.parse_args()

    results = []

    if args.files:
        for file_name in args.files:
            file_path = os.path.join(DB_DIR, file_name)
            if os.path.exists(file_path):
                result = process_file(file_path)
                if result:
                    results.append(result)
            else:
                print(f"Error: File '{file_name}' not found in {DB_DIR}")
    else:
        js_files = sorted(f for f in os.listdir(DB_DIR) if f.endswith(".js"))
        for file_name in js_files:
            result = process_file(os.path.join(DB_DIR, file_name))
            if result:
                results.append(result)

    if results:
        print("\n" + "=" * 60)
        print("SUMMARY REPORT")
        print("=" * 60)
        total_urls = sum(r["total"] for r in results)
        total_kept = sum(r["kept"] for r in results)
        total_filtered = sum(r["filtered"] for r in results)

        for r in results:
            flag = "  <-- UNDER 100" if r["kept"] < 100 else ""
            print(f"{r['file']}: {r['kept']}/{r['total']} kept "
                  f"({r['filtered']} filtered){flag}")

        print("-" * 60)
        print(f"TOTAL: {total_kept}/{total_urls} kept "
              f"({total_filtered} filtered)")
        print("=" * 60)


if __name__ == "__main__":
    main()
