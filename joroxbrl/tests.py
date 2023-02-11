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
            self.assertTrue(found)
    
class TestFiling(unittest.TestCase):
    
    def test1(self):
        latestFiling = joroxbrl.secFiles.Filing.getLatestFiling('20', '10-K')
        specificFiling = joroxbrl.secFiles.Filing.getFilingByTypeAndDate('20', '10-K', '2010-01-02')
        self.assertEqual(latestFiling.accessionNumber, specificFiling.accessionNumber)
        self.assertEqual(specificFiling.accessionNumber, '0000950123-10-024631')
        
    def test2(self):
        filing = joroxbrl.secFiles.Filing.getFilingByTypeAndDate('20', '10-Q', '2009-10-03')
        self.assertEqual( filing.cik, '0000000020' )
        self.assertEqual( filing.accessionNumber, '0000950123-09-060709' )
        self.assertEqual( filing.filingDate, '2009-11-10' )
        self.assertEqual( filing.reportDate, '2009-10-03' )
        self.assertEqual( filing.acceptanceDateTime, '2009-11-10T15:08:38.000Z' )
        self.assertEqual( filing.act, '34' )
        self.assertEqual( filing.form, '10-Q' )
        self.assertEqual( filing.fileNumber, '000-09576' )
        self.assertEqual( filing.filmNumber, '091171711' )
        self.assertEqual( filing.items, '' )
        self.assertEqual( filing.size, 376591 )
        self.assertEqual( filing.isXBRL, 0 )
        self.assertEqual( filing.isInlineXBRL, 0 )
        self.assertEqual( filing.primaryDocument, 'c92294e10vq.htm' )
        self.assertEqual( filing.primaryDocDescription, 'FORM 10-Q' )
        
    def testGetListFilings(self):
        listFilings = joroxbrl.secFiles.Filing.getListFilings('1786842', ['10-K'], isXBRL=True)
        # for f in listFilings:
        #     print(f.getPrimaryDocumentUrl())
        self.assertEqual( len(listFilings), 2 )
       
class TestFact(unittest.TestCase):
    def test1(self):
        fact = joroxbrl.core.Fact('id', '{http://fasb.org/us-gaap/2021-01-31}DeferredTaxAssetsGross', 'value', 'context', 'format', 'unit', 'scale')
        self.assertEqual( fact.namespace, 'http://fasb.org/us-gaap/2021-01-31' )
        self.assertEqual( fact.unqualifiedName, 'DeferredTaxAssetsGross' )
        
    def test2(self):
        fact = joroxbrl.core.Fact('id', 'DeferredTaxAssetsGross', 'value', 'context', 'format', 'unit', 'scale')
        self.assertIsNone( fact.namespace )
        self.assertEqual( fact.unqualifiedName, 'DeferredTaxAssetsGross' )
        
class TestMetrics(unittest.TestCase):
    def test1(self):
        filing = joroxbrl.secFiles.Filing.getFilingByTypeAndDate('1672688', '10-K', '2021-12-31')
        m = joroxbrl.metrics.MetricCalculator()
        m.genMetrics(filing)
        self.assertEqual( int(m.concepts['Revenues']), 4782000 )
        self.assertEqual( int(m.concepts['OperatingIncome']), -75238000 )
        self.assertEqual( int(m.concepts['NetIncome']), -100960000 )
        self.assertEqual( int(m.concepts['Taxes']), -8899000 )
        self.assertEqual( int(m.concepts['Interest']), 3432000 )
        self.assertEqual( int(m.concepts['EBIT']), -106427000 )
        self.assertEqual( int(m.concepts['Assets']), 426195000 )
        self.assertEqual( int(m.concepts['Liabilities']), 60088000 )
        self.assertEqual( int(m.concepts['CurrentLiabilities']), 33859000 )
        self.assertEqual( int(m.concepts['AFCF']), -74714000 )
        self.assertEqual( int(m.concepts['cwc']), -3146000 )
        self.assertNotEqual( m.concepts['SharesOutstanding'], 0 ) # Because it's taken dinamically from Polygon, we can't check for a specific value
        self.assertNotEqual( m.concepts['MarketCap'], 0 ) # Because it's taken dinamically from Polygon, we can't check for a specific value
        self.assertEqual( int(m.metrics['ROE']), 0 )
        self.assertEqual( int(m.metrics['ROA']), 0 )
        self.assertEqual( int(m.metrics['ROCE']), 0 )
        self.assertEqual( int(m.metrics['OperatingMargin']), -15 )
        self.assertEqual( int(m.metrics['InterestCoverageRatio']), -31 )
        self.assertNotEqual( m.metrics['PriceToAFCF'], 0 )
        
    # def test2(self):
    #     # This will test the calculation of CWC when there is no CWC Abstract item in PRES
    #     accessionNumber = '0001417398-20-000042'
        
        
