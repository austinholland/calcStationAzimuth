""" This python script is a driver to process event based station azimuths using
gatAzi.py on github kschramm-usgs
"""
import os

fh=open('query.csv')
header=fh.readline()
resdirs=[]
for line in fh:
  lvals=line.split(',')
  ot=lvals[0]
  # Split the time to make result directories
  tsplit=ot.split('T')
  dir=tsplit[0]

  resdirs.append(dir)
  cmd="./getAzi.py -resDir %s -n US -cha 'BH1' -eventTime '%s' -eventLat %f -eventLon %f -eventDepth %d -sta '*'" % (dir,ot,float(lvals[1]),float(lvals[2]),float(lvals[3]))
  print(cmd)
  os.system(cmd)
fh.close()