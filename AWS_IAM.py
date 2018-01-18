#!/usr/bin/python

from botocore.exceptions import ClientError 
from pytz import timezone
from datetime import datetime, timedelta
from pythonModule import pwdCaller, AWSClient

def insdata(aList,db,aws):
    tableName = pwdCaller(aws)['data']['table']
    cur = db.cursor()
    for elem in aList:
        sql = 'SELECT * FROM ' + tableName + ' WHERE userID = "%s" AND Location = "%s"' % (elem['userID'],aws)
        if (cur.execute(sql)) > 0:
            sql1 = 'UPDATE ' + tableName + ' SET lastLogin="%s" WHERE userID="%s" and Location = "%s"' % (elem['lastLogin'], elem['userID'],aws)
            cur.execute(sql1)
        else:
            sql1 = 'INSERT INTO ' + tableName + ' (uuid,Location, userID, userName, company, created, lastLogin, ticket, vpnUser,memberOf) VALUES ("uuid","%s","%s","%s","%s","%s","%s","%s", "%d","%s")' % (elem['location'], elem ['userID'], elem['userName'],elem['company'], elem['Ctime'],elem['lastLogin'],elem['ticket'], elem['VPN'],elem['memberOf'])
            cur.execute(sql1)
    db.commit()
    cur.close()
    return


def delAWSTable(db, aws):
        cur = db.cursor()
        tableName = pwdCaller(aws)['data']['table']
        sql = 'DELETE FROM ' + tableName + ' WHERE Location = "%s"' % (aws)
        cur.execute(sql)
        db.commit()
        cur.close()
        return

def getdata(db, aws):
    cur = db.cursor()
    tableName = pwdCaller(aws)['data']['table']
    sql = 'SELECT userID,userName, company, created, lastLogin, ticket, vpnUser from  ' + tableName + ' WHERE Location="%s"' % (aws)
    cur.execute(sql)
    rows = list(cur)
    db.commit()
    cur.close()
    return rows

def mfaChecker(client, username):
    mfaUser = client.list_mfa_devices(UserName=username)
    
    try:
       profile = client.get_login_profile(UserName=username)
    except client.exceptions.NoSuchEntityException:
       return 1

    if len(mfaUser['MFADevices']) > 0 :
        if mfaUser['MFADevices'][0].has_key('SerialNumber'):
	    return 1
	else:
	    return 0 
    return 0

def IAMQuerymain(db, aws):
   newSet = []
   mfaSet={}
   print aws
   keyValue = pwdCaller(aws)['data']
   TZ = keyValue['timezone']
   client = AWSClient(aws, 'iam', keyValue['region'])
   uList = client.list_users()['Users']

   for user in uList:
      aList = {}
      userID = user['UserName']
      cn = ''
      Ctime= user['CreateDate'].astimezone(TZ).strftime("%Y%m%d")
      Company = ''
      ticket=''
      VPN = 0
      lastLogon = 'Never Logged in'
      if user.has_key('PasswordLastUsed'):
         lastLogon = user['PasswordLastUsed'].astimezone(TZ).strftime("%Y%m%d%H%M")
      try:
         VPN = mfaChecker(client, userID)
      except ClientError :
         VPN = 0
      aList['location'] = aws
      aList['userID'] = userID
      aList['userName'] = cn
      aList['company'] = Company
      aList['ticket'] = ticket
      aList['Ctime'] = Ctime
      aList['lastLogin'] = lastLogon
      aList['VPN'] = VPN
      aList['memberOf'] = ''
      newSet.append(aList)
      if VPN == 0:
         mfaSet.update({aList['userID']:aList})
   final = compareUsers(getdata(db,aws),newSet,mfaSet)
   delAWSTable(db,aws)
   insdata(newSet,db,aws)
   return final

def compareUsers(oldList, newList,mfaSet):
    final={}
    final['removed']={}
    final['created']={}
    final['mfaSet'] = mfaSet
    oldUlist = []
    newUlist = []
    for oldU in oldList:
        oldUlist.append(oldU['userID'])
    for newU in newList:
        newUlist.append(newU['userID'])
    
    for oldU in oldList:
        if oldU['userID'] not in newUlist:U
            final['removed'].update({oldU['userID']:oldU})
    for newU in newList:
        if newU['userID'] not in oldUlist:
            final['created'].update({newU['userID']:newU}) 
    return final
