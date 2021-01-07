"""
Script to push information on Fermilab publications
to OSTI using the webservice AN241.1.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom

import re
import cgi
import getopt
import sys
import datetime
import pytz
import os

from urllib2 import Request, urlopen
import PyPDF2
from PyPDF2 import PdfFileReader
from StringIO import StringIO


from json import loads
from requests import request

from invenio.search_engine import perform_request_search
from invenio.search_engine import get_fieldvalues
from invenio.intbitset import intbitset
from invenio.bibformat_engine import BibFormatObject
from check_url import checkURL

from osti_web_service_constants import TYPE_DICT, DIRECTORY, \
        ACCEPTED_SEARCH, DADD_SEARCH, THESIS_SEARCH, \
        DOE_SUBJECT_CATEGORIES_DICT, \
        DOE_FERMILAB_DICT, DOE_AFF_DICT, \
        INSPIRE_AFF_DICT, SEARCH

CHICAGO_TIMEZONE = pytz.timezone('America/Chicago')

REC_URL = 'https://labs.inspirehep.net/api/literature/'

CONF_URL = 'https://labs.inspirehep.net/api/conferences/'

LOGFILE = 'osti_web_service.log'
VERBOSE = True
VERBOSE = False
TEST = True
TEST = False
RECIDS = False
ENDING_COUNTER = 20

CMS = intbitset(perform_request_search(p="find r fermilab and cn cms", \
                                       cc='Fermilab'))

CMS = intbitset(perform_request_search(p="037__z:fermilab*", cc='Fermilab'))


def create_osti_id_pdf(jrec, osti_id):
    """
    Places a PDF named after the OSTI id in a location that
    can be pushed to OSTI.
    If the pdf is not of an excepted paper it skips this.
    """
    final_pdf = None
    final_txt = None
    if VERBOSE:
        print recid, osti_id
    if not jrec or not osti_id:
        return None
    try:
        [url, accepted] = get_url(jrec)
        if accepted == False:
            return None
    except IndexError:
        print "No url on", jrec
        return None
    except TypeError:
        print "No url on", recid
        return None
    remote_file = urlopen(Request(url)).read()
    memory_file = StringIO(remote_file)
    try:
        PdfFileReader(memory_file)
    except PyPDF2.utils.PdfReadError:
        print "PDF invalid for", recid
        return None
    except TypeError:
        print "Problem with", url
        return None
    final_pdf = DIRECTORY + str(osti_id) + ".pdf"
    final_txt = DIRECTORY + str(osti_id) + ".txt"
    if os.path.exists(final_pdf) or os.path.exists(final_txt):
        print "Already have PDF for recid=", recid, "osti_id=", osti_id
        print final_pdf
        print final_txt
        return None
    output = open(final_pdf, 'wb')
    output.write(remote_file)
    output.close()


def get_language(jrec):
    """ Find the langauge of the work. """
    try:
        return jrec['metadata']['languages'][0]
    except KeyError:
        return 'English'

def get_osti_id(jrec):
    """ Find the osti_id from an INSPIRE record """
    try:
        for item in jrec['metadata']['external_system_identifiers']:
            if item['schema'].lower() == 'osti':
                return item['value']
    except KeyError:
        return None

def check_already_sent(jrec):
    """Looks to see if we've already sent the AM to OSTI."""

    osti_id = get_osti_id(jrec)
    if osti_id:
        final_pdf = DIRECTORY + str(osti_id) + ".pdf"
        final_txt = DIRECTORY + str(osti_id) + ".txt"
        if os.path.exists(final_pdf) or os.path.exists(final_txt):
            if VERBOSE:
                print final_pdf
                print final_txt
            return True
    return False


def get_url(jrec):
    """Is there a valid url? Is it to an accepted PDF?"""
    if VERBOSE:
        print 'get_url', jrec['id']
    url = None
    url_fermilab = None
    url_arxiv = None
    url_openaccess = None
    url_postprint = None
    url_inspire = None
    accepted = False
    has_doi = False
    docs = None

#    for item in BibFormatObject(int(recid)).fields('8564_'):
#        if item.has_key('y'):
#            if item['y'] in ['Article from SCOAP3',
#                             'Fulltext from Publisher']:
#                url_openaccess = item['u']
#                accepted = True
#        if item.has_key('z') and not url_openaccess:
#            if item['z'] == 'openaccess':
#                url_openaccess = item['u']
#                accepted = True
#            elif item['z'] == 'postprint':
#                url_postprint = item['u']
#                accepted = True
    
#    How do we get openaccess and accepted manuscripts????
    if 'documents' in jrec['metadata']:
        docs = jrec['metadata']['documents']
        if any('url' in d for d in jrec['metadata']['documents']):
#            accepted = True
             has_docs = True

    #For an accepted paper to count, it should have a DOI.
#    if 'DOI' in (element.upper() for element in
#                 get_fieldvalues(recid, '0247_2')):

    if 'dois' in jrec['metadata']
        has_doi = True

    if not has_doi:
        accepted = False

    if not accepted:
        if 'urls' in jrec['metadata']:
            urls = jrec['metadata']['urls']
#        urls = get_fieldvalues(recid, '8564_u')
        for url_i in urls:
            if re.search(r'lss.*fermilab\-.*pdf', url_i['value'], re.IGNORECASE):
                url_fermilab = url_i['value']
        if docs:
            for doc in docs:
                if 'source' in doc and doc['source'] == 'arXiv':
                    url_arxiv = 'https://arxiv.org/pdf/' + doc['key']
                if re.search(r'fermilab-.*pdf', doc['key'], re.IGNORECASE):
                url_inspire = doc['key']
            elif re.search(r'.*?MUCOOL\-.*pdf', doc['key'], re.IGNORECASE):
                url_inspire = doc['key']

    if url_openaccess:
        url = url_openaccess
    elif url_postprint:
        url = url_postprint
    elif url_fermilab:
        url = url_fermilab
    elif url_arxiv and int(jrec['id']) in CMS:
        url = url_arxiv
    elif url_inspire:
        url = url_inspire

    if VERBOSE:
        print 'url =', url

    if url:
        try:
            if checkURL(url):
                return [url, accepted]
            else:
                print "Check recid", jrec['id']
                print "Problem (if) with", url
                return [None, accepted]
        except:
            print "Check recid", jrec['id']
            print "Problem with (try) ", url
            return [None, accepted]
        #if checkURL(url):
        #    return [url, accepted]
        #else:
        #    print "Problem with", url
        #    return [None, accepted]
    else:
        return [None, False]

def get_title(jrec):
    """Get title with in xml compliant form."""
    try:
        title = jrec['metadata']['titles'][0]['title']
        title = cgi.escape(title)
        return title
    except IndexError:
        print 'Problem with title on', jrec['id']
        return None

def get_pubnote(jrec):
    """Gets publication information"""
    try:
        journal = jrec['metadata']['publication_info'][0]['journal_title']
    except KeyError:
        journal = None
    try:
        volume = jrec['metadata']['publication_info'][0]['journal_volume']
    except KeyError:
        volume = None
    try:
        issue = jrec['metadata']['publication_info'][0]['journal_issue']
    except KeyError:
        issue = None
    try:
        pages = jrec['metadata']['publication_info'][0]['artid']
    except KeyError:
        try:
        pages = jrec['metadata']['publication_info'][0]['page_start']
        except KeyError:
            pages = None
    try:
        doi = jrec['metadata']['dois'][0]['value']
    except KeyError:
        doi = None
    return [journal, volume, issue, pages, doi]

def get_conference(jrec_hep):
    """ Get conference information """
    try:
        cnum  = jrec_hep['metadata']['publication_info'][0]['cnum']
    except KeyError:
        return None
#    search = '111__g:' + cnum
    search = 'cnum:' + cnum
#    insert search terms used in Labs Conferences database when available!
    result = perform_request_search(p=search, cc='Conferences')
    if len(result) != 1:
        return None
    recid = result[0]
    jrec_conf = request('GET', CONF_URL + str(recid)).json()
    try:
        conference_note = jrec_conf['metadata']['titles'][0]['title']
    except KeyError:
        conference_note = ''
    try:
        for item in jrec_conf['metadata']['address']:
            if 'cities' in item:
                conference_note += ', ' + item['cities'][0]
            if 'state' in item:
                conference_note += ', ' + item['state']
            if 'country_code' in item:
                conference_note += ', ' + item['country_code']
                
    except KeyError:
        pass
    try:
        date = jrec_conf['metadata']['opening_date']
        date = get_fieldvalues(recid, "111__x")[0]
        date_object = datetime.datetime.strptime(date, '%Y-%m-%d')
        date = date_object.strftime('%m/%d')
        conference_note += ', ' + date
    except KeyError:
        pass
    try:
        date = jrec_conf['metadata']['closing_date']
        date_object = datetime.datetime.strptime(date, '%Y-%m-%d')
        date = date_object.strftime('%m/%d/%Y')
        conference_note += '-' + date
    except KeyError:
        pass
    if conference_note:
        return conference_note
    else:
        return None

def get_author_details(jrec, authors):
    """Get authors broken out as individuals"""
    try:
        for item in jrec['metadata']['authors']:
        authors_detail = ET.SubElement(authors, 'authors_detail')
        author = None
        last_name = None
        first_name = None
        middle_name = None
        affiliation = None
        email = None
        orcid = None
        try:
            author = item['full_name']
            try:
                matchobj = re.match(r'(.*)\, (.*)\, (.*)', author)
                last_name = matchobj.group(1)
                fore_name = matchobj.group(2)
                title     = matchobj.group(3)
                fore_name = fore_name + ', ' + title
            except AttributeError:
                last_name = re.sub(r'\,.*', '', author)
                fore_name = re.sub(r'.*\, ', '', author)
            if re.search(r' ', fore_name):
                first_name = re.sub(r' .*', '', fore_name)
                middle_name = re.sub(r'.* ', '', fore_name)
            elif re.search(r'^\w\.\w\.', fore_name):
                first_name = re.sub(r'^(\w\.).*', r'\1', fore_name)
                middle_name = re.sub(r'^\w\.', '', fore_name)
            else:
                first_name = fore_name
        except KeyError:
            pass
        try:
            affiliation = '; '.join([x['value'] for x in item['affiliations']])
        except KeyError:
            pass
        try:
            email = item['emails'][0]
            email = email.replace('email:', '')
        except KeyError:
            pass
        try:
            for id in item['ids']:
                if id['schema'] == 'ORCID':
                     orcid = re.sub(r'ORCID:', '', id['value'])
        except KeyError:
            pass
        ET.SubElement(authors_detail, 'first_name').text = first_name
        ET.SubElement(authors_detail, 'middle_name').text = middle_name
        ET.SubElement(authors_detail, 'last_name').text = last_name
        ET.SubElement(authors_detail, 'affiliation').text = affiliation
        ET.SubElement(authors_detail, 'private_email').text = email
        ET.SubElement(authors_detail, 'orcid_id').text = orcid

def get_corporate_author(jrec):
    """Check to see if there is a corporte author and return it."""
    try:
        author_list = [x for x in jrec['metadata']['corporate_author']]
        return '; '.join([unicode(a, "utf-8") for a in author_list])
    except KeyError:
        return None

def get_author_first(jrec):
    """Get authors as a long string, truncate at 10."""
    try:
        return jrec['metadata']['authors'][0]['full_name'] + '; et al.'
    except KeyError:
        return None

def get_author_number(jrec):
    """Gets number of authors."""
    try:
        return len(jrec['metadata']['authors'])
    except KeyError:
        return 0

def get_collaborations(jrec):
    """Get the collaboration information"""
    try:
        collaborations = [x['value'] for x in jrec['metadata']['collaborations']]
        return '; '.join([unicode(a, "utf-8") for a in collaborations])
    except KeyError:
        return None

def get_abstract(jrec):
    """Get abstract if it exists."""
    try:
        abstract = jrec['metadata']['abstracts'][0]['value'] 
        if len(abstract) > 4990:
            abstract = abstract[:4990] + '...'
        return abstract
    except KeyError:
        return None

def get_reports(jrec):
    """Get reports as a long string."""
    try:
        reports = [x['value'] for x in jrec['metadata']['report_numbers']]
        return '; '.join(r for r in reports)
    except KeyError:
        return ''

def get_product_type(jrec):
    """Get product type in OSTI format."""
    type_dict = TYPE_DICT
    product_type = '??'
    report_string = get_reports(jrec)
    for key in type_dict:
        pattern = 'FERMILAB-' + key
        if re.search(pattern, report_string):
            product_type = type_dict[key]
    if VERBOSE:
        print product_type
    return product_type

def get_subject_categories(jrec):
    """Convert INSPIRE subject codes to OSTI codes."""
    try:
        categories = jrec['metadata']['inspire_categories']
    except KeyError:
        return None
    try:
        osti_categories = []
        for category['term'] in categories:
            for key in DOE_SUBJECT_CATEGORIES_DICT:
                if re.search(key, category.lower()):
                    osti_categories.append(DOE_SUBJECT_CATEGORIES_DICT[key])
        return '; '.join(c for c in set(osti_categories))
    except IndexError:
        return None

def get_affiliations(jrec, long_flag):
    """Get affiliations using OSTI institution names."""
#    affiliations = get_fieldvalues(recid, "100__u") \
#                 + get_fieldvalues(recid, "700__u")
    affiliations = [y['value'] for x in jrec['metadata']['authors'] for y in x['affiliations'] if 'affiliations' in x]
    affiliations.append("Fermilab")
    doe_affs = []
    doe_affs_long = []
    for aff in set(affiliations):
        #if aff in INSPIRE_AFF_DICT and not INSPIRE_AFF_DICT[aff] in doe_affs:
        if aff in INSPIRE_AFF_DICT:
            doe_affs.append(INSPIRE_AFF_DICT[aff])
            doe_affs_long.append(DOE_AFF_DICT[INSPIRE_AFF_DICT[aff]])
    if long_flag:
        return '; '.join([a for a in doe_affs_long])
    else:
        return '; '.join([a for a in doe_affs])

def get_date(jrec, product_type):
    """Get date in format mm/dd/yyyy, yyyy or yyyy Month."""
    try:
        date = jrec['metadata']['imprints'][0]['date'] 
    except KeyError:
        try:
            date = jrec['metadata']['preprint_date']
        except KeyError:
            try:
                date = jrec['metadata']['thesis_info']['date']
            except KeyError:
                date = '1900'
    try:
        date_object = datetime.datetime.strptime(date, '%Y-%m-%d')
        date = date_object.strftime('%m/%d/%Y')
    except ValueError:
        try:
            date_object = datetime.datetime.strptime(date, '%Y-%m')
            date = date_object.strftime('%Y %B')
            if product_type in ['TR', 'TD', 'JA']:
                date = date_object.strftime('%m/01/%Y')
        except ValueError:
            if product_type in ['TR', 'TD', 'JA']:
                date = '01/01/' + str(date)
    return date

def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def create_xml(recid, records):
    """
    Creates xml entry for a recid and feeds it to list of records.
    Tests to see if all the necessary information is present.
    If an accepted version has already been submitted, returns None.
    """

    jrec = request('GET', REC_URL+str(recid)).json()    

    [url, accepted] = get_url(jrec)
    if url is None:
        return None
    osti_id = get_osti_id(jrec)
    if osti_id:
        file_txt = DIRECTORY + '/' + str(osti_id) + '.txt'
        file_pdf = DIRECTORY + '/' + str(osti_id) + '.pdf'
        if os.path.isfile(file_txt) or os.path.isfile(file_pdf):
            #print "Already sent AM for", osti_id
            return None
    product_type = get_product_type(jrec)
    if accepted:
        product_type = 'JA'
    ##journal_info = get_pubnote(jrec)
    ##if product_type == 'JA' and journal_info[0] == None:
    ##    return None
    #Begin building record
    record = ET.SubElement(records, 'record')
    if osti_id:
        ET.SubElement(record, 'osti_id').text = osti_id
        dict_osti_id = {'osti_id':osti_id}
        ET.SubElement(record, 'revdata', dict_osti_id)
        ET.SubElement(record, 'revprod', dict_osti_id)
    else:
        ET.SubElement(record, 'new')
    ET.SubElement(record, 'site_input_code').text = \
        DOE_FERMILAB_DICT['site_input_code']
    if product_type == 'JA':
        if accepted:
            ET.SubElement(record, 'journal_type').text = 'AM'
            #print 'Accepted Manuscript', recid, osti_id
            create_osti_id_pdf(jrec, osti_id)
        else:
            ET.SubElement(record, 'journal_type').text = 'FT'
    ET.SubElement(record, 'product_type').text = product_type
    access_limitation = ET.SubElement(record, 'access_limitation')
    ET.SubElement(access_limitation, 'unl')
    if not accepted:
        ET.SubElement(record, 'site_url').text = url
    ET.SubElement(record, 'title').text = get_title(jrec)
    collaborations = get_collaborations(jrec)
    author_number = get_author_number(jrec)

    corporate_author = get_corporate_author(jrec)
    if corporate_author:
        author = ET.SubElement(record, 'author')
        author.text = corporate_author

    elif author_number > 20:
        author = ET.SubElement(record, 'author')
        author_first = get_author_first(jrec)
        if author_first:
            author.text = get_author_first(jrec)
    else:
        authors = ET.SubElement(record, 'authors')
        get_author_details(jrec)
    ET.SubElement(record, 'contributor_organizations').text = \
        collaborations
    ET.SubElement(record, 'report_nos').text = get_reports(jrec)
    for key in DOE_FERMILAB_DICT:
        ET.SubElement(record, key).text = DOE_FERMILAB_DICT[key]
    ET.SubElement(record, 'description').text = get_abstract(jrec)
    ET.SubElement(record, 'originating_research_org').text = \
        get_affiliations(jrec, True)
    journal_info = get_pubnote(jrec)
    if product_type == 'JA' and journal_info[0] == None:
        journal_elements = ['journal_name']
        journal_info = ['TBD']
    else:
        journal_elements = ['journal_name', 'journal_volume', 'journal_issue',
                        'product_size', 'doi']
    i_count = 0
    for journal_element in journal_elements:
        ET.SubElement(record, journal_element).text = journal_info[i_count]
        i_count += 1
    if product_type == 'CO':
        ET.SubElement(record, 'conference_information').text = \
        get_conference(jrec)
    ET.SubElement(record, 'other_identifying_nos').text = str(recid)
    ET.SubElement(record, 'publication_date').text = \
        get_date(jrec, product_type)
    ET.SubElement(record, 'language').text = \
        get_language(jrec)
    ET.SubElement(record, 'subject_category_code').text = \
        get_subject_categories(jrec)
    ET.SubElement(record, 'released_date').text = \
          CHICAGO_TIMEZONE.fromutc(datetime.datetime.utcnow()).\
          strftime('%m/%d/%Y')
    return 1

def main(recids):
    """Generate OSTI posting from a recid or an INSPIRE search."""

    counter = 0
    if not recids:
        print "No, that search did not work"
        return None
    filename = 'tmp_' + __file__
    filename = re.sub('.py', '.out', filename)
    output = open(filename,'w')

    #recids = [1400805, 1373745, 1342808, 1400935]
    records = ET.Element('records')
    for recid in recids:
        if VERBOSE:
            print recid
        if counter > ENDING_COUNTER:
            break
        if check_already_sent(recid):
            if VERBOSE:
                print "Already have", recid
            continue
        record_test = create_xml(recid, records)
        if record_test:
            counter += 1
        #if get_url(recid)[0]:
        #    if get_product_type(recid) == 'JA' and \
        #    get_pubnote(recid)[0] == None:
        #        pass
        #    else:
        #        create_xml(recid, records)
        #        counter += 1
    if TEST:
        print prettify(records)
    else:
        #output.write(XML_PREAMBLE)
        output.write(prettify(records))
    output.close()
    print "Number of records:", counter

def find_records(search_input=None):
    """
    Finds records to send email to.
    """

    print """
    Let's do a HEP search in INSPIRE format
    """
    if SEARCH:
        search_input = SEARCH
    elif not search_input:
        search_input = raw_input("Your search? ").lower()
    if len(search_input) > 3:
        if re.search(r'ignore', search_input):
            search = re.sub(r'ignore', '', search_input)
            search = search + ' 037:fermilab*'
#            search = search + ' report_numbers.value:Fermilab*'
        else:
            search = search_input + ' 037:fermilab* -035__9:osti'
#            search = search_input +' report_numbers.value:Fermilab* -external_system_identifiers.schema:OSTI'
    else:
        print "That's not a search. Game over."
        return None
    print search
    result = perform_request_search(p=search, cc='Fermilab')
#    result = ???
    if VERBOSE:
        print len(result)
    if len(result) > 0:
        log = open(LOGFILE, 'a')
        date_time_stamp = \
            CHICAGO_TIMEZONE.fromutc(datetime.datetime.utcnow()).\
            strftime('%Y-%m-%d %H:%M:%S')
        date_time_stamp = date_time_stamp + ' ' + search + ' : '\
                    + str(len(result)) + '\n'
        log.write(date_time_stamp)
        log.close()
        result.reverse()
        return result
    else:
        print "No results found."
        return None




if __name__ == '__main__':

    try:
        OPTIONS, ARGUMENTS = getopt.gnu_getopt(sys.argv[1:], 'air:tv')
    except getopt.error:
        print 'error: you tried to use an unknown option'
        sys.exit(0)

    for option, argument in OPTIONS:
        if option == '-i':
            RECIDS = find_records(ACCEPTED_SEARCH)
        elif option == '-a':
            RECIDS = find_records(DADD_SEARCH)
        elif option == '-t':
            RECIDS = find_records(THESIS_SEARCH)
        elif option == '-r':
            SEARCH = '001:' + argument + ' ignore'
            RECIDS = find_records(SEARCH)
        if option == '-v':
            VERBOSE = True
    if not RECIDS:
        RECIDS = find_records()
    try:
        main(RECIDS)
    except KeyboardInterrupt:
        print 'Exiting'



