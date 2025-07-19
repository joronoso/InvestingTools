import datetime
import json as jsonlib
from jinja2 import Environment, FileSystemLoader
import os
import webbrowser
from dotenv import load_dotenv
load_dotenv()

import joroxbrl.secGov
import joroxbrl.secFiles

class GlobalFilingListAdder:

    # Create a new instance for each company. Assumes that filings are added in a reverse chronological order. 
    def __init__(self, company, global_filing_list):
        self.global_filing_list = global_filing_list
        self.company = company
        self.i = 0

    def add(self, filing):
        while self.i < len(self.global_filing_list) and self.global_filing_list[self.i]['filings'][0]['filingDate'] > filing['filingDate']:
            self.i += 1
        self.global_filing_list.insert(self.i, {
            'company': self.company,
            'filings': [filing]
        })

dataFolder = os.getenv('DATA_DIR')
# How many days of filings to fetch
number_of_days = 30

companies = [
    {
        "ticker": "RPAY",
        "name": "Repay Holdings Corp",
        "cik": "1720592",
    },
    {
        "ticker": "CURV",
        "name": "Torrid Holdings Inc.",
        "cik": "1792781",
    },
    {
        "ticker": "CODI",
        "name": "Compass Diversified Holdings",
        "cik": "1345126",
    },
    {
        "ticker": "GLNG",
        "name": "Golar LNG Ltd",
        "cik": "1207179",
    },
]

base_url = 'https://data.sec.gov'

# Data structures will be:
# - filing: is a dic, with the details of the filing
# - filing_list: is a dic, with a company (which itself is a dic), and the actual list of filings
# - company_filing_lists: is a list of filing_list entries, with all the filings for a given company.
# - global_filing_list: is a list of filing_list entries, ordered by date (most recent first). 
#   Each item will only contain one filing (the purpose is to have the company for each filing).
company_filing_lists = []
global_filing_list = []

for company in companies:
    cik = joroxbrl.secFiles.Filing.correctCIK(company['cik'])
    filing_url = f"{base_url}/submissions/CIK{cik}.json"
    
    # print(f"Fetching filings for {company['name']} ({company['ticker']}) from {filing_url}")
    
    json = joroxbrl.secGov.SecGovCaller.callSecGovUrl(filing_url).text
    #print(json)

    # Parse the JSON response
    data = jsonlib.loads(json)
    filings = data.get('filings', {}).get('recent', {})
    global_filing_list_adder = GlobalFilingListAdder(company, global_filing_list)

    current_company_filing_list = []
    for i in range(len(filings.get('accessionNumber', []))):
        days_since = (datetime.date.today() - datetime.datetime.strptime(filings['filingDate'][i], "%Y-%m-%d").date()).days
        if days_since > number_of_days:
            break

        filing = {
            'accessionNumber': filings['accessionNumber'][i],
            'filingDate': filings['filingDate'][i],
            'reportDate': filings['reportDate'][i],
            'acceptanceDateTime': filings['acceptanceDateTime'][i],
            'act': filings['act'][i],
            'form': filings['form'][i],
            'fileNumber': filings['fileNumber'][i],
            'filmNumber': filings['filmNumber'][i],
            'items': filings['items'][i],
            'core_type': filings['core_type'][i],
            'size': filings['size'][i],
            'isXBRL': filings['isXBRL'][i],
            'isInlineXBRL': filings['isInlineXBRL'][i],
            'primaryDocument': filings['primaryDocument'][i],
            'primaryDocDescription': filings['primaryDocDescription'][i],
        }
        
        # Add to the global filing list
        global_filing_list_adder.add(filing)
        
        # Add to the company filing list
        current_company_filing_list.append(filing)
    company_filing_lists.append({
        'company': company,
        'filings': current_company_filing_list
    })

env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('filings.html.jinja')
output = template.render(company_filing_lists = company_filing_lists, global_filing_list=global_filing_list)
output_filename = f"LatestFilings_{datetime.date.today().isoformat()}.html"
output_path = os.path.join(dataFolder, output_filename)
with open(output_path, "w", encoding="utf-8") as f:
    f.write(output)

webbrowser.open_new_tab(f"file://{output_path}")