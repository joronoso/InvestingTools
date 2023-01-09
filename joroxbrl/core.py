from bs4 import BeautifulSoup
import re
import logging
import xml.etree.ElementTree as ET
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import joroxbrl.secGov


reNumber = re.compile('^(\+|-)?\d\d?\d?(\d*|(,\d{3})*)(\.\d+)?$')
reFactName = re.compile('^\{(.*)\}(.*)')
log = logging.getLogger('joroxbrl.core')


class Fact:
    
    def __init__(self, id, fullName, value, context, format, unit, scale):
        self.id = id
        self.fullName = fullName
        self.value = value
        self.context = context
        self.format = format
        self.unit = unit
        self.scale = scale
        m = reFactName.match(fullName)
        if m is None:
            self.namespace = None
            self.unqualifiedName = fullName
        else:
            self.namespace = m.group(1)
            self.unqualifiedName = m.group(2)
        
    def getDescription(self):
        return 'Fact: '+self.fullName+','+str(self.context)+','+str(self.format)+','+str(self.unit)+','+str(self.scale)+','+str(self.value)

    def getValueAsNumber(self):
        if isinstance(self.value, int) or isinstance(self.value, float):
            num = self.value
        elif self.value is None:
            num = 0
        elif reNumber.match(self.value):
            num = float(self.value.replace(',', ''))
        else:
            raise Exception('In Fact.getValueAsNumber: "' + self.value + 
                            '" can\'t be returned as a number. '+self.fullName)
        return num*10**int(self.scale) if self.scale else num
    
class Context:
    
    __slots__ = ('id', 'start', 'end', 'dimensions', 'period_db_id')
    
    # Lo inicializamos solo con esta lista, pero luego le metemos tambien el objeto period (Period)
    # Podemos meter tambien aqui start y end del periodo, no necesitamos un objeto aparte
    def __init__(self, id):
        self.dimensions = []
        self.id = id
        
class Dimension:
    __slots__ = ('namespace', 'dimension', 'value')
    
    def __init__(self, namespace, dimension, value):
        self.namespace = namespace
        self.dimension = dimension
        self.value = value

# Contains:
#        facts = []
#        contexts = {} -> key is context id
class IXBRL:

    #__slots__ = ('EntityCentralIndexKey', 'DocumentFiscalYearFocus', 'DocumentFiscalPeriodFocus', 'AmendmentFlag')

    _numerator = 0

    def _contextHandler(self, element):
        print('Entering _contextHandler for '+element['id'])
        context = Context(element['id'])
        
        for i in element.find_all('xbrldi:explicitmember'):
            spl = i.attrs['dimension'].split(':')
            if len(spl) == 2:
                context.dimensions.append(Dimension(spl[0], spl[1], i.string))
            else:
                context.dimensions.append(Dimension(None, spl[0], i.string))
                
        
        period = element.find('xbrli:period')
        if not period: 
            log.debug('Nos salimos de _contextHandler sin hacer nada para id='+element['id'])
            return
        instant = period.find('xbrli:instant')
        if instant:
            context.start = instant.string
            context.end = None
        else:
            start = period.find('xbrli:startdate')
            end = period.find('xbrli:enddate')
            if not start or not end:
                log.debug('Nos salimos de _contextHandler porque no hemos encontrado ni period ni startdate+enddate para id='+element['id'])
            else:
                context.start = start.string
                context.end = end.string

        self.contexts[context.id] = context

    def _nonFractionHandler(self, element):
        format = element['format'] if 'format' in element.attrs else None
        unit = element['unitref'] if 'unitref' in element.attrs else None
        sign = element['sign'] if 'sign' in element.attrs else ''
        scale = int(element['scale'].strip()) if 'scale' in element.attrs else None
        try:
            # This is not very good. Some documents use other prefixes, not 'xsi'.
            content = '0' if ('xsi:nil' in element.attrs and element['xsi:nil']=='true') or ('format' in element.attrs and element['format']=='ixt:fixed-zero') or element.string is None else element.string.strip()
            s_id = element['id'] if 'id' in element else 'joronid'+str(self._getNextNumerator())
            self.addFact(s_id, element['name'], sign+content, element['contextref'], format, unit, scale)
        except Exception as ex:
            log.exception(str(type(ex))+' en _nonFractionHandler con name='+element['name']+' - '+str(ex))
            raise ex
        return content

    def _getNextNumerator(self):
        self._numerator = self._numerator+1
        return self._numerator

    # El tratamiento de los nonnumerics es jodido. Hay las siguientes casuisticas:
    # - Texto
    # - HTML
    # - Otro nonnumeric
    # - Otro nunnumeric y texto adicional   
    def _nonNumericHandler(self, element):
        format = element['format'] if 'format' in element.attrs else None
        unit = element['unitref'] if 'unitref' in element.attrs else None
        
        try:
            # This is not very good. Some documents use other prefixes, not 'xsi'. I've seen include both xs: and xsi: for the same namespace
            # Let's see if this is enough. If not, it will get more complicated
            content = '' if (('xsi:nil' in element.attrs and element['xsi:nil']=='true') or 
                             ('xs:nil' in element.attrs and element['xs:nil']=='true')) else self._iterateElement(element)
            
            if not re.match('.*TextBlock', element['name']): # Todos los que sean TextBlock los ignoramos
                s_id = element['id'] if 'id' in element else 'joronid'+str(self._getNextNumerator())
                self.addFact(s_id, element['name'], content, element['contextref'], format, unit, None)
        except Exception as ex:
            log.exception(str(type(ex))+' en _nonNumericHandler con name='+element['name']+' - '+str(ex))
            raise ex

        return content
    
    # Will remove the prefix, as it gives many problems
    _handlers = { 'context': _contextHandler,
                  'nonfraction': _nonFractionHandler, 
                  'nonnumeric': _nonNumericHandler }


    def _iterateElement(self, element):
        content = ''
        for item in element:
            if str(type(item))=="<class 'bs4.element.Tag'>":
                self.tags[item.name] = True # Solo para testing
                # Remove prefix
                s = item.name.split(':')
                itemNameWoPrefix = s[1] if len(s)==2 else item.name 
                if itemNameWoPrefix in IXBRL._handlers:  
                    content = content + str(IXBRL._handlers[itemNameWoPrefix](self, item))
                else:
                    content = content + self._iterateElement(item)
            else:
                content = content+str(item)
                
        return content
        
    def __init__(self, ixbrlStr):
        self.tags = {}  # Solo para testing
        self.facts = []
        self.contexts = {}

        soup = BeautifulSoup(ixbrlStr,'html.parser')
        self._iterateElement(soup)

    # Devuelve la primera ocurrencia que encuentre, o None
    def getFact(self, factName):
        for i in self.facts:
            if i.name==factName: 
                return i
        return None
    
    # Lo importante de este metodo es que controla que no se repita un fact que ya tenemos
    def addFact(self, id, name, value, context, format, unit, scale):
        guardamos = True
        for f in self.facts:
            if f.context == context and f.fullName == name:
                if f.value==value and f.format==format and f.unit==unit and f.scale==scale:
                    log.info('No vamos a guardar el fact '+id+' porque es identico a '+f.id)
                else: 
                    # Podemos aprovechar esto para mejorar la calidad de los datos y tomar la mejor copia
                    # - Coger la version que no tenga Nones
                    # - He visto un caso en que el contenido estaba escrito en un caso como 50, y en otro como Fifty. Si alguno es parseable como número, entonces es preferible.
                    newIsNum = True if reNumber.match(value) else False
                    oldIsNum = True if reNumber.match(f.value) else False
                    if (newIsNum and not oldIsNum) or (newIsNum==oldIsNum and ((format is not None and f.format is None) or (unit is not None and f.unit is None) or (scale is not None and f.scale is None))):
                        log.warning('Sustituimos el fact '+f.id+' por  '+id+' porque es mejor: '+str(f.value)+'->'+str(value)+' | '+str(f.format)+'->'+str(format) +' | '+ str(f.unit)+'->'+str(unit)+' | '+str(f.scale)+'->'+str(scale) +' : '+str(f.value==value)+' | '+str(f.format==format)+' | '+str(f.unit==unit)+' | '+str(f.scale==scale))
                        f.id = id
                        f.value = value
                        f.format = format
                        f.unit = unit
                        f.scale = scale
                    else:
                        log.warning('Will not save fact '+id+', it\'s an imperfect copy of '+f.id+'. '+str(f.value)+'=?'+str(value)+' | '+str(f.format)+'=?'+str(format) +' | '+ str(f.unit)+'=?'+str(unit)+' | '+str(f.scale)+'=?'+str(scale) +' : '+str(f.value==value)+' | '+str(f.format==format)+' | '+str(f.unit==unit)+' | '+str(f.scale==scale))
                guardamos = False
                break
        if guardamos: 
            self.facts.append(Fact(id, name, value, context, format, unit, scale))

    def getActualGlobalFacts(self, factNameList):
        c = self.contexts[self.getFact('dei:DocumentPeriodEndDate').context]
            
        res = {}
        for factName in factNameList:
            for f in self.facts:
                p = self.contexts[f.context]
                if f.fullName==factName and len(p.dimensions)==0 and ((p.end is None and p.start==c.end) or (p.end==c.end and p.start==c.start) or (p.end==c.end and c.end==c.start)): # This last condition added to fix https://www.sec.gov/Archives/edgar/data/885275/000143774922006238/wbhc20211231e_10k_htm.xml
                    res[factName] = f
                    break
        return res
            
    def getActualGlobalFact(self, factName):
        d = self.getActualGlobalFacts([factName])
        return d[factName] if factName in d else None


class XBRL:
    
    def __init__(self):
        self.facts = []
        self.contexts = {}
        self.factCounter = 0 # Unlike iXBRL, facts don't have ids, so we'll just add a counter
        
        # In the namespaces dict we will expect to create up to 6 entries when 
        #  reading and xml: 'us-gaap', 'us-gaap-sup', 'dei', 'srt', 'invest' and 'local'
        # I don't know what invest is for. Found it for the 1st time in /Archives/edgar/data/320193/000032019317000070/aapl-20170930.xml
        self.namespaces = {}
        
    # xmlFile: pass xml file as a single string
    def readXml(self, xml):
        self.root = ET.fromstring(xml)
        self._parseXml()
        
    def readXmlFile(self, xmlFile):
        self.root = ET.parse(xmlFile).getroot()
        self._parseXml()
        
    def readXmlUrl(self, xmlUrl):
        xml = joroxbrl.secGov.SecGovCaller.callSecGovUrl(xmlUrl).text
        self.readXml(xml)
    
    # Will parse the xml in self.root
    def _parseXml(self):
        namespaces = set()
        # Start with the contexts
        for element in self.root:
            m = reFactName.match(element.tag)
            unqualifiedTag = None
            if m is None or len(m.groups())!=2: 
                print('Groups es '+m.groups)
                unqualifiedTag = element.tag
            else: unqualifiedTag = m.group(2)
            if unqualifiedTag == 'context':
                self._contextHandler(element)
            elif unqualifiedTag in ['schemaRef', 'unit', 'footnoteLink']:
                continue
            else:
                # All the rest should be facts
                f = self._factHandler(element)
                namespaces.add(f.namespace)
        log.debug('These are the namespaces we\'ve found: '+str(namespaces))
        
        # Now we try to identify the namespaces
        if len(namespaces)>6: 
            raise Exception('More than 6 namespaces found in XBRL facts: '+str(namespaces))
        for n in namespaces:
            if n is None:
                if 'local' in self.namespaces:
                    raise Exception('There\'s more than one local namespace: '+str(namespaces))
                else:
                    self.namespaces['local'] = None
            elif '/us-gaap/' in n:
                if 'us-gaap' in self.namespaces:
                    raise Exception('There\'s more than one us-gaap namespace: '+str(namespaces))
                else:
                    self.namespaces['us-gaap'] = n
            elif '/us-gaap-sup/' in n:
                if 'us-gaap-sup' in self.namespaces:
                    raise Exception('There\'s more than one us-gaap-sup namespace: '+str(namespaces))
                else:
                    self.namespaces['us-gaap-sup'] = n
            elif '/dei/' in n:
                if 'dei' in self.namespaces:
                    raise Exception('There\'s more than one dei namespace: '+str(namespaces))
                else:
                    self.namespaces['dei'] = n
            elif '/srt/' in n:
                if 'srt' in self.namespaces:
                    raise Exception('There\'s more than one srt namespace: '+str(namespaces))
                else:
                    self.namespaces['srt'] = n
                    
            elif '/invest' in n:
                if 'invest' in self.namespaces:
                    raise Exception('There\'s more than one invest namespace: '+str(namespaces))
                else:
                    self.namespaces['invest'] = n
            else:
                if 'local' in self.namespaces:
                    raise Exception('There\'s more than one local namespace: '+str(namespaces))
                else:
                    self.namespaces['local'] = n
            
        
    def _contextHandler(self, cont):
        if '{http://www.xbrl.org/2003/instance}id' in cont.attrib:
            id = cont.attrib['{http://www.xbrl.org/2003/instance}id']
        else:
            id = cont.attrib['id']
        context = Context(id)

        for explicitMember in cont.iter('{http://xbrl.org/2006/xbrldi}explicitMember'):
            spl = explicitMember.attrib['dimension'].split(':')
            if len(spl) == 2:
                context.dimensions.append(Dimension(spl[0], spl[1], explicitMember.text))
            else:
                context.dimensions.append(Dimension(None, spl[0], explicitMember.text))
            
        period = cont.find('{http://www.xbrl.org/2003/instance}period')
        if not period: 
            log.warning('Exiting XBRL._parseXml doing nothing for context id='+id)
            return

        instant = period.find('{http://www.xbrl.org/2003/instance}instant')
        if instant is not None:
            context.start = instant.text
            context.end = None
        else:
            start = period.find('{http://www.xbrl.org/2003/instance}startDate')
            end = period.find('{http://www.xbrl.org/2003/instance}endDate')
                
            if start is None or end is None:
                log.warning('Exiting XBRL._parseXml because we haven\'t found instant nor startdate+enddate for context id='+id)
            else:
                context.start = start.text
                context.end = end.text
        self.contexts[id] = context
        #log.debug('Context '+id+'; start='+str(context.start)+'; end='+str(context.end))
        
    def _factHandler(self, fact):
        # It doesn't look like facts can contain other facts or anything, so we will just go ahead and create
        #log.debug('Fact ('+str(len(list(fact)))+'): '+fact.tag)
        
        f = Fact(self.factCounter,
                 fact.tag,
                 fact.text.strip() if fact.text is not None else None,
                 fact.get('contextRef'),
                 None, # There seems to be no format attribute in XBRL
                 fact.get('unitRef'),
                 fact.get('scale', '0'))
     
        self.facts.append(f)
        self.factCounter = self.factCounter + 1
        return f
    
    def getActualGlobalFacts(self, factNameList):
    # We accept fact name as both full and unquialified names
        c = self.contexts[self.getFact('{'+self.namespaces['dei']+'}DocumentPeriodEndDate').context]
            
        res = {}
        res2 = {} # The ones with dimensions, because I'm not 100% sure we want them
        for factName in factNameList:
            for f in self.facts:
                p = self.contexts[f.context]
                if (f.fullName==factName or f.unqualifiedName==factName) and ((p.end is None and p.start==c.end) or (p.end==c.end and p.start==c.start) or (p.end==c.end and c.end==c.start) or (p.end is None and p.start==c.end and c.end==c.start)):  # Last 2 conditions added to fix https://www.sec.gov/Archives/edgar/data/885275/000143774922006238/wbhc20211231e_10k_htm.xml
                    if (len(p.dimensions)==0): # This is the perfect scenario, with 100% certainty
                        res[factName] = f
                        break
                    # Weird cases in which the main context also has a dimension
                    elif (len(p.dimensions)==1 
                          and 'LegalEntityAxis' in p.dimensions[0].dimension
                          and 'TotalCompanyDomain' in p.dimensions[0].value):
                        res2[factName] = f

        # Now we consolidate what's in res2 into res
        for r in res2.keys():
            if r not in res:
                res[r] = res2[r]

        return res
            
    def getActualGlobalFact(self, factName):
        d = self.getActualGlobalFacts([factName])
        return d[factName] if factName in d else None

    # Returns first occurrence found, or None
    def getFact(self, factName):
        for i in self.facts:
            if i.fullName==factName or i.unqualifiedName==factName: 
                return i
        return None

