# This will generate the metrics for the last 10-K of a single company.
# Useful for debugging problems extracting a single filing.
import joroxbrl.secFiles
import joroxbrl.metrics
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)
load_dotenv()

filing = joroxbrl.secFiles.Filing.getLatestFiling('1013934', '10-K')
m = joroxbrl.metrics.MetricCalculator()
m.genMetrics(filing)
print(filing.getFilingUrl())
print('CONCEPTS:')
for i in m.concepts.items():
    print(i[0]+': '+str(i[1]))
print('METRICS:')
for i in m.metrics.items():
    print(i[0]+': '+str(i[1]))
    

