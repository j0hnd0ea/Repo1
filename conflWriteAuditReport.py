import json, datetime
from confluence import Confluence
from jira import JIRA
from json2html import *
from pythonModule import DBConnector,pwdCaller, getAWSAccountID

def write_page(server, token, space, title, content, parent_id=None):
    if not parent is None:
        try:
            # Find out the ID of the parent page
            parent_id = server.confluence1.getPage(token, space, parent)['id']
            print "parent page id is %s" % parent_id
        except:
            print "couldn't find parent page; ignoring error..."
    try:
        existing_page = server.confluence1.getPage(token, space, title)
    except:
        # In case it doesn't exist
        existing_page = {}
        existing_page["space"] = space
        existing_page["title"] = title
    
    if not parent_id is None:
        existing_page["parentId"] = parent_id

    existing_page["content"] = content
    existing_page = server.confluence1.storePage(token, existing_page)
    return

def createJIRATicket(desc, jiraConnector):
   options = {
   'server':jiraConnector['url'],
   'verify':jiraConnector['verify']
   }
   keyValue = pwdCaller('officeLdap')['data']
   jira = JIRA(options, basic_auth=(keyValue['user'],keyValue['password']))
   qType = 'Daily Audit'
   new_issue = jira.create_issue(project=jiraConnector['project'], summary = qType, description=desc, issuetype={'name':'Task'})
   jira.add_watcher(new_issue.id,jiraConnector['watcher'])
   return

def confluenceConnector(conflConnector):
   options = {
   'server':conflConnector['url'],
   'verify':conflConnector['verify']
   }
   keyValue = pwdCaller('officeLdap')['data']
   confl = Confluence(profile='confluence',username=keyValue['user'],password=keyValue['password'])
   return confl

def writeAuditReport(fileJSON):
   db = DBConnector()
   awsAccountIDList = getAWSAccountID(db)
   db.close()
   conflConnector = pwdCaller(Confluence)['data']
   jiraConnector = pwdCaller(JIRA)['data']
   fhM = open(fileJSON,'r+')
   oData = json.load(fhM)
   summary = {}
   raw = """h2.Summary
           This page contains daily audit.
           - AD/AWS account
   """
   for key0, value0 in oData.iteritems():
      for key1, value1 in value0.iteritems():
         for key2, value2 in value1.iteritems():
            if len(value2) > 0:
               if key0 in summary.keys():
                  if key1 in summary[key0].keys():
                     summary[key0][key1][key2] = len(value2)
                  else:
                     summary[key0][key1]={}
                     summary[key0][key1][key2] = len(value2)
               else:
                  summary[key0]={}
                  summary[key0][key1]={}
                  summary[key0][key1][key2] = len(value2)

   summary = {}
   summary['OfficeADAudit'] = {}
   summary['OfficeADAudit']['created'] = len(oData['OfficeADAudit']['created'])
   summary['OfficeADAudit']['removed'] = len(oData['OfficeADAudit']['removed'])
   summary['OfficeADAudit']['updated'] = len(oData['OfficeADAudit']['updated'])
   for AWSAccount in awsAccountIDList:
      AWSAccountID = AWSAccount['AccountID']
      AWSAccountName = AWSAccount['AWSAccountName']
      summary[AWSAccountName] = {'mfaSet':0,'removed':0,'created':0}
      summary[AWSAccountName]['mfaSet'] = len(oData[AWSAccountName]['mfaSet'])
      summary[AWSAccountName]['removed'] = len(oData[AWSAccountName]['removed'])
      summary[AWSAccountName]['created'] = len(oData[AWSAccountName]['created'])
   
   jiraRaw = """
      AD Accounts
      || Location || Created || removed ||Updated || 
      | Office | """ + str(summary['OfficeADAudit']['created']) + " | " + str(summary['OfficeADAudit']['removed']) + " | " + str(summary['OfficeADAudit']['updated']) + " |" + """
      AWS Account
      || AWS || created || removed || mfaSet ||
      """
   for AWSAccount in awsAccountIDList:
      AWSAccountID = AWSAccount['AccountID']
      AWSAccountName = AWSAccount['AWSAccountName']
      AWSCategory = AWSAccount['AWSCategory']
      try:
         jiraRaw = jiraRaw + """ | """ + AWSAccountName + "_" + AWSCategory + " | " + str(summary[AWSAccountName]['created']) + " | " + str(summary[AWSAccountName]['removed']) + " | " + str(summary[AWSAccountName]['mfaSet']) +" |" + """
            """
      except KeyError:
         continue
   jiraRaw = """Confluence page: """ + conflConnector['url']+"""/display/"""+conflConnector['space']+"""/Daily+audit+report

            """+ jiraRaw
   createJIRATicket(jiraRaw, jiraConnector)
   teamEvents={}

   fhM.close()
   
   ############################
   # Confluence               #
   ############################

   confl = confluenceConnector(conflConnector)
   token = confl._token
   server = confl._server
   conflConnector = pwdCaller(Confluence)['data']
   parent_id = conflConnector['pID']
   space = conflConnector['space']
   title = conflConnector['title']
   try:
      existing_page = confl.storePageContent(title, space, raw) 
   except:
      write_page(server, token, space, title, raw, parent_id)
   return
