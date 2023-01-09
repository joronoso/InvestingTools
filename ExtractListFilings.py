# Go through all 10K entries in the local sec files, ang generate one entry for each
#  (those which are XBRL) in the pending_data table
import json
import joroxbrl.secFiles
import sqlite3
import logging

_db_file = 'xbrl1.db'
ctickers = 'secInfo/company_tickers.json'
insertQuery = 'insert into pending_data values (?,?,?,?,?,?)'

logging.basicConfig(filename='ExtractListFilings.log', encoding='utf-8', level=logging.DEBUG)  

with open(ctickers) as jFile:
    jSubms = json.load(jFile)

conn = sqlite3.connect(_db_file)
c = conn.cursor()
i=0
for k in list(jSubms.values()):
    lis = joroxbrl.secFiles.Filing.getListFilings(str(k['cik_str']), ['10-K'], isXBRL=True)
    for j in lis:
        try:
            c.execute(insertQuery, (j.cik, k['ticker'], j.accessionNumber, j.filingDate, j.reportDate, j.getFilingUrl()))
        except sqlite3.IntegrityError:
            logging.warning('Integrity error: '+'{0} - {1} - {2} - {3} - {4} - {5}'.format(j.cik, k['ticker'], j.accessionNumber, j.filingDate, j.reportDate, j.getFilingUrl()))
    conn.commit()
    
c.close()
conn.close()