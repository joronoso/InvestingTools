# Add metrics to an InsiderTrades file
import pandas as pd
from dotenv import load_dotenv
import logging
import sys
import os
import joroxbrl.secFiles
import joroxbrl.metrics
import csv

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
load_dotenv()

df = pd.read_csv(os.getenv('DATA_DIR') + 'InsiderTrades_2025-05-16.csv')
unique_ciks = df.loc[df['comment'].isna(), 'cik'].unique()
print(unique_ciks)

for cik in [str(c) for c in unique_ciks]:
    try:
        filing = joroxbrl.secFiles.Filing.getLatestFiling(cik, '10-K')
        m = joroxbrl.metrics.MetricCalculator()
        m.genMetrics(filing)
        print(filing.getFilingUrl())
        # Add AFCF and PriceToAFCF to the DataFrame for the current cik
        df.loc[df['cik'] == int(cik), 'AFCF'] = m.concepts.get('AFCF')
        df.loc[df['cik'] == int(cik), 'PriceToAFCF'] = m.metrics.get('PriceToAFCF')
    except Exception as e:
        print(f"Error processing CIK {cik}: {e}")
        
df.to_csv(os.getenv('DATA_DIR')+'InsiderTrades_prueba.csv', index=False, quoting=csv.QUOTE_NONNUMERIC)

    
