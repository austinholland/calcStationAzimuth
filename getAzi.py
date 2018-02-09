#!/usr/local/bin/python3

from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.geodetics.base import locations2degrees
from obspy.geodetics.base import gps2dist_azimuth
from obspy.taup import TauPyModel
from obspy.clients import iris
from obspy import Stream
from numpy import sin, cos
from numpy import arctan as atan
from scipy.sparse.linalg import lsqr
from scipy.linalg import eig

import numpy as np
import matplotlib.pyplot as plt
import sys
import argparse
import os

# Add path to dependencies
sys.path.append('/Users/aaholland/Documents/ANSS/Orientation/waveformUtils')
from getCommandLineInfo import getargs
''' 
This function will calculate the azimuth of a station from particle motion.

This is a translation of Adam Ringler's matlab function.  

'''

    
  

########################################################################

def rotatehorizontal(stream, angle1, angle2):
    """
    A function to rotate the horizontal components of a seismometer from 
    radial and transverse into E and North components.

    taken from syncomp.py.  
    
    changed math.radians to np.radians
    """
    debugRot = False
    if stream[0].stats.channel in set(['LHE', 'LHN', 'BHE', 'BHN']):
        stream.sort(['channel'], reverse=True)
        angle1, angle2 = angle2, angle1
    if debugRot:
        print(stream)
        print( 'Angle1: ' + str(angle1) + ' Angle2: ' + str(angle2))
    theta_r1 = np.radians(angle1)
    theta_r2 = np.radians(angle2)
    swapSecond = False
    if (angle2 >= 180. and angle2 <= 360.) or angle2 == 0.:
        swapSecond = True 
# if the components are swaped swap the matrix
    if theta_r1 > theta_r2 and swapSecond:
        if debugRot:
            print('Swap the components: ' + str((360. - angle1) - angle2))
        stream.sort(['channel'], reverse=True)
        theta_r1, theta_r2 = theta_r2, theta_r1
        print(stream)
# create new trace objects with same info as previous
    rotatedN = stream[0].copy()
    rotatedE = stream[1].copy()
# assign rotated data
    rotatedN.data = stream[0].data*np.cos(-theta_r1) +\
        stream[1].data*np.sin(-theta_r1)
    rotatedE.data = -stream[1].data*np.cos(-theta_r2-np.pi/2.) +\
        stream[0].data*np.sin(-theta_r2-np.pi/2.)
    rotatedN.stats.channel = 'BHN'
    rotatedE.stats.channel = 'BHE'
# return new streams object with rotated traces
    streamsR = Stream(traces=[rotatedN, rotatedE])
    return streamsR

########################################################################

# Start of the main part of the program
if __name__ == "__main__":

#use a modified version of AdamR's parser function to get information 
    parserval = getargs()
# event in bolivia
    eventTime = UTCDateTime(parserval.eventTime)
    eventLat = parserval.eventLat
    eventLon = parserval.eventLon
    eventDepth = parserval.eventDepth
    print(eventTime,eventLat,eventLon,eventDepth)

#check for existence of the result directory
    resultdir = parserval.resDir
    if resultdir[-1] == '/':
        resultdir = resultdir[:-1]

    if not os.path.exists(os.getcwd() + '/' + resultdir):
        os.mkdir(os.getcwd() + '/' + resultdir)

    statfile = open(os.getcwd()+'/'+parserval.resDir+'/Results.csv','w')
    statfile.write('station, channel, location, expected Baz, calc Baz 1, difference, calcBaz2, difference, linearity\n')

# event in philipines
#eventTime = UTCDateTime("2017-01-10T06:13:48")
#eventLat = 4.478
#eventLon = 122.617
#eventDepth = 627.2

    net = parserval.network
    stat = parserval.sta
    chan = parserval.cha
    resDir = parserval.resDir

# get station info
# first build the inventory of stations
    print("building station list for the event")
    print (net,stat,chan,eventTime)
    client = Client("IRIS")
    inventory = client.get_stations(network=net, station=stat, channel=chan,level="response", location="*",starttime=eventTime)
    #inventory.plot()
# next, get the station coordinates
    print("getting station coordinates")
    station_coordinates = []
    for network in inventory:
        for station in network:
            for channel in station:
                if channel.code=='LH1':
                    station_coordinates.append((network.code, station.code, 
                                            station.latitude, station.longitude, 
                                            station.elevation,channel.azimuth,channel.location_code))

# then for each station in the list get the distance and azimuth
# need to think about what source-receiver distances we want to use
# for p-waves.
# pick a model for estimating arrival times
    print("calculating travel times and requesting data")
    model = TauPyModel(model="iasp91")
    irisClient=iris.Client()
    for station in station_coordinates:
# first calculate the source-receiver distance
        DegDist = locations2degrees(eventLat, eventLon,
                                    station[2], station[3])
# need to add tolerance for distance so that we are only using P-arrivals
# need to talk to tyler about which P should be used?  P? Pdiff? pP? PP?
# tyler also feels we really want a direct P at teleseismic distances, so 
# let us start with 25-90
        if DegDist > 25 and DegDist < 90:
            print("Station "+station[1]+" will have a P-wave arrival")
            StationAziExpec = gps2dist_azimuth(eventLat, eventLon,
                                               station[2], station[3]) 
            print("station lat, lon:"+str(station[2])+","+str(station[3]))
            statBaz = StationAziExpec[2]
            print("The expected back azimuth for "+station[1]+" is "+str(statBaz))
            arrivals = model.get_travel_times(source_depth_in_km = eventDepth,
                                              distance_in_degree=DegDist,
                                              phase_list = ["P"])
# now use the arrival time to get some data
            arrTime=eventTime + arrivals[0].time
# ask for data one minute before and 5 minutes after P time
# ask for data 200 s before and 50 s after P time
# the larger window at the beginning is so that we can look at the SNR
            bTime=arrTime-200
            eTime=arrTime+50
            try:
               # st = client.get_waveforms(station[0],station[1],"00","BH?",
               #                           bTime,eTime,attach_response=True)
#                 st = getMSDdata(station[0],station[1],"00","BH",btime,etime)
#                 st.sort(keys=['channel'])
                st=irisClient.timeseries(station[0],station[1],station[6],'LH1',bTime,eTime)
                st+=irisClient.timeseries(station[0],station[1],station[6],'LH2',bTime,eTime)
                st+=irisClient.timeseries(station[0],station[1],station[6],'LHZ',bTime,eTime)
                st.merge()
            except Exception as err:
                print("No data for station "+station[1]+'\n\t'+str(err))
                continue #use a continue to go back to the beginning of the loop

# Break up the stream into traces to remove the gain
            try:
                BH1 = st[0]
                BH2 = st[1]
                BHZ = st[2]

            except:
                print("Station "+ station[1] + " doesn't have 3-comp data.")
                continue

            st[0] = BH1.remove_sensitivity(inventory)
            st[1] = BH2.remove_sensitivity(inventory)
            st[2] = BHZ.remove_sensitivity(inventory)
         
# take a look at the data
            #st.plot()

# make sure we are in NE orientation
# using the function from syncomp.py
            BHN = st[0].copy()
            BHE = st[1].copy()
            BHZ = st[2].copy()
            st2=st.copy() 
            
            statOrientation = station[5]
            statOrientation2 = station[5]+90
            rotated="Not Rotated"
            if (statOrientation != 0.0):
                st += rotatehorizontal(st,statOrientation,
                                        statOrientation2)
                rotated="Rotated"
#
                BHN = st[3].copy()
                BHE = st[4].copy()
            #st2.plot()

# want to look at plots with travel times...
#             plt.subplot(3,1,1)
#             plt.plot(st[0].data,label='BH1')
#             plt.legend()
#             print(arrTime)
#             plt.subplot(3,1,2)
#             plt.plot(st[1].data,label='BH2')
#             plt.legend()
#             plt.subplot(3,1,3)
#             plt.plot(st[2].data,label='BHZ')
#             plt.legend()
#             #plt.show()
# next we need to filter. first some waveform prep...
            BHN.detrend('demean')
            BHE.detrend('demean')
            BHZ.detrend('demean')
        
            BHN.taper(max_percentage=0.05)
            BHE.taper(max_percentage=0.05)
            BHZ.taper(max_percentage=0.05)
# now, we actually filter!
            BHN.filter('lowpass', freq=0.05, corners=4, zerophase=True)
            BHE.filter('lowpass', freq=0.05, corners=4, zerophase=True)
            BHZ.filter('lowpass', freq=0.05, corners=4, zerophase=True)
         
# calculate the SNR - I forsee putting in something here to skip calculation
# if the SNR is below a defined tolerance.
# The signal is defined as 1 second before predicted arrival and 8 seconds after
            NoiseBHN = BHN.copy()
            NoiseBHE = BHE.copy()
            NoiseBHZ = BHZ.copy()
            NoiseStart = BHN.stats.starttime + 10
            NoiseEnd = BHN.stats.starttime + 150
            NoiseBHN.trim(NoiseStart, NoiseEnd)
            NoiseBHE.trim(NoiseStart, NoiseEnd)
            NoiseBHZ.trim(NoiseStart, NoiseEnd)
     
            SignalBHN = BHN.copy()
            SignalBHE = BHE.copy()
            SignalBHZ = BHZ.copy()
            SignalStart = arrTime-15
            SignalEnd = arrTime+10
            SignalBHN.trim(SignalStart, SignalEnd)
            SignalBHE.trim(SignalStart, SignalEnd)
            SignalBHZ.trim(SignalStart, SignalEnd)
     
            SNR_BHN = (SignalBHN.std()**2)/(NoiseBHN.std()**2)
            SNR_BHE = (SignalBHE.std()**2)/(NoiseBHE.std()**2)
            SNR_BHZ = (SignalBHZ.std()**2)/(NoiseBHZ.std()**2)
     
            print("Signal to Noise")
            print(SNR_BHN, SNR_BHE, SNR_BHZ)
# normalize
            BHNmax=np.max(abs(SignalBHN.data))
            BHNmin=np.min(abs(SignalBHN.data))
            BHEmax=np.max(abs(SignalBHE.data))
            BHEmin=np.min(abs(SignalBHE.data))
            normFac=np.max([BHNmax,BHNmin,BHEmax,BHEmin])
            SignalBHN.data = SignalBHN.data/normFac
            SignalBHE.data = SignalBHE.data/normFac
            SignalBHZ.data = SignalBHZ.data/normFac
            plt.figure()
            plt.subplot(3,1,1)
            plt.suptitle('Filtered, rotated and cut waveforms for %s'%(station[1]))
            plt.plot(SignalBHN.data,label="LHN-%s" % (station[6]))
            plt.legend()
            #SignalBHN.plot()
            plt.subplot(3,1,2)
            plt.plot(SignalBHE.data,label="LHE-%s" % (station[6]))
            plt.legend()
            plt.subplot(3,1,3)
            plt.plot(SignalBHZ.data,label="LHZ-%s" % (station[6]))
            plt.legend()
            fileName =(os.getcwd() +'/'+ resDir +'/Input_'+
                    station[0] +'_'+ station[1] +'_'+station[6]+'_'+
                    str(eventTime) + '.png')
            print(fileName)
            plt.savefig(fileName,format='png')

    
# time to get serious!  we are ready to do the actual calculation!!!!!!!!
            A = np.transpose(np.matrix(SignalBHE.data))
            b = SignalBHN.data

            lresult = lsqr(A,b)
            ang = np.degrees(np.arctan2(1.,lresult[0]))

# Adam uses this to calculate the linearity.
            BHNsq = sum(SignalBHN.data*SignalBHN.data)
            BHNEsq = sum(SignalBHN.data*SignalBHE.data)
            BHEsq = sum(SignalBHE.data*SignalBHE.data)
            eigMat = np.matrix([[BHNsq, BHNEsq], [BHNEsq, BHEsq]])
            eigd,eigv = eig(eigMat)
            print("The eigenvalues")
            print(eigd)
            line = np.real((eigd[1]/(eigd[0]+eigd[1]))-
                           (eigd[0]/(eigd[0]+eigd[1])))
            ang2 = np.degrees(np.arctan2(eigv[0][1],eigv[1][1]))

# now do some stuff about the quadrant
            if (ang2<0):
                ang2 = abs(ang2)+90
                print("ang2 lt 0")

            if (ang2<0):
                ang2 = ang2+180
                print("ang2 lt 0")

            if abs(statBaz-(ang2+180))<abs(statBaz-ang2):
                ang2 = np.mod(ang2+180,360)
                print("ang2 is 180 off: "+str(ang2) )

            if(abs(statBaz-(ang+180))<abs(statBaz-ang)):
                ang=np.mod(ang+180,360)
                print("ang is 180 off: "+str(ang) )

            if(ang<0):
                ang=ang+180;
                print("ang lt 0")
            print("The calculated values are: "+str(ang)+" and "+str(ang2))
# capture some statistics
# there is likely a better way to do this, but in the interest of time...
#            statfile.write('%s,%s,%s,%s,%s\n'%
#                    station[1],station[2],statBaz,ang,ang2,line)
            statfile.write(station[0]+',')
            statfile.write(station[1]+',')
            statfile.write(station[6]+',')
            statfile.write(str(statBaz)+',')
            statfile.write(str(ang)+',')
            statfile.write(str(ang2)+',')
            statfile.write(str(line)+'\n')

# don't look at the plot if it's not worth your time.
#            if abs(line) < 0.8:
#                print("Linearity value bad.  Skipping station.")
#                continue

# now create a nice plot. 
            plt.figure()
            ax = plt.subplot(111, projection='polar')
            ax.set_theta_zero_location("N")
            ax.set_theta_direction(-1)
# get the particle motion
            #theta = np.arctan2(SignalBHN.data,SignalBHE.data)
            #r = np.sqrt(SignalBHE.data*SignalBHE.data 
            #      + SignalBHN.data*SignalBHN.data)
# get the gradient on the particle motion
            #gradPM = 
# get the information for the lines
            calcR = [1., 1.]
            calcTheta = [np.radians(ang),np.radians(ang+180)]
            calcTheta2 = [np.radians(ang2),np.radians(ang2+180)]
            expcTheta = ([np.radians(StationAziExpec[2]), 
                          np.radians(StationAziExpec[2]+180)])
            label1="Baz_calc = %.2f" % (ang)
            label2="Baz2_calc = %.2f" % (ang2)
            label3="Baz_meas = %.2f" % (StationAziExpec[2])
# actually plot the things
            plt.plot(calcTheta,calcR,'blue',label=label1)
            plt.plot(calcTheta2,calcR,'cyan',label=label2)
            plt.plot(expcTheta,calcR,'black',label=label3)
            #plt.plot(theta,r,'red',label='Particle Motion')
            plt.plot(SignalBHE.data,SignalBHN.data, 'red',label='Particle Motion')
            plt.text(7*np.pi/4,2.5,str(station[1]+' '+ rotated + ' '+str(eventTime)),fontsize=14)
            printstr="linearity %.2f" % (line)
            printstr1="SNR, LHN %.2f" % (SNR_BHN)
            printstr2="SNR, LHE %.2f" % (SNR_BHE)
            plt.text(32*np.pi/20,2.7,(printstr+'\n'+
                     printstr1+'\n'+printstr2))
            fileName =(os.getcwd() +'/'+ resDir +'/Azimuth_'+
                    station[0] +'_'+ station[1] +'_'+station[6]+'_'+
                    str(eventTime) + '.png')
            print(fileName)
            #plt.close()
            #plt.figure()
            #x = SignalBHE.data**2.
            #y = SignalBHN.data**2.
            #plt.plot(x,y,marker="o")
            #p = np.polyfit(x,y,1)
            #print p
            #ycalc = p[0]*x + p[1]
            #plt.plot(x,ycalc,marker="v")
            #pfitR=np.sqrt(x+ycalc**2.)
            #calcR=[max(pfitR), abs(min(pfitR))]
            #pfitTheta= np.arctan2(ycalc,SignalBHE.data)
            #aveTheta=np.average(pfitTheta)
            #plotAveTheta=[aveTheta, aveTheta+np.pi]
            #print np.degrees(aveTheta)

            #print "Max r "+str(max(r))
            #print "Min r "+str(min(r))
            #print "Max index r "+str(np.argmax(r))
            #print "Min index r "+str(np.argmin(r))
            ##print np.degrees(theta)
            #print "theta at r max "+str(np.degrees(theta[np.argmax(r)]))
            #print "theta at r min "+str(np.degrees(theta[np.argmin(r)]))
            #print "Max index theta "+str(np.argmax(theta))
            #print "Min index theta "+str(np.argmin(theta))
            #print "Max theta "+str(np.degrees(np.max(theta)))
            #print "Min theta "+str(np.degrees(np.min(theta)))

            #label4=("Baz_part = %.2f" % (np.degrees(aveTheta)))
            #plt.plot(plotAveTheta, calcR,'orange',label=label4)
            #plt.plot(pfitTheta, pfitR,'orange',label=label4)

            plt.legend(bbox_to_anchor=(0.8, 0.85, 1., 0.102),loc=3,borderaxespad=0.)
            plt.savefig(fileName,format='png')

                    

        else:
            print("Station "+ station[1] +" doesn't fit in parameters for P-wave arrivals")
