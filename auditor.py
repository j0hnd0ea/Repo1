#!/usr/bin/python

from ldapOffice_V1 import OfficeQuerymain
from AWS_IAM import IAMQuerymain
from pythonModule import DBConnector, json_serial, getAWSAccountID
from datetime import datetime
import json, os, copy
from conflWriteAuditReport import writeAuditReport
from searchJIRA_AWS import searchJIRATicket

def compareDict(dict1, dict2):
   d1_keys = dict1.keys()
   d2_keys = dict2.keys()
   intersect_keys = set(d1_keys).intersection(set(d2_keys))
   modified = {}
   for i in intersect_keys:
      if dict1[i] != dict2[i]:
         if isinstance(dict1[i], dict) and isinstance(dict2[i], dict):
            modified[i] = compareDict(dict1[i], dict2[i])
         else:
            modified.update({i: (dict1[i],dict2[i])})
   return copy.deepcopy(modified)


def writeDaily(nData):
   today = datetime.today().strftime('%d')
   thisMonth = datetime.today().strftime('%m')
   thisYear = datetime.today().strftime('%Y')   
   if datetime.now().hour < 12:
      AMPM = 'am'
   else:
      AMPM = 'pm'
   thisDay = thisYear+thisMonth+today
   fileJSON = './' + thisDay+'_'+ AMPM + '_dailyJSON.html'
   print "create fileJSON"
   print fileJSON

   if os.path.exists(fileJSON):
      fhM = open(fileJSON,'rw+')
      oData = json.load(fhM)
   else:
      fhM = open(fileJSON,'w+')      
      fhM.write(json.dumps(nData,fhM,indent=4,sort_keys=True,default=json_serial,ensure_ascii=False))
      fhM.close()
      writeAuditReport(fileJSON)
      return

   o1Data = oData
   tata = compareDict(nData, oData)
   for nkey, nvalue in nData.iteritems():
      if nkey not in oData.keys():
         oData[nkey] = {}
      for nkey1, nvalue1 in nvalue.iteritems():
         if nkey1 not in oData[nkey].keys():
            oData[nkey][nkey1] = {}
         for k,v in nvalue1.iteritems():
            if k not in oData[nkey][nkey1]:
               oData[nkey][nkey1].update({k:v})
            else:
               del oData[nkey][nkey1][k]
               oData[nkey][nkey1].pop(k,None)
               oData[nkey][nkey1].update({k:nData[nkey][nkey1][k]})
   fhM.close()
   fhM = open(fileJSON,'w')
   fhM.write(json.dumps(oData,fhM,indent=4,sort_keys=True,default=json_serial,ensure_ascii=False))
   
   fhM.close()
   if AMPM == 'pm':
      writeAuditReport(fileJSON)
   return

if __name__ == "__main__" :
   searchJIRATicket() 
   db = DBConnector()   
   cur = db.cursor()
   
   awsAccountIDList = getAWSAccountID(db)
   #After Create audit data, zabbixAuditor and splunkCheckMain will update Zabbix and Splunk audit result
   result = {}
   
   result['OfficeADAudit'] = OfficeQuerymain(db)
   result['AWS'] = {}
   for AWSAccount in awsAccountIDList:
      AWSAccountID = AWSAccount['AccountID']
      AWSAccountName = AWSAccount['AWSAccountName']
      result['AWS'][AWSAccountName] = IAMQuerymain(db,'AWS'+AWSAccountID)   
   writeDaily(result)
   cur.close()
   db.close()
