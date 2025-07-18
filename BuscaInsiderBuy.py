from bs4 import BeautifulSoup
import datetime
import re
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import csv
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv
import os
import joroxbrl.secGov
import joroxbrl.secFiles
import joroxbrl.metrics
import logging

load_dotenv()

dataFolder = os.getenv('DATA_DIR')
base_url = 'https://www.sec.gov'
re_xmlForm4 = re.compile('.*xml')
SEC_USER_AGENT = os.getenv('SEC_USER_AGENT')

def parseFiling(url):
    try:
        page_content = joroxbrl.secGov.SecGovCaller.callSecGovUrl(base_url + url).text 
        soup = BeautifulSoup(page_content, features='html.parser')
        tbl = soup.find('table', class_='tableFile') 
        for tr in tbl.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds)<5: continue
            if re_xmlForm4.match(tds[2].string):
                form4url = tds[2].find('a')['href']
                return form4url
    except:
        print('In parseFiling: we are having trouble parsing '+url)
        return None
        
class TransactionList:
    
    def __init__(self):
        self.df = pd.DataFrame(columns=['reportingOwner', 'issuer', 'securityTitle', 'trxDate', 'trxAcquiredDisposed', 'shares', 'price', 'sharesAfterTrx', 'reportingOwnerRelationship', 'trxCode'])
        
    def addTrx(self, xmlUrl, reportingOwner, issuer, securityTitle, trxDate, transactionAcquiredDisposedCode, shares, price, sharesAfterTrx, reportingOwnerRelationship, transactionCode, ticker, cik):
        if price!='0' and price!='0.00' and price!='0.0' and price!='0.0000': # Discard it if the price is zero
            dfCheck = self.df.loc[(self.df['reportingOwner']==reportingOwner) & (self.df['issuer']==issuer) & (self.df['securityTitle']==securityTitle) & 
                   (self.df['trxDate']==trxDate) & (self.df['trxAcquiredDisposed']==transactionAcquiredDisposedCode) & 
                   (self.df['shares']==shares) & (self.df['price']==price)  & (self.df['sharesAfterTrx']==sharesAfterTrx)]
            if dfCheck.empty: # Discard it if it's duplicated
                new_row = pd.DataFrame([{
                    'xmlUrl': xmlUrl,
                    'reportingOwner': reportingOwner,
                    'issuer': issuer,
                    'securityTitle': securityTitle,
                    'trxDate': trxDate,
                    'trxAcquiredDisposed': transactionAcquiredDisposedCode,
                    'shares': shares,
                    'price': price,
                    'sharesAfterTrx': sharesAfterTrx,
                    'reportingOwnerRelationship': reportingOwnerRelationship,
                    'trxCode': transactionCode,
                    'ticker': ticker,
                    'cik': cik
                }])

                self.df = pd.concat([self.df, new_row], ignore_index=True)

    # This method should be called at the end, when we already have all transactions.
    # Eliminate entries for issuers that only have Ds (sells)
    # We'll also calculate some additional columns
    def complete(self): 
        sign = np.where(self.df['trxAcquiredDisposed']=='D', -1, 1)
        self.df['sharesConSigno'] = self.df['shares'].astype(float) * sign
        self.df['totalAmount'] = self.df['shares'].astype(float) * self.df['price'].astype(float)
        self.df['totalConSigno'] = self.df['totalAmount'].astype(float) * sign

        # Eliminamos las que no tienen mas compras (en numero de acciones) que ventas
        sums = self.df.groupby('issuer').sum(numeric_only=True)
        self.df = self.df[self.df['issuer'].isin(sums.loc[sums['sharesConSigno']>0].index)]

        # Ahora vamos a marcar los que parezca que han comprado a precios no de mercado
        issuers_wAD = self.df[self.df['trxAcquiredDisposed']=='D'].issuer.unique()
        sums0 = self.df[self.df['issuer'].isin( issuers_wAD )]
        sums = sums0.groupby(['issuer', 'trxAcquiredDisposed']).sum()
        sums['precioMedio'] = sums['totalConSigno'] / sums['sharesConSigno']
        
        self.df['comment'] = None
        
        for iss in issuers_wAD:
            if sums.loc[iss, 'A']['precioMedio']*1.5 <  sums.loc[iss, 'D']['precioMedio']:
                self.df.loc[self.df['issuer']==iss, 'comment'] = 'Parece que las compras no han sido a precio de mercado'

        # Siguiente, queremos descartar todos los que solo tienen A en el trxCode (awards) y no tengan ya un comentario
        issuers_A = self.df[(self.df['trxCode']=='A') & (self.df['comment'].isna()) ].issuer.unique()
        for i in issuers_A:
            if self.df[(self.df['issuer']==i) & (self.df['trxCode']!='A')].shape[0]==0: # Si todos tienen A
                self.df.loc[self.df['issuer']==i, 'comment'] = 'Awards'

        self.df.sort_values(by='issuer', inplace=True)
        
        # Terminamos aplicando el archivo de filtros
        filters = pd.read_csv(dataFolder+'filters.csv')
        issuers_rest = self.df[self.df['comment'].isna()].ticker.unique()
        for i in issuers_rest:
            f = filters[filters['ticker'].str.casefold()==i.casefold()]
            if f.shape[0]>0:
                f0 = f.iloc[0]
                datepart = ' ('+str(f0['date'])+')' if f0['date']==f0['date'] else '' # Si una variable no es igual a si misma, tiene que ser NaN
                self.df.loc[self.df['ticker']==i, 'comment'] = f0['opinion']+': '+f0['reason']+datepart

        # Add metrics to entries without comments
        
        # Create empty columns for metrics, so that if none apply it nothing breaks
        self.df['AFCF'] = np.nan
        self.df['PriceToAFCF'] = np.nan

        unique_ciks = self.df.loc[self.df['comment'].isna(), 'cik'].unique()
        for cik in [str(c) for c in unique_ciks]:
            try:
                filing = joroxbrl.secFiles.Filing.getLatestFiling(cik, '10-K')
                m = joroxbrl.metrics.MetricCalculator()
                m.genMetrics(filing)
                # Add AFCF and PriceToAFCF to the DataFrame for the current cik
                self.df.loc[self.df['cik'] == cik, 'AFCF'] = m.concepts.get('AFCF')
                self.df.loc[self.df['cik'] == cik, 'PriceToAFCF'] = m.metrics.get('PriceToAFCF')
            except Exception as e:
                logging.warning(f"Error getting metrics for CIK {cik}: {e}")
        
def parseForm4Xml(xmlUrl, n=0):
    try:
        xml = joroxbrl.secGov.SecGovCaller.callSecGovUrl(base_url + xmlUrl).text 
    except:
        if n<3: return parseForm4Xml(xmlUrl, n+1)
        else: raise Exception('Exception in parseForm4Xml calling '+xmlUrl)
        
    root =  ET.fromstring(xml)
    try:
        reportingOwner = root.find('./reportingOwner/reportingOwnerId/rptOwnerName').text.strip()
    except:
        print('No podemos encontrar reportingOwner en '+xmlUrl)
        return None
    reportingOwnerRelationship = ''
    isDirector = root.find('./reportingOwner/reportingOwnerRelationship/isDirector')
    isOfficer = root.find('./reportingOwner/reportingOwnerRelationship/isOfficer')
    isTenPercentOwner = root.find('./reportingOwner/reportingOwnerRelationship/isTenPercentOwner')
    isOther = root.find('./reportingOwner/reportingOwnerRelationship/isOther')
    if isDirector is not None and (isDirector.text.strip()=='1' or isDirector.text.strip().lower()=='true'): reportingOwnerRelationship = 'Director'
    if isOfficer is not None and (isOfficer.text.strip()=='1' or isOfficer.text.strip().lower()=='true'): 
        if reportingOwnerRelationship != '': reportingOwnerRelationship += ' - '
        reportingOwnerRelationship += 'Officer'
        title = root.find('./reportingOwner/reportingOwnerRelationship/officerTitle').text.strip()
        reportingOwnerRelationship = reportingOwnerRelationship + '(' + title + ')'
    if isTenPercentOwner is not None and (isTenPercentOwner.text.strip()=='1' or isTenPercentOwner.text.strip().lower()=='true'): 
        if reportingOwnerRelationship != '': reportingOwnerRelationship += ' - '
        reportingOwnerRelationship += '10% Owner'
    if isOther is not None and (isOther.text.strip()=='1' or isOther.text.strip().lower()=='true'): 
        if reportingOwnerRelationship != '': reportingOwnerRelationship += ' - '
        reportingOwnerRelationship += 'Other'
        otherText = root.find('./reportingOwner/reportingOwnerRelationship/otherText').text.strip()
        reportingOwnerRelationship = reportingOwnerRelationship + '(' + otherText + ')'
    
    issuer = root.find('./issuer/issuerName').text.strip()
    ticker = root.find('./issuer/issuerTradingSymbol').text.strip()
    cik = root.find('./issuer/issuerCik').text.strip()
    
    transactions = []
    for trx in root.findall('./nonDerivativeTable/nonDerivativeTransaction'):
        try:
            trxDate = trx.find('./transactionDate/value')
            if trxDate is not None: trxDate = trxDate.text.strip()
            else: trxDate = '9999-12-31'
    
            securityTitle = trx.find('./securityTitle/value')
            if securityTitle is not None: securityTitle = securityTitle.text.strip()
            else: securityTitle = ''
            
            transactionAcquiredDisposedCode = trx.find('./transactionAmounts/transactionAcquiredDisposedCode/value')
            if transactionAcquiredDisposedCode is not None: transactionAcquiredDisposedCode = transactionAcquiredDisposedCode.text.strip()
            else: transactionAcquiredDisposedCode = ''
            
            shares = trx.find('./transactionAmounts/transactionShares/value')
            if shares is not None: shares = shares.text.strip()
            else: shares = -1
            
            price = trx.find('./transactionAmounts/transactionPricePerShare/value')
            if price is not None: price = price.text.strip()
            else: 
                print(f'Precio de {issuer} esta vacio')
                continue # Los precios vacios no nos interesan para nada
    
            sharesAfterTrx = trx.find('./postTransactionAmounts/sharesOwnedFollowingTransaction/value')
            if sharesAfterTrx is not None: sharesAfterTrx = sharesAfterTrx.text.strip()
            else: sharesAfterTrx = -1
            
            transactionCode = trx.find('./transactionCoding/transactionCode')
            if transactionCode is not None: transactionCode = transactionCode.text.strip()
            else: transactionCode = ''
            
            transactions.append([xmlUrl, reportingOwner, issuer, securityTitle, trxDate, transactionAcquiredDisposedCode, shares, price, sharesAfterTrx, reportingOwnerRelationship, transactionCode, ticker, cik] )
        except:
            print("Excepcion")
            continue
    if len(transactions): return transactions
        

#base_url = 'https://www.sec.gov/cgi-bin/current?q2=0&q3=10&q1='
searchRecentUrl = base_url + '/cgi-bin/current?q2=0&q3=4&q1='
re_linea = re.compile(r'(\d\d-\d\d-\d\d\d\d)\s+<a href="(.*?)">(.*?)</a>\s*<a href="(.*?)">(.*?)</a>\s*(.*)')

transactions = TransactionList()
for i in range(1):
    print(f"Vamos a buscar en {searchRecentUrl+str(i)}")
    page_content = joroxbrl.secGov.SecGovCaller.callSecGovUrl(searchRecentUrl+str(i)).text 
    soup = BeautifulSoup(page_content, features='html.parser')
    chorizo = str(soup.find('pre'))
    for line in re.split('<hr/>', chorizo)[1].splitlines():
        grupetos = re_linea.match(line).groups()
        if grupetos[2]=='4': 
            xmlUrl = parseFiling(grupetos[1])
            if xmlUrl is not None: 
                newTrx = parseForm4Xml(xmlUrl)
                if newTrx: 
                    for t in newTrx: transactions.addTrx(*t)
   
# Y ahora lo que falta por hacer es sacar transactions como csv
    # df = pd.DataFrame(transactions)
    # df.columns =['reportingOwner', 'issuer', 'securityTitle', 'trxDate', 'transactionAcquiredDisposed', 'shares', 'price']
transactions.complete()


transactions.df.to_csv(dataFolder+'InsiderTrades_'+str(transactions.df['trxDate'].max())[0:10]+'.csv', index=False, quoting=csv.QUOTE_NONNUMERIC)
print(dataFolder+'InsiderTrades_'+str(transactions.df['trxDate'].max())[0:10]+'.csv')
# Lo que se genera es un poco excesivo. Lo que podemos hacer:
    # Tirar directamente todas las entradas donde el precio es 0
    # A las Ds, ponerles el precio negativo.
    # Guardar hashes por empresa:
        # La empresa donde todo sean Ds, tirarla entera
        # Eliminar entradas que tengan todos los parámetros idénticos

# Generate new_filters DataFrame
today = datetime.date.today().strftime('%Y-%m-%d')
new_filters = transactions.df[transactions.df['PriceToAFCF'].notna()][['issuer', 'ticker', 'PriceToAFCF']].drop_duplicates()
new_filters['opinion'] = new_filters['PriceToAFCF'].apply(lambda x: 'BEAR' if x <= 0 or x > 15 else ('MID' if 10 <= x <= 15 else 'BULL'))
new_filters['RoundPriceToAFCF'] = new_filters['PriceToAFCF'].round().astype(int)
new_filters['reason'] = new_filters['RoundPriceToAFCF'].apply(lambda x: 'No es rentable' if x <= 0 else 'P/AFCF~=' + str(x))
new_filters['date'] = today
new_filters = new_filters.rename(columns={'issuer': 'company'})
new_filters = new_filters.drop(columns=['PriceToAFCF', 'RoundPriceToAFCF'])

# Write new_filters to CSV
new_filters.to_csv(dataFolder+'new_filters.csv', index=False, quoting=csv.QUOTE_NONNUMERIC)
print(dataFolder+'new_filters.csv')
