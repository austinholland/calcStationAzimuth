#!/bin/env/ python
''' Routine to calculate phase arrivals '''
from obspy.taup import TauPyModel

#specify earth model
model = TauPyModel(model="iasp91")

# the source - receiver distance in degrees
distance = 45
# the source depth in km
depth = 500
# list of phases you are interested in
phaseList = ["P", "S", "PKiKP"]

arrivals = model.get_travel_times(source_depth_in_km=depth,
                                  distance_in_degree=distance,
                                  phase_list=phaseList)

# to get the travel time for a phase...
arr = arrivals[0] 
pTime=arr.time

# if  you want to plot the raypaths... this is totally cool!
arrivals = model.get_ray_paths(source_depth_in_km=depth, 
                               distance_in_degree=distance)

