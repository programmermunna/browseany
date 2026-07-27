import concurrent.futures
import re
import os
import sys
import argparse
import requests
from urllib3.exceptions import InsecureRequestWarning
from urllib.parse import urlparse

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

DB_DIR = "DB"
MAX_WORKERS = 50
TIMEOUT = 10

def filter_unique_domains(urls):
    seen_domains = set()
    unique_urls = []
    for url in urls:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain and domain not in seen_domains:
                seen_domains.add(domain)
                unique_urls.append(url)
        except Exception:
            unique_urls.append(url)
    return unique_urls

def has_frame_blocker_headers(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.head(
            url,
            timeout=TIMEOUT,
            allow_redirects=True,
            verify=False,
            headers=headers
        )
    except requests.RequestException:
        try:
            response = requests.get(
                url,
                timeout=TIMEOUT,
                allow_redirects=True,
                verify=False,
                headers=headers
            )
        except requests.RequestException:
            return False

    for key in response.headers:
        lower_key = key.lower()
        if lower_key in ("x-frame-options", "content-security-policy"):
            return True

    return False

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
    print(f"After unique domain filter: {len(urls)} URLs. Checking iframe blocking headers...")

    keep_urls = []
    blocked_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = zip(urls, executor.map(has_frame_blocker_headers, urls))
        for url, blocked in results:
            if blocked:
                print(f"[BLOCKED] {url}")
                blocked_count += 1
            else:
                print(f"[OK]      {url}")
                keep_urls.append(url)

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
        "blocked": blocked_count
    }

def main():
    parser = argparse.ArgumentParser(description="Filter URLs in DB files")
    parser.add_argument("files", nargs="*", help="Specific DB file names to filter (e.g., file1.js file2.js)")
    args = parser.parse_args()

    results = []

    if args.files:
        # Filter only the specified files
        for file_name in args.files:
            file_path = os.path.join(DB_DIR, file_name)
            if os.path.exists(file_path):
                result = process_file(file_path)
                if result:
                    results.append(result)
            else:
                print(f"Error: File '{file_name}' not found in {DB_DIR}")
    else:
        # Filter all JS files
        js_files = sorted([f for f in os.listdir(DB_DIR) if f.endswith(".js")])
        for file_name in js_files:
            result = process_file(os.path.join(DB_DIR, file_name))
            if result:
                results.append(result)

    # Print summary report
    if results:
        print("\n" + "=" * 60)
        print("SUMMARY REPORT")
        print("=" * 60)
        total_urls = sum(r["total"] for r in results)
        total_kept = sum(r["kept"] for r in results)
        total_blocked = sum(r["blocked"] for r in results)
        
        for r in results:
            print(f"{r['file']}: {r['kept']}/{r['total']} kept ({r['blocked']} blocked)")
        
        print("-" * 60)
        print(f"TOTAL: {total_kept}/{total_urls} kept ({total_blocked} blocked)")
        print("=" * 60)

if __name__ == "__main__":
    main()

