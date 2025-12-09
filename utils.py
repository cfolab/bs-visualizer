import requests
import pandas as pd
import datetime
import os
import io
import zipfile
from bs4 import BeautifulSoup

# Constants
EDINET_API_KEY = "c4ce27d66c84409d868224b250accfd5"
EDINET_CODE_LIST_URL = "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip"
API_ENDPOINT_DOCS = "https://disclosure.edinet-fsa.go.jp/api/v2/documents.json"
API_ENDPOINT_DOC = "https://disclosure.edinet-fsa.go.jp/api/v2/documents"

def get_edinet_code_list():
    """
    Downloads and provides a mapping of Ticker -> EdinetCode.
    """
    cache_path = "edinet_code_list.csv"
    
    if os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path, encoding="cp932", skiprows=1)
            return df
        except:
            pass # Reload if error
            
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(EDINET_CODE_LIST_URL, headers=headers, timeout=30)
        
        if res.status_code == 200:
            # Check content type or just try unzip
            content = res.content
            
            # Extract CSV from ZIP in memory
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                # Find the CSV file
                csv_filename = None
                for name in z.namelist():
                    if name.endswith(".csv"):
                        csv_filename = name
                        break
                
                if not csv_filename:
                    print("Error: No CSV found in Code List ZIP")
                    return None
                    
                with z.open(csv_filename) as f:
                    # Save to cache
                    with open(cache_path, "wb") as cache:
                        cache.write(f.read())
            
            # Read from cache
            df = pd.read_csv(cache_path, encoding="cp932", skiprows=1)
            return df
        else:
            print(f"Error downloading code list: Status {res.status_code}")
            return None
    except Exception as e:
        print(f"Error downloading code list: {e}")
        return None
    return None

def get_edinet_code(ticker, code_list_df):
    """
    Finds EdinetCode and Company Name for a given ticker.
    Returns (edinet_code, company_name)
    """
    if code_list_df is None:
        raise ValueError("Code list is empty or failed to load.")
    
    ticker = str(ticker)
    
    cols = code_list_df.columns
    sec_code_col = [c for c in cols if "証券コード" in c]
    edinet_code_col = [c for c in cols if "ＥＤＩＮＥＴコード" in c or "EdinetCode" in c]
    company_name_col = [c for c in cols if "提出者名" in c or "SubmitterName" in c]
    
    if not sec_code_col or not edinet_code_col:
        return None, None
        
    sec_col = sec_code_col[0]
    edinet_col = edinet_code_col[0]
    name_col = company_name_col[0] if company_name_col else None
    
    target = code_list_df[code_list_df[sec_col].astype(str).str.startswith(ticker, na=False)]
    if not target.empty:
        ecode = target.iloc[0][edinet_col]
        cname = target.iloc[0][name_col] if name_col else "Unknown"
        return ecode, cname
        
    return None, None

def search_latest_yuho(edinet_code):
    """
    Searches for the latest Annual (120), Quarterly (140), or Semi-Annual (160) Report in the last 365 days.
    Returns docID if found.
    """
    # 120: Annual Security Report
    # 140: Quarterly Report
    # 160: Semi-Annual Report
    target_docs = ["120", "140", "160"]
    
    today = datetime.date.today()
    
    # Check last 365 days
    for i in range(365): 
        date = today - datetime.timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        
        params = {
            "date": date_str,
            "type": 2,
            "Subscription-Key": EDINET_API_KEY
        }
        
        try:
            res = requests.get(API_ENDPOINT_DOCS, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                results = data.get("results", [])
                if not results:
                    continue
                
                # Filter for this proper company and doc type
                for item in results:
                    if item.get("edinetCode") == edinet_code:
                        dtype = item.get("docTypeCode")
                        if dtype in target_docs:
                            # Preferentially we might want the newest
                            return item.get("docID")
        except:
            continue
            
    return None

def fetch_financial_data(ticker_code):
    """
    Main function to get BS data.
    """
    # 1. Get Code List
    try:
        df_code = get_edinet_code_list()
    except Exception as e:
         return {"error": "Failed to load EDINET Code List", "details": str(e)}

    if df_code is None:
        return {"error": "Failed to load EDINET Code List (returned None)"}
        
    # 2. Get Edinet Code
    try:
        edinet_code, company_name = get_edinet_code(ticker_code, df_code)
    except Exception as e:
        return {"error": f"Error finding ticker {ticker_code}", "details": str(e)}

    if not edinet_code:
        return {"error": f"Ticker {ticker_code} not found or no EDINET Code"}
        
    # 3. Search Document
    doc_id = search_latest_yuho(edinet_code)
    if not doc_id:
        return {"error": "No Annual/Quarterly Report found in the last 365 days"}
        
    # 4. Download and Parse
    # Use API to get XBRL zip
    url = f"{API_ENDPOINT_DOC}/{doc_id}"
    params = {
        "type": 1, # 1 for ZIP (XBRL)
        "Subscription-Key": EDINET_API_KEY
    }
    
    res = requests.get(url, params=params)
    if res.status_code != 200:
        return {"error": "Failed to download document"}
        
    # Process Zip
    # Save zip temporarily
    zip_path = f"doc_{doc_id}.zip"
    with open(zip_path, "wb") as f:
        f.write(res.content)
        
    extract_dir = f"doc_{doc_id}"
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    # Find .xbrl file
    xbrl_file = None
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(".xbrl") and "Cc" not in file:
                if "PublicDoc" in root:
                    xbrl_file = os.path.join(root, file)
                    break
        if xbrl_file: 
            break
            
    if not xbrl_file:
         return {"error": "XBRL file not found in archive"}

    # Parse using BeautifulSoup
    try:
        import re
        with open(xbrl_file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "lxml-xml") 
            
        def get_val_by_tag(local_names, soup):
            candidates = []
            for name in local_names:
                pattern = re.compile(f".*:{name}$|^{name}$")
                found = soup.find_all(pattern)
                candidates.extend(found)
            
            if not candidates:
                return 0
                
            best_val = 0
            priority_score = -1
            
            for el in candidates:
                context_ref = el.get("contextRef", "")
                val_str = el.text.strip()
                if not val_str:
                    continue
                try:
                    val = float(val_str)
                except:
                    continue
                
                score = 0
                if "Prior" in context_ref:
                    score = 0
                elif "CurrentYearInstant" in context_ref or "CurrentQuarterInstant" in context_ref:
                    score = 3
                elif "CurrentYear" in context_ref or "CurrentQuarter" in context_ref:
                    score = 2
                else:
                    score = 1
                    
                if score > priority_score:
                    priority_score = score
                    best_val = int(val)
                    
            return best_val

        data = {}
        data["CompanyName"] = company_name
        data = {}
        data["CompanyName"] = company_name
        
        # Fetch Components
        ca = get_val_by_tag(["CurrentAssets", "AssetsCurrent"], soup)
        nca = get_val_by_tag(["NonCurrentAssets", "AssetsNonCurrent"], soup)
        cl = get_val_by_tag(["CurrentLiabilities", "LiabilitiesCurrent"], soup)
        ncl = get_val_by_tag(["NonCurrentLiabilities", "LiabilitiesNonCurrent"], soup)
        na = get_val_by_tag(["NetAssets", "Equity"], soup)
        
        # Fetch Totals for Validation
        total_assets = get_val_by_tag(["Assets"], soup)
        total_liabilities = get_val_by_tag(["Liabilities"], soup)
        
        # Logic to ensure balance and fill gaps
        # 1. Trust Total Assets if available
        if total_assets == 0:
            total_assets = ca + nca
        
        # 2. Check Assets breakdown
        # If Current + NonCurrent < Total, the diff is "Deferred" or "Other"
        # We will add it to NonCurrent for simplicity or return as separate?
        # Let's adjust NonCurrent to absorb small diffs or missing parts? 
        # Actually, creating a robust "Other" category is better but might break UI.
        # Let's force consistency:
        if ca + nca < total_assets:
            # Assume remainder is other/non-current
            nca = total_assets - ca
            
        # 3. Handle Liabilities and Net Assets
        # Ideally: Total Assets = Total Liabilities + Net Assets
        # If Total Liabilities is missing, infer it?
        if total_liabilities == 0 and na > 0:
             total_liabilities = total_assets - na
        
        # If Net Assets is missing, infer it?
        if na == 0 and total_liabilities > 0:
            na = total_assets - total_liabilities

        # Check Liabilities breakdown
        if cl + ncl < total_liabilities:
             # Add to NonCurrent Liab
             ncl = total_liabilities - cl
             
        # Final Force Balance (BS must balance!)
        # We trust Assets side.
        limit_diff = total_assets - (cl + ncl + na)
        if abs(limit_diff) > 0:
            # If discrepancy exists, adjust Net Assets (common plug)
            na += limit_diff

        data["CurrentAssets"] = ca
        data["NonCurrentAssets"] = nca
        data["CurrentLiabilities"] = cl
        data["NonCurrentLiabilities"] = ncl
        data["NetAssets"] = na
        data["TotalAssets"] = total_assets # Informational
        
        return data
        
    except Exception as e:
        return {"error": "Parsing Failed", "details": str(e)}
    
    # Cleanup
    # shutil.rmtree(extract_dir) # Maybe later
    # os.remove(zip_path)

if __name__ == "__main__":
    # Test
    print(fetch_financial_data(7203))
