import sqlite3
import logging
import joroxbrl.secFiles
import joroxbrl.metrics
import datetime

_db_file = 'xbrl1.db'

qInsert = '''insert into data_10k (
            cik, ticker, accessionNumber, filing_url, filing_date, end_period_date, 
            Revenues, OperatingIncome, NetIncome, Taxes, Interest, EBIT, Assets, 
            Liabilities, CurrentLiabilities, AFCF, cwc, ROE, ROA, ROCE, 
            OperatingMargin, InterestCoverageRatio, PriceToAFCF, 
            DebtToEquity, market_cap, market_cap_date, create_timestamp) values  
            ( ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            '''

qSelectPending = '''select pd.cik, pd.accessionNumber, pd.ticker  
                    from pending_data pd left join data_10k dk
                    on pd.accessionNumber = dk.accessionNumber 
                    where 
                    pd.filingDate>DATE('now', '-2 years', '-9 days')
                    and dk.accessionNumber is NULL
                    and pd.cik not in (select cik from company_details where exclude=1)
                    order by pd.filingDate'''
            
logging.basicConfig(filename='RetrievePendingFilingData.log', encoding='utf-8', level=logging.INFO) 

conn = sqlite3.connect(_db_file)
c = conn.cursor()

c.execute(qSelectPending)
res = c.fetchall()
print('Total: '+str(len(res)))
for r in res:
    try:
        print('Accessing '+str(r))
        ticker = r[2]
        f = joroxbrl.secFiles.Filing.getFilingByAccession(r[0], r[1])
        print(f.getFilingUrl())
        
        xbrl = f.getFilingUrls().getXbrl()
        DocumentPeriodEndDate = xbrl.getFact('{'+xbrl.namespaces['dei']+'}DocumentPeriodEndDate').value
        dFiling = datetime.datetime.strptime(f.filingDate, '%Y-%m-%d')
        dFiling10 = dFiling + datetime.timedelta(days=10)
        strDFiling10 = dFiling10.strftime('%Y-%m-%d')
        print('filingDate: {}; filingDate+10: {}'.format(f.filingDate, strDFiling10))
        
        
        if not f.checkDataFiles():
            logging.warning('Problem getting data files for '+f.accessionNumber)
        else:
            m = joroxbrl.metrics.MetricCalculator()
            m.genMetrics(f, date=strDFiling10)
            
            for i in m.concepts.items():
                print(i[0]+':\t'+str(i[1]))
            for i in m.metrics.items():
                print(i[0]+':\t'+str(i[1]))
            con = m.concepts
            met = m.metrics
        
            print('filingDate: {}; filingDate+10: {}'.format(f.filingDate, strDFiling10))
            
            print(DocumentPeriodEndDate)
            c.execute(qInsert, 
                      (f.cik, ticker, f.accessionNumber, f.getFilingUrl(), f.filingDate,
                        DocumentPeriodEndDate, con['Revenues'], con['OperatingIncome'],
                        con['NetIncome'], con['Taxes'], con['Interest'], con['EBIT'], 
                        con['Assets'], con['Liabilities'], con['CurrentLiabilities'], 
                        con['AFCF'], con['cwc'], met['ROE'], met['ROA'], met['ROCE'],
                        met['OperatingMargin'], met['InterestCoverageRatio'],
                        met['PriceToAFCF'], met['DebtToEquity'], 
                        con['MarketCap'], strDFiling10, 
                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')) )
            conn.commit()
    except KeyboardInterrupt: # We want to be able to manually stop the execution
        break
    except Exception:
        continue
      
c.close()
conn.close()