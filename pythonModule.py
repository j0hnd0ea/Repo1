#!/usr/bin/python
import pymysql, hashlib, re, copy, time, os, hvac, smtplib, json, logging, errno, signal, boto3
from datetime import datetime
from rundeck.client import Rundeck
from confluence import Confluence
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory import Inventory
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.plugins import callback_loader
from ansible.plugins.callback import CallbackBase
from functools import wraps
from jira import JIRA

def DBConnector(node='MySQL'):
   keyValue=pwdCaller(node)['data']
   db = pymysql.connect(host=keyValue['host'],
                     user=keyValue['user'],
                     passwd = keyValue['passwd'],
                     db=keyValue['db'],
                     cursorclass=pymysql.cursors.DictCursor)
   return db

class TimeoutException(Exception):
   pass

def getAWSAccountID(aws,db):
   cur = db.cursor()
   table = pwdCaller(aws)['data']['table']
   sql = 'SELECT * from ' + table
   cur.execute(sql)
   listA = cur.fetchall()
   cur.close()
   return listA

def getAWSUserList(db,AWSAccountID):
   cur = db.cursor()
   table = pwdCaller('officeLdap')['data']['table']
   sql = 'SELECT * from codes_aduser WHERE Location = "%s"' % (AWSAccountID)
   cur.execute(sql)
   listA = cur.fetchall()
   cur.close()
   return listA

def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
   def decorator(func):
      def _handle_timeout(signum, frame):
         raise TimeoutError(error_message)
      def wrapper(*args, **kwargs):
         signal.signal(signal.SIGALRM, _handle_timeout)
         signal.alarm(seconds)
         try:
            result = func(*args,**kwargs)
         finally:
            signal.alarm(0)
         return result
      return wraps(func)(wrapper)
   return decorator

def getUserDB(db, location):
    cur = db.cursor()
    sql = 'SELECT * from codes_aduser WHERE Location = "%s"' % (location)
    cur.execute(sql)
    listA = cur.fetchall()
    cur.close()
    return listA

def makeKeyHash(aDict):
   str1 = ''
   for key,value in aDict.iteritems():
      str1 = str1+str(value)
   m = hashlib.md5()
   m.update(str1)
   return m.hexdigest()

def json_serial(obj):
   if isinstance(obj, datetime):
      serial = obj.isoformat()
      return serial
   raise TypeError ("Type not serializable")
   return obj

def convert_ad_timestamp(timestamp):
    epoch_start=datetime(year=1601, month=1,day=1)
    seconds_since_epoch=int(timestamp)/10**7
    return epoch_start + timedelta(seconds=seconds_since_epoch)

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

def pwdCaller(key):
   client = hvac.Client(url='SERVER URL',token='TOKEN')
   pwd =  client.read('KEY PATH'+key)
   return pwd 

def ConfluenceWritePage(space, title, content, parent):
   confl = Confluence(profile='confluence')
   token = confl._token
   server = confl._server
   parent_id = parent
   try:
      existing_page = confl.storePageContent(title, space, content)
      #print "Updated the page"
   except:
      write_page(server, token, space, title, content)
      #print "Created a page"

   return

def write_page(server, token, space, title, content):
    parent_id = parent
    if not parent is None:
        try:
            # Find out the ID of the parent page
            parent_id = server.confluence1.getPage(token, space, parent)['id']
            print parent_id
            print "parent page id is %s" % parent_id
        except:
            print "couldn't find parent page; ignoring error..."
    try:
        print space, title
        existing_page = server.confluence1.getPage(token, space, title)
        print existing_page
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

#AWS Client Module
def AWSClient(aws, service='iam'):
   keyValue = pwdCaller(aws)['data']
   client = boto3.client(service, keyValue['region'], aws_access_key_id=keyValue['aws_access_key_id'], aws_secret_access_key=keyValue['aws_secret_access_key'])
   return client

#AWS SES Caller
def SESRequest(aws, mailDict):
   keyValue = pwdCaller(aws)['data']
   client = AWSClient(aws,'ses', keyValue[region])

   response = client.send_email(
         Source=mailDict['From'],
         Destination={
            'ToAddresses': mailDict['To']
         },
         Message={
            'Subject': {
               'Data': mailDict['Subject'],
               'Charset': 'UTF-8'
            },
            'Body': {
               'Text': {
               'Data': mailDict['Body'],
               'Charset': 'UTF-8'
                }
            }
         }
      )
   if response['ResponseMetadata']['HTTPStatusCode'] == 200:
      return True
   else:
      return False



#Send e-mail
class sMail:
   def __init__(self, Subject, From, To, HTML):
      self.Subject = Subject
      self.Sender = From
      self.Receiver = To
      self.HTML = HTML

   def sendMail(self):
      msg = {}
      receivers=[]
      receivers.append(self.Receiver)
      msg['Subject'] = self.Subject
      msg['From']  = self.Sender
      msg['To'] = receivers
      msg['Body'] = self.HTML
      SESRequest(msg)

#Related to ansible:

class ResultsCollector(CallbackBase):
   def __init__(self, *args, **kwargs):
      super(ResultsCollector, self).__init__(*args, **kwargs)
      self.host_ok = []
      self.host_unreachable = []
      self.host_failed = []

   def v2_runner_on_unreachable(self, result, ignore_errors=False):
      name = result._host.get_name()
      task = result._task.get_name()
      self.host_unreachable.append(dict(ip=name, task=task, result=result))

   def v2_runner_on_ok(self, result,  *args, **kwargs):
      name = result._host.get_name()
      task = result._task.get_name()
      if task == "setup":
         pass
      elif "Info" in task:
         self.host_ok.append(dict(ip=name, task=task, result=result))
      else:
         #ansible_log(result)
         self.host_ok.append(dict(ip=name, task=task, result=result))

   def v2_runner_on_failed(self, result,   *args, **kwargs):
      name = result._host.get_name()
      task = result._task.get_name()
      #ansible_log(result)
      self.host_failed.append(dict(ip=name, task=task, result=result))

class Options(object):
   def __init__(self):
      self.connection = "smart"
      self.forks = 10
      self.check = False
      self.become = None
      self.become_method = None
      self.become_user=None
   def __getattr__(self, name):
      return None

class ansibleC:
   global loader, variable_manager, inventory, options
   loader = DataLoader()
   variable_manager = VariableManager()
   inventory = Inventory(loader=loader, variable_manager=variable_manager)
   variable_manager.set_inventory(inventory)
   options = Options()

   def __init__(self, Host):
      self.host = Host

   def run_adhoc(self,order,user):
      variable_manager.extra_vars={"ansible_ssh_user":user}
      play_source = {
            "name":"Ansible Ad-Hoc",
            "hosts":"%s"%self.host,
            "gather_facts":"no",
            "tasks":[ {"action": {"module":"command", "args":"%s"%order} } ]
            }
         
      play = Play().load(play_source, variable_manager=variable_manager, loader=loader)
      tqm = None
      callback = ResultsCollector()

      try:
         tqm = TaskQueueManager(
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            options=options,
            passwords=None,
            run_tree=False,
            stdout_callback=callback
          )
         #tqm._stdout_callback = callback
         result = tqm.run(play)
         #print callback.host_ok[0]['result']._result
         return callback

      finally:
         if tqm is not None:
            tqm.cleanup()
   def run_playbook(books):
      results_callback = callback_loader.get('json')
      playbooks = [books]

      variable_manager.extra_vars={"ansible_ssh_user":"root" , "ansible_ssh_pass":"passwd"}
      callback = ResultsCollector()

      pd = PlaybookExecutor(
        playbooks=playbooks,
        inventory=inventory,
        variable_manager=variable_manager,
        loader=loader,
        options=options,
        passwords=None,
        )
      pd._tqm._stdout_callback = callback

      try:
         result = pd.run()
         return callback

      except Exception as e:
         print e

#12233
