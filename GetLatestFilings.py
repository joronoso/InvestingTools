import datetime
import json as jsonlib
import joroxbrl.secGov
import joroxbrl.secFiles
from jinja2 import Environment, FileSystemLoader

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

# How many days of filings to fetch
number_of_days = 30

companies = [
    {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "cik": "320193",
    },
    {
        "ticker": "CURV",
        "name": "Torrid Holdings Inc.",
        "cik": "1792781",
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
print(output)
