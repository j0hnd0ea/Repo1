#!/usr/bin/python
import ldap, pymysql
from datetime import datetime, timedelta
import hashlib
from pythonModule import DBConnector, pwdCaller

userIDstatusRef = {'1':'SCRIPT', '2':'ACCOUNTDISABLE','8':'HOMEDIR_REQUIRED',
                   '16':'LOCKOUT','32':'PASSWD_NOTREQD','64':'PASSWD_CANT_CHANGE',
                   '128':'ENCRYPTED_TEXT_PWD_ALLOWED','256':'TEMP_DUPLICATE_ACCOUNT',
                   '512':'NORMAL_ACCOUNT','514':'Disabled Account','544':'Enabled, Password Not Required',
                   '546':'Disabled, Password Not Required','2048':'INTERDOMAIN_TRUST_ACCOUNT',
                   '4096':'WORKSTATION_TRUST_ACCOUNT','8192':'SERVER_TRUST_ACCOUNT',
                   '65536':'DONT_EXPIRE_PASSWORD','66048':'Enabled, Password Does not Expire',
                   '66050':'Disabled, Password Does not Expire',
                   '66082':'Disabled, Password Does not Expire & Not Required',
                   '131072':'MNS_LOGON_ACCOUNT','262144':'SMARTCARD_REQUIRED','262656':'Enabled, Smartcard Required',
                   '262658':'Disabled, Smartcard Required',
                   '262690':'Disabled, Smartcard Required, Password Not Required',
                   '328194':'Disabled, Smartcard Required, Password Does not Expire',
                   '328226':'Disabled, Smartcard Required, Password Does not Expire & Not Required',
                   '524288':'TRUSTED_FOR_DELEGATION','532480':'Domain controller','1048576':'NOT_DELEGATED',
                   '2097152':'USE_DES_KEY_ONLY','4194304':'DONT_REQ_PREAUTH','8388608':'PASSWORD_EXPIRED',
                   '16777216':'TRUSTED_TO_AUTH_FOR_DELEGATION','67108864':'PARTIAL_SECRETS_ACCOUNT'}

def returnHash(strA):
    m = hashlib.md5()
    m.update(strA)
    return m.hexdigest()

def compareI(userNI, userOI):
  userUP = {}
  keys = userNI.keys()
  for key in keys:
     if userNI[key]==userOI[key] or key=='uuid':
        userUP[key] = userNI[key]
     else:
        userUP[key] = str(userOI[key]) + " -> " + str(userNI[key])
  return userUP  

def insdata(userN,db):
   updatedU = {}
   createdU = {}
   removedU = {}
   final = {}
   cur = db.cursor(pymysql.cursors.DictCursor)
   tableName = pwdCaller['officeLdap']['data']['table']

   sql = 'SELECT * FROM '+tableName+' WHERE Location = "Office"'
   cur.execute(sql)
   userO = cur.fetchall()
   uuidOL = []
   uuidNL = []
   for uuid in userO:
      uuidOL.append(uuid['uuid'])
   for uuid in userN:
      uuidNL.append(uuid['uuid'])
   
   for userNI in userN:
      if userNI['uuid'] not in uuidOL:
         #Then the account would be new or updated.
         sql = 'SELECT * FROM '+tableName+' WHERE userID = "%s" AND Location = "Office"' % (userNI['userID'])
         cur.execute(sql)
         userOI = cur.fetchall()
         if (len(userOI)) > 0:
            updatedU1 = compareI(userNI, userOI[0])  
            updatedU.update({updatedU1['userID']:updatedU1})
            #Then the account is updated.
            sql1 = 'UPDATE '+tableName+' SET uuid="%s",Location="%s", userName="%s", company="%s", lastLogin="%s",vpnUser="%s",userIDstatus="%s",memberOf="%s" WHERE userID="%s"' % (userNI['uuid'],userNI['Location'], userNI['userName'],userNI['company'],userNI['lastLogin'],userNI['vpnUser'],userNI['userIDstatus'],userNI['memberOf'],userNI['userID'])
            cur.execute(sql1)         
         else:
            #Then the account is created.
            createdU.update({userNI['userID']:userNI})
            sql1 = 'INSERT INTO '+tableName+' (uuid,Location, userID, userName, company, created, lastLogin, ticket, vpnUser,userIDstatus,memberOf) VALUES ("%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s")' % (userNI['uuid'],userNI['Location'],userNI['userID'], userNI['userName'],userNI['company'],userNI['created'],userNI['lastLogin'],userNI['ticket'],userNI['vpnUser'],userNI['userIDstatus'],userNI['memberOf'])
            cur.execute(sql1)
      else:
        #Then the account does not changed but, possibly, only lastlogon.
         sql1 = 'UPDATE '+tableName+' SET lastLogin="%s" WHERE uuid="%s"' % (userNI['lastLogin'],userNI['uuid'])
         cur.execute(sql1)

   for userOI in userO:
      #if userOI['uuid'] not in uuidNL:
      #   print userOI['uuid']
      #   #then the account would be removed or updated.
      flag=True
      for userNI in userN:
         if (userNI['userID'] == userOI['userID']) and (userNI['userName'] == userOI['userName']):
            #if there is the same ID and name and then...
            flag=False
      if flag:
         #if Flag is True, and then it means the account is removed.
         sql = 'DELETE FROM '+tableName+' WHERE Location = "Office" AND uuid="%s"' % (userOI['uuid'])
         cur.execute(sql)  
         removedU.update({userOI['userID']:userOI})
   db.commit()
   cur.close()
   final['created']=createdU
   final['updated']=updatedU
   final['removed']=removedU
   
   return final

def convert_ad_timestamp(timestamp):
    epoch_start=datetime(year=1601, month=1,day=1)
    seconds_since_epoch=int(timestamp)/10**7
    return epoch_start + timedelta(seconds=seconds_since_epoch)

def queryLDAP(aList):
   result_user = []
   for elem in  aList:
      for elem1 in elem:
         aList={}
         userID = elem1[1]['sAMAccountName'][0]
         cn = elem1[1]['cn'][0]
         Ctime=elem1[1]['whenCreated'][0][:8]
         Company = ''
         VPN = 0
         ticket=''
         status=''
         lastLogon = 'Never Logged in' 
         if elem1[1].has_key('info'):
            ticket = elem1[1]['info'][0]
            if len(ticket) > 8 :
               ticket1 = ticket
               ticket = ticket1[-9:].replace('/','')
         if elem1[1].has_key('company'):
            Company = elem1[1]['company'][0]
	 if elem1[1].has_key('description'):
            desc = str(elem1[1]['description'])
            if 'VPN' in desc:
               VPN = 1
         if elem1[1].has_key('lastLogonTimestamp'):
            lastLogon = convert_ad_timestamp(elem1[1]['lastLogonTimestamp'][0]).strftime("%Y%m%d%H%M")
         if elem1[1].has_key('userAccountControl'):
            ustat = str(elem1[1]['userAccountControl'][0])
            status = userIDstatusRef[ustat]
         aList['Location'] = 'Office'
         aList['userID'] = userID
         aList['userName'] = cn
         aList['company'] = Company
         aList['ticket'] = ticket
         aList['created'] = Ctime
         aList['lastLogin'] = lastLogon
         aList['vpnUser'] = str(VPN)
         aList['userIDstatus'] = status
         if elem1[1].has_key('memberOf'):
            aList['memberOf'] = ''
            for grp in elem1[1]['memberOf']:
               aList['memberOf'] = aList['memberOf'] + grp.split(',')[0] + ';'
         else:
            aList['memberOf'] = ''
         aList['uuid'] = returnHash(aList['Location']+aList['userID']+aList['userName']+aList['vpnUser']+aList['userIDstatus']+aList['memberOf'])
         result_user.append(aList)
   return result_user

def OfficeQuerymain(db):
   keyValue = pwdCaller('officeLdapBind')['data']
   try:
      ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
      l = ldap.initialize(keyValue['url'])
      l.set_option(ldap.OPT_REFERRALS,0)
      l.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
      l.set_option(ldap.OPT_X_TLS,ldap.OPT_X_TLS_DEMAND)
      l.set_option(ldap.OPT_X_TLS_DEMAND, True)
      l.set_option(ldap.OPT_DEBUG_LEVEL, 255)
      l.simple_bind
      l.set_option
      l.protocol_version = ldap.VERSION3
      username = keyValue['username']
      password  = keyValue['password']
      l.simple_bind(username, password)
      l.result()
   except ldap.LDAPError, e:
      print e
   # The next lines will also need to be changed to support your search requirements and directory
   baseDN = "OU="+keyValue['basedn']
   searchScope = ldap.SCOPE_SUBTREE
   # retrieve all attributes - again adjust to your needs - see documentation for more options
   retrieveAttributes = None
   searchFilter = "(&(sAMAccountName=*)(!(objectClass=group)))"
   try:
      ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
      result_set = []
      while 1:
         result_type, result_data = l.result(ldap_result_id, 0)
	 if (result_data == []):
            break
         else:
            ## here you don't have to append to a list
            ## you could do whatever you want with the individual entry
            ## The appending to list is just for illustration.
            if result_type == ldap.RES_SEARCH_ENTRY:
               result_set.append(result_data)
      #result_set has all information
      newSet = queryLDAP(result_set)
      final=insdata(newSet,db)
      l.unbind_s() 
   except ldap.LDAPError, e:
      print e
   return final

if __name__ == "__main__" :
    db = DBConnector()
    final = OfficeQuerymain(db)
    print final
