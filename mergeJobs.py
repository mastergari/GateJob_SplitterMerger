# -*- coding: utf-8 -*-
"""
Created on Tues Feb 4 2020
@author: mstrugari
"""

import os
import argparse
import SimpleITK as sitk
import numpy as np
import glob
import shutil
from pathlib import Path


def checkIfFolderExists(Output):
        # Create output directory if it does not exist
        if os.path.isdir(Output) == 1:
                print("Output folder " + Output + " exists.")
        else:
                os.makedirs(Output)
                print("The following directory was created:", Output, '')
        return


def checkIfFileExists(Output,Filename,Extension,Flag):
        filename = os.path.join(Output,Filename)+Extension

        # Remove filename being overwritten
        if Flag == True:
                if os.path.exists(filename):
                        os.remove(filename)
                        print(filename + ' is being overwritten.')
        # Append next available index to filename to avoid overwriting
        else:
                i=0
                while os.path.exists(filename):
                        i+=1
                        print(filename + ' already exists. ')
                        filename = os.path.join(Output,Filename)+str(i)+Extension
                print('Data will be written to', filename, '\n')

        return filename


def loadITK(filename):
    itkImage = sitk.ReadImage(filename)
    image = sitk.GetArrayFromImage(itkImage)
    origin = itkImage.GetOrigin()
    spacing = itkImage.GetSpacing()

    return image, origin, spacing


def locateFiles(path,dataType):
        primary = []
        secondary = []
        primaryKey = ''
        secondaryKey = ''

        # Assign keywords for names of files to be retrieved
        if dataType == 1:
                primaryKey = '*Dose.mhd'
        elif dataType == 2:
                primaryKey = '*Dose.mhd'
                secondaryKey = '*Dose-Squared.mhd'
        elif dataType == 3:
                primaryKey = '*.root'
        elif dataType == 4:
                primaryKey = '*.mhd'
        else:
                print("Unexpected selection. Exiting...\n")
                exit()

        # Record filenames in a list
        for f1 in glob.glob(os.path.join(path,'**',primaryKey),recursive=True):
                BaseDir = os.path.basename(os.path.dirname(f1))
                if BaseDir != 'results':
                        primary.append(f1)
        if secondaryKey != '':
                for f2 in glob.glob(os.path.join(path,'**',secondaryKey),recursive=True):
                        BaseDir = os.path.basename(os.path.dirname(f2))
                        if BaseDir != 'results':
                                secondary.append(f2)

        # Record filenames in a list
        #for _,dirnames,_ in os.walk(path):
        #        for d in dirnames:
        #                if d != 'results':
        #                        for f1 in glob.glob(os.path.join(path,d,'**',primaryKey),recursive=True):
        #                                primary.append(f1)
        #                        if secondaryKey != '':
        #                                for f2 in glob.glob(os.path.join(path,d,'**',secondaryKey),recursive=True):
        #                                        secondary.append(f2)

        # Print results from file search
        if primary == []:
                if dataType == 1 or dataType == 2 or dataType == 4:
                        print('The expected .mhd files were not located in the specified input folder. Exiting...')
                elif dataType == 3:
                        print('The expected .root files were not located in the specified input folder. Exiting...')
                exit()
        elif primary != [] and secondary == [] :
                print('The following ' + str(len(primary)) + ' files will be merged:',*primary,'\n',sep="\n")
        else:
                print('The following files will be used to calculate the Dose-Uncertainty. \nDose files: \n', *primary, '\nDose-squared files: \n', *secondary, '\n',sep='\n')

        return primary, secondary


def sumImage(inputFiles):
        Image = []
        Origin = []
        Spacing = []
        tempImage = []
        tempOrigin = []
        tempSpacing = []

        for f in inputFiles:
                tempImage, tempOrigin, tempSpacing = loadITK(f)

                if len(Image) == 0:
                        Image = tempImage
                        Origin = tempOrigin
                        Spacing = tempSpacing
                else:
                        # Verify image dimensions are the same between files and add arrays together
                        if tempImage.shape != Image.shape:
                                print("Image dimensions do not match. Exiting...")
                                exit()
                        elif tempOrigin != Origin:
                                print("Image origins are misaligned. Exiting...")
                                exit()
                        elif tempSpacing != Spacing:
                                print("Image voxels differ in size. Exiting...")
                                exit()
                        else:
                                Image += tempImage
        
        return Image


def calcUncertainty(doseFiles,doseSquaredFiles,NbPrimaries):
        N = NbPrimaries

        # Combine separate arrays into one array and mask images where dose = 0 and dose^2 = 0
        dose = sumImage(doseFiles)
        sq_dose = sumImage(doseSquaredFiles)
        dose = np.ma.masked_equal(dose, 0.0)
        sq_dose = np.ma.masked_equal(sq_dose,0)

        # calculate standard deviation using GATE formula from GateDoseActor.cc
        std_dose = np.sqrt( (1.0/(N-1))*(sq_dose/N - pow(dose/N, 2)) )/(dose/N)
        std_dose[std_dose > 1.0] = 1.0

        print('The maximum relative uncertainty is: ', np.max(std_dose))
        print('The minimum relative uncertainty is: ', np.min(std_dose))

        # Convert masked images into data type expected by .mhd header
        std_dose = np.ma.filled(std_dose, 1.0).astype(np.float32)

        return std_dose


def haddROOTfiles(outputFolder,inputFiles,Flag):
        # Check if output file exists and rename accordingly
        filename = 'output'
        fileExt = '.root'
        filename = checkIfFileExists(outputFolder,filename,fileExt,Flag)

        # Combine .root files using the hadd application provided by ROOT
        cmd = "hadd " + filename + ' ' + ' '.join(str(i) for i in inputFiles)
        print(cmd)
        os.system(cmd)

        exit()


def writeImage(outputFolder,image,files,dataType,Flag):
        # Check if output files exist and rename accordingly
        if dataType == 1:
                filename = 'Dose'
                rawExt = '.raw'
        elif dataType == 2:
                filename = 'Dose-Uncertainty'
                rawExt = '.raw'
        elif dataType == 4:
                filename = 'projections'
                rawExt = '.sin'
        mhdFile = checkIfFileExists(outputFolder,filename,'.mhd',Flag)
        rawFile = checkIfFileExists(outputFolder,filename,rawExt,Flag)

        # Update .mhd header and write data to files
        lines = open(files[0], 'r').readlines()
        lineOfInterest = 'ElementDataFile = '
        for i in range(len(lines)):
                if lineOfInterest in lines[i]:
                        lines[i] = lineOfInterest + os.path.basename(rawFile) + '\n'
        
        if any(lineOfInterest in s for s in lines):
                open(mhdFile, 'w').writelines(lines)
                image.tofile(rawFile)
                print('Data has been written to ' + mhdFile + ' and ' + rawFile + '\n')
        else:
                print('The copied mhd header does not appear to contain \"ElementDataFile\". Exiting...')

        exit()



# Retrieve arguments from terminal input
parser = argparse.ArgumentParser(description='''This is a script to merge output from multiple GATE simulations. This merger is designed to merge ROOT and mhd/raw files 
                                                contained in subdirectories from the batch output. Files in the \"results\/\" directory are ignored. The expected files are 
                                                Dose.mhd and Dose-Squared.mhd produced by the GATE Dose Actor, as well as ROOT files. The files are simply 
                                                summed whereas Dose-Uncertainty.mhd is calculated from Dose.mhd, Dose-Squared.mhd, and number of primary particles.''')
parser.add_argument('-i','--inputFolder', help='Path to folder containing the batch subdirectories of completed jobs',required=True)
parser.add_argument('-n','--NbPrimaries', help='Total number of primaries simulated across all subsimulations',type=int,default=0,required=False)
parser.add_argument('-d','--dataType',choices=[1,2,3,4],help='Specify the type of combined output desired: \n1 = Dose image; \n2 = Dose uncertainty; \n3 = ROOT data; \n4 = SPECT Interfile/MetaImage',type=int,required=True)
parser.add_argument('-f','--forceOverwrite', help='Force the output to overwrite existing files with the same name',action='store_true',required=False)
parser.add_argument('-oF','--outputFolder', help='Path to the output folder',default='results',required=False)

args = parser.parse_args()
Path = args.inputFolder
NbPrimaries = args.NbPrimaries
DataType = args.dataType
overwriteFlag = args.forceOverwrite
OutputFileFolder = args.outputFolder

# First, check to see if files exist
primaryFiles, secondaryFiles = locateFiles(Path,DataType)

# Check to see if output folder exists
destination = os.path.join(Path,OutputFileFolder)
checkIfFolderExists(destination)

# Combine images and/or calculate uncertainty
if DataType == 1:
        image = sumImage(primaryFiles)
        writeImage(destination,image,primaryFiles,DataType,overwriteFlag)
elif DataType == 2 and NbPrimaries is not None:
        uncertainty = calcUncertainty(primaryFiles,secondaryFiles,NbPrimaries)
        writeImage(destination,uncertainty,primaryFiles,DataType,overwriteFlag)
elif DataType == 3:
        haddROOTfiles(destination,primaryFiles,overwriteFlag)
elif DataType == 4:
        image = sumImage(primaryFiles)
        writeImage(destination,image,primaryFiles,DataType,overwriteFlag)
else:
    print('Incorrect program call. Exiting...')
    exit()
