# -*- coding: utf-8 -*-
"""
Created on Mon Feb 3 2020
@author: mstrugari
"""

import os
import argparse
import numpy as np

# check if output folder esists, exit if it does
def outputFolderExists(Output):
        if os.path.isdir(Output) == 1:
                print("Output folder already exists. Exiting...")
                exit()
        else:
                os.makedirs(Output)
        return

# split the simulation by number of primaries or time
def split(Splits,TotalPrimaries,Duration,Prj,AcqType):
        if AcqType == 'T':
                SubLimit = splitTime(Duration,Splits,Prj)
        else:
                SubLimit = splitPrimaries(TotalPrimaries,Splits)
        return SubLimit

def splitPrimaries(Primaries, Splits):
        NbPrimaries = np.ceil(Primaries/Splits).astype(int)
        return NbPrimaries

def splitTime(Duration,Splits,Prj):
        if Prj > 1:
            Time = np.divide(Duration,Prj)
        else:
            Time = np.divide(Duration,Splits)
        return Time

# create the alias to call GATE
def createAlias(currentSplit,Output,Activity,initialTime,finalTime,Duration,Prj,Iso,SubLimit,xPos,yPos,zPos,AcqType,Splits,Nruns,submittedNb):
        Tc_halfLife = 6.00718 * 60 * 60  # seconds
        In_halfLife = 2.8049 * 24 * 60 * 60  # seconds
        I_halfLife = 13.2234 * 60 * 60 # seconds
        Ga67_halfLife = 3.2613 * 24 * 60 * 60 # seconds
        alias = {}
        alias['job'] = currentSplit
        alias['outputFolder'] = Output
        if AcqType == 'T':
                #initialA = SubLimit
                #timeStart = initialTime #0
                #timeStop = timeStart + Duration
                initialA = Activity

                if Prj > 1:
                    # Ensure that each subsimulation has whole runs
                    timeSlice = SubLimit
                    timeStart = initialTime + submittedNb*timeSlice
                    timeStop = timeStart + Nruns*timeSlice
                    if finalTime < (initialTime + Duration):
                        finalTime = initialTime + Duration

                else:
                    timeStart = initialTime + (currentSplit-1)*SubLimit
                    timeSlice = SubLimit
                    timeStop = timeStart + SubLimit
                    if finalTime < (initialTime + Duration):
                        finalTime = initialTime + Duration

                alias['initialTime'] = initialTime
                alias['timeStart'] = timeStart
                alias['timeSlice'] = timeSlice
                alias['timeStop'] = timeStop
                alias['finalTime'] = finalTime
                alias['proj'] = Prj
                alias['xPos'] = xPos
                alias['yPos'] = yPos
                alias['zPos'] = zPos
                if len(initialA) == 1:
                    alias['A'] = initialA[0]*np.exp(-np.log(2)*timeStart/Tc_halfLife)  #use exponential decay; timeStart and timeStop do not account for exponential decay of activity
                elif len(initialA) > 1:
                    for i in range(len(initialA)):
                        tempStr = 'A'+str(i+1)
                        alias[tempStr] = initialA[i]*np.exp(-np.log(2)*timeStart/Tc_halfLife)
                    if Iso[1] == 'In111':
                        alias['A2'] = initialA[1]*np.exp(-np.log(2)*timeStart/In_halfLife)
                    elif Iso[1] == 'I123':
                        alias['A2'] = initialA[1]*np.exp(-np.log(2)*timeStart/I_halfLife)
                if isinstance(Iso,list):
                    alias['iso2'] = Iso[1]

        else:
                alias['NbPrimaries'] = SubLimit

        aliasStr = ''
        for k in alias.keys():
                aliasStr += '[' + str(k) + ',' + str(alias[str(k)]) + '] '

        return aliasStr.rstrip()




parser = argparse.ArgumentParser(description='This is a script to submit multiple simulation jobs running in parallel. Execute this script in the folder containing your data, mac, and output folders.')
parser.add_argument('-n','--numberofsplits', help='The number of job splits; default = 12',type=int,default=12,required=False)
parser.add_argument('-ac','--acquisitionType',choices=['T','Nb'],help='Specify the type of acquisition: \nT = time limited; \nNb = count limited',type=str,required=True)
parser.add_argument('-Ti','--initialTime',help='Initial time in seconds to begin acquisition; default = 0.0', type=np.float64,default=0.0,required=False)
parser.add_argument('-Tf','--finalTime',help='Final time in seconds to end acquisition; default = 1.0', type=np.float64,default=1.0,required=False)
parser.add_argument('-D','--duration', help='Acquisition duration in seconds; default = 1.0', type=np.float64,default=1.0,required=False)
parser.add_argument('-p','--projections', help='Number of projection angles; default = 1', type=int,default=1,required=False)
parser.add_argument('-Nb','--NbPrimaries', help='Total number of primaries', type=int,default=0,required=False)
parser.add_argument('-Iso','--isotopes', help='Isotopes in simulations',nargs='*',type=str,default='Tc99m',required=False)
parser.add_argument('-A','--initialActivity', help='Initial activity in MBq at t = 0 s. Activities for multiple sources A1 to AN can be specified when separated by spaces',nargs='*',type=np.float64,default=0.0,required=False)
parser.add_argument('-x','--xSourcePos', help='x position of source; default = 0.0 mm.', type=np.float64,default=0.0,required=False)
parser.add_argument('-y','--ySourcePos', help='y position of source; default = 0.0 mm. Alias source to collimator distance, 76.95 mm corresponds to 10 cm.', type=np.float64,default=0.0,required=False)
parser.add_argument('-z','--zSourcePos', help='z position of source; default = 0.0 mm.', type=np.float64,default=0.0,required=False)
parser.add_argument('-m','--macro', help='Input GATE macro filename',required=True)
parser.add_argument('-oF','--outputFolder', help='Path to the output folder',required=True)

args = parser.parse_args()

Splits = args.numberofsplits
Acq = args.acquisitionType
initialTime = args.initialTime
finalTime = args.finalTime
Duration = args.duration
Prj = args.projections
Iso = args.isotopes
TotalPrimaries = args.NbPrimaries
Activity = args.initialActivity
xPos = args.xSourcePos
yPos = args.ySourcePos
zPos = args.zSourcePos
Macro = args.macro
OutputFileFolder = args.outputFolder

if Splits > 12:
        print('Number of physical cores exceeded. Please specify no more than 12 jobs.')
        exit()

# Prepare output folder and calculate subdivision of jobs
outputFolderExists(OutputFileFolder)
SubLimit = split(Splits,TotalPrimaries,Duration,Prj,Acq)

# Determine number of individual runs to divy across final subsimulations to ensure subsimulations have whole runs
submittedNb = 0
Nruns=0
if Prj > 1:
    Nruns = np.floor(np.divide(Prj,Splits)) # Nb projections per simulation
    addOnRuns = Prj - Splits*Nruns

for i in range(Splits):
        # Ensure that the total number of primaries does not exceed the requested amount
        if Acq == 'Nb' and (submittedNb + SubLimit) > TotalPrimaries:
            SubLimit = TotalPrimaries - submittedNb
        if Prj > 1 and i >= (Splits-addOnRuns):
            Nruns = np.floor(np.divide(Prj,Splits))+1

        CurrentOutputFolder = os.path.join(OutputFileFolder,str(i+1))
        os.makedirs(CurrentOutputFolder)
        tempStr = createAlias(i+1,CurrentOutputFolder,Activity,initialTime,finalTime,Duration,Prj,Iso,SubLimit,xPos,yPos,zPos,Acq,Splits,Nruns,submittedNb)
        tspOpen = "tsp -n bash -c \""
        gateCmd = "Gate -a \'" + tempStr + "\' " + Macro + ' &> ' + CurrentOutputFolder + '/simulation.log'
        tspClose = "\""
        cmd = tspOpen + gateCmd + tspClose
        print(cmd)
        os.system(cmd)

        if Prj > 1:
            submittedNb += Nruns
        elif Prj == 1:
            submittedNb += SubLimit

print('All jobs submitted')
