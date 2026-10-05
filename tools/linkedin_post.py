"""Posts one edition to a LinkedIn page: the prepared text plus the public PDF as a document.

    python3 tools/linkedin_post.py <post.txt> <public-pdf> [--dry-run]

Credentials come from paper.conf (LINKEDIN_PAGE_URN, LINKEDIN_TOKEN_FILE) or from the
environment. Without both, the script exits 0 and says it skipped, so a missing token never
fails the morning run.

What LinkedIn needs before this can work:
  - a LinkedIn Page you administer;
  - a developer app verified against that Page;
  - the Community Management API product approved for the app (LinkedIn reviews this);
  - a member access token with the w_organization_social scope, saved in LINKEDIN_TOKEN_FILE.
Tokens last 60 days, so the file has to be refreshed; the script says so when LinkedIn
answers 401.
"""
import json, os, re, sys, urllib.error, urllib.request

API = "https://api.linkedin.com/rest"
VERSION = "202506"          # LinkedIn requires an explicit, dated API version


def conf(name, default=""):
    if os.environ.get(name):
        return os.environ[name]
    for p in (os.path.join(os.path.expanduser("~"), "DailyReconcile", "paper.conf"),
              os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "paper.conf")):
        if os.path.exists(p):
            for line in open(p):
                m = re.match(rf'\s*{name}\s*=\s*"?([^"#\n]*)"?', line)
                if m:
                    return m.group(1).strip()
    return default


def req(url, token, data=None, method=None, ctype="application/json", raw=False):
    headers = {"Authorization": f"Bearer {token}",
               "LinkedIn-Version": VERSION,
               "X-Restli-Protocol-Version": "2.0.0"}
    if data is not None and not raw:
        data = json.dumps(data).encode()
        headers["Content-Type"] = ctype
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r) as resp:
        body = resp.read()
        return resp.headers, (json.loads(body) if body and resp.headers.get("content-type", "").startswith("application/json") else body)


def post(text, pdf, page_urn, token, title):
    # 1. ask LinkedIn where to put the document
    _, init = req(f"{API}/documents?action=initializeUpload", token,
                  {"initializeUploadRequest": {"owner": page_urn}})
    value = init["value"]
    upload_url, doc_urn = value["uploadUrl"], value["document"]
    # 2. upload the bytes
    req(upload_url, token, open(pdf, "rb").read(), method="PUT",
        ctype="application/octet-stream", raw=True)
    # 3. create the post
    headers, _ = req(f"{API}/posts", token, {
        "author": page_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED",
                         "targetEntities": [], "thirdPartyDistributionChannels": []},
        "content": {"media": {"title": title, "id": doc_urn}},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    })
    return headers.get("x-restli-id") or headers.get("X-RestLi-Id") or "(no id returned)"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if len(args) < 2:
        print(__doc__.strip()); sys.exit(2)
    post_txt, pdf = args[0], args[1]

    page_urn = conf("LINKEDIN_PAGE_URN")
    token_file = conf("LINKEDIN_TOKEN_FILE")
    token = os.environ.get("LINKEDIN_TOKEN", "")
    if not token and token_file and os.path.exists(os.path.expanduser(token_file)):
        token = open(os.path.expanduser(token_file)).read().strip()

    if not page_urn or not token:
        missing = " and ".join(x for x in (
            "LINKEDIN_PAGE_URN" if not page_urn else "",
            "a token (LINKEDIN_TOKEN_FILE)" if not token else "") if x)
        print(f"LINKEDIN SKIPPED: {missing} not set in paper.conf")
        return
    if not os.path.exists(post_txt) or not os.path.exists(pdf):
        print("LINKEDIN SKIPPED: post text or public PDF missing"); return

    text = open(post_txt).read().strip()
    title = os.path.basename(pdf).replace(".pdf", "").replace("-", " ").title()
    if dry:
        print(f"LINKEDIN DRY RUN: would post {len(text)} chars + {pdf} to {page_urn}")
        return
    try:
        pid = post(text, pdf, page_urn, token, title)
        print(f"LINKEDIN POSTED {pid}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        hint = "  (token expired - refresh LINKEDIN_TOKEN_FILE)" if e.code == 401 else ""
        print(f"LINKEDIN FAILED: HTTP {e.code} {detail}{hint}")
    except Exception as e:                                  # network, DNS, bad JSON
        print(f"LINKEDIN FAILED: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
