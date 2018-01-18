#!/bin/python -w
import re
from pythonModule import pwdCaller, JIRA, json, DBConnector, sMail

def searchJIRATicket(aws):
   AWSIDPattern = re.compile('[0-9]{12}')
   jiraConnector = pwdCaller('jira')['data']
   AWSList = []
   options = {
   'server':jiraConnector['url'],
   'verify':jiraConnector['verify']
   }
   tableName = pwdCaller(aws)['data']['table']
   keyValue = pwdCaller('officeLdap')['data']
   jira = JIRA(options, basic_auth=(keyValue['user'],keyValue['password']))
   exam = jira.search_issues('project='+jiraConnector['project']+' AND issuetype = '+jiraConnector['issuetype']+' AND "'+jiraConnector['subissuetype']+'"="'jiraConnector['subissuetypecontent']+'" AND status=Resolved',maxResults=100)
   for issue in exam:
      tDict = {}
      tDict['ticket'] = str(issue)
      tDict['Owner'] = issue.fields.customfield_11811
      tDict['Category'] = str(issue.fields.customfield_11807)
      tDict['AccountID'] = issue.fields.customfield_11819.replace(' ','')
      if AWSIDPattern.match(tDict['AccountID']):
         AWSList.append(tDict)

   #Call DB handler
   db = DBConnector()
   cur = db.cursor()
   if len(AWSList) == 0:
      print AWSList
   else:
      sql = 'DELETE from '+tableName+';'
      cur.execute(sql)
      for eAWS in AWSList:
         sql = 'INSERT INTO '+tableName+' (AWSAccountName, JiraTicket, AccountID, AWSCategory) values ("%s", "%s", "%s", "%s");' % (eAWS['Owner'], eAWS['ticket'],eAWS['AccountID'],eAWS['Category'])
         cur.execute(sql)
      cur.close()
   db.commit()
   db.close()
   return


if __name__ == "__main__":
   searchJIRATicket()
