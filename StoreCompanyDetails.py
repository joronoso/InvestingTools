import sqlite3
import json

_db_file = 'xbrl1.db'
_submissionsDir = 'secInfo/submissions/'

selectCiks = 'select distinct cik from pending_data'
insertData = '''insert into company_details 
                (cik, name, ticker, sic, sicDescription) values (?,?,?,?,?)'''

conn = sqlite3.connect(_db_file)
c = conn.cursor()
c.execute(selectCiks)
res = c.fetchall()
print('Total: '+str(len(res)))
for r in res:
    cik = r[0]
    with open(_submissionsDir+'CIK'+cik+'.json') as jFile:
        jSubms = json.load(jFile)
    
    try:
        tickers = ','.join(jSubms['tickers'])
    except TypeError:
        tickers = None
        
    c.execute(insertData, 
              (cik, jSubms['name'], tickers, jSubms['sic'], jSubms['sicDescription']))
    
    conn.commit()
    
c.close()
conn.close()