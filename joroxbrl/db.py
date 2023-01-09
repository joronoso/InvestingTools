import sqlite3
from joroxbrl.core import Fact

_db_file = 'xbrl1.db'

class IXBRL_sqlite_writer:

    _getPeriodId = 'select id from xbrl_period_instant where start_date=? and end_date=?'    
    _getInstantId = 'select id from xbrl_period_instant where start_date=? and end_date is NULL'    
    _insertPeriodInstant = 'insert into xbrl_period_instant (start_date, end_date) values (?,?)'
    _getCompanyId = 'select id from xbrl_company where sec_id=?'
    _insertCompany = 'insert into xbrl_company (sec_id, name, ticker) values (?,?,?)'
    _insertDocument = 'insert into xbrl_document (company_id, doctype, year, period) values (?,?,?,?)'
    _insertFact = ('insert into xbrl_fact '
                   '(company_id, document_id, namespace, name, '
                   'period_instant_id, unit, scale, format, value) '
                   'values (?,?,?,?,?,?,?,?,?)')
    _insertDimension = 'insert into xbrl_dimension (fact_id, dim_namespace, dimension, value) values (?,?,?,?)'

    

    @staticmethod
    def writeIXBRL(ixbrl):
        
        # Nos conectamos a la base de datos
        conn = sqlite3.connect(_db_file)
        c = conn.cursor()
        
        # Siguiente, la empresa. Si existe la buscamos, y si no la creamos
        sec_id = ixbrl.getFact('dei:EntityCentralIndexKey').value
        c.execute(IXBRL_sqlite_writer._getCompanyId, (sec_id,))
        company_id = c.fetchone()
        if not company_id: # Lo creamos
            c.execute(IXBRL_sqlite_writer._insertCompany, 
                      (sec_id, 
                       ixbrl.getFact('dei:EntityRegistrantName').value, 
                       ixbrl.getFact('dei:TradingSymbol').value))
            company_id = c.lastrowid
        else: company_id = company_id[0]
        
        # Insertamos el documento
        c.execute(IXBRL_sqlite_writer._insertDocument, 
                  (company_id, 
                   ixbrl.getFact('dei:DocumentType').value,
                   ixbrl.getFact('dei:DocumentFiscalYearFocus').value,
                   ixbrl.getFact('dei:DocumentFiscalPeriodFocus').value))
        doc_id = c.lastrowid
        
        # Ahora enchufamos todos los facts a la base de datos!
        for fact in ixbrl.facts:
            # Empezamos por identificar o guardar el periodo
            context = ixbrl.contexts[fact.context]
            if not hasattr(context, 'period_db_id'):
                if context.end: 
                    c.execute(IXBRL_sqlite_writer._getPeriodId, 
                              (context.start, context.end))
                else: 
                    c.execute(IXBRL_sqlite_writer._getInstantId, 
                              (context.start, ))
                pid = c.fetchone()
                if pid: 
                    context.period_db_id = pid[0]
                else: 
                    c.execute(IXBRL_sqlite_writer._insertPeriodInstant, 
                              (context.start, context.end))
                    context.period_db_id = c.lastrowid
            
            # Ahora guardamos el fact
            namesplit = fact.name.split(':')
            c.execute(IXBRL_sqlite_writer._insertFact, 
                      (company_id, doc_id, namesplit[0], namesplit[1], 
                       context.period_db_id, fact.unit, 
                       fact.scale, fact.format, fact.value))
            
            # Por ultimo, guardamos las dimensiones asociadas al fact
            fact_id = c.lastrowid
            for dim in context.dimensions:
                c.execute(IXBRL_sqlite_writer._insertDimension,
                          (fact_id, dim.namespace, dim.dimension, dim.value))
            
        
        conn.commit()
        c.close()
        conn.close()



class IXBRL_sqlite_reader:

    _getFactsActualGlobal1 =("select f.id, f.namespace, f.name, f.value, "
                             "f.period_instant_id, f.format, f.unit, f.scale "
                             "from xbrl_fact f left join xbrl_dimension d "
                                 "on d.fact_id=f.id "
                             "where f.document_id=? and d.fact_id is null "
                             "and f.period_instant_id in (?,?) "
                             "and ( (f.namespace=? and f.name=?) ")
    _getFactsActualGlobal2 = ("or (f.namespace=? and f.name=?) ")
    _getFactsActualGlobal3 = ")"
    
    _getMainDocPeriod = ("select p.id, p.start_date, p.end_date "
                         "from xbrl_fact f join xbrl_period_instant p "
                         "on f.period_instant_id=p.id "
                         "where f.namespace='dei' and f.name='DocumentPeriodEndDate'")
    
    _getEndOfPeriodInstant = ("select id from xbrl_period_instant "
                              "WHERE start_date=? and end_date is null")
    
    # Actual means we are only getting the facts for the last period
    # Global means we're only getting facts that apply to the whole company
    # For example, Revenue can refer to 2021, 2020 or 2019, and also to specific segments. 
    # This method will only retrieve those of 2021 for the whole company
    @staticmethod
    def getFactsActualGlobal(document_id, facts):
        conn = sqlite3.connect(_db_file)
        c = conn.cursor()
        
        # First obtain the main period of the document
        c.execute(IXBRL_sqlite_reader._getMainDocPeriod)
        res = c.fetchone()
        period_id = res[0]
        #period_start = res[1] # Finally, we are not using this
        period_end = res[2]
        
        # Now, the id of the instant at the end of the main period
        c.execute(IXBRL_sqlite_reader._getEndOfPeriodInstant, (period_end, ))
        res = c.fetchone()
        end_instant_id = res[0]
        
        # We are now ready to retrieve the facts
        q = IXBRL_sqlite_reader._getFactsActualGlobal1 \
            + (len(facts)-1)*IXBRL_sqlite_reader._getFactsActualGlobal2 \
            + IXBRL_sqlite_reader._getFactsActualGlobal3
        q_params = [document_id, period_id, end_instant_id]
        for f in facts:
            q_params.extend(f.split(':'))
        c.execute(q, q_params)
        result = {}
        # id, name, value, context, format, unit, scale
        for i in c.fetchall():
            # We will return the period_id in place of context. 
            # This smells a little weird, but I'm not sure at this point if we 
            #  really need to complicate it more for what we are trying to do
            result[i[1]+':'+i[2]] = Fact(i[0], i[1]+':'+i[2], i[3], i[4], i[5], i[6], i[7])
        
        c.close()
        conn.close()
        
        return result
        