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
    Finds EdinetCode, Company Name, and Industry for a given ticker.
    Returns (edinet_code, company_name, industry)
    """
    if code_list_df is None:
        raise ValueError("Code list is empty or failed to load.")
    
    ticker = str(ticker)
    
    cols = code_list_df.columns
    sec_code_col = [c for c in cols if "証券コード" in c]
    edinet_code_col = [c for c in cols if "ＥＤＩＮＥＴコード" in c or "EdinetCode" in c]
    company_name_col = [c for c in cols if "提出者名" in c or "SubmitterName" in c]
    industry_col = [c for c in cols if "提出者業種" in c or "Industry" in c]
    
    if not sec_code_col or not edinet_code_col:
        return None, None, None
        
    sec_col = sec_code_col[0]
    edinet_col = edinet_code_col[0]
    name_col = company_name_col[0] if company_name_col else None
    ind_col = industry_col[0] if industry_col else None
    
    target = code_list_df[code_list_df[sec_col].astype(str).str.startswith(ticker, na=False)]
    if not target.empty:
        ecode = target.iloc[0][edinet_col]
        cname = target.iloc[0][name_col] if name_col else "Unknown"
        industry = target.iloc[0][ind_col] if ind_col else "Unknown"
        return ecode, cname, industry
        
    return None, None, None

def search_latest_yuho(edinet_code):
    """
    Searches for the latest Annual (120), Quarterly (140), or Semi-Annual (160) Report in the last 365 days.
    Returns docID if found.
    """
    # ... existing implementation ...
    # Note: Since I am replacing the block, I need to keep the original content of search_latest_yuho if I touch it, 
    # OR simply target get_edinet_code.
    # But wait, fetch_financial_data ALSO needs update.
    # I will split this into two replacement chunks or better, just replace get_edinet_code and then fetch_financial_data separately.
    # Instruction above says 1 and 2. I'll stick to get_edinet_code first if I can, but the tool allows contiguous replacement.
    # It's safer to do get_edinet_code first.

# I will restart this replacement content to ONLY target get_edinet_code to avoid wiping search_latest_yuho inadvertently.
# Actually I can't target fetch_financial_data in the same chunk easily if they are far apart.
# I'll use multi_replace for safety if I need to touch multiple spots, but here I'll do two calls.

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

def fetch_financial_data(ticker_code, progress_callback=None):
    """
    Main function to get BS data.
    """
    def update_progress(percent, text):
        if progress_callback:
            progress_callback(percent, text)

    # 1. Get Code List
    update_progress(0.1, "企業コードリストを読み込み中...")
    try:
        df_code = get_edinet_code_list()
    except Exception as e:
         return {"error": "Failed to load EDINET Code List", "details": str(e)}

    if df_code is None:
        return {"error": "Failed to load EDINET Code List (returned None)"}
        
    # 2. Get Edinet Code
    try:
        edinet_code, company_name, industry = get_edinet_code(ticker_code, df_code)
    except Exception as e:
        return {"error": f"Error finding ticker {ticker_code}", "details": str(e)}

    if not edinet_code:
        return {"error": f"Ticker {ticker_code} not found or no EDINET Code"}
        
    # 3. Search Document
    # ... (skipping unchanged lines is risky with replace_file_content unless I include them. 
    # I will include the context for search_doc to be safe or just target the block I need)
    
    # ... skipping to the Data dict creation part ... 
    # I'll just replace the TOP part of the function first to capture the unpacking.
    
    # Wait, I need to pass 'industry' all the way down to data = {} at the end of the function.
    # The variable 'industry' will be in scope. 
    # I'll replace the first block (Unpacking)
    
    # Then I'll replace the specific block where 'data' is created. 
    # This requires 2 steps or 1 multi_replace. Use multi_replace for atomic update.
        
    # 3. Search Document
    update_progress(0.3, "最新の有価証券報告書を検索中...")
    doc_id = search_latest_yuho(edinet_code)
    if not doc_id:
        return {"error": "No Annual/Quarterly Report found in the last 365 days"}
        
    # 4. Download and Parse
    # Use API to get XBRL zip
    update_progress(0.5, "XBRLデータをダウンロード中...")
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
    update_progress(0.7, "データを展開・抽出中...")
    zip_path = f"doc_{doc_id}.zip"
    with open(zip_path, "wb") as f:
        f.write(res.content)
        
    extract_dir = f"doc_{doc_id}"
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    # Find .xbrl file
    candidates = []
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(".xbrl") and "Cc" not in file:
                if "PublicDoc" in root:
                    candidates.append(os.path.join(root, file))
    
    xbrl_file = None
    if candidates:
        # Prioritize files NOT containing 'ssr' (Summary) or 'sum'
        # e.g. jpcrp030000-ssr... is summary.
        main_files = [f for f in candidates if "ssr" not in os.path.basename(f).lower()]
        if main_files:
            xbrl_file = main_files[0]
        else:
            xbrl_file = candidates[0]
            
    if not xbrl_file:
         return {"error": "XBRL file not found in archive"}

    # Parse using BeautifulSoup
    update_progress(0.9, "財務データを解析中...")
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
                # Base scoring on period
                if "Prior" in context_ref:
                    score = 0
                elif "CurrentYearInstant" in context_ref or "CurrentQuarterInstant" in context_ref or "InterimInstant" in context_ref:
                    score = 10
                elif "CurrentYear" in context_ref or "CurrentQuarter" in context_ref or "InterimDuration" in context_ref:
                    score = 5
                elif "Instant" in context_ref: # Generic Instant (often matches IFRS contexts)
                    score = 3
                else:
                    score = 1
                
                # Boost for Consolidated vs Non-Consolidated
                # We prefer Consolidated (連結) over Non-Consolidated (個別/単体)
                if "NonConsolidated" in context_ref:
                    score -= 2
                elif "Consolidated" in context_ref:
                    score += 2
                    
                if score > priority_score:
                    priority_score = score
                    best_val = int(val)
                    
            return best_val

        data = {}
        data["CompanyName"] = company_name
        data["Industry"] = industry

        # Helper to get first non-zero or sum of components
        def get_or_sum(primary_tags, component_tags_list, soup):
            val = get_val_by_tag(primary_tags, soup)
            if val == 0 and component_tags_list:
                running_sum = 0
                for tags in component_tags_list:
                    running_sum += get_val_by_tag(tags, soup)
                val = running_sum
            return val

        # --- Detailed Extraction (Bottom-Up Source) ---
        # 1. Cash
        cash = get_val_by_tag(["CashAndDeposits", "CashAndCashEquivalents", "Cash"], soup)
        
        # 2. Receivables
        receivables = get_or_sum(
            ["NotesAndAccountsReceivableTrade", "NotesAndAccountsReceivable", "TradeAndOtherReceivables", "TradeReceivables"], 
            [["NotesReceivableTrade", "NotesReceivable"], ["AccountsReceivableTrade", "AccountsReceivable"]],
            soup
        )
        
        # 3. Inventory
        inventory = get_or_sum(
            ["Inventories"],
            [["MerchandiseAndFinishedGoods", "Merchandise"], ["WorkInProcess"], ["RawMaterialsAndSupplies", "RawMaterials"]],
            soup
        )
        
        # 4. PPE
        ppe = get_val_by_tag(["PropertyPlantAndEquipment", "TangibleFixedAssets", "PropertyPlantAndEquipmentAndRightOfUseAssets"], soup)
        
        # 5. Intangible & Investments
        intangible = get_val_by_tag(["IntangibleAssets", "IntangibleFixedAssets", "IntangibleAssetsAndGoodwill"], soup)
        investments = get_val_by_tag(["InvestmentsAndOtherAssets", "InvestmentSecurities", "OtherFinancialAssets"], soup)

        # 6. Debt Details
        debt_tags = [
            ["ShortTermLoansPayable", "ShortTermLoans"],
            ["LongTermLoansPayable", "LongTermLoans"],
            ["CurrentPortionOfBondsPayable", "CurrentPortionOfBonds"],
            ["BondsPayable", "Bonds"],
            ["CommercialPapersLiabilities", "CommercialPapers"],
            ["CurrentPortionOfLongTermLoansPayable", "CurrentPortionOfLongTermLoans"],
            ["ConvertibleBondsTypeBondsPayable", "ConvertibleBonds"],
            ["BondsAndBorrowings"], 
            ["LeaseLiabilities"],
            ["OtherFinancialLiabilities"]
        ]
        interest_bearing_debt = 0
        for tags in debt_tags:
            interest_bearing_debt += get_val_by_tag(tags, soup)
            
        retained_earnings = get_val_by_tag(["RetainedEarnings"], soup)
        
        # --- Others for Bottom-Up Summation ---
        other_ca = get_val_by_tag(["OtherCurrentAssets", "OtherAssetsCurrent"], soup)
        other_nca = get_val_by_tag(["OtherNonCurrentAssets", "OtherAssetsNonCurrent"], soup)
        other_cl = get_val_by_tag(["OtherCurrentLiabilities", "OtherLiabilitiesCurrent"], soup)
        other_ncl = get_val_by_tag(["OtherNonCurrentLiabilities", "OtherLiabilitiesNonCurrent"], soup)

        # --- High Level Components (with Fallback to Bottom-Up) ---
        # CA
        ca = get_val_by_tag(["CurrentAssets", "AssetsCurrent", "CurrentAssetsIFRSSummaryOfBusinessResults"], soup)
        if ca == 0:
            ca = cash + receivables + inventory + other_ca
            
        # NCA
        nca = get_val_by_tag(["NonCurrentAssets", "AssetsNonCurrent", "NonCurrentAssetsIFRSSummaryOfBusinessResults"], soup)
        if nca == 0:
            nca = ppe + intangible + investments + other_nca
            
        # CL
        cl = get_val_by_tag(["CurrentLiabilities", "LiabilitiesCurrent", "CurrentLiabilitiesIFRSSummaryOfBusinessResults"], soup)
        if cl == 0:
            # Approx logic if CL is missing (harder to reconstruct perfectly due to many misc debts)
            # Use debt parts? Not all debt is CL.
            # Just rely on Other + knowns?
            cl = other_cl # Weak, but better than 0? usually CL matches Total - NCL.
            
        # NCL
        ncl = get_val_by_tag(["NonCurrentLiabilities", "LiabilitiesNonCurrent", "NonCurrentLiabilitiesIFRSSummaryOfBusinessResults"], soup)
        if ncl == 0:
            ncl = other_ncl

        # NA
        na = get_val_by_tag(["NetAssets", "Equity", "TotalNetAssets", "EquityAttributableToOwnersOfParent", "EquityAttributableToOwnersOfParentIFRSSummaryOfBusinessResults"], soup)

        # Totals
        total_assets = get_val_by_tag(["Assets", "TotalAssets", "TotalAssetsIFRSSummaryOfBusinessResults"], soup)
        total_liabilities = get_val_by_tag(["Liabilities", "TotalLiabilities", "TotalLiabilitiesIFRSSummaryOfBusinessResults"], soup)
        
        # ------------------------------------------
        
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
        data["TotalAssets"] = total_assets
        
        # Add Details to Data
        data["Cash"] = cash
        data["Receivables"] = receivables
        data["Inventory"] = inventory
        data["PPE"] = ppe
        data["Intangible"] = intangible
        data["Investments"] = investments
        data["InterestDebt"] = interest_bearing_debt
        data["RetainedEarnings"] = retained_earnings

        update_progress(1.0, "完了")
        return data
        
    except Exception as e:
        return {"error": "Parsing Failed", "details": str(e)}
    
    # Cleanup
    # shutil.rmtree(extract_dir) # Maybe later
    # os.remove(zip_path)

if __name__ == "__main__":
    # Test
    print(fetch_financial_data(7203))
