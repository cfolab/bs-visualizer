import requests
import pandas as pd
import datetime
import os
import io
import zipfile
from edinet_xbrl.edinet_xbrl_parser import EdinetXbrlParser

# Constants
EDINET_API_KEY = "c4ce27d66c84409d868224b250accfd5"
EDINET_CODE_LIST_URL = "https://disclosure.edinet-fsa.go.jp/E01EW/BL/Config/EdinetcodeDlInfo.csv"
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
        res = requests.get(EDINET_CODE_LIST_URL)
        if res.status_code == 200:
            # EDINET CSV is usually CP932
            content = res.content
            with open(cache_path, "wb") as f:
                f.write(content)
            df = pd.read_csv(io.BytesIO(content), encoding="cp932", skiprows=1)
            return df
    except Exception as e:
        print(f"Error downloading code list: {e}")
        return None
    return None

def get_edinet_code(ticker, code_list_df):
    """
    Finds EdinetCode for a given ticker (e.g. '7203').
    Note: Ticker in CSV is usually '72030' (5 digits).
    """
    if code_list_df is None:
        return None
    
    # Try 4 digit match
    # '証券コード' column usually contains something like '72030'
    # Let's search for exact partial match or formatted
    
    # Ensure ticker is string
    ticker = str(ticker)
    
    # Try to find where '証券コード' starts with ticker
    # Filter where '証券コード' divides by 10 is the ticker? 
    # Or just string match.
    
    if len(ticker) == 4:
        ticker5 = ticker + "0"
    else:
        ticker5 = ticker

    # Column names in EdinetCodeDlInfo.csv (approximate):
    # [EdinetCode, SubmitType, SecCode, JCN, OrgName, ...]
    # '証券コード' is usually index 2?
    
    # Let's assume standard columns. 
    # We will look for a row where '証券コード' == ticker5
    
    # Check columns
    # Actually, let's just loop or use pandas string search
    
    # Normalize column names if possible or guess
    cols = code_list_df.columns
    sec_code_col = [c for c in cols if "証券コード" in c]
    edinet_code_col = [c for c in cols if "ＥＤＩＮＥＴコード" in c or "EdinetCode" in c]
    
    if not sec_code_col or not edinet_code_col:
        return None
        
    sec_col = sec_code_col[0]
    edinet_col = edinet_code_col[0]
    
    # Search
    # The csv might have non-listed companies without sec code.
    
    target = code_list_df[code_list_df[sec_col].astype(str).str.startswith(ticker, na=False)]
    if not target.empty:
        return target.iloc[0][edinet_col]
        
    return None

def search_latest_yuho(edinet_code):
    """
    Searches for the latest Annual Securities Report (Yuho) in the last 90 days.
    Returns docID if found.
    """
    # 030000 is Yuho (Annual Report)
    
    today = datetime.date.today()
    # Check last 90 days
    # To speed up, we could use threads, but let's do sequential for safety first, or jump by weeks? No.
    # Actually, we can check specific dates? No.
    # Let's check the last 3 months (90 days). 
    # 90 requests is a lot.
    # Maybe limit to 30 days for demo purpose?
    # Or start with a wide scan? 
    # Let's try 60 days.
    
    for i in range(60): 
        date = today - datetime.timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        
        params = {
            "date": date_str,
            "type": 2,
            "Subscription-Key": EDINET_API_KEY
        }
        
        try:
            res = requests.get(API_ENDPOINT_DOCS, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                results = data.get("results", [])
                if not results:
                    continue
                
                # Filter for this proper company and doc type
                for item in results:
                    if item.get("edinetCode") == edinet_code:
                        # Check docTypeCode
                        # Yuho is 120? Form code 030000? 
                        # 'docTypeCode' 120 is 'Annual Securities Report' (Yuho)
                        # Let's check 'docDescription' too
                        if item.get("docTypeCode") == "120":
                            return item.get("docID")
        except:
            continue
            
    return None

def fetch_financial_data(ticker_code):
    """
    Main function to get BS data.
    """
    # 1. Get Code List
    df_code = get_edinet_code_list()
    if df_code is None:
        return {"error": "Failed to load EDINET Code List"}
        
    # 2. Get Edinet Code
    edinet_code = get_edinet_code(ticker_code, df_code)
    if not edinet_code:
        return {"error": f"Ticker {ticker_code} not found or no EDINET Code"}
        
    # 3. Search Document
    doc_id = search_latest_yuho(edinet_code)
    if not doc_id:
        return {"error": "No recent Annual Securities Report found in the last 60 days"}
        
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
    # We need to extract the xbrl file.
    # edinet-xbrl library needs a path or file-like?
    # Parser.parse(file_path)
    
    # Save zip temporarily
    zip_path = f"doc_{doc_id}.zip"
    with open(zip_path, "wb") as f:
        f.write(res.content)
        
    extract_dir = f"doc_{doc_id}"
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    # Find .xbrl file in 'XBRL/PublicDoc' usually
    xbrl_file = None
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(".xbrl") and "Cc" not in file: # Avoid calculations?
                # Usually look for PublicDoc
                if "PublicDoc" in root:
                    xbrl_file = os.path.join(root, file)
                    break
        if xbrl_file: 
            break
            
    if not xbrl_file:
         return {"error": "XBRL file not found in archive"}

    # Parse
    parser = EdinetXbrlParser()
    parsed_xbrl = parser.parse(xbrl_file)
    
    # Extract Key BS Items
    # Context 'CurrentYearInstant' (usually)
    # Keys for Assets, Liabilities, NetAssets
    
    # Standard labels (approximate, context needs checking)
    # We'll use get_data_by_cxt_and_tag if possible or simple lookup
    
    # Simplification: Get value for 'jppfs_cor:Assets', etc.
    # Context ref is tricky. Usually 'CurrentYearInstant' or similar.
    # edinet-xbrl returns a list of objects?
    
    # Helper to find value
    def get_value(key):
        val = parsed_xbrl.get_data_by_tag(key)
        if val:
            # val is a list of tuples? or list of objects?
            # Library returns list of values found?
            # Let's inspect ONE value.
            # Ideally filter by context 'CurrentYearInstant'
            for v in val:
                context = v.get_context_ref()
                if "CurrentYearInstant" in context or "CurrentYearDuration" not in context: # Primitive check
                     value = v.get_value()
                     if value:
                         return int(value)
        return 0

    # IFRS Tags
    ifrs_tags = {
        "CurrentAssets": ["jppfs_cor:CurrentAssets", "ifrs-full:AssetsCurrent"],
        "NonCurrentAssets": ["jppfs_cor:NonCurrentAssets", "ifrs-full:AssetsNonCurrent"],
        "CurrentLiabilities": ["jppfs_cor:CurrentLiabilities", "ifrs-full:LiabilitiesCurrent"],
        "NonCurrentLiabilities": ["jppfs_cor:NonCurrentLiabilities", "ifrs-full:LiabilitiesNonCurrent"],
        "NetAssets": ["jppfs_cor:NetAssets", "ifrs-full:Equity"],
    }

    def get_value_multitags(key_list):
        for key in key_list:
            v = get_value(key)
            if v and v > 0:
                return v
        return 0

    data = {
        "CurrentAssets": get_value_multitags(ifrs_tags["CurrentAssets"]),
        "NonCurrentAssets": get_value_multitags(ifrs_tags["NonCurrentAssets"]),
        "CurrentLiabilities": get_value_multitags(ifrs_tags["CurrentLiabilities"]),
        "NonCurrentLiabilities": get_value_multitags(ifrs_tags["NonCurrentLiabilities"]),
        "NetAssets": get_value_multitags(ifrs_tags["NetAssets"]),
    }
    
    # Cleanup
    # shutil.rmtree(extract_dir) # Maybe later
    # os.remove(zip_path)

    return data

if __name__ == "__main__":
    # Test
    print(fetch_financial_data(7203))
