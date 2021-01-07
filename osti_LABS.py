#!/usr/bin/python

import re
import cgi
import sys

from invenio.search_engine import perform_request_search
from invenio.search_engine import get_fieldvalues
from invenio.search_engine import print_record
from invenio.intbitset import intbitset
from check_url import checkURL
from osti_web_service import get_url

VERBOSE = False
#VERBOSE = True

def perform_search(search, cc):
    results_list = []
    page = 1
    next = True
    while next:
        try:
            search = "https://labs.inspirehep.net/api/%s?page=%s&q=%s&size=100" % (cc, str(page), search)
            results = request('GET', search, headers={'Accept': 'application/json'})
            results = results.json()
            for item in results['hits']['hits']:
                results_list.append(item)
            if 'next' in results['links']:
                page += 1
                length = results['hits']['total']
            else:
                next = False
        except KeyError:
             print 'Something went wrong: ', search
             length = 0
    return results_list, length

def main(search):
    if not search:
        search = "find r fermilab and dadd 2014"
    search_original = search
    x = intbitset(perform_request_search(p=search, cc='HEP'))
    print search, ':', len(x)
    fermilab         = intbitset(perform_request_search(p="8564_y:fermilab*", cc='HEP'))
    fermilabtoday   = intbitset(perform_request_search(p="8564_y:fermilabtoday", cc='HEP'))
    fermilabpub     = intbitset(perform_request_search(p="8564_y:fermilabpub", cc='HEP'))
    fermilabthesis  = intbitset(perform_request_search(p="8564_y:fermilabthesis", cc='HEP'))
    fermilabconf    = intbitset(perform_request_search(p="8564_y:fermilabconf", cc='HEP'))
    fermilabtm      = intbitset(perform_request_search(p="8564_y:fermilabtm", cc='HEP'))
    scoap           = intbitset(perform_request_search(p="8564_y:'Article from SCOAP3'", cc='HEP'))
    oa              = intbitset(perform_request_search(p="8564_z:postprint or 8564_z:openaccess", cc='HEP'))
    cms = intbitset(perform_request_search(p="find r fermilab and cn cms", cc='HEP'))
    ok = fermilab - fermilabtoday | fermilabpub | fermilabthesis | fermilabconf | fermilabtm | scoap | cms | oa
    print 'Total number of Fermilab links:', len(ok)
    x = x & ok
    print 'Intersection:', len(x), x

    fileName    = 'osti.out'
    fileName2 = 'osti2.out'
    output = open(fileName, 'w')
    output.write("<harvest-site>\n")
    for r in x:
            output.write(print_record(r, format='xsti'))
    output.write("</harvest-site>\n")
    output.close()


    output2 = open(fileName2, 'w')
    #noUrl = False
    #arXiv_flag = False
    subj_category_flag = False
    subj_keywords_flag = False
    url_check_flag = True
    url_check_flag = False
    url_oa = False
    counter = 1

    for i in open(fileName, 'r'):
        issue = None
        i = re.sub(r'(find_paper\.pl\?[\w\-]+)', r'\1.pdf', i)
        i = re.sub(r'pdf\.pdf', 'pdf', i)
        i = re.sub(r'shtml\.pdf', 'shtml', i)

        if re.search(r'accession_num', i):
            matchObj = re.match(r'.*<accession_num>(\d+)</accession_num>.*', i)
            if matchObj:
                doctype_flag = False
                accepted = False
                accession_num = matchObj.group(1)
                search = "find recid " + accession_num + " or irn " + accession_num + " and r fermilab"
                y = perform_request_search(p=search, cc='HEP')
                if len(y) == 1 : recid = y[0]
                if VERBOSE:
                    print("{0} {1} {2}".format(counter, accession_num, recid))
                counter += 1
                url_oa = False
                try:
                    doi = get_fieldvalues(recid, '0247_a')[0]
                    search_oa = 'find recid ' + str(recid) + ' and exp cern-lhc-cms'                    
                    if VERBOSE:
                        print "doi =", doi
                        print "search_oa =", search_oa
                    if re.search(r'PhysRevSTAB', doi):
                        url_oa = 'http://journals.aps.org/prstab/pdf/' + doi
                    #elif perform_request_search(p=search_oa, cc='HEP'):
                    #    if re.search(r'PhysRevD', doi):
                    #        url_oa = 'http://journals.aps.org/prd/pdf/10.1103/' + doi
                    #    elif re.search(r'PhysRevLett', doi):
                    #        url_oa = 'http://journals.aps.org/prl/pdf/10.1103/' + doi
                    #    if VERBOSE:
                    #        print url_oa
                except:
                    pass
                try:
                    accepted = get_fieldvalues(recid, '8564_3')
                    urls = get_fieldvalues(recid, '8564_u')
                    for url in urls:
                        if re.search('scoap3-fulltext.pdf', url):
                            url_oa = url
                            accepted = True
                        elif re.search(r'record/\d+/files/arXiv', url) and recid in cms and not url_oa:
                            #This is to catch the CMS papers
                            url_oa = url 
                    [url_oa, accepted] = get_url(recid)
                except:
                    pass
                if url_oa:
                    i += "  <url>" + url_oa + "</url>\n"
                if accepted:
                    i += "  <journal_type>AM</journal_type>\n"
                else:
                    i += "  <journal_type>FT</journal_type>\n"
                authors = get_fieldvalues(recid, '700__a')
                if len(authors) > 9 :
                    author = get_fieldvalues(recid, '100__a')[0]
                    author = "    <author>" + author + "; et al.</author>\n"
                    i = i + author
                    collaboration = get_fieldvalues(recid, '710__g')
                    if collaboration:
                        collaboration = cgi.escape(collaboration[0])
                        collaboration = "    <contributor_organizations>" + collaboration + "</contributor_organizations>\n"
                        i = i + collaboration

                #search = "001:" + str(recid) + " 8564_y:FERMILAB*"
                ##search = "001:" + str(recid) + " 037__9:arXiv"
                #z = perform_request_search(p=search, cc='HEP')
                #if len(z) < 1 :
                #  noUrl = True
                #  print 'No url for ', recid
                #  break
                #if len(z) == 1 : arXiv_flag = True
                #else : arXiv_flag = False

                phd_date = get_fieldvalues(recid, '502__d')
                normal_date = get_fieldvalues(recid, '269__c')
                try:
                    published_date = get_fieldvalues(recid, '260__c')[0]
                except IndexError:
                    published_date = False
                if phd_date and not normal_date:
                    phd_date = "    <date>" + phd_date[0] + "</date>\n"
                    i = i + phd_date
                elif published_date and not normal_date:
                    published_date = "    <date>" + published_date + "</date>\n"
                    i = i + published_date
            if VERBOSE:
                print i
        #if arXiv_flag and re.search("<availability>http://arXiv.org", i) :
        #    url = i
        #    url = re.sub(r'availability', 'url', url)
        #    url = re.sub(r'arXiv.org/abs', 'arXiv.org/pdf', url)
        #    i = i + url
        #    #noUrl = False

        elif re.search("<url>", i):
            if url_oa: 
                i = ''
            if re.search("www.fnal.gov/pub/today", i):
                i = ''
            elif re.search("<url>.*fnal", i) :
                matchObj = re.match(r'.*<url>(.*fnal.*)</url>.*', i)
                if matchObj:
                    url_to_check =    matchObj.group(1)
                    if re.search("shtml", url_to_check) :
                        url_to_check = re.sub(r'.*fermilab\-(.*)\.shtml', r'http://lss.fnal.gov/cgi-bin/find_paper.pl?\1.pdf', url_to_check)
                        if url_check_flag:
                            if not checkURL(url_to_check) :
                                error_message = "Something wrong with " + url_to_check
                                print error_message
                                break
                            else : print "No problem with url: ", url_to_check
                    i = "  <url>" + url_to_check + "</url>\n"
            
            else : i = ''

        if re.search("<title>", i) :
            title = get_fieldvalues(recid, '245__a')[0]
            title = cgi.escape(title)
            i = "  <title>" + title + "</title>\n"

        if re.search("<date>", i) :
            if re.search(">\d\d\d\d\-\d\d\-\d\d<", i) :
              i = re.sub(r'>(\d\d\d\d)\-(\d\d)\-(\d\d)<', r'>\2/\3/\1<', i)
            elif re.search(">\d\d\d\d\-\d\d<", i) :
              i = re.sub(r'>(\d\d\d\d)\-(\d\d)<', r'>\2/01/\1<', i)
            elif re.search(">\d\d\d\d<", i) :
              i = re.sub(r'>(\d\d\d\d)<', r'>01/01/\1<', i)
            else :
                print "Bad date: ", recid, i
                break
            abstract = get_fieldvalues(recid, '520__a')
            if abstract :
                abstract = abstract[0]
                abstract = cgi.escape(abstract)
                abstract = "  <abstract>" + abstract + "</abstract>\n"
                i = i + abstract

        if re.search("<doctype>", i) :
            doctype_flag = True

        if re.search("<arXiv_eprint>", i) :
            if not doctype_flag:
                try:
                    report = get_fieldvalues(recid, '037__z')[0]
                    report = "  <report_number>" + report + "</report_number>\n"
                    i = i + report
                    i = i + "  <doctype>JA</doctype>\n"
                except:
                    pass

        if re.search("journal", i) :
            i = re.sub(r'<journal_info>(.*[ \.])(\S+)\:(\S+)\,(\d+)</journal_info>', r'<journal_name>\1</journal_name>\n    <journal_volume>\2</journal_volume>\n    <journal_issue></journal_issue>', i)
            issue = get_fieldvalues(recid, '773__n')
            if issue :
                issue = issue[0]
                issue = "<journal_issue>" + str(issue) + "</journal_issue>"
                i = re.sub(r'<journal_issue></journal_issue>', issue, i)

        if re.search("<sponsor_org>", i) :
            i = re.sub(r'DOE Office of Science', r'USDOE Office of Science (SC), High Energy Physics (HEP) (SC-25)', i)

        if re.search("<subj_category>", i) :
            if subj_category_flag : i = ''
            subj_category_flag = True

        if re.search("<subj_keywords>", i) :
            if subj_keywords_flag : i = ''
            subj_keywords_flag = True

        if i: 
            #print i
            output2.write(i)

    output2.close()
    print search_original

if __name__ == '__main__':
    search = sys.argv[1:][0]
    try:
        main(search)
    except KeyboardInterrupt:
        print 'Exiting'

