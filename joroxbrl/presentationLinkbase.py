import xml.etree.ElementTree as ET
from treelib import Tree
import treelib.exceptions
import re
import joroxbrl.core
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import joroxbrl.secGov


reAbstractNode = re.compile('(.*)Abstract')

def getHrefFromLabel(xmlRoot, label):
    href = None
    for loc in xmlRoot.iter('{http://www.xbrl.org/2003/linkbase}loc'):
        if loc.attrib['{http://www.w3.org/1999/xlink}label'] == label:
            href = loc.attrib['{http://www.w3.org/1999/xlink}href']
            break
    if href is None:
        print('Couldn\'t find the href for '+label+'!!!')
    return href

def getXbrlFactfromHref(href):
    pass

def getLabelFromHref(xmlRoot, href):
    label = None
    for loc in xmlRoot.iter('{http://www.xbrl.org/2003/linkbase}loc'):
        if loc.attrib['{http://www.w3.org/1999/xlink}href'] == href:
            label = loc.attrib['{http://www.w3.org/1999/xlink}label']
            break
    if label is None:
        print('Could not find the label corresponding to '+href)
    return label

xsdNamespaceDict = {}

def getNamespaceFromXsd(xsdUrl):
    if xsdUrl not in xsdNamespaceDict:
        xsd = joroxbrl.secGov.SecGovCaller.callSecGovUrl(xsdUrl).text
        xsdNamespaceDict[xsdUrl] = ET.fromstring(xsd).get('targetNamespace')
    return xsdNamespaceDict[xsdUrl]    

class PresentationTreeNodeData:
    # Really, this class is only intended for data storage.
    # The need of this is because the number of ids and relationships can get extremely convoluted:
    # - An item will have a loc entry in the presentation and calculation linkbases. Each of these entries has an href and a label.
    # - While the href is the same between both files, the label may not be.
    # - The labels are necessary, because those are used to reference them by the presentationArcs and calculationArcs.
    # Attributes:
    # - href
    # - presentationLabel
    # - calculationLabel
    # - xbrlFact
    # - factValue (signed according to calculation)
    pass
    

class PresentationLinkbase:
    
    def __init__(self, filingUrls):
        self.filingUrls = filingUrls
        
    
    # xml: pass xml file as a single string
    def readXml(self, xml):
        self.root = ET.fromstring(xml)
        
    def readXmlFile(self, xmlFile):
        self.root = ET.parse(xmlFile).getroot()
        
    def readXmlUrl(self, xmlUrl):
        self.readXml(joroxbrl.secGov.SecGovCaller.callSecGovUrl(xmlUrl).text)
        
    # We will put a dict in the data entry of each node.
    # The need of this is because the number of ids and relationships can get extremely convoluted:
    # - An item will have a loc entry in the presentation and calculation linkbases. Each of these entries has an href and a label.
    # - While the href is the same between both files, the label may not be.
    # - The labels are necessary, because those are used to reference them by the presentationArcs and calculationArcs.
    # Dict entries:
    # - href (whole, whithout removing the part before the #) -> identifier of the treelib node
    # - presentationLabel -> tag of the treelib node
    # - calculationLabel
    # - xbrlFact
    # - factValue
    def _createPresentationTree(self, rootLocation):
        logging.debug('In _createPresentationTree: we enter for '+rootLocation)
        # rootLocation is the href of the abstract node whose contents we want. 
        #   We accept it complete or just the the second part(after the #) 
        tree = Tree()

        # Need to obtain the corresponding label for rootLocation
        rootLocationLabel = None
        for loc in self.root.iter('{http://www.xbrl.org/2003/linkbase}loc'):
            if (loc.attrib['{http://www.w3.org/1999/xlink}href'].split('#')[-1]==rootLocation or
                loc.attrib['{http://www.w3.org/1999/xlink}href']==rootLocation):
                rootLocation = loc.attrib['{http://www.w3.org/1999/xlink}href'] # In case we only got the partial name
                rootLocationLabel = loc.attrib['{http://www.w3.org/1999/xlink}label']
                break
        if rootLocationLabel is None:
            logging.warning('Could not find the label corresponding to the rootLocation '+rootLocation)
            
        def _addNode(node):
            result = []
            for arc in self.root.iter('{http://www.xbrl.org/2003/linkbase}presentationArc'):
                if arc.attrib['{http://www.w3.org/1999/xlink}from'] == node.data['presentationLabel']:
                    # attribute 'to' gives us the label, but we need to find the name
                    label = arc.attrib['{http://www.w3.org/1999/xlink}to']
                    href = getHrefFromLabel(self.root, label)
                    try:
                        newNode = tree.create_node(identifier=href, tag=label, parent=node)
                        newNode.data = {}
                        newNode.data['href'] = href
                        newNode.data['presentationLabel'] = label
                        subHref = href.split('#')
                        if href[0:4] != 'http': # In this case xsd has to be taken from filingUrls
                            logging.info('we will retrieve the xsd from filingUrls for '+href)
                            ns = getNamespaceFromXsd(self.filingUrls.getXsdUrl())
                        else:
                            ns = getNamespaceFromXsd(subHref[0])
                            
                        newNode.data['xbrlFact'] = '{'+ns+'}'+subHref[-1].split('_', 1)[-1]
                        logging.debug('Adding node: '+str(newNode.tag))
                        result.append(newNode)
                    except treelib.exceptions.DuplicatedNodeIdError:
                        logging.error("Exception adding node "+href+" because it's duplicate")

            return result
        
        firstNode = tree.create_node(identifier=rootLocation, tag=rootLocationLabel)
        firstNode.data = {}
        firstNode.data['href'] = rootLocation
        firstNode.data['presentationLabel'] = rootLocationLabel
        pending = [firstNode]
        
        while len(pending) > 0:
            pending = pending + _addNode(pending.pop(-1))
        
        tree.show()
        
        return tree
    
    def getChangesInOperatingCapital(self, calRoot, xbrl):

        def _getSign(name):
            ret = None

            if calRoot is not None:
                label = getLabelFromHref(calRoot, name)
                for arc in calRoot.iter('{http://www.xbrl.org/2003/linkbase}calculationArc'):
                    if arc.attrib['{http://www.w3.org/1999/xlink}to'] == label:
                        ret = float(arc.attrib['weight'])
                        break

            if ret is None:
                logging.warning('Could not find reference of '+name+' in calculation linkbase')
                # If calculation linkbase doesn't help us, we'll try some aducated guesses
                if 'Inventories' in name:
                    ret = -1.0
                elif 'Receivable' in name:
                    ret = -1.0
                elif 'Payable' in name:
                    ret = 1.0
                elif 'Asset' in name:
                    ret = -1.0
                elif 'LeaseLiabilit' in name:
                    ret = -1.0
                elif 'Liabilit' in name:
                    ret = 1.0
                elif 'OperatingCapital' in name:
                    ret = -1.0
                elif 'DeferredIncomeTaxes' in name:
                    ret = 1.0
                elif 'IncomeTaxes' in name:
                    ret = 1.0
                elif 'AccruedSalar' in name:
                    ret = 1.0
                else:
                    ret = -1.0
                    logging.warning('Defaulting sign for '+name)
                    
            return ret
            
        def _getTotalCwc(name_check):
            total = 0
            logging.debug('Calculation of CWC:')
            ##  VAMOS A PROBAR QUE TAL VA ESTO
            #        for i in tree.children(tree.root): #tree.all_nodes():
            for i in tree.all_nodes():
                logging.debug('Data: '+str(i.data))
                logging.debug("Tag we'll get: "+i.data['presentationLabel']+'('+i.data['href']+')')
                label_name = i.data['href'].split('#')[-1]
                u_label_name = label_name.split('_')[-1]
                if name_check:
                    if ((u_label_name[0:16]!='IncreaseDecrease' and u_label_name[0:11]!='NetChangeIn') 
                        or u_label_name[-8:]=='Abstract'):
                        logging.info('Calculation CWC with name_check: skipping '+i.data['href'])
                        continue
                else:
                    if label_name=='us-gaap_NetCashProvidedByUsedInOperatingActivities':
                        # This if shouldn't be necessary but I've seen cases (eg: CVU 2021 10K) in which they include this as child of us-gaap_IncreaseDecreaseInOperatingCapitalAbstract in the presentation linkbase
                        logging.info('Skipping us-gaap:NetCashProvidedByUsedInOperatingActivities from the CWC calculation')
                        continue
                    elif label_name=='us-gaap_AdjustmentsToReconcileNetIncomeLossToCashProvidedByUsedInOperatingActivities':
                        # This also shouldn't be necessary, but found it in /Archives/edgar/data/1069533/000143774921027683/rgco20210930_10k.htm
                        logging.info('Skipping us-gaap:AdjustmentsToReconcileNetIncomeLossToCashProvidedByUsedInOperatingActivities from the CWC calculation')
                        continue
                    elif label_name=='us-gaap_NetCashProvidedByUsedInContinuingOperations':
                        # This also shouldn't be necessary, but found it in /Archives/edgar/data/1587523/000158752322000005/kn-20211231.htm
                        logging.info('Skipping us-gaap:NetCashProvidedByUsedInContinuingOperations from the CWC calculation')
                        continue
                    elif label_name=='us-gaap_NetCashProvidedByUsedInOperatingActivitiesContinuingOperations':
                        # This also shouldn't be necessary, but found it in /Archives/edgar/data/1587523/000158752322000005/kn-20211231.htm
                        logging.info('Skipping us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations from the CWC calculation')
                        continue
                    elif 'xbrlFact' not in i.data:
                        logging.info('Skipping '+i.data['href']+' from the CWC calculation, because apparently it doesn\'t have an XBRL entry associated')
                        continue
    
                logging.debug('KOKODATA: '+str(i.data))
                logging.debug("The XBRL fact we'll look for: "+i.data['xbrlFact'])
                actualFact = xbrl.getActualGlobalFact(i.data['xbrlFact'])
                logging.debug("What we found in the xbrl: "+str(actualFact))
                
                if actualFact is None: # Added this because I've found cases where the presentation included facts that then were not in the XBRL
                    i.data['factValue'] = 0
                else:
                    try:
                        i.data['factValue'] = int(_getSign(i.identifier)) * actualFact.getValueAsNumber()
                    except Exception as ex: # This may kick in if we found a fact that contains a text block or something like that
                        logging.warning(f'Exception in _getTotalCwc getting the value for {i.data['xbrlFact']}: '+str(ex))
                        i.data['factValue'] = 0
                        
                total = total + i.data['factValue']
                logging.debug('Value added to CWC: '+i.data['xbrlFact']+': '+str(i.data['factValue']))
            logging.debug('The total change in operating capital is '+str(total))
            return total
        
        possibleCwcGroupings = [
            ( 'us-gaap_IncreaseDecreaseInOperatingCapitalAbstract', False ),
            ( 'us-gaap_IncreaseDecreaseInOperatingAssetsAbstract', False ),
            ( 'us-gaap_IncreaseDecreaseInOtherOperatingAssetsAndLiabilitiesNetAbstract', False ),
            ( 'us-gaap_IncreaseDecreaseInOperatingLiabilitiesAbstract', False ),
            ( 'cspi_ChangesInOperatingAssetsAndLiabilitiesAbstract', False ),  # This only applies to CSP INC (CIK: 0000356037)
            ( 'bwa_ChangesInAssetsAndLiabilitiesExcludingEffectsOfAcquisitionsDivestituresAndForeignCurrencyTranslationAdjustmentsAbstract', False ), # This only applies to BORGWARNER INC (CIK  0000908255)
            ( 'us-gaap_NetCashProvidedByUsedInOperatingActivitiesContinuingOperationsAbstract', True ),
            ( 'us-gaap_NetCashProvidedByUsedInOperatingActivitiesAbstract', True ),
            ( 'us-gaap_OtherSignificantNoncashTransactionsTable', True ),
            ( 'us-gaap_StatementOfCashFlowsAbstract', True ),
        ]

        totalCwc = 0
        for grouping in possibleCwcGroupings:
            tree = self._createPresentationTree( grouping[0] )
            if len(tree.children(tree.root))!=0: 
                totalCwc = _getTotalCwc(grouping[1])
                if totalCwc!=0: break
            
        return totalCwc
      

    def getChangesInOperatingCapitalFromFiles(self, calculationXmlFile, xbrlFile):
        calRoot = ET.parse(calculationXmlFile).getroot()
        xbrl = joroxbrl.core.XBRL(open(xbrlFile))
        return self.getChangesInOperatingCapital(calRoot, xbrl)
      
    def getChangesInOperatingCapitalFromStrings(self, calculationXmlStr, xbrlStr=None, xbrl=None):
        if xbrl is None:
            if xbrlStr is None:
                print('Either xbrl or xbrlStr must be provided')
                return
            xbrl = joroxbrl.core.XBRL(xbrlStr) 
        calRoot = ET.fromstring(calculationXmlStr)
        return self.getChangesInOperatingCapital(calRoot, xbrl)


