A number of scripts in Python related to investments.
joroxblr is a pseudo-library used by some of these scripts, that parses XBRL (and partially iXBRL) and calculates values for 10-Ks and 10-Qs.
Many of them mix English and Spanish in a bad way, sorry.

# Local SEC files
A number of scripts will need some local SEC files to be downloaded.
The local SEC files are expected to be found in the "secInfo" directory, and can be downloaded from:
- https://www.sec.gov/file/company-tickers (company-tickers.json should be placed in "secInfo").
- https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip (contents should be placed in "secInfo/companyfacts").
- https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip (contents should be placed in "secInfo/submissions").

# SQLite data model
createDatabase.sql includes creation scripts for the (sqlite) data model that some scripts and parts of joroxbrl will use.
The scripts that use it will expect to find a "xbrl1.db" file with the SQLite database.

## XBRL storage data model
Tables xbrl_period_instant, xbrl_fact, xbrl_company, xbrl_document and xbrl_dimension.
This is designed with the idea of parsing XBRLs and keeping a DB storage of all the details of this. It works, but stopped working on it, because it ended up not making much sense to continue down this path.

## Report concepts data model
Tables data_10k, pending_data, company_details and sic_codes
The idea is to store only a few concepts for each 10-K, which can later be user to identify trends, train models, etc.

## Valuations

# Python scripts

## BuscaInsiderBuy.py
Looks in sec.gov for Form 10s (insider transactions), and generates a csv with detailed information. 
It was written with the purpose of using insider buys as a market signal, so sells are discarded in some cases.

## BuscaSpinoffs.py
Look for spinoffs presented at sec.gov. It's an old script that uses selenium, and should be rewritten to use requests.

## CompanyNewSubmissions.py
Find submissions in sec.gov for a list of companies in recent days. 
Will look for a file 'following.csv' with a column 'CIK' to identify the companies to follow.

## ExtractLisFilings.py
Go through all 10K entries in the local sec files, ang generate one entry for each (those which are XBRL) in the pending_data table.
The entries in pending_data are meant to be used by RetrievePendingFilingData.py to then populate data_10k.

## FromSecTest.py
Generate the metrics for the last 10-K of a single company. Useful for debugging problems extracting a single filing.

## FromSecTestHistory.py
Generate the metrics for a specific 10-K of a single company. Useful for debugging problems extracting a single filing.

## GenerateDataSet.py
Retrieves information from table data_10k, and uses it to train an NN model using pytorch.
Needs a lot more work. It technically works, but the predictions it generates are not worth much.

## RetrievePendingFilingData.py
To be executed after ExtractLisFilings.py. Populates the data_10k table based on the entries in pending_data.

## StoreCompanyDetails.py
Populates company_details for entries in pending_data. Uses local SEC files.

# joroxbrl library
Used by many of the scripts to parse XBRL and extract financial concepts from them.
joroxbrl.metrics.py uses polygon API (https://polygon.io) to retrieve market cap information. You need to obtain a polygon API key (free) and edit the file to put your key in the _PolygonKey variable.

 
