# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.

class awsTable(models.Model):
    AWSAccountName = models.CharField(max_length=100,null=True)
    JiraTicket = models.CharField(max_length=15,null=True)
    AccountID = models.CharField(max_length=12,null=True)
    AWSCategory = models.CharField(max_length=15,null=True)

class auditTable(models.Model):
    updated = models.DateTimeField(null=True)
    uuid = models.CharField(max_length=32,null=True)
    Owner = models.CharField(max_length=13,null=True)
    Hostname = models.CharField(max_length=100,null=True)
    PublicIP = models.CharField(max_length=100,null=True)
    PrivateIP = models.CharField(max_length=100,null=True)
    Project = models.CharField(max_length=50,null=True)
    Application = models.CharField(max_length=300,null=True)
    OS = models.CharField(max_length=100,null=True)
    Engineer = models.CharField(max_length=50,null=True)
    Zabbix = models.CharField(max_length=3,null=True)
    Splunk = models.CharField(max_length=3,null=True)
    Rundeck = models.CharField(max_length=3,null=True)
    zCommand = models.CharField(max_length=3,null=True)
    masterT = models.CharField(max_length=1,null=True)
    WSUS = models.CharField(max_length=3,null=True)
    Power = models.CharField(max_length=3,null=True)
    users = models.CharField(max_length=300,null=True)

class memRef(models.Model):
    memName = models.CharField(max_length=100,null=True)
    device = models.CharField(max_length=20,null=True)
    item = models.CharField(max_length=100,null=True)
    updated = models.DateTimeField(null=True)

class grpRef(models.Model):
    grpName = models.CharField(max_length=100,null=True)
    device = models.CharField(max_length=20,null=True)
    members = models.CharField(max_length=1000,null=True)

class ADgrpRef(models.Model):
    location = models.CharField(max_length=20,null=True)
    teamName = models.CharField(max_length=100,null=True)
    members = models.CharField(max_length=1000,null=True)

class ADUser(models.Model):
    uuid = models.CharField(max_length=100,null=True)
    Location = models.CharField(max_length=15)
    userID = models.CharField(max_length=100)
    userName = models.CharField(max_length=40)
    company = models.CharField(max_length=100,null=True)
    created = models.CharField(max_length=8)
    lastLogin = models.CharField(max_length=16)
    ticket = models.CharField(max_length=11,null=True)
    vpnUser = models.BooleanField(default=False)
    userIDstatus = models.CharField(max_length=100,null=True)
    memberOf = models.CharField(max_length=120,null=True,default=' ')
    
#test

#12332
#1321231
#1231234
#13129837
