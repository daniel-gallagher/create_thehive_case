#!/usr/bin/env python

# most of the code here was based on the following example on splunk custom alert actions
# http://docs.splunk.com/Documentation/Splunk/6.5.3/AdvancedDev/ModAlertsAdvancedExample

import os
import sys
import json
import gzip
import csv
import requests
import uuid
from requests.auth import HTTPBasicAuth

def create_case(config, row):

	# Filter empty multivalue fields
	row = {key: value for key, value in row.iteritems() if not key.startswith("__mv_")}

	# Take KV pairs and make a list-type of dicts
	artifacts = []
	for key, value in row.iteritems():
		artifacts.append(dict(
			dataType = key,
			data = value,
			message = "%s observed in this Splunk alert" % key
		))

	# Get the payload for the case from the config, use defaults if they are not specified
	case_payload = json.dumps(dict(
		title = config.get('title'),
		description = config.get('description', "No description provided."),
		severity = int(config.get('severity', 1)),
		owner = config.get('owner'),
		tlp = int(config.get('tlp', 2)),
		tags = [] if config.get('tags') is None else config.get('tags').split(",") # capable of continuing if Tags is empty and avoids split failing on empty list
	))
	send_message(case_payload)

def send_message(payload):

	url = config.get('url') # Get TheHive URL from Splunk configuration
	username = config.get('username') # Get TheHive username from Splunk configuration
	password = config.get('password') # Get TheHive password from Splunk configuration
	auth = requests.auth.HTTPBasicAuth(username=username,password=password) # Generate basic auth key

	try:
		print >> sys.stderr, 'INFO Calling url="%s" with payload=%s' % (url, payload)

		headers = {'Content-type': 'application/json'} # set proper headers
		response = requests.post(url, headers=headers, data=payload, auth=auth, verify=False) # POST case to TheHive API

		print >> sys.stderr, "INFO TheHive server responded with HTTP status %s" % response.status_code
		response.raise_for_status() # check if status is anything other than 200; throw an exception if it is
		print >> sys.stderr, "INFO TheHive server response: %s" % response.json() # response is 200 by this point or we would have thrown an exception
	except requests.exceptions.HTTPError as e: # somehow we got a bad response code from thehive
		print >> sys.stderr, "ERROR TheHive server returned following error: %s" % e
	except requests.exceptions.RequestException as e: # some other request error occurred
		print >> sys.stderr, "ERROR Error creating case: %s" % e


if __name__ == "__main__":
	if len(sys.argv) > 1 and sys.argv[1] == "--execute": # make sure we have the right number of arguments - more than 1; and first argument is "--execute"
	   	payload = json.loads(sys.stdin.read()) # read the payload from stdin as a json string
		config = payload.get('configuration') # extract the config from the payload
		filepath = payload.get('results_file') # extract the file path from the payload
		if os.path.exists(filepath): # test if the results file exists
			try: # file exists - try to open it; fail gracefully
				with gzip.open(filepath) as file: # open the file with gzip lib, start making alerts
					# DictReader lets us grab the first row as a header row and other lines will read as a dict mapping the header to the value
					# instead of reading the first line with a regular csv reader and zipping the dict manually later
					# at least, in theory
					reader = csv.DictReader(file)
					for row in reader: # iterate through each row, creating a alert for each and then adding the observables from that row to the alert that was created
						create_case(config, row) # make the alert with predefined function; fail gracefully
				sys.exit(0)
			except IOError as e:
				print >> sys.stderr, "FATAL Results file exists but could not be opened/read"
				sys.exit(3)
		else:
			print >> sys.stderr, "FATAL Results file does not exist"
			sys.exit(2)
	else:
		print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
		sys.exit(1)
