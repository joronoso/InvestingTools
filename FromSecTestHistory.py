# This will generate the metrics for a specific 10-K of a single company.
# Useful for debugging problems extracting a single filing.
import joroxbrl.secGov
import joroxbrl.secFiles
import joroxbrl.core
import joroxbrl.metrics
import logging
logging.basicConfig(level=logging.DEBUG) 

filing = joroxbrl.secFiles.Filing.getFilingByAccession('0001126956', '0001564590-20-054448')
m = joroxbrl.metrics.MetricCalculator()
m.genMetricsAfterFiling(filing)
print(filing.getFilingUrl())
print('CONCEPTS:')
for i in m.concepts.items():
    print(i[0]+': '+str(i[1]))
print('METRICS:')
for i in m.metrics.items():
    print(i[0]+': '+str(i[1]))
    

