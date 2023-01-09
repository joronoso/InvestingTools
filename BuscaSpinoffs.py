from selenium import webdriver
from bs4 import BeautifulSoup
import re

base_url = 'https://www.sec.gov/cgi-bin/current?q2=0&q3=10&q1='
re_linea = re.compile('(\d\d-\d\d-\d\d\d\d)\s+<a href="(.*?)">(.*?)</a>\s*<a href="(.*?)">(.*?)</a>\s*(.*)')

driver = webdriver.Firefox()
for i in range(25):
    print(f"Vamos a buscar en {base_url+str(i)}")
    driver.get(base_url+str(i))
    page_content = driver.page_source
   
    soup = BeautifulSoup(page_content, features='html.parser')
    chorizo = str(soup.find('pre'))
    for line in re.split('<hr/>', chorizo)[1].splitlines():
        grupetos = re_linea.match(line).groups()
        if grupetos[2]=='10-12B/A': print(grupetos)

driver.close()