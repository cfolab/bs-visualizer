import requests
import zipfile
import io
import os
import pandas as pd
from bs4 import BeautifulSoup
import re

# Copy of necessary utils
EDINET_CODE_LIST_URL = "https://disclosure.edinet-fsa.go.jp/LI/WLI/KAIJI/CONF/EN/edinet_code_list.zip" # Using EN list? No, try standard.
# Actually let's just hardcode 8058's known edinet code if possible, or fetch list.
# 8058 is Mitsubishi Corp.
# To be safe, I'll use the existing generic logic but stripped down.

API_ENDPOINT_LIST = "https://disclosure.edinet-fsa.go.jp/api/v2/documents.json"
API_ENDPOINT_DOC = "https://disclosure.edinet-fsa.go.jp/api/v2/documents"
KEY = "8f037ddc5c6444c9b3e1555546294d3f" # From local file env

def get_code(ticker):
    # Quick hack: Download list or use existing cache
    if os.path.exists("edinet_code_list.csv"):
        df = pd.read_csv("edinet_code_list.csv", encoding="cp932", skiprows=1)
        # Search
        # Column names might differ if I messed up earlier, just print columns
        # print(df.columns)
        # Assuming standard
        sec_col = [c for c in df.columns if "証券コード" in c][0]
        edt_col = [c for c in df.columns if "ＥＤＩＮＥＴコード" in c][0]
        
        row = df[df[sec_col].astype(str).str.startswith(str(ticker))]
        if not row.empty:
            return row.iloc[0][edt_col]
    return None

def search_doc(ecode):
    params = {
        "Subscription-Key": KEY,
        "type": 2, 
        "EdinetCode": ecode,
        "periodStart": "2024-01-01", # Recent
        "periodEnd": "2025-01-01"    # To now
    }
    # Try different doc types
    res = requests.get(API_ENDPOINT_LIST, params=params)
    if res.status_code != 200: return None
    j = res.json()
    # Filter for type 120, 140
    docs = [d for d in j.get("results", []) if d["docTypeCode"] in ["120", "130", "140"]]
    if docs:
        return docs[0]["docID"]
    return None

def main():
    ticker = "8058"
    print(f"Searching for {ticker}...")
    ecode = get_code(ticker)
    if not ecode:
        print("Edinet Code not found (cache might be missing).")
        return

    print(f"EdinetCode: {ecode}")
    docid = search_doc(ecode)
    if not docid:
        print("Doc ID not found.")
        return
        
    print(f"DocID: {docid}")
    
    # Download
    url = f"{API_ENDPOINT_DOC}/{docid}"
    params = {"type": 1, "Subscription-Key": KEY}
    res = requests.get(url, params=params)
    
    # Unzip
    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
        xbrl = None
        for n in z.namelist():
            if n.endswith(".xbrl") and "PublicDoc" in n:
                xbrl = n
                with z.open(n) as f:
                    content = f.read()
                    break
        
        if not xbrl:
            print("No XBRL found")
            return
            
        print(f"Parsing {xbrl}...")
        soup = BeautifulSoup(content, "lxml-xml")
        
        # ANALYSIS
        print("\n--- CONTEXT REFS ---")
        contexts = set()
        for tag in soup.find_all(contextRef=True):
            contexts.add(tag["contextRef"])
        
        for c in sorted(list(contexts))[:20]:
            print(c)
            
        print("\n--- TAGS (Assets/Equity) ---")
        # Find all tags ending in Assets or Equity
        # We'll just look at children of root or specific namespaces
        # Or just regex search name
        import re
        pat = re.compile(r".*:(Total)?Assets$|.*:Equity.*")
        found = soup.find_all(pat)
        seen = set()
        for t in found[:50]:
            if t.name not in seen:
                print(f"{t.name} | Context: {t.get('contextRef')} | Val: {t.text[:20]}")
                seen.add(t.name)
                
        print("\n--- IFRS SPECIFIC ---")
        pat_ifrs = re.compile(r".*ifrs.*", re.IGNORECASE)
        found_ifrs = soup.find_all(pat_ifrs)
        seen_ifrs = set()
        for t in found_ifrs[:50]:
             if t.name not in seen_ifrs:
                print(f"{t.name} | Context: {t.get('contextRef')}")
                seen_ifrs.add(t.name)

if __name__ == "__main__":
    main()
