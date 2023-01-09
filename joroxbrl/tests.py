import unittest
import joroxbrl.core
import joroxbrl.secFiles
import joroxbrl.metrics
import logging

class TestXBRL(unittest.TestCase):
    
    def test1(self):
        xbrl = joroxbrl.core.XBRL()
        xbrl.readXmlUrl('https://www.sec.gov/Archives/edgar/data/1448597/000139390522000073/augg-20211231_htm.xml')
        
        assert len(xbrl.contexts)==123
        assert len(xbrl.facts)==529
        
        values = [('{http://fasb.org/us-gaap/2021-01-31}AdjustmentsToAdditionalPaidInCapitalWarrantIssued', '0'),
                  ('{http://fasb.org/us-gaap/2021-01-31}NetCashProvidedByUsedInFinancingActivities', '16671204'),
                  ('{http://xbrl.sec.gov/dei/2021q4}EntityAddressCityOrTown', 'Vancouver'),
                  ('{http://www.augustagold.com/20211231}PreferredStockValueB', '67')]
        
        for v in values:
            logging.debug('We\'ll look for '+v[0])
            found = False
            for f in xbrl.facts:
                if f.fullName == v[0]: 
                    print('Estamos: '+f.fullName)
                    assert f.value == v[1]
                    found = True
                    break
            assert found
    
class TestFiling(unittest.TestCase):
    
    def test1(self):
        latestFiling = joroxbrl.secFiles.Filing.getLatestFiling('20', '10-K')
        specificFiling = joroxbrl.secFiles.Filing.getFilingByTypeAndDate('20', '10-K', '2010-01-02')
        assert latestFiling.accessionNumber == specificFiling.accessionNumber
        assert specificFiling.accessionNumber == '0000950123-10-024631'
        
    def test2(self):
        filing = joroxbrl.secFiles.Filing.getFilingByTypeAndDate('20', '10-Q', '2009-10-03')
        assert filing.cik=='0000000020'
        assert filing.accessionNumber=='0000950123-09-060709'
        assert filing.filingDate=='2009-11-10'
        assert filing.reportDate=='2009-10-03'
        assert filing.acceptanceDateTime=='2009-11-10T15:08:38.000Z'
        assert filing.act=='34'
        assert filing.form=='10-Q'
        assert filing.fileNumber=='000-09576'
        assert filing.filmNumber=='091171711'
        assert filing.items==''
        assert filing.size==376591
        assert filing.isXBRL==0
        assert filing.isInlineXBRL==0
        assert filing.primaryDocument=='c92294e10vq.htm'
        assert filing.primaryDocDescription=='FORM 10-Q'
        
    def testGetListFilings(self):
        listFilings = joroxbrl.secFiles.Filing.getListFilings('1786842', ['10-K'], isXBRL=True)
        # for f in listFilings:
        #     print(f.getPrimaryDocumentUrl())
        assert len(listFilings)==2
       
class TestFact(unittest.TestCase):
    def test1(self):
        fact = joroxbrl.core.Fact('id', '{http://fasb.org/us-gaap/2021-01-31}DeferredTaxAssetsGross', 'value', 'context', 'format', 'unit', 'scale')
        assert fact.namespace == 'http://fasb.org/us-gaap/2021-01-31'
        assert fact.unqualifiedName == 'DeferredTaxAssetsGross'
        
    def test2(self):
        fact = joroxbrl.core.Fact('id', 'DeferredTaxAssetsGross', 'value', 'context', 'format', 'unit', 'scale')
        assert fact.namespace is None
        assert fact.unqualifiedName == 'DeferredTaxAssetsGross'
        
class TestMetrics(unittest.TestCase):
    def test1(self):
        filing = joroxbrl.secFiles.Filing.getFilingByTypeAndDate('1672688', '10-K', '2021-12-31')
        m = joroxbrl.metrics.MetricCalculator()
        m.genLatestMetrics(filing)
        assert int(m.concepts['Revenues'])==4782000
        assert int(m.concepts['OperatingIncome'])==-75238000
        assert int(m.concepts['NetIncome'])==-100960000
        assert int(m.concepts['Taxes'])==-8899000
        assert int(m.concepts['Interest'])==3432000
        assert int(m.concepts['EBIT'])==-106427000
        assert int(m.concepts['Assets'])==426195000
        assert int(m.concepts['Liabilities'])==60088000
        assert int(m.concepts['CurrentLiabilities'])==33859000
        assert int(m.concepts['AFCF'])==-72614000
        assert int(m.concepts['cwc'])==-3146000
        assert m.concepts['SharesOutstanding']!=0 # Because it's taken dinamically from Polygon, we can't check for a specific value
        assert m.concepts['MarketCap']!=0 # Because it's taken dinamically from Polygon, we can't check for a specific value
        assert int(m.metrics['ROE'])==0
        assert int(m.metrics['ROA'])==0
        assert int(m.metrics['ROCE'])==0
        assert int(m.metrics['OperatingMargin'])==-15
        assert int(m.metrics['InterestCoverageRatio'])==-31
        assert m.metrics['PriceToAFCF']!=0
        
    def test2(self):
        # This will test the calculation of CWC when there is no CWC Abstract item in PRES
        accessionNumber = '0001417398-20-000042'
        
        
TestXBRL().test1()
TestFiling().test1()
TestFiling().test2()
TestFiling().testGetListFilings()
TestFact().test1()
TestFact().test2()
TestMetrics().test1()
