""" This python script is a driver to process event based station azimuths using
gatAzi.py on github kschramm-usgs
"""
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from matplotlib.dates import date2num
from obspy.core import *

def add_azi_measurement(stadict,stakey,time,difference,linearity):
  """ This method is a hack to allow evaluating stations using multiple events and somewhat
  breaks the original concept for this program.  Ideally this program would be built more
  modular such that another script could access functions here, but since that is not
  the case we will use this hack.
  This solution uses a dictionary with the NSL (Station,Network,Location) as the
  key it then saves the data in a nested list.
  """
  if stakey in stadict.keys():
      stadict[stakey].append([time,difference,linearity])
  else:
      stadict[stakey]=[[time,difference,linearity]]
  return stadict
  
def plot_network_azi(stadict):
  """ This method takes a dictionary of azimuth measurements for multiple events and 
  creates plots for station netwok location NSL keys.
  """
  for key in stadict.keys():
    data=np.array(stadict[key])
    text="Mean %.2f - Std %.2f\nMedian %.2f" % (np.mean(data[:,1]),np.std(data[:,1]),np.median(data[:,1]))
    plt.figure()
    plt.subplot(211)
    plt.plot_date(data[:,0],data[:,1])
    plt.figtext(.6,.8,text)
    plt.ylabel('Offset (degrees)')
    plt.subplot(212)
    plt.plot_date(data[:,0],data[:,2])
    plt.ylabel('Linearity') 
    plt.savefig("Azimuth_%s.png" % (key))
    plt.close()
  
  
def process_results(stadict,dir,ot):
  """ Read in data from the results for each event and add it to the station dictionary
  """
  # If the absolute value of linearity 
  ignore_linearity=0.90
  # Process our output
  csvfile="%s/Results.csv" % (dir)
  csv=open(csvfile,'r')
  hl=csv.readline() # Read the header
  for line in csv:
    lvals=line.split(',')
    nsl="%s-%s-%s" % (lvals[0],lvals[1],lvals[2])
    difference=float(lvals[3])-float(lvals[4])
    linearity=np.abs(float(lvals[6]))
    if linearity>=ignore_linearity:  #Could move this to the plot section but it adds complexity if you do
      stadict=add_azi_measurement(stadict,nsl,ot,difference,linearity)
  return stadict


if __name__=="__main__":

  # Process Data
#   fh=open('query.csv')
#   header=fh.readline()
#   resdirs=[]
#   for line in fh:
#     lvals=line.split(',')
#     ot=lvals[0]
#     # Split the time to make result directories
#     tsplit=ot.split(':')
#     dir=tsplit[0]
#     ot=UTCDateTime(ot)
# 
#     resdirs.append(dir)
#     cmd="./getAzi.py -resDir %s -n US -cha 'LH*' -eventTime '%s' -eventLat %f -eventLon %f -eventDepth %d -sta '*'" % (dir,ot,float(lvals[1]),float(lvals[2]),float(lvals[3]))
#     print(cmd)
#     os.system(cmd)
#     
#   fh.close()
  
  
  # Synthesize results
  stadict={}
  fh=open('query.csv')
  header=fh.readline()
  for line in fh:
    lvals=line.split(',')
    ot=lvals[0]
    # Split the time to make result directories
    tsplit=ot.split(':')
    dir=tsplit[0]
    ot=UTCDateTime(ot)

    stadict=process_results(stadict,dir,ot.datetime)
    
  fh.close()
  plot_network_azi(stadict)
