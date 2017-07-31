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

def create_case(csv_rows, config):

    url = config.get('url') # Get TheHive URL from Splunk configuration
    headers = {'Content-type': 'application/json'} # set proper headers
    username = config.get('username') # Get TheHive username from Splunk configuration
    password = config.get('password') # Get TheHive password from Splunk configuration
    auth = requests.auth.HTTPBasicAuth(username=username,password=password) # Generate basic auth key

    # Get the payload for the case from the config, use defaults if they are not specified
    payload = json.dumps(dict(
        title = config.get('title'),
        description = config.get('description', "No description provided."),
        severity = int(config.get('severity', 1)),
        owner = config.get('owner'),
        tlp = int(config.get('tlp', 2)),
        tags = [] if config.get('tags') is None else config.get('tags').split(",") # capable of continuing if Tags is empty and avoids split failing on empty list
    ))

    print >> sys.stderr, 'INFO csv_rows="%s"' % (csv_rows)

    # Filter empty multivalue fields
    parsed_rows = {key: value for key, value in csv_rows.iteritems() if not key.startswith("__mv_")}
    print >> sys.stderr, 'INFO parsed_rows="%s"' % (parsed_rows)

    # Take KV pairs and make a list-type of dicts
    artifacts = []
    for key, value in parsed_rows.iteritems():
        artifacts.append(dict(
            dataType = key,
            data = [] if value is None else value.split(",")
        ))

    print >> sys.stderr, 'INFO Artifacts="%s"' % (artifacts)

    try:
        print >> sys.stderr, 'INFO Calling url="%s" with payload=%s' % (url, payload)

        response = requests.post(url=url + "/api/case", headers=headers, data=payload, auth=auth, verify=False) # POST case to TheHive API
        if response.status_code == 201:
            print >> sys.stderr, (json.dumps(response.json(), indent=4, sort_keys=True))
            print >> sys.stderr, ('')
            case_id = response.json()['id']
        else:
            print >> sys.stderr, ('ERROR Status Code: {} Message: {}'.format(response.status_code, response.text))

        observ_url = url + "/%s/artifact" % (case_id)

        response = requests.post(observ_url, headers=headers, data=artifacts, auth=auth, verify=False) # POST observables to the case
        if response.status_code == 201:
            print >> sys.stderr, (json.dumps(response.json(), indent=4, sort_keys=True))
            print >> sys.stderr, ('')
        else:
            print >> sys.stderr, ('ERROR Status Code: {} Message: {}'.format(response.status_code, response.text))
    except requests.exceptions.RequestException as e:
        sys.exit("Error: {}".format(e))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute": # make sure we have the right number of arguments - more than 1; and first argument is "--execute"
        payload = json.loads(sys.stdin.read()) # read the payload from stdin as a json string
        config = payload.get('configuration') # extract the config from the payload
        results_file = payload.get('results_file') # extract the file path from the payload
        if os.path.exists(results_file): # test if the results file exists
            try: # file exists - try to open it; fail gracefully
                with gzip.open(results_file) as file: # open the file with gzip lib, start making alerts
                    reader = csv.DictReader(file)
                    for csv_rows in reader:
                        create_case(csv_rows, config) # make the alert with predefined function; fail gracefully
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
