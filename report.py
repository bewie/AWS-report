#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Draw graph from AWS csv report
"""
__author__ = "Mathieu Lecarme <mathieu@garambrogne.net>"

import csv
from datetime import datetime
import calendar
import json
import sys
import fnmatch

class SDB(object):
	def filter(self, line):
		return {
		'service' : line[0],
		'operation': line[1],
		'usageType': line[2],
		'start' : datetime.strptime(line[3], '%m/%d/%y %H:%M:%S'),
		'end'   : datetime.strptime(line[4], '%m/%d/%y %H:%M:%S'),
		'value' : float(line[5])
		}
	def draw_request(self, report):
		report.draw('sdb_request', ('SelectGet', 'Requests'), ('PutAttributes','Requests'), ('GetAttributes', 'Requests'), ('ListDomains', 'Requests'))
	def draw_bytes(self, report):
		report.draw('sdb_bytes', ('GetAttributes','EC2DataTransfer-In-Bytes'), ('SelectGet','EC2DataTransfer-Out-Bytes'), ('PutAttributes','EC2DataTransfer-Out-Bytes'),('ListDomains','DataTransfer-Out-Bytes'))
	def draw_all(self, report):
		self.draw_request(report)
		self.draw_bytes(report)

class S3(object):
#S3 facturation:
#Nb requests & Data transfert
#UE:
#   POST/PUT/LIST/COPY
#   GET & Others
#US:
#   POST/PUT/LIST/COPY
#   GET & Others
	def draw_request(self, report):
		report.draw('s3_requests_EU', ('GetObject', 'EU-Requests-Tier?'), ('PutObject', 'EU-Requests-Tier?'), ('ListBucket', 'EU-Requests-Tier?'), ('HeadObject', 'EU-Requests-Tier?'), ('s3_request_sum', '*Requests-Tier?'))
		report.draw('s3_requests_US', ('GetObject', 'Requests-Tier?'), ('PutObject', 'Requests-Tier?'), ('ListBucket', 'Requests-Tier?'), ('HeadObject', 'Requests-Tier?'))
	def draw_bytes(self, report):
		report.draw('s3_bytes_EU', ('GetObject','EU-DataTransfer-Out-Bytes'), ('PutObject','EU-C3DataTransfer-In-Bytes'), ('ListBucket','EU-DataTransfer-Out-Bytes'),('s3_bytes_sum','*DataTransfer-*') )
		report.draw('s3_bytes_US', ('GetObject','DataTransfer-Out-Bytes'), ('PutObject','C3DataTransfer-In-Bytes'), ('ListBucket','DataTransfer-Out-Bytes'))
	def draw_objects(self, report):
		report.draw('s3_objects', ('StandardStorage_sum','StorageObjectCount'))
	def draw_all(self, report):
		self.draw_request(report)
		self.draw_bytes(report)
		self.draw_objects(report)
	def filter(self, line):
		return {
		'service' : line[0],
		'operation': line[1],
		'usageType': line[2],
		'resource' : line[3],
		'start' : datetime.strptime(line[4], '%m/%d/%y %H:%M:%S'),
		'end'   : datetime.strptime(line[5], '%m/%d/%y %H:%M:%S'),
		'value' : float(line[6])
		}

class SQS(object):
	def filter(self, line):
		return {
		'service' : line[0],
		'operation': line[1],
		'usageType': line[2],
		'start' : datetime.strptime(line[3], '%m/%d/%y %H:%M:%S'),
		'end'   : datetime.strptime(line[4], '%m/%d/%y %H:%M:%S'),
		'value' : float(line[5])
		}
	def draw_request(self, report):
		report.draw('sqs_request', ('Receive','Requests-RBP'), ('Send','Requests-RBP'))
	def draw_bytes(self, report):
		report.draw('sqs_bytes', ('Receive','EC2DataTransfer-Out-Bytes'), ('Send','EC2DataTransfer-In-Bytes'))
	def draw_all(self, report):
		self.draw_request(report)
		self.draw_bytes(report)

class CloudFront(object):
	def filter(self, line):#Service, Operation, UsageType, Resource, StartTime, EndTime, UsageValue
		return {
		'service' : line[0],
		'operation': line[1],
		'usageType': line[2],
		'resource' : line[3],
		'start' : datetime.strptime(line[4], '%m/%d/%y %H:%M:%S'),
		'end'   : datetime.strptime(line[5], '%m/%d/%y %H:%M:%S'),
		'value' : float(line[6])
		}
	def draw_request(self, report):
		report.draw('cf_request', ('GET','EU-Requests-Tier1'), ('GET','JP-Requests-Tier1'), ('GET','US-Requests-Tier1'), ('GET','AP-Requests-Tier1') )
	def draw_bytes(self, report):
		report.draw('cf_bytes', ('GET','EU-DataTransfer-Out-Bytes'), ('GET','JP-DataTransfer-Out-Bytes'), ('GET','US-DataTransfer-Out-Bytes'), ('GET','AP-DataTransfer-Out-Bytes'))
	def draw_all(self, report):
		self.draw_request(report)
		#self.draw_bytes(report)

class SES(object):
	def filter(self,line):#Service, Operation, UsageType, StartTime, EndTime, UsageValue
		return {
		'service' : line[0],
		'operation': line[1],
		'usageType': line[2],
		'start' : datetime.strptime(line[3], '%m/%d/%y %H:%M:%S'),
		'end'   : datetime.strptime(line[4], '%m/%d/%y %H:%M:%S'),
		'value' : float(line[5])
		}
	def draw_request(self, report):
		report.draw('ses_request', ('SendEmail','Requests'), ('SendEmail','Recipients'), ('SendEmail','Requests-EC2'))
	def draw_bytes(self, report):
		report.draw('ses_bytes', ('SendEmail','DataTransfer-In-Bytes'), ('SendEmail','DataTransfer-Out-Bytes'), ('SendEmail', 'EC2DataTransfer-In-Bytes'))
	def draw_all(self, report):
		self.draw_request(report)
		self.draw_bytes(report)
	

filters = {
	'AmazonS3': S3,
	'AmazonSimpleDB': SDB,
	'AWSQueueService': SQS,
	'AmazonCloudFront': CloudFront,
	'AmazonSES': SES
}

class Report:
	def __init__(self, f):
		self.f = f
		self.filters = {}
	def __iter__(self):
		r = csv.reader(open(self.f), delimiter=',')
		r.next()
		for line in r:
			#print "DEBUG:%s" % (line[0])
			if not self.filters.has_key(line[0]):
				self.filters[line[0]] = filters[line[0]]()
			yield self.filters[line[0]].filter(line)
	def makelist(self, listOp, listUsage):
	  for line in self.__iter__():
            if not (line['operation'] in listOp):
                listOp.append(line['operation'])
            if not (line['usageType'] in listUsage):
                listUsage.append(line['usageType'])

	def printlist(self, listOp, listUsage):
          print "Operation / Type d'utilisation : Nb"
          for Usage in listUsage:
            for Op in listOp:
              S = r.sum(Op, Usage)
              if ( S > 0) :
                print "%s/%s : %s" % (Usage, Op, S)

	def sum(self, action, metric):
		total = 0.0
		for line in self.__iter__():
			if (line['operation'], line['usageType']) == (action, metric):
				total += line['value']
		return total
	def draw_all(self):
		for f in self.filters.values():
			f.draw_all(self)


	def draw(self, title, *filters):
		data = []
		print title
		for filtr in filters:
			print filtr
			values = []
			for line in self:
                            if not ( fnmatch.fnmatchcase(filtr[0], '*sum*') ):
				if line['operation'] == filtr[0] and fnmatch.fnmatch(line['usageType'], filtr[1]):
					values.append([calendar.timegm(line['start'].timetuple()) * 1000, line['value']])
                            else:
				if fnmatch.fnmatch(line['usageType'], filtr[1]):
                                        #make sum 
                                        if ( values and values[-1][0] == calendar.timegm(line['start'].timetuple()) * 1000 ):
                                            prev_v = values.pop()[1]
				            values.append([calendar.timegm(line['start'].timetuple()) * 1000, line['value'] + prev_v])
                                        else:
					    values.append([calendar.timegm(line['start'].timetuple()) * 1000, line['value']])

			data.append({
				'label': ':'.join(filtr),
				'data': values,
				'hoverable': True
			})
		tpl = open('index.tpl','r')
		target = open('%s.html' % title, 'w')
		target.write(tpl.read() % {'data': json.dumps(data, indent=4)})
		tpl.close()
		target.close()

if __name__ == '__main__':
	if len(sys.argv) == 1:
		rep = 'report.csv'
	else:
		rep = sys.argv[1]
	r = Report(rep)

#debug
#	l = 0
#	for line in r:
#		print "line: %s |%s" % (line,l)
#		l += 1

        listOp = []
        listUsage = []
        r.makelist(listOp, listUsage)
        #r.printlist(listOp, listUsage)

        r.draw_all()
