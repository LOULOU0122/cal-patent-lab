# -*- coding: utf-8 -*-0
#!/usr/bin/env python
#

# parse Guan Cheng's OCR text and extract key data
# output separate text files for each appeal decision
# we want Doc ID, Cause, Patent ID, App ID, Keywords, Date, Inventor,
# Decision, US Code

# This function takes the PTAB OCR text as input and uses the "PAGE 1" delimiter to
# break the PTAB file into separate files for each document
# Return value: number of files generated

import re
# import nameparser as np

casefile_tmpl = "./output/file_{:03}.txt"
propfile_tmpl = "./output/file_{:03}_properties.txt"

def splitDocument(filename):
    with open(filename) as f:
        # newDocBuf is a buffer to read in the file lines
        newDocBuf = ""
        # counter to assist in creating new file names
        count = -1
        for line in f:
            # when encountering this delimiter, write newDoc to another file
            # then reset the newDoc buffer
            if "*** PAGE 1 ***" in line:
                # this check prevents false positives from very beginning of file
                if count >= 0:
                    # write the legal document to its own file
                    newFile = open(casefile_tmpl.format(count), 'w')
                    newFile.write(newDocBuf)
                    newFile.close()
                    # also make a properties file
                    newFile = open(propfile_tmpl.format(count), 'w')
                    newFile.close()
                # increment counter
                count += 1
                # reset the buffer
                newDocBuf = ""
            newDocBuf += line
    return count


# Finds and records the document ID (appeal ID)
def parseDocId(fileIndex):
    infile = casefile_tmpl.format(fileIndex)
    outfile = propfile_tmpl.format(fileIndex)
    with open(infile) as f:
        for line in f:
            line = line.strip()
            if "Appeal No." in line:
                words = line.split(' ')
                if len(words) > 2:
                    docId = words[2]
                    propertiesFile =  open(outfile, 'a')
                    propertiesFile.write("docId: %s\n" % docId)
                    propertiesFile.close()
                    return


# Counts keywords
def parseKeywords(fileIndex):
    infile = casefile_tmpl.format(fileIndex)
    outfile = propfile_tmpl.format(fileIndex)
    with open(infile) as f:
        keywords = set(["reject", "unpatentable", "not", "fail", "incorrect"])
        counter = dict.fromkeys(keywords,0)
        for line in f:
            for word in keywords:
                counter[word] += line.count(word)

        propertiesFile =  open(outfile, 'a')
        propertiesFile.write("Keyword Score: %s\n" % sum(counter.values()))
        propertiesFile.close()


# Finds and records the patent application ID
def parseAppId(fileIndex):
    infile = casefile_tmpl.format(fileIndex)
    outfile = propfile_tmpl.format(fileIndex)
    appIdMatcher = re.compile('Application.+([Ol0-9]{1,2}/[Ol0-9]{1,3}[\.,][Ol0-9]{3})')
    with open(infile) as f:
        for line in f:
            line = line.strip()
            appIds = appIdMatcher.findall(line)
            if len(appIds) >= 1:
                propertiesFile =  open(outfile, 'a')
                for appId in appIds:
                    appId = appId.replace('O', '0').replace('l', '1')
                    propertiesFile.write("appId: {}\n".format(appId))
                propertiesFile.close()
                return

# Finds and records first-listed inventor
#
# TODO: Verify that ex parte field is always inventor
# (appears to be the case based on inspection), need to verify with lawyer
#
# TODO: "Ex parte" was not read exactly by OCR (e.g., ex paqte in some places)
# Need to correct for that
def parseInventor(fileIndex):
    infile = casefile_tmpl.format(fileIndex)
    outfile = propfile_tmpl.format(fileIndex)
    inventorMatcher = re.compile('([A-z-.])+(\s)+([A-z-.])+(\s)*([A-z-.])*')
    with open(infile) as f:
        lines = f.readlines()
        for i in range(len(lines)):
            curr = lines[i].strip()
            lwr = curr.lower()
            match = "ex parte "
            if match in lwr:
                nameStart = lwr.find(match) + len(match)
                name = curr[nameStart:]
                if "," in name:
                    commaLoc = name.find(",")
                    subname = name[:commaLoc]
                elif " and" in name:
                    andLoc = name.find(" and")
                    subname = name[:andLoc]
                else:
                    nm = re.search(inventorMatcher, name)
                    subname = nm.group(0)
                propertiesFile =  open(outfile, 'a')
                propertiesFile.write("Inventor: {}\n".format(subname))
                propertiesFile.close()
                return # prevents ex parte from being written twice in same file


# Finds the appeal's final decision
def parseDecision(fileIndex):
    infile = casefile_tmpl.format(fileIndex)
    outfile = propfile_tmpl.format(fileIndex)
    deniedMatcher = re.compile('(DEN[Il]ED(-IN-PART)?)')
    grantedMatcher = re.compile('([GQ]RANTED(-IN-PART)?)')
    vacatedMatcher = re.compile('VACATED')
    remandedMatcher = re.compile('(REMAND(ED)?)')
    with open(infile) as f:
        for line in f:
            line = line.strip()
            deniedMatchResult = deniedMatcher.search(line)
            grantedMatchResult = grantedMatcher.search(line)
            vacatedMatchResult = vacatedMatcher.search(line)
            remandedMatchResult = remandedMatcher.search(line)
            if deniedMatchResult or grantedMatchResult or vacatedMatchResult or remandedMatchResult:
                propertiesFile =  open(outfile, 'a')
                if deniedMatchResult:
                    result = deniedMatchResult.group(0).replace('l', 'I')
                    propertiesFile.write("decision: {}\n".format(result))
                if grantedMatchResult:
                    result = grantedMatchResult.group(0).replace('Q', 'G')
                    propertiesFile.write("decision: {}\n".format(result))
                if vacatedMatchResult:
                    result = vacatedMatchResult.group(0)
                    propertiesFile.write("decision: {}\n".format(result))
                if remandedMatchResult:
                    result = remandedMatchResult.group(0)
                    propertiesFile.write("decision: {}\n".format(result))
                propertiesFile.close()
                return


# Find the US Code
def parseUSC(fileIndex):
    infile = "./output/file_{:03}.txt".format(fileIndex)
    outfile = "./output/file_{:03}_properties.txt".format(fileIndex)
    USCMatcher = re.compile('U.S.C. \§')
    with open(infile) as f:
        # Read the file and check if we can find the mention of U.S.C.
        text = f.read().strip()
        USCMatchResult = USCMatcher.search(text)
        # If we find a mention of U.S.C, we find the code
        if USCMatchResult:
            USCode = re.compile('\§\s*[l0-9]+\s*(\([a-z]+\))*')
            USCodeResult = USCode.search(text).group(0)
            with open(outfile, 'a') as propertiesFile:
                propertiesFile.write("USC: {}\n".format(USCodeResult))



'''
def parser(filename):
    with open(filename) as f:
        docId = ""
        patentId = ""
        appId = ""
        date = ""
        inventor = ""
        count = 0
        code = ""
        newFilename = "file_"
        for line in f:
            # new document
            if "*** PAGE 1 ***" in line:
                docId = ""
                patentId = ""
                appId = ""
                date = ""
                inventor = ""
                newFilename = "./output/file_"
                code = ""
                count += 1
            # get document ID
            elif "Appeal No." in line:
                if docId=="":
                    words = line.split(' ')
                    if len(words)>2:
                        docId = words[2]
                        if count<10:
                            newFilename += "00" + str(count)+".txt"
                        elif count<100:
                            newFilename += "0" + str(count)+".txt"
                        else:
                            newFilename += str(count)+".txt"
                        newDoc = open(newFilename, 'a')
                        newDoc.write("docId: "+docId+"\n");
                        newDoc.close();
            # get application ID
            elif "Application No." in line:
                if len(docId)>1 and len(appId)<1:
                    words = line.split(' ')
                    if len(words)>2:
                        appId = words[2]
                        if len(newFilename)>5:
                            newDoc = open(newFilename, 'a')
                            newDoc.write("appId: "+appId+"\n");
                            newDoc.close();
            # decision
            elif ("GRANTED" in line) or ("DENIED" in line):
                if len(newFilename)>5:
                    newDoc = open(newFilename, 'a')
                    newDoc.write("decision: "+line+"\n");
                    newDoc.close();

            # US Code
            elif "U.S.C." in line:
                if len(docId)>1 and len(code)<1:
                    code = ""
                    words = line.split(' ')
                    for i in xrange(len(words)):
                        if words[i]=="U.S.C.":
                            if len(words[i+1])==2: #that stupid section symbol
                                code = words[i+2]
                            else:
                                code = words[i+1]
                            break
                    if len(newFilename)>5:
                            newDoc = open(newFilename, 'a')
                            newDoc.write("code: "+code+"\n");
                            newDoc.close();
'''
numFiles = splitDocument("../ptab-data/ptab.sample.200.txt")

for i in xrange(numFiles):
    parseDocId(i)
    parseAppId(i)
    parseInventor(i)
    parseDecision(i)
    parseUSC(i)
    parseKeywords(i)
