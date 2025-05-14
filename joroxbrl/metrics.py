import joroxbrl.secFiles
import logging
import polygon
import time
import datetime
import joroxbrl.secGov
import os

class MetricCalculator:

    _factList = ['OperatingIncomeLoss', 
                  'Assets', 
                  'Liabilities',
                  'LongTermDebtAndCapitalLeaseObligations',
                  'LiabilitiesNoncurrent', 
                  'LiabilitiesCurrent', 
                  'StockholdersEquity',
                  'InterestExpense', 
                  'InterestExpenseDebt',
                  'LongTermDebtAndCapitalLeaseObligations', 
                  'NetIncomeLoss', 
                  'IncomeTaxExpenseBenefit',
                  'Revenues', 
                  'RevenueFromContractWithCustomerIncludingAssessedTax',
                  'RevenueFromContractWithCustomerExcludingAssessedTax',
                  'RevenuesNetOfInterestExpense',
                  'LongTermDebtNoncurrent',
                  'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
                  'CostsAndExpenses', 
                  'AmortizationOfIntangibleAssets',
                  'ShareBasedCompensation',
                  'Depreciation',
                  'DepreciationAndAmortization',
                  'DepreciationDepletionAndAmortization',
                  'IncreaseDecreaseInAccountsReceivable',
                  'IncreaseDecreaseInInventories',
                  'IncreaseDecreaseInOtherCurrentAssets',
                  'IncreaseDecreaseInAccountsPayable',
                  'IncreaseDecreaseInEmployeeRelatedLiabilities',
                  'IncreaseDecreaseInOtherAccruedLiabilities',
                  'IncreaseDecreaseInOtherOperatingCapitalNet',
                  'IncreaseDecreaseInAccountsPayableTrade',
                  'IncreaseDecreaseInAccruedIncomeTaxesPayable',
                  'IncreaseDecreaseInRestructuringReserve',
                  'IncreaseDecreaseInAccountsAndNotesReceivable',
                  'IncreaseDecreaseInAccruedLiabilities',
                  'IncreaseDecreaseInContractWithCustomerAsset',
                  'IncreaseDecreaseInContractWithCustomerLiability',
                  'IncreaseDecreaseInDeferredRevenue',
                  'IncreaseDecreaseInOtherOperatingLiabilities',
                  'IncreaseDecreaseInPrepaidExpensesOther',
                  'NetCashProvidedByUsedInOperatingActivities',
                  'IncreaseDecreaseInOperatingCapital',
                  'InterestIncomeExpenseNonoperatingNet',
                  'InterestIncomeExpenseNet',
                  'InterestAndDebtExpense',
                  'InterestRevenueExpenseNet',
                  'InterestExpenseDebtExcludingAmortization',
                  'ProfitLoss',
                  'NetIncomeLossAvailableToCommonStockholdersBasic',
                  'IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic',
                  'NetCashProvidedByUsedInContinuingOperations',
                  'GrossProfit',
                  'SellingGeneralAndAdministrativeExpense',
                  'GeneralAndAdministrativeExpense',
                  'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
                  'ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost',
                  'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
                  'IncomeLossFromContinuingOperations',
                  'SalesRevenueNet',
                  'CostOfRevenue',
                  'OperatingExpenses',
                  'CostOfGoodsAndServicesSold',
                  'InterestExpenseBorrowings',
                  'InterestExpenseOther',
                  'RegulatedAndUnregulatedOperatingRevenue']
    
    def __init__(self, company=None):
         self.company = company
         self.concepts = {} 
         self.metrics = {}

    
    def genMetricsAfterFiling(self, filing:joroxbrl.secFiles.Filing):
        # The idea here is to generate the metrics with the prices right after the filing.
        # Will use the market cap of filingDate + 10 days
        dFiling = datetime.datetime.strptime(filing.filingDate, '%Y-%m-%d')
        dFiling10 = dFiling + datetime.timedelta(days=10)
        strDFiling10 = dFiling10.strftime('%Y-%m-%d')
        self.genMetrics(filing, date=strDFiling10)


    def genMetrics(self, filing:joroxbrl.secFiles.Filing, date:str=None, getPrice:bool=True):
        self.filing = filing
        if self.company is None: self.company = filing.cik
        
        self.facts = filing.getFilingUrls().getXbrl().getActualGlobalFacts(self._factList)
        logging.debug(self.facts.keys())
    
        # Because it looks like each XBRL is going to use slightly different facts, 
        # we are going to use 'concepts' as an equalizing layer, from which then we 
        # can start building comparable metrics.
        self._extractConcepts(date, getPrice)

        self.getROE()
        self.getROA()
        self.getROCE()
        
        self.getOperatingMargin()
        self.getInterestCoverageRatio()
        self.getDebtToEquity()
        self.getPriceToAFCF()
    
    # Stop using this. I'll use a profitability ratio that doesn't require the Debt concept
    # def getROTC(self):
    #     self.metrics['ROTC'] = (self.concepts['EBIT'] / ( self.concepts['Assets']
    #                                                      - self.concepts['Liabilities']
    #                                                      + self.concepts['Debt'] ) )
    
    # Return On Equity
    def getROE(self):
        try:
            self.metrics['ROE'] = (self.concepts['NetIncome'] 
                               / (self.concepts['Assets'] - self.concepts['Liabilities']))
        except ZeroDivisionError:
            self.metrics['ROE'] = None
    
    # Return On Assets
    def getROA(self):
        try:
            self.metrics['ROA'] = self.concepts['NetIncome'] / self.concepts['Assets']
        except ZeroDivisionError:
            self.metrics['ROA'] = None
    
    # Return On Capital Employed
    def getROCE(self):
        try:
            self.metrics['ROCE'] = (self.concepts['EBIT'] 
                                    / (self.concepts['Assets'] - self.concepts['CurrentLiabilities']))
        except ZeroDivisionError:
            self.metrics['ROCE'] = None
        
    def getOperatingMargin(self):
        if self.concepts['Revenues'] != 0:
            self.metrics['OperatingMargin'] = (self.concepts['OperatingIncome']
                                               / self.concepts['Revenues'])
        else:
            self.metrics['OperatingMargin'] = None

    # Leverage ratios
    def getInterestCoverageRatio(self):
        if self.concepts['Interest'] != 0:
            self.metrics['InterestCoverageRatio'] = self.concepts['EBIT'] / self.concepts['Interest']
        else: 
            self.metrics['InterestCoverageRatio'] = None
    
    # Stop using this. I'll use a profitability ratio that doesn't require the Debt concept
    # def getDebtToEquity(self):
    #     self.metrics['DebtToEquity'] = (self.concepts['Debt'] / 
    #                                     (self.concepts['Assets'] 
    #                                      - self.concepts['Liabilities']))
        
    def getPriceToAFCF(self):
        try:
            self.metrics['PriceToAFCF'] = self.concepts['MarketCap'] / self.concepts['AFCF']
        except ZeroDivisionError:
            self.metrics['PriceToAFCF'] = 100000 # Something very big
        
    def getDebtToEquity(self):
        try:
            self.metrics['DebtToEquity'] = self.concepts['Liabilities'] / (self.concepts['Assets']-self.concepts['Liabilities'])
        except ZeroDivisionError:
            self.metrics['DebtToEquity'] = 100000 # Something very big
              
    def _extractConcepts(self, date:str=None, getPrice:bool=True):
        # Revenues
        if 'Revenues' in self.facts:
            self.concepts['Revenues'] = self.facts['Revenues'].getValueAsNumber() 
        elif 'RevenueFromContractWithCustomerIncludingAssessedTax' in self.facts:
            self.concepts['Revenues'] = self.facts['RevenueFromContractWithCustomerIncludingAssessedTax'].getValueAsNumber()
        elif 'RevenueFromContractWithCustomerExcludingAssessedTax' in self.facts:
            self.concepts['Revenues'] = self.facts['RevenueFromContractWithCustomerExcludingAssessedTax'].getValueAsNumber()
        elif 'RevenuesNetOfInterestExpense' in self.facts:
            self.concepts['Revenues'] = self.facts['RevenuesNetOfInterestExpense'].getValueAsNumber()
        elif 'SalesRevenueNet' in self.facts:
            self.concepts['Revenues'] = self.facts['SalesRevenueNet'].getValueAsNumber()
        elif 'RegulatedAndUnregulatedOperatingRevenue' in self.facts:
            self.concepts['Revenues'] = self.facts['RegulatedAndUnregulatedOperatingRevenue'].getValueAsNumber()
        else:
            self.concepts['Revenues'] = 0
            logging.warning('There are no Revenues for '+self.company+'!!!')
        
        # Gross profit
        remDeprec = False # Set to True if DepreciationAndAmortization should be discounted at the end
        if 'GrossProfit' in self.facts:
            self.concepts['GrossProfit'] = self.facts['GrossProfit'].getValueAsNumber()
        elif 'CostOfRevenue' in self.facts:
            self.concepts['GrossProfit'] = self.concepts['Revenues'] - self.facts['CostOfRevenue'].getValueAsNumber()
            remDeprec = True
        elif  'CostOfGoodsAndServicesSold' in self.facts:
            self.concepts['GrossProfit'] = self.concepts['Revenues'] - self.facts['CostOfGoodsAndServicesSold'].getValueAsNumber()
            remDeprec = True

        if remDeprec:
            if 'DepreciationAndAmortization' in self.facts:
                self.concepts['GrossProfit'] = self.concepts['GrossProfit'] - self.facts['DepreciationAndAmortization'].getValueAsNumber()
            elif 'DepreciationDepletionAndAmortization' in self.facts:
                self.concepts['GrossProfit'] = self.concepts['GrossProfit'] - self.facts['DepreciationDepletionAndAmortization'].getValueAsNumber()

        else:
            logging.warning('There is no GrossProfit for '+self.company+'!!!')
        
        # OperatingIncome
        if 'OperatingIncomeLoss' in self.facts:
            self.concepts['OperatingIncome'] = self.facts['OperatingIncomeLoss'].getValueAsNumber() 
        # Removing this, because it's giving us wrong results with /Archives/edgar/data/200406/000020040622000022/jnj-20220102.htm
        # elif 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic' in self.facts:
        #     self.concepts['OperatingIncome'] = self.facts['IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic'].getValueAsNumber() 
        # elif 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest' in self.facts:
        #     self.concepts['OperatingIncome'] = self.facts['IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'].getValueAsNumber() 
        elif 'IncomeLossFromContinuingOperations' in self.facts:
            self.concepts['OperatingIncome'] = self.facts['IncomeLossFromContinuingOperations'].getValueAsNumber() 
        elif ('GrossProfit' in self.concepts 
              and ('SellingGeneralAndAdministrativeExpense' in self.facts
                   or 'GeneralAndAdministrativeExpense' in self.facts)):
            if 'SellingGeneralAndAdministrativeExpense' in self.facts:
                self.concepts['OperatingIncome'] = (
                    self.concepts['GrossProfit'] - self.facts['SellingGeneralAndAdministrativeExpense'].getValueAsNumber() )
            else:
                self.concepts['OperatingIncome'] = (
                    self.concepts['GrossProfit'] - self.facts['GeneralAndAdministrativeExpense'].getValueAsNumber() )
            if 'ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost' in self.facts:
                self.concepts['OperatingIncome'] = self.concepts['OperatingIncome'] - self.facts['ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost'].getValueAsNumber()
        elif 'CostsAndExpenses' in self.facts:
            self.concepts['OperatingIncome'] = \
                (self.concepts['Revenues'] 
                 - self.facts['CostsAndExpenses'].getValueAsNumber() )
        elif 'OperatingExpenses' in self.facts:
            self.concepts['OperatingIncome'] = \
                (self.concepts['Revenues'] 
                 - self.facts['OperatingExpenses'].getValueAsNumber() )
        else:
            self.concepts['OperatingIncome'] = 0
            logging.warning('There is no Operating Income for '+self.company+'!!!')

        # NetIncome
        # We prefer NetIncomeLossAvailableToCommonStockholdersBasic because it excludes
        #  non controlling porting, while ProfitLoss includes it
        if 'NetIncomeLoss' in self.facts:
            self.concepts['NetIncome'] = self.facts['NetIncomeLoss'].getValueAsNumber()
        elif 'NetIncomeLossAvailableToCommonStockholdersBasic' in self.facts:
            self.concepts['NetIncome'] = self.facts['NetIncomeLossAvailableToCommonStockholdersBasic'].getValueAsNumber()
        elif 'ProfitLoss' in self.facts:
            self.concepts['NetIncome'] = self.facts['ProfitLoss'].getValueAsNumber()
        else:
            self.concepts['NetIncome'] = 0
            logging.warning('There is no Net Income for '+self.company+'!!!')

        # Taxes
        self.concepts['Taxes'] = self.facts['IncomeTaxExpenseBenefit'].getValueAsNumber() \
            if 'IncomeTaxExpenseBenefit' in self.facts else 0
            
        # Interest
        if 'InterestExpense' in self.facts:
            self.concepts['Interest'] = self.facts['InterestExpense'].getValueAsNumber() 
        elif 'InterestExpenseDebt' in self.facts :
            self.concepts['Interest'] = self.facts['InterestExpenseDebt'].getValueAsNumber() 
        elif 'InterestAndDebtExpense' in self.facts:
            self.concepts['Interest'] = self.facts['InterestAndDebtExpense'].getValueAsNumber() 
        elif 'InterestExpenseBorrowings' in self.facts:
            self.concepts['Interest'] = self.facts['InterestExpenseBorrowings'].getValueAsNumber() 
        elif 'InterestExpenseDebtExcludingAmortization' in self.facts:
            self.concepts['Interest'] = self.facts['InterestExpenseDebtExcludingAmortization'].getValueAsNumber() 
        elif 'InterestExpenseOther' in self.facts:
            self.concepts['Interest'] = self.facts['InterestExpenseOther'].getValueAsNumber() 
        # I found this being used for interest expense in /Archives/edgar/data/69488/000095017022003355/mye-20211231.htm
        # However, I'm not sure it's a good idea to use this normally, but I've seen it used at lease twice. 
        # We will use it, only when it actually represents an expense
        # Note the change in sign when we use it!!
        elif 'InterestIncomeExpenseNet' in self.facts and self.facts['InterestIncomeExpenseNet'].getValueAsNumber()<0:
            self.concepts['Interest'] = -self.facts['InterestIncomeExpenseNet'].getValueAsNumber()
        elif 'InterestRevenueExpenseNet' in self.facts and self.facts['InterestRevenueExpenseNet'].getValueAsNumber()<0:
            self.concepts['Interest'] = -self.facts['InterestRevenueExpenseNet'].getValueAsNumber()
        elif 'InterestIncomeExpenseNonoperatingNet' in self.facts and self.facts['InterestIncomeExpenseNonoperatingNet'].getValueAsNumber()<0:
            self.concepts['Interest'] = -self.facts['InterestIncomeExpenseNonoperatingNet'].getValueAsNumber() 
        else: 
            self.concepts['Interest'] = 0
            logging.warning('There is no Interest expense for '+self.company+'!!!')
        
        # EBIT (with this definition, it includes non-operation income, which
        #   I think I may want to remove, but am not sure)
        self.concepts['EBIT'] = (self.concepts['NetIncome'] 
            + self.concepts['Interest'] + self.concepts['Taxes'])
        
        # Assets
        if 'Assets' in self.facts:
            self.concepts['Assets'] = self.facts['Assets'].getValueAsNumber()
        else:
            self.concepts['Assets'] = 0
            logging.warning('There are no Assets for '+self.company+'!!!')
            
        # Liabilities
        if 'Liabilities' in self.facts:
            self.concepts['Liabilities'] = self.facts['Liabilities'].getValueAsNumber()
        elif 'LiabilitiesNoncurrent' in self.facts and 'LiabilitiesCurrent' in self.facts:
            self.concepts['Liabilities'] = self.facts['LiabilitiesNoncurrent'].getValueAsNumber() + self.facts['LiabilitiesCurrent'].getValueAsNumber()
        elif 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest' in self.facts:
            self.concepts['Liabilities'] = self.concepts['Assets'] - self.facts['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'].getValueAsNumber()
        elif 'StockholdersEquity' in self.facts:
            self.concepts['Liabilities'] = self.concepts['Assets'] - self.facts['StockholdersEquity'].getValueAsNumber()
        else:
            self.concepts['Liabilities'] = 0
            logging.warning('There are no Liabilities for '+self.company+'!!!')
        
        # CurrentLiabilities
        if 'LiabilitiesCurrent' in self.facts:
            self.concepts['CurrentLiabilities'] = self.facts['LiabilitiesCurrent'].getValueAsNumber()
        else:
            self.concepts['CurrentLiabilities'] = 0
            logging.warning('There are no Current Liabilities for '+self.company+'!!!')
        
        # Debt
        # I haven't been able to find a reliable way of obtaining this, so I'll stop using it
        # if 'LongTermDebtAndCapitalLeaseObligations' in self.facts:
        #     self.concepts['Debt'] = self.facts['LongTermDebtAndCapitalLeaseObligations'].getValueAsNumber()
        # elif 'LongTermDebtNoncurrent' in self.facts: # I'm not sure both are completely comparable, but we'll make do with this for now
        #     self.concepts['Debt'] = self.facts['LongTermDebtNoncurrent'].getValueAsNumber()
        # else:
        #     self.concepts['Debt'] = 0
        #     logging.warning('There is no Debt for '+self.company+'!!!')
            
        # AFCF
        temp = 0
        logging.debug('temp: '+str(temp))
        if 'NetCashProvidedByUsedInOperatingActivities' in self.facts:
            temp = self.facts['NetCashProvidedByUsedInOperatingActivities'].getValueAsNumber()
            logging.debug('AFCF - us-gaap:NetCashProvidedByUsedInOperatingActivities: '+str(self.facts['NetCashProvidedByUsedInOperatingActivities'].value))
        elif 'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations' in self.facts:
            temp = self.facts['NetCashProvidedByUsedInOperatingActivitiesContinuingOperations'].getValueAsNumber()
            logging.debug('AFCF - us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations: '+str(self.facts['NetCashProvidedByUsedInOperatingActivitiesContinuingOperations'].value))
        elif 'NetCashProvidedByUsedInContinuingOperations' in self.facts:
            # I'm not sure this shoud be right, but found it used in /Archives/edgar/data/1587523/000158752322000005/kn-20211231.htm#i8a37b74de9684c71b86678064fae9900_61
            temp = self.facts['NetCashProvidedByUsedInContinuingOperations'].getValueAsNumber()
            logging.debug('AFCF - us-gaap:NetCashProvidedByUsedInContinuingOperations: '+str(self.facts['NetCashProvidedByUsedInContinuingOperations'].value))
        else: 
            logging.warning('There is no NetCashProvidedByUsedInOperatingActivities for '+self.company+'!!!')

        logging.debug('temp: '+str(temp))
        if 'ShareBasedCompensation' in self.facts:
            temp = temp - self.facts['ShareBasedCompensation'].getValueAsNumber()
            logging.debug('AFCF - us-gaap:ShareBasedCompensation: '+str(self.facts['ShareBasedCompensation'].value))
        else: 
            logging.warning('There is no ShareBasedCompensation for '+self.company+'!!!')
            
        logging.debug('temp: '+str(temp))
        depF = None
        addBackAmortizationOfIntangibles = False 
        if 'DepreciationDepletionAndAmortization' in self.facts: 
            depF = self.facts['DepreciationDepletionAndAmortization']
            addBackAmortizationOfIntangibles = True
        elif 'DepreciationAndAmortization' in self.facts:
            depF = self.facts['DepreciationAndAmortization']
            addBackAmortizationOfIntangibles = True
        elif 'Depreciation' in self.facts:
            depF = self.facts['Depreciation']
            
        if depF is not None:    
            temp = temp - depF.getValueAsNumber()
            logging.debug('AFCF - us-gaap:Depreciation(Depletion)AndAmortization: '+str(depF.value))
        else: 
            logging.warning('There is no Depreciation(Depletion)AndAmortization for '+self.company+'!!!')

        if addBackAmortizationOfIntangibles:
            # We don't want to add back amortization of intangibles if we haven't substracted total depreciation and amortization to begin with
            logging.debug('temp: '+str(temp))
            if 'AmortizationOfIntangibleAssets' in self.facts:
                amortInt = self.facts['AmortizationOfIntangibleAssets'].getValueAsNumber()
                # I've seen cases (/Archives/edgar/data/1861795/000095017022003770/dh-20211231.htm)
                #  in which the DepreciationDepletionAndAmortization didn't actually 
                #  include amortization of intangibles. This is a hack, to take care of some cases.
                # To properly take care, I think it would be necessary to check in the presentation of
                #  calculation linkBases if amortization of intangibles had already been added.
                if amortInt < temp:
                    temp = temp + amortInt
                logging.debug('AFCF - us-gaap:AmortizationOfIntangibleAssets: '+str(self.facts['AmortizationOfIntangibleAssets'].value))
            else: 
                logging.warning('There is no AmortizationOfIntangibleAssets for '+self.company+'!!!')
            
        logging.debug('AFCF before undoing working capital changes: '+str(temp))
        # Reverse changes in working capital
        cwc = 0
        try:
            plb = self.filing.getFilingUrls().getPresentationLinkbase()
            cwc = plb.getChangesInOperatingCapitalFromStrings(
                    joroxbrl.secGov.SecGovCaller.callSecGovUrl(self.filing.getFilingUrls().getCalculationLinkbaseUrl()).text, 
                    xbrl = self.filing.getFilingUrls().getXbrl() )
        except Exception as ex:
            # I've seen this happen in cases where the calculation linkbase doesn't include this
            # A possible workaround could be to control that specific error, and then try
            #  to hardcode each of the typical values, and whether they should be positive or negative
            logging.error(str(ex)+' calculating CWC. Unfortunately will need to skip for '
                          +self.filing.cik+'-'+self.filing.accessionNumber)
            
        if cwc==0:
            if 'IncreaseDecreaseInOperatingCapital' in self.facts:
                # Notice negative sign
                cwc = -self.facts['IncreaseDecreaseInOperatingCapital'].getValueAsNumber()

        logging.debug('cwc: '+str(cwc))
        self.concepts['AFCF'] = temp - cwc # It's minus because we want to undo the effect
        self.concepts['cwc'] = cwc
        
        # Market cap
        listTickers = joroxbrl.secFiles.getTickersFromCIK(self.filing.cik)
        ticker = listTickers[0] if (listTickers is not None and len(listTickers)>0) else None
        logging.debug('We look for the ticker '+str(ticker))
        #ticker='LGF.A'
        try:
            td = PolygonCaller.get_ticker_details(ticker, date) if getPrice else None
            logging.debug(td)
        except Exception as ex:
            logging.error(str(ex)+'\nError getting the ticker details for '+str(ticker))
            td = None
        self.concepts['SharesOutstanding'] = float(td.share_class_shares_outstanding) if td is not None and td.share_class_shares_outstanding is not None else 0
        self.concepts['MarketCap'] = float(td.market_cap) if td is not None and td.market_cap is not None else 0
        
    @classmethod
    def calculateTTMMetrics(cls, cik: str): #-> MetricCalculator: # returns concepts and metrics
        lis = joroxbrl.secFiles.Filing.getListFilings(cik, ['10-Q', '10-K'], isXBRL=True)
        # They come in reverse chronological order (newer first)
        
        recentMetric = MetricCalculator()
        recentMetric.genMetrics(lis[0])
        if lis.pop(0).form=='10-K':
            # This will be easy, we just have to return the metrics of the 10-K, and we're done
            return recentMetric

        # This is 10-Q then
        recentXbrl = recentMetric.filing.getFilingUrls().getXbrl()
        recentYear = recentXbrl.getFact('DocumentFiscalYearFocus').value
        q = recentXbrl.getFact('DocumentFiscalPeriodFocus').value
        recentDocumentPeriodEndDate = recentXbrl.getFact('DocumentPeriodEndDate').value
        annualMetric = None # this will contain the MetricsCalculator corresponding to the 10-K
        olderMetric = None # this will contain the MetricsCalculator corresponding to the previous year's 10-Q
        for fil in lis:
            if fil.form=='10-K':
                if annualMetric is not None: 
                    logging.error('Error finding corresponding filings in calculateTTMMetrics for '+cik)
                    return None
                else:
                    annualMetric = joroxbrl.metrics.MetricCalculator()
                    annualMetric.genMetrics(fil, getPrice=False)
            else: # Has to be 10-Q
                xbrl = fil.getFilingUrls().getXbrl()
                # Tenemos que cambiar esto, porque hay casos en que no encaja.
                # Vamos a reescribir la lógica para hacer que la fecha de fin de periodo sea aproximadamente
                # un año anterior.
                filDocumentPeriodEndDate = xbrl.getFact('DocumentPeriodEndDate').value
                monthsPeriodDelta = round((datetime.datetime.strptime(recentDocumentPeriodEndDate, '%Y-%m-%d') 
                                      - datetime.datetime.strptime(filDocumentPeriodEndDate, '%Y-%m-%d')).total_seconds()
                                     / (3600*24*31) )
                            
                # OLD LOGIC:
                # if ( str(int(recentYear)-1)==xbrl.getFact('DocumentFiscalYearFocus').value
                #      and q==xbrl.getFact('DocumentFiscalPeriodFocus').value):
                if monthsPeriodDelta < 14 and monthsPeriodDelta > 10:
                    olderMetric = joroxbrl.metrics.MetricCalculator()
                    olderMetric.genMetrics(fil, getPrice=False)
                
            if annualMetric is not None and olderMetric is not None:
                break
        
        if annualMetric is None or olderMetric is None:
            logging.error('Ran out of filings in calculateTTMMetrics for '+cik)
            return None
        
        # Now we calculate the combined stats
        calc_concepts = ['Revenues', 'OperatingIncome', 'NetIncome', 'Taxes', 'Interest', 'EBIT', 'AFCF', 'cwc'] 
        recent_concepts = ['Assets', 'Liabilities', 'CurrentLiabilities', 'MarketCap']
        
        ttmMetric = joroxbrl.metrics.MetricCalculator()

        for c in calc_concepts:
            ttmMetric.concepts[c] = annualMetric.concepts[c] + recentMetric.concepts[c] - olderMetric.concepts[c]

        for c in recent_concepts:
            ttmMetric.concepts[c] = recentMetric.concepts[c]

        ttmMetric.getROE()
        ttmMetric.getROA()
        ttmMetric.getROCE()
        ttmMetric.getOperatingMargin()
        ttmMetric.getInterestCoverageRatio()
        ttmMetric.getDebtToEquity()
        ttmMetric.getPriceToAFCF()                 
        
        ttmMetric.filing = recentMetric.filing
        
        return ttmMetric
    

class PolygonCaller:
    _lastCall = datetime.datetime.today() - datetime.timedelta(minutes=1)
    _polyDelta = datetime.timedelta(seconds=13) # Our Polygon license allows us to do 5 calls per minute
    
    @classmethod
    def get_ticker_details(cls, ticker:str, date:str=None):
        logging.debug('PolygonCaller.get_ticker_details('+ticker+','+str(date)+')')
        cls._callLimit()
        # In some cases, when SEC includes a - in the ticker, Polygon prefers a .
        ticker = ticker.replace('-', '.')
        params = {'date': date} if date is not None else {}
        return polygon.RESTClient(os.getenv('POLYGON_KEY')).get_ticker_details(ticker, date=date, params=params)
    
    @classmethod
    def _callLimit(cls):
        # Maintain control of how many calls we are doing
        while (cls._lastCall+cls._polyDelta > datetime.datetime.today()):
            time.sleep(1) # Wait for 1 second and check again
        cls._lastCall = datetime.datetime.today()
        