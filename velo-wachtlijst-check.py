# Selenium is nodig omdat de website javascript gebruikt, anders was urllib voldoende...
from selenium import webdriver
from collections import deque
from imapclient import IMAPClient
import matplotlib.pyplot as plt
import matplotlib.dates as dts
import datetime
import time
import csv
import os
import getpass

url = 'https://www.velo-antwerpen.be/nl/registreren/wachtlijst-positie'
email =  'name@something.com'
imapadres = 'imap.something.com'
paswd = ''
datapath = "data.csv"
plotpath = "plot.png"

def deleteEmails(delay = 3, maxIter = 10):
	""" Verwijdert de automatisch gegenereerde e-mail(s) """
	try:
		# Inloggen via IMAP
		print('// Inloggen bij '+imapadres)
		paswd = getpass.getpass(prompt="Wachtwoord voor "+email+":")
		imapObj = IMAPClient(imapadres, ssl=True)
		imapObj.login(email, paswd)
		# E-mail verwijderen
		print('// Verwijderen van de e-mail(s)')
		print('// {} seconden wachten'.format(delay))
		time.sleep(delay)
		imapObj.select_folder('Inbox')
		iter = 0
		while iter < maxIter:
			UID = imapObj.search(criteria=[u'UNSEEN', u'SUBJECT', u'Positie op wachtlijst raadplegen', u'FROM', u'registratie@velo-antwerpen.be'])
			if len(UID)>0:
				imapObj.delete_messages(UID)
				imapObj.expunge()
				iter = maxIter+1
				print('// E-mail(s) zijn verwijderd')
			else:
				print('// {} seconden wachten...'.format(delay))
				iter = iter+1
				time.sleep(delay)
		# Uitloggen bij IMAP
		imapObj.logout()
	except:
		print("Oeps, foutje bij het adutomatisch verwijderen van de e-mail.")

def getRank():
	""" Methode om je huidige rangschikking op de Velo wachtlijst op te halen. """
	try:
		# Gebruiken Selenium omdat de website javascript gebruikt.
		# PantomJS toont geen venster,
		browser = webdriver.PhantomJS(service_log_path=os.path.devnull)
		# Formulier invullen
		print('// Formulier aan het invullen')
		browser.get(url)
		elem = browser.find_element_by_name('CustEmail') # Find the e-mailaddres box
		elem.send_keys(email)
		button = browser.find_element_by_xpath("//input[@value='Bekijk']") # Find the submit button
		button.click()
		source = browser.page_source
		# PhantomJS afsluiten
		browser.close()
	except:
		print("Oeps, fout bij het ophalen van je rangnummer.")

	try:
		# Positie op de wachtlijst terugvinden in de HTML
		print('// Positie op wachtlijst halen uit HTML')
		searchstring = 'Je huidige positie op de wachtlijst is'
		startInd = source.find(searchstring)
		endInd = source.find('.', startInd)
		num = source[startInd+len(searchstring)+1:endInd]
		num = int(num) # Parse to integer
		# E-mails verwijderen
		deleteEmails()
		return num
	except:
		print('Oeps, foutje bij zoeken naar nummer in HTML.')

def writeToFile(date, rank, file=datapath):
	"""" Methode die een regel wegschrijft naar de csv-file datapath """
	try:
		# Data wegschrijven naar datapath
		csvfileWrite = open(datapath, 'a')
		writer = csv.writer(csvfileWrite, delimiter = ",")
		writer.writerow([date, rank])
		print('// Data weggeschreven naar '+datapath)
	except IndexError:  # empty file
		print('// Eerste keer laten lopen...')
		writer = csv.wdriter(csvfile, delimiter = ",")
		writer.writerow([date, rank])
		print('// Data weggeschreven naar '+datapath)
	except:
		print("Oeps, foutje bij wegschrijven van de data.")

def plotEvolution(dates, ranks, file=plotpath):
	""" Methode om een plot te maken van de evolutie """
	try:
		fig = plt.figure()
		ax = fig.add_subplot(111)
		ax.plot_date(dates, ranks, '.-')
		ax.set_ylim(0, 15000)
		ax.set_xlabel('Datum')
		ax.set_ylabel('Positie op wachtlijst')
		ax.fmt_xdata = dts.DateFormatter('%d-%m-%Y')
		# Data in plot beter weergeven
		fig.autofmt_xdate()
		# Plot opslaan
		fig.savefig(plotpath, bbox_inches='tight')
		print('// Dataplot opgeslagen als '+plotpath)
	except:
		print('Oeps, foutje tijdens het plotten.')

def addDataPoint(dates, ranks, plotfile = 'img.png', datafile = 'data.csv'):
	writeToFile(dates[-1], ranks[-1], file=plotfile)
	plotEvolution(dates, ranks, file=datafile)

def determineNumberOfDays(dates, ranks):
	""" Methode om het aantal dagen dat de ranking gelijk is te bepalen. """
	k = len(ranks)
	ind = k-1
	for i in range(k-2, -1, -1):
		if (ranks[i] == ranks[-1]):
			ind = i
		elif (ranks[i] > ranks[-1]):
			break
	n = (dates[-1]-dates[ind]).days
	return n

print('{:*^40}'.format(''))
print('{:*^40}'.format(" Velo-wachtlijst-check "))
print('{:*^40}'.format(''))
print('Automatische check van de plaats op de wachtlijst van '+email)

# Initialising the used arrays
dates = []
ranks = []
# Reading current data
try:
	if os.path.isfile(datapath):
		csvfile = open(datapath)
		csvreader = csv.reader(csvfile)
		for row in csvreader:
			dates.append(datetime.datetime.strptime(row[0],'%Y-%m-%d').date())
			ranks.append(int(row[1]))
		csvfile.close()
	else:
		# Initialiseren van de file als deze nog niet bestaat
		open(datapath, 'a').close()
except:
	print('Oeps, fout bij openen of initialiseren van '+datapath)

# Adding a data point if necessary
currentDate = datetime.datetime.now().date()
currentRank = getRank()

if len(dates)>0:
	if (currentDate==dates[-1])and(ranks[-1]==currentRank):
		print('Vandaag ({}) al laten lopen, je bent nog steeds {}e..'.format(currentDate,currentRank))
	else:
		# Add data points
		dates.append(currentDate)
		ranks.append(currentRank)
		addDataPoint(dates, ranks, plotfile = plotpath, datafile = datapath)
		# Print to console
		if (currentDate==dates[-2]):
			print('Je was vandaag ({}) eerst {}e, maar nu be je {}e.'.format(currentDate,ranks[-2], currentRank))
		else:
			n = determineNumberOfDays(dates, ranks)
			if (n == 0):
				print('Vandaag ({}) ben je {}e, je bent dus {} plaatsen gestegen.'.format(currentDate, currentRank, ranks[-2]-currentRank))
			elif (n == 1):
				print('Vandaag ({}) ben je {}e, net als gisteren.'.format(currentDate, currentRank, n))
			else:
				print('Vandaag ({}) ben je {}e, net als de vorige {} dagen.'.format(currentDate, currentRank, n))
else:
	dates.append(currentDate)
	ranks.append(currentRank)
	addDataPoint(dates, ranks, plotfile = plotpath, datafile = datapath)
	print('Eerste maal laten lopen, vandaag ({}) ben je {}e.'.format(currentDate, currentRank))
