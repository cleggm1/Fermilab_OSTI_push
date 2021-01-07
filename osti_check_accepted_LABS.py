#!/usr/bin/python
"""Check that we have an accepted manuscript."""

import getopt
import re
import sys
from Counter import Counter
import urllib

#from invenio.search_engine import perform_request_search, \
#                                  get_fieldvalues

from osti_web_service import get_url, get_osti_id, \
     check_already_sent
from osti_check_accepted_dois import DOIS, TOTAL, YEARS

import requests
import json

JOURNALS = []
headers = {'Accept':'application/json'}

API_URL = 'https://labs.inspirehep.net/api/literature/'


def check_record_status(jrec):
    """Checks to see if a PDF has already been sent
       or if we have an accepted manuscript.
    """

    if check_already_sent(jrec):
        return True

    try:
        JOURNALS.append(jrec['metadata']['publication_info'][0]['journal_title'])
    except KeyError:
        print 'No journal on:\nhttp://inspirehep.net/record/' + \
               jrec['id']

    if not PDF_CHECK:
        return False
    print "Checking accepted status", jrec['id']
    accepted_status = get_url(jrec)
    if True in accepted_status:
        return True
    elif None in accepted_status:
        if VERBOSE:
            print 'No url on:\nhttp://inspirehep.net/record/' + jrec['id']
        return False
    else:
        if VERBOSE:
            print jrec['id'], accepted_status
        return False

def check_doi(doi):
    """Checks to see if we have the DOI in INSPIRE."""
    search = "doi:" + doi + " report_numbers.value:Fermilab*"
    encodesearch = {'q': search}
    result = request('GET', API_URL[:-1] + '?' + urllib.urlencode(encodesearch), headers = headers).json()
    if result['hits']['total'] == 1:
        return result['hits']['hits'][0]['id']
    else:
        search = "doi:" + doi
        result = request('GET', API_URL[:-1] + '?' + urllib.urlencode(encodesearch), headers = headers).json()
        if result['hits']['total'] == 1:
            recid = result['hits']['hits'][0]['id']
            jrec = request('GET', API_URL + str(recid)).json()
            if 'refereed' not in jrec['metadata']:
                print '** Record not marked as published:'
                print 'http://inspirehep.net/record/' + str(recid) + '\n'
            affiliations = []
            try:
                affiliations = [aff['value'] for auth in jrec['metadata']['authors'] for aff in auth['affiliations'] if 'affiliations' in auth]
            except KeyError:
                pass
            if "Fermilab" not in affiliations:
                print '** Fermilab affiliation needed on:'
                print 'http://inspirehep.net/record/' + str(recid) + '\n'
                return False
            eprint = None
            try:
                report_numbers = [rn['value'] for rn in jrec['metadata']['report_numbers']]
                for report_number in report_numbers:
                    if report_number.startswith('arXiv'):
                        eprint = report_number
                        break
            except KeyError:
                pass
            if eprint or VERBOSE:
                print '* Fermilab report number needed on:'
                if eprint:
                    print eprint
                    print 'http://inspirehep.net/record/' + str(recid) + '\n'
                return False
        else:
            print "** Don't have DOI " + doi
            return False

def calc_output(counter, total):
    """Calculates a percentage."""

    percentage = 100*float(counter)/float(total)
    output = str(counter) + '/' + str(total) + \
             ' (' + "%.2f" % percentage + '%)'
    return output

def check_accepted(input_list, input_total):
    """Checks a list of DOIs or recids to see our accepted rate."""

    counter = 0
    counter_osti = 0
    total = len(input_list)
    open_access = input_total - total
    #print total
    for element in input_list:
        if re.match(r'^10\..*', element):
            element = check_doi(element)
        if str(element).isdigit():
            result = check_record_status(element)
            if result:
                counter += 1
                if get_osti_id(element):
                    counter_osti += 1
    counter += open_access
    counter_osti += open_access
    return [counter, counter_osti, input_total]
    #print 'Number of records: ', calc_output(counter, input_total)
    #print 'Number -> OSTI:    ', calc_output(counter_osti, input_total)

def main():
    """Examines compliance by fiscal year."""

    result = {}
    for year in YEARS:
        print 'Year:', year
        result[year] = check_accepted(DOIS[year], TOTAL[year])
    for year in YEARS:
        print 'Fiscal Year:', year
        print 'Number of records: ', calc_output(result[year][0],
                                                 result[year][2])
        print 'Number -> OSTI:    ', calc_output(result[year][1],
                                                 result[year][2])
    JOURNALS.sort()
    for key in Counter(JOURNALS):
        print '{0:26s} {1:2d}'.format(key, Counter(JOURNALS)[key])

if __name__ == '__main__':

    PDF_CHECK = False
    VERBOSE = False
    try:
        OPTIONS, ARGUMENTS = getopt.gnu_getopt(sys.argv[1:], 'pvy:')
    except getopt.error:
        print 'error: you tried to use an unknown option'
        sys.exit(0)

    for option, argument in OPTIONS:
        if option == '-p':
            PDF_CHECK = True
        if option == '-v':
            VERBOSE = True
        if option == '-y':
            try:
                YEARS = [int(argument)]
            except ValueError:
                print argument, 'is not a year'
                quit()
    try:
        RECID = ARGUMENTS[0]
        check_accepted([RECID], 1)
    except IndexError:
        try:
            main()
        except KeyboardInterrupt:
            print 'Exiting'

