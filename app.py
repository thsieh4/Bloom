# TODO: add preview table
# TODO: check if a given excel is valid or not
# TODO: remove pandas if possible to reduce app size

import re
import os
import datetime
import urllib.request
import numpy as np
import pandas as pd
from appJar import gui

# initialize
ZWSID = ""
app = gui("Venus Flytrap")

# define functions and events
def zillow(row, ZWSID):
	""" func for query house price given ZWSID """
    
    # query url
	url = 'http://www.zillow.com/webservice/GetSearchResults.htm?zws-id=' + \
		ZWSID + '&address=' + '+'.join(row.address1.split(" ")) + \
		'&citystatezip=' + row.zipcode
	
	# regular expression
	PATTERN = ['<code>.*</code>', '<zpid>.*</zpid>', '<city>.*</city>',
				'<state>.*</state>', '<latitude>.*</latitude>',
				'<longitude>.*</longitude>',
				'<amount currency="USD">.*</amount>',
				'<low currency="USD">.*</low>',
				'<high currency="USD">.*</high>',
				'<last-updated>.*</last-updated>']

	# start query
	with urllib.request.urlopen(url) as response:

		content = response.read().decode(response.headers.get_content_charset())

		data = []
		for i in range(len(PATTERN)):
			obs = re.findall(PATTERN[i], content)
			obs = re.findall('>.*<', obs[0])[0][1:-1]
			if i == 0:
				if obs == '0':
					data.append(obs)

				# special case: ZWSID is invalid
				elif obs == '2':
					app.infoBox("Error", "Invalid or missing ZWSID parameter")
					break

				# special case: no house price info
				else:
					data = [obs]
					data.extend([np.nan for i in range(len(PATTERN)-1)])
					break
			else:
				data.append(obs)

	return pd.Series(data)


def get_ZWSID(x):
	""" func for getting the ZWSID from user input """

	global ZWSID
	ZWSID = app.getEntry(x)


def get_file(excel_file):
	""" func for reading the excel_file, querying the house price """

	# set msg to empty everytime when reading the file
	# app.setLabel("msg1", "")

	# read excel file
	file_path = app.getEntry(excel_file)
	df = pd.ExcelFile(file_path).parse(0)
	df = df.rename( columns={
		"ShipStation Order Detail": "base_info", 
		"Unnamed: 1": "prds",
		"Unnamed: 3": "record",
		"Unnamed: 4": "date", 
		"Unnamed: 7": "unit_price", 
		"Unnamed: 9": "qty"})

	# MAIN CODE:
	mask = df.prds.notnull().fillna(False)
	prds_list = df.prds[mask].values[::-1]
	pri_list = df.unit_price[mask].values[::-1]
	qty_list = df.qty[mask].values[::-1]

	# initialize
	prds, qty, unit_pri, total_pri = [], [], [], []
	temp_prds, temp_pri, temp_qty = [], [], []

	# extract info 1
	for i in range(prds_list.shape[0]):

	    if prds_list[i] != 'Item ID':
	        temp_prds.append(prds_list[i])
	        temp_pri.append(pri_list[i])
	        temp_qty.append(qty_list[i])
	             
	    else:
	        prds.append(temp_prds)
	        unit_pri.append(temp_pri)
	        qty.append(temp_qty)
	        total_pri.append((np.array(temp_pri)*np.array(temp_qty)).sum())
	        
	        temp_prds, temp_pri, temp_qty = [], [], []
	
	# reverse for simple cleaning
	prds, unit_pri, qty = prds[::-1], unit_pri[::-1], qty[::-1]
	total_pri = total_pri[::-1]

	# extract info 2
	mask = df.record.str.contains('Date Paid:').fillna(False).values

	# build df
	customer = pd.DataFrame({"name": df[mask].base_info.values, 
		"address1": df[np.roll(mask, 1)].base_info.values, 
		"address2": df[np.roll(mask, 4)].base_info.str.replace(",", ""), 
		"date_paid": df[mask].date.values, 
		"amt_paid": df[np.roll(mask, 2)].date.values, 
		"record_no": df[np.roll(mask, 5)].date.values, 
		"product": ['+'.join(i) for i in prds], 
		"unit_price": ['+'.join(map(str, i)) for i in unit_pri],
		"qty": ['+'.join(map(str, i)) for i in qty],
		"total_price": [round(i, 2) for i in total_pri]})

	# extract info 3: zipcode
	customer['zipcode'] = customer.address2.str.extract('(\d{5})', expand=False)

	# save file if no ZWSID provided
	if ZWSID == "":
		
		file_name = os.getcwd() + '/customer_info_' + \
					datetime.date.today().strftime("%Y%m%d")
		customer.to_csv(file_name + '.csv', index=False)

		app.infoBox("Success", "Customer info file has been extracted")
	
	# query the house price if ZWSID provided
	else:

		# column names
		col = ['z_errorcode', 'zpid', 'z_city', 'z_state', 'z_lat', 'z_lon',
				'z_price', 'z_lowprice', 'z_highprice', 'z_last_updated']

		customer_sub = customer.iloc[:2,]	# debug

		# get house price
		temp = customer_sub.apply(lambda row: zillow(row, ZWSID), axis=1)
		temp.columns = col

		# merge data
		df = pd.concat([customer_sub, temp], axis=1)
		df = df[['z_lon', 'z_lat', 'address1', 'address2', 'amt_paid', 
			'date_paid', 'name', 'product', 'qty', 'record_no', 'total_price', 
			'unit_price', 'zipcode', 'z_errorcode', 'zpid', 'z_city', 'z_state',
			'z_price', 'z_lowprice', 'z_highprice', 'z_last_updated']]

		# save file
		file_name = os.getcwd() + '/customer_info_houseprice_' + \
					datetime.date.today().strftime("%Y%m%d")
		df.to_csv(file_name + '.csv', index=False)

		app.infoBox("Success", "Customer info file has been extracted")

# style
app.setFont(size=25, family="Courier", weight="bold")
app.setBg("lightgreen")

# layout: ZWSID input
app.addLabelEntry("ZWSID")
app.setEntryChangeFunction("ZWSID", get_ZWSID)
# app.addHorizontalSeparator()

# layout: read file
app.addFileEntry("f1")
app.setEntryChangeFunction("f1", get_file)
# app.addHorizontalSeparator()

# layout: show successful / error msg
# app.addLabel("msg1", "")
# app.setResizable(False)

app.go()
