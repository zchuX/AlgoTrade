import urllib.request as urllib2

def internet_on():
	try:
		urllib2.urlopen('https://www.google.com', timeout=1)
		return True
	except Exception as e:
		print(e)
		return False


import time
from datetime import datetime

while True:
	print(datetime.now())
	if not internet_on():
		print("XXXXXXXXXXX")
	time.sleep(30)