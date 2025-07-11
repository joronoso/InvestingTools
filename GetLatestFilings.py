import joroxbrl.secGov

companies = [
    {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "cik": "0000320193",
    }
]

base_url = 'https://data.sec.gov'

for company in companies:
    cik = company['cik']
    filing_url = f"{base_url}/submissions/CIK{cik}.json"
    
    print(f"Fetching filings for {company['name']} ({company['ticker']}) from {filing_url}")
    
    json = joroxbrl.secGov.SecGovCaller.callSecGovUrl(filing_url).text
    print(json)