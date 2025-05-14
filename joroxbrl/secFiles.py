# This module retrieves information from downloaded json files from SEC (companyfacts and submissions)
import json
from joroxbrl.core import Fact
import joroxbrl.secGov
import logging
import requests
import sys
import os
companyfactsDir = None #'secInfo/companyfacts/' # If left empty, it will be retrieved from the SEC
submissionsDir = None #'secInfo/submissions/' # If left empty, it will be retrieved from the SEC
companyfactsUrl = 'https://data.sec.gov/api/xbrl/companyfacts/'
submissionsUrl = 'https://data.sec.gov/submissions/'
secDocAccessUrl = 'https://www.sec.gov/Archives/edgar/data/'

class Filing:
    """
    Attributes:
       cik
       accessionNumber
       filingDate
       reportDate
       acceptanceDateTime
       act
       form
       fileNumber
       filmNumber
       size
       isXBRL
       isInlineXBRL
       primaryDocument
       primaryDocDescription
       filingUrls: joroxbrl.secGov.FilingUrls object
    """
    _acceptableSubmissionTypes = [ '10-K', '10-Q' ]
    
    filingUrls = None

    @classmethod
    def correctCIK(cls, cik: str) -> str:
        if len(cik) < 10:
            cik = '0'*(10-len(cik)) + cik
        elif len(str(cik)) > 10:
            raise Exception('Invalid CIK: '+cik)
        return cik

    
    def __init__(self, cik, accessionNumber, filingDate, reportDate, 
                 acceptanceDateTime, act, form, fileNumber, filmNumber, items, 
                 size, isXBRL, isInlineXBRL, primaryDocument, primaryDocDescription):
        self.cik = self.correctCIK(cik)
        self.accessionNumber = accessionNumber
        self.filingDate = filingDate
        self.reportDate = reportDate
        self.acceptanceDateTime = acceptanceDateTime
        self.act = act
        self.form = form
        self.fileNumber = fileNumber
        self.filmNumber = filmNumber
        self.items = items
        self.size = size
        self.isXBRL = isXBRL
        self.isInlineXBRL = isInlineXBRL
        self.primaryDocument = primaryDocument
        self.primaryDocDescription = primaryDocDescription
    
    
    @classmethod
    def getLatestFiling(cls, cik: str, submissionType: str):
        return cls.getFilingByTypeAndDate(cik, submissionType, None)

    @classmethod
    def getSubmission(cls, cik: str):
        if submissionsDir:
            with open(submissionsDir+'CIK'+cik+'.json') as jFile:
                jSubm = json.load(jFile)
        else:
            # We are going to download the submissions
            url = submissionsUrl+'CIK'+cik+'.json'
            try:
                resp = requests.get(url, headers={
                    "User-agent": os.getenv('SEC_USER_AGENT'),
                    "Accept-Encoding": "gzip, deflate",
                    "Host": "data.sec.gov",
                },)
                if resp.status_code == 200:
                    jSubm = resp.json()
                else:
                    logging.error('joroxbrl.secFiles.Filing.getSubmission: Could not download company submissions file from '+url)
                    logging.debug(resp)
                    jSubm = None
            except Exception as e:
                logging.error(e+'\njoroxbrl.secFiles.Filing.getSubmission: Could not download company submissions file for '+cik)
                jSubm = None
        return jSubm

    @classmethod
    def getFilingByTypeAndDate(cls, cik:str, submissionType: str, reportDate: str):
        if submissionType not in cls._acceptableSubmissionTypes:
            print(submissionType+' is not an acceptable submission type')
            return None
        cik = cls.correctCIK(cik)
        jSubms = cls.getSubmission(cik)

        # Assume the submissions appear in inverse chronological order
        found = False
        for idx, x in enumerate(jSubms['filings']['recent']['form']):
            if (x == submissionType and 
                (reportDate is None or jSubms['filings']['recent']['reportDate'][idx]==reportDate)):
                found = True
                break
        if not found:
            exceptionMessage  = 'Could not find '+submissionType+' for '+cik
            if reportDate is not None:
                exceptionMessage = exceptionMessage + ' and ' + reportDate
            raise Exception(exceptionMessage)
        
        return cls(cik,
            jSubms['filings']['recent']['accessionNumber'][idx],
            jSubms['filings']['recent']['filingDate'][idx],
            jSubms['filings']['recent']['reportDate'][idx],
            jSubms['filings']['recent']['acceptanceDateTime'][idx],
            jSubms['filings']['recent']['act'][idx],
            jSubms['filings']['recent']['form'][idx],
            jSubms['filings']['recent']['fileNumber'][idx],
            jSubms['filings']['recent']['filmNumber'][idx],
            jSubms['filings']['recent']['items'][idx],
            jSubms['filings']['recent']['size'][idx],
            jSubms['filings']['recent']['isXBRL'][idx],
            jSubms['filings']['recent']['isInlineXBRL'][idx],
            jSubms['filings']['recent']['primaryDocument'][idx],
            jSubms['filings']['recent']['primaryDocDescription'][idx])
        
    @classmethod
    # isXBRL: If TRUE, 
    def getListFilings(cls, cik:str, submissionTypes:list[str], isXBRL:bool=False):
        listFilings = []
        cik = cls.correctCIK(cik)
        jSubms = cls.getSubmission(cik)

        for idx, x in enumerate(jSubms['filings']['recent']['form']):
            # print(idx, x, x in submissionTypes, jSubms['filings']['recent']['isXBRL'][idx])
            if (x in submissionTypes and 
                (isXBRL is None 
                 or (isXBRL and jSubms['filings']['recent']['isXBRL'][idx]==1)
                 or (not isXBRL and jSubms['filings']['recent']['isXBRL'][idx]==0))):
                listFilings.append (
                    cls(cik,
                        jSubms['filings']['recent']['accessionNumber'][idx],
                        jSubms['filings']['recent']['filingDate'][idx],
                        jSubms['filings']['recent']['reportDate'][idx],
                        jSubms['filings']['recent']['acceptanceDateTime'][idx],
                        jSubms['filings']['recent']['act'][idx],
                        jSubms['filings']['recent']['form'][idx],
                        jSubms['filings']['recent']['fileNumber'][idx],
                        jSubms['filings']['recent']['filmNumber'][idx],
                        jSubms['filings']['recent']['items'][idx],
                        jSubms['filings']['recent']['size'][idx],
                        jSubms['filings']['recent']['isXBRL'][idx],
                        jSubms['filings']['recent']['isInlineXBRL'][idx],
                        jSubms['filings']['recent']['primaryDocument'][idx],
                        jSubms['filings']['recent']['primaryDocDescription'][idx]))
        return listFilings
    
    @classmethod
    def getFilingByAccession(cls, cik:str, accessionNumber:str):
        cik = cls.correctCIK(cik)
        jSubms = cls.getSubmission(cik)

        for idx, x in enumerate(jSubms['filings']['recent']['accessionNumber']):
            if x==accessionNumber:
                return cls(cik,
                           accessionNumber,
                           jSubms['filings']['recent']['filingDate'][idx],
                           jSubms['filings']['recent']['reportDate'][idx],
                           jSubms['filings']['recent']['acceptanceDateTime'][idx],
                           jSubms['filings']['recent']['act'][idx],
                           jSubms['filings']['recent']['form'][idx],
                           jSubms['filings']['recent']['fileNumber'][idx],
                           jSubms['filings']['recent']['filmNumber'][idx],
                           jSubms['filings']['recent']['items'][idx],
                           jSubms['filings']['recent']['size'][idx],
                           jSubms['filings']['recent']['isXBRL'][idx],
                           jSubms['filings']['recent']['isInlineXBRL'][idx],
                           jSubms['filings']['recent']['primaryDocument'][idx],
                           jSubms['filings']['recent']['primaryDocDescription'][idx])
        logging.warning('joroxbrl.secFiles.Filing.getFilingByAccession: Could not find entry for '+cik+' - '+accessionNumber)
                
                
    def getPrimaryDocumentUrl(self) -> str:
        url = (secDocAccessUrl+str(int(self.cik))+'/'+
               self.accessionNumber.replace('-', '')+'/'+self.primaryDocument)
        return url
    
    def getFilingUrl(self) -> str:
        url = (secDocAccessUrl+str(int(self.cik))+'/'+
               self.accessionNumber.replace('-', '')+'/'+
               self.accessionNumber+'-index.htm')
        return url
    
    def getFilingUrls(self) -> joroxbrl.secGov.FilingUrls:
        if not self.filingUrls:
            self.filingUrls = joroxbrl.secGov.FilingUrls(self.getFilingUrl())
        return self.filingUrls

    def checkDataFiles(self):
        return self.filingUrls.checkDataFiles()
    
def getFactsActualGlobal(cik: str, facts: list[str]) -> dict:
    # # First we are going to identify the document we are interested in, 
    # #  and the period, using the submissions file
    filing = Filing.getLatestFiling(cik, '10-K')
    
    if companyfactsDir:
        with open(companyfactsDir+'CIK'+filing.cik+'.json') as jFile:
            jFacts = json.load(jFile)
    else:
        # We are going to download the company facts file
        url = companyfactsUrl+'CIK'+filing.cik+'.json'
        try:
            jFacts = requests.get(url, headers={
                "User-agent": os.getenv('SEC_USER_AGENT'),
                "Accept-Encoding": "gzip, deflate",
                "Host": "data.sec.gov",
            },).text 
        except requests.exceptions.RequestException as e:
            logging.error('joroxbrl.secFiles.getFactsActualGlobal: Could not download company facts file for '+cik)
            sys.exit(1)
    result = {}
    for f in facts:
        fsplit = f.split(':')
        if fsplit[0] in jFacts['facts'] and fsplit[1] in jFacts['facts'][fsplit[0]]:
            # We are going to assume there is only one unit
            unit = list(jFacts['facts'][fsplit[0]][fsplit[1]]['units'])[0]
            for i in jFacts['facts'][fsplit[0]][fsplit[1]]['units'][unit]:
                if ((i['accn']==filing.accessionNumber and i['end']==filing.reportDate) or 
                    (f[:3]=='dei' and i['accn']==filing.accessionNumber and i['end'][:4]==filing.reportDate[:4])): # If it's dei, we can make an exception and only match the year. I do this for a problem getting dei:EntityCommonStockSharesOutstanding from AIR 2022 10K
                    result[f] = Fact( None, f, i['val'], filing.reportDate, None, unit, 0) # Using reportDate in place of the context is not very good, but I'm not sure we need more than that
                    print('Hemos metido: '+result[f].getDescription())
    return result

def getTickersFromCIK(cik: str) -> list[str]:
    cik = Filing.correctCIK(cik)
    jSubms = Filing.getSubmission(cik)
    return jSubms['tickers']
