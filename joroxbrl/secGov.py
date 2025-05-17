# This module encapsulates access to sec.gov
# The criteria to consider whether something should be included in this module is 
#  that all absolutes about sec.gov's base URL and HTML parsing of its pages should be here

import requests
from bs4 import BeautifulSoup
import joroxbrl.presentationLinkbase
import joroxbrl.core
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import datetime
import time
import os
import re

_baseUrl = 'https://www.sec.gov'
hostRegex = re.compile(r'^(https?://)?(([^\.]+\.)?sec\.gov)(/.*)?$')

class SecGovCaller:
    
    _SecGov_lastCall = datetime.datetime.today() - datetime.timedelta(minutes=1)
    _SecGov_Delta = datetime.timedelta(milliseconds=100) # sec.gov doesn't like it when we call more than 10 times per second
    
    _session = None
    
    @classmethod
    def callSecGovUrl(cls, url:str) -> requests.Response:
        if cls._session is None:
            # Prepare request retries
            cls._session = requests.Session()
            retry = Retry(connect=3, backoff_factor=0.5)
            adapter = HTTPAdapter(max_retries=retry)
            cls._session.mount('http://', adapter)
            cls._session.mount('https://', adapter)

        hostMatch = hostRegex.match(url)
        if hostMatch is None:
            logging.warning(f"URL {url} is not actually sec.gov.")
            host = 'www.sec.gov'
            # We don't apply the call limit if the URL is not sec.gov
        else:
            host = hostMatch.group(2)
            cls._callLimit()

        return cls._session.get(url, headers={
                "User-agent": os.getenv('SEC_USER_AGENT'),
                "Accept-Encoding": "gzip, deflate",
                "Host": host
            })
    
    @classmethod
    def _callLimit(cls):
        # Maintain control of how many calls we are doing
        while (cls._SecGov_lastCall+cls._SecGov_Delta > datetime.datetime.today()):
            time.sleep( cls._SecGov_Delta.total_seconds()/2 ) # Wait for half the duration of the delta
        cls._SecGov_lastCall = datetime.datetime.today()
        

class FilingUrls:
    """
    Attributes:
        filingRootUrl: URL of the filing html, from which all the rest of the documents can be extracted 
            (e.g.: https://www.sec.gov/Archives/edgar/data/1750/000110465922102374/0001104659-22-102374-index.htm)
        mainFormType: 10-K, !0-Q, ...
        mainDocumentUrl: URL of the 10-K or 10-Q itself. 
            (e.g.: https://www.sec.gov/ix?doc=/Archives/edgar/data/1750/000110465922102374/air-20220831x10q.htm)
        dataFileUrls: The URLs of the independent datafiles. Will only contain those type found in _dataFileTypes.
        
        presentationLinkbase: joroxbrl.presentationLinkbase.PresentationLinkbase object
        xbrl: joroxbrl.core.XBRL object
    """
    _mainFormType = { 'Form 10-K': '10-K',
                      'Form 10-Q': '10-Q' }
    _dataFileTypes = [ 'EX-101.CAL', 'EX-101.PRE', 'XML', 'EX-101.SCH', 'EX-101.INS' ]
    
    presentationLinkbase = None
    xbrl = None

    def __init__(self, filingRootUrl):
        logging.debug('Initializing FilingUrls for '+filingRootUrl)
        self.filingRootUrl = filingRootUrl

        r = SecGovCaller.callSecGovUrl(filingRootUrl)
        soup = BeautifulSoup(r.text, features='html.parser')
        formName = soup.find('div', id='formName').strong.text
        self.mainFormType = self._mainFormType[formName]
        
        documentTable = soup.find('table', class_='tableFile', summary='Document Format Files')
        for tr in documentTable.find_all('tr'):
            tdList = tr.find_all('td')
            if len(tdList)>3 and tdList[3].text==self.mainFormType:
                self.mainDocumentUrl = _baseUrl + tdList[2].a['href'].replace('/ix?doc=', '')
                break
            
        dataFileUrls = {}
        documentTable = soup.find('table', class_='tableFile', summary='Data Files')
        if documentTable is not None: # If None, probably means that there is no XBRL in this filing
            for tr in documentTable.find_all('tr'):
                tdList = tr.find_all('td')
                if len(tdList)>3:
                    for dataf in self._dataFileTypes:
                        if tdList[3].text==dataf:
                            dataFileUrls[dataf] = _baseUrl + tdList[2].a['href'].replace('/ix?doc=', '')
                            break
    
        self.dataFileUrls = dataFileUrls
        
    def checkDataFiles(self):
        if len(self.dataFileUrls)==4: return True
        else: return False
        
    def getPresentationLinkbaseUrl(self):
        try:
            return self.dataFileUrls['EX-101.PRE']
        except:
            return None
    
    def getCalculationLinkbaseUrl(self):
        try:
            return self.dataFileUrls['EX-101.CAL']
        except:
            return None
    
    def getXbrlUrl(self):
        try:
            return self.dataFileUrls['XML']
        except:
            return None
    
    def getXsdUrl(self):
        try:
            return self.dataFileUrls['EX-101.SCH']
        except:
            return None
    
    def getPresentationLinkbase(self):
        if not self.presentationLinkbase:
            self.presentationLinkbase = joroxbrl.presentationLinkbase.PresentationLinkbase(self)
            self.presentationLinkbase.readXmlUrl(self.getPresentationLinkbaseUrl())
        return self.presentationLinkbase
    
    def getXbrl(self):
        if not self.xbrl:
            self.xbrl = joroxbrl.core.XBRL()
            if 'XML' in self.dataFileUrls:
                self.xbrl.readXmlUrl(self.dataFileUrls['XML'])
            elif 'EX-101.INS' in self.dataFileUrls:
                self.xbrl.readXmlUrl(self.dataFileUrls['EX-101.INS'])
        return self.xbrl
            