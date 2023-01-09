import sqlite3
import pandas as pd
import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt 

_db_file = 'xbrl1.db'


# qSelect = '''select ROE, ROA, ROCE, OperatingMargin, InterestCoverageRatio, 
#                 DebtToEquity, market_cap, PriceToAFCF  
#             from data_10k dk 
#             where cik in (
#              	select cik from company_details cd where exclude is null
#             )
#             and market_cap !=0
#             and ROE is not null and ROA is not null and ROCE is not null 
#             and OperatingMargin is not null and InterestCoverageRatio is not null 
#             and DebtToEquity is not null and PriceToAFCF is not null'''

qSelect = '''select * --ROE, ROA, ROCE, OperatingMargin, InterestCoverageRatio, 
                -- DebtToEquity, market_cap, PriceToAFCF  
            from data_10k dk 
            where cik in (
             	select cik from company_details cd where exclude is null
                --and sic='2834'
            )
            and market_cap !=0
            and ROE is not null and ROA is not null and ROCE is not null 
            and OperatingMargin is not null --and InterestCoverageRatio is not null 
            and DebtToEquity is not null 
            and PriceToAFCF is not null'''

conn = sqlite3.connect(_db_file)
sql_query = pd.read_sql_query (qSelect, conn)
df_orig = pd.DataFrame(sql_query) #, columns = ['product_id', 'product_name', 'price'])
conn.close()


# A couple adjustments
df = df_orig[['ROE', 'ROA', 'ROCE', 'OperatingMargin', 'InterestCoverageRatio','DebtToEquity', 'market_cap', 'PriceToAFCF']].copy()
df.loc[df['InterestCoverageRatio'].isnull(), 'InterestCoverageRatio'] = 1000
df.loc[df['PriceToAFCF']>150, 'PriceToAFCF'] = 150


# Classify by size:
sizes = [ ('Micro', 0, 300e6),
          ('Small', 300e6, 2e9),
          ('Mid', 2e9, 10e9),
          ('Large', 10e9, 1e20) ]

for s in sizes:
    df[s[0]] = ((df['market_cap']>=s[1]) & (df['market_cap']<s[2])).replace({True: 1, False: 0})

df.drop('market_cap', axis=1, inplace=True)  
df_y = df['PriceToAFCF']
df.drop('PriceToAFCF', axis=1, inplace=True)  


X = torch.tensor(df.values).float()
y = torch.tensor(df_y.values).reshape(-1, 1)
y2 = 1/y # AFCF/P seems like a more stable value

# --------------------------------------------
# # TEST
# X_np = np.random.rand(1000,10)
# y2_np = np.zeros((1000,1))

# for i in range(1000):
#     y2_np[i] = (3*X_np[i][0]**3 + np.sin(X_np[i][1]) + np.tanh(X_np[i][2]) + 67*X_np[i][3]**2
#             + 3*X_np[i][4]**3 + np.sin(X_np[i][5]) + np.tanh(X_np[i][6]) + 67*X_np[i][7]**2
#             + 6*X_np[i][8]**3 + 50*np.sin(X_np[i][9]) )

# X = torch.tensor(X_np).float()
# y2 = torch.tensor(y2_np).float()
# --------------------------------------------


model = nn.Sequential(
            nn.Linear(10, 8),
            nn.CELU(),
            nn.Linear(8,6),
            nn.RReLU(),
            nn.Linear(6,4),
            nn.Mish(),
            nn.Linear(4,1) 
            # nn.Linear(10, 5),
            # nn.Mish(),
            # nn.Linear(5,1) 
            )
optimizer = torch.optim.Adam(model.parameters())
loss_fn = nn.L1Loss()

y_calc = model(X)
loss = loss_fn(y_calc, y2)
loss_history = []
print('Initial loss: '+str(loss))
for epoch in range(3000):
    if epoch%100==0: 
        #print('Epoch: '+str(epoch))
        loss_history.append(loss.item())
        
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    y_calc = model(X)
    loss = loss_fn(y_calc, y2)

loss_history.append(loss.item())
print('Final loss: '+str(loss.item()))
plt.plot(loss_history)
plt.title('CELU-RReLU-Mish - '+str(loss.item()))

y2 = 1/y_calc
df_orig['PriceToAFCFCalc'] = y2.detach().numpy()
df_orig['dif'] = df_orig['PriceToAFCFCalc'] - df_orig['PriceToAFCF']
df_orig.to_csv('PriceToAFCFCalc.csv',  index=False)
df_filt=df_orig.loc[(df_orig['PriceToAFCF']>0) & (df_orig['PriceToAFCFCalc']>0) &
                    (df_orig['PriceToAFCF']<15) & (df_orig['end_period_date']>'2021-07-31')]
df_filt.to_csv('PriceToAFCFCalc_filt.csv',  index=False)
