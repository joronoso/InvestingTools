import pandas as pd
import requests
import datetime

# CONSTANTS
daysBack = 5
baseUrl = 'https://data.sec.gov/submissions/'

today = datetime.date.today()
backDate = today - datetime.timedelta(days=daysBack)
print('backDate='+str(backDate))

following = pd.read_csv('following.csv', dtype={'CIK':str})
dataf = pd.DataFrame(columns=['cik', 'name', 'date', 'url', 'form'])

for cik in following['CIK']:
    url = baseUrl+'CIK'+'0'*(10-len(cik))+cik+'.json'
    print(cik+': '+url)
    r = requests.get(url, headers={'User-agent': 'Mozilla/5.0'})
    print(cik+': '+str(r.status_code))
    js = r.json()
    r.close()

    for i in range(0, len(js['filings']['recent']['filingDate'])):
        d = js['filings']['recent']['filingDate'][i]
        if datetime.datetime.strptime(d, '%Y-%m-%d').date()>=backDate:
            print('Vamos a meter uno: '+js['filings']['recent']['filingDate'][i])
            dataf = dataf.append({'cik': cik,
                                  'name': js['name'],
                                  'date': d,
                                  'form': js['filings']['recent']['form'][i],
                                  'url': 'https://www.sec.gov/Archives/edgar/data/'+'0'*(10-len(cik))+cik+'/'+js['filings']['recent']['accessionNumber'][i].replace('-', '')+'/'+js['filings']['recent']['primaryDocument'][i]}, ignore_index=True )
                          
month = str(today.month) if today.month>9 else '0'+str(today.month)
day = str(today.day) if today.day>9 else '0'+str(today.day)

dataf.to_csv('FollowingUpdate_'+str(today.year)+'-'+month+'-'+day+'.csv', index=False)