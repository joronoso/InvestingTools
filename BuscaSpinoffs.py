import time
from bs4 import BeautifulSoup
import re
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

base_url = 'https://www.sec.gov/cgi-bin/current?q2=0&q3=10&q1='
re_linea = re.compile(r'(\d\d-\d\d-\d\d\d\d)\s+<a href="(.*?)">(.*?)</a>\s*<a href="(.*?)">(.*?)</a>\s*(.*)')

session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)



for i in range(20):
    time.sleep(.1) # La SEC se enfada si llamamos más de 10 veces por segundo
    print(f"Vamos a buscar en {base_url+str(i)}")
    page_content = session.get(base_url+str(i), headers={
            "User-agent": "JoroBot joronoso@joronoso.net",
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov",
        }).text 
   
    soup = BeautifulSoup(page_content, features='html.parser')
    chorizo = str(soup.find('pre'))
    for line in re.split('<hr/>', chorizo)[1].splitlines():
        grupetos = re_linea.match(line).groups()
        if grupetos[2]=='10-12B/A': print(grupetos)

