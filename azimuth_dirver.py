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
  cmd="./getAzi.py -resDir %s -n US -cha 'LH*' -eventTime '%s' -eventLat %f -eventLon %f -eventDepth %d -sta '*'" % (dir,ot,float(lvals[1]),float(lvals[2]),float(lvals[3]))
  print(cmd)
  os.system(cmd)
fh.close()

def add_azi_measurment(stadict,stakey,time,difference,linearity):
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
  # If the absolute value of linearity 
  ignore_linearity=0.87
  for keys in stadict.keys():