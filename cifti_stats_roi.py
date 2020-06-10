#!/usr/bin/env python 

# Import modules
import os
import numpy as np
import nibabel as nib
import pandas as pd
import subprocess

# Import modules for argument parsing
import argparse

# Define class(es)

class Command():
    '''
    Creates a command and an empty command list for UNIX command line programs/applications. Primary use and
    use-cases are intended for the subprocess module and its associated classes (i.e. run).
    Attributes:
        command: Command to be performed on the command line
    '''

    def __init__(self):
        '''
        Init doc-string for Command class.
        '''
        pass

    def init_cmd(self, command):
        '''
        Init command function for initializing commands to be used on UNIX command line.
        Arguments:
            command (string): Command to be used. Note: command used must be in system path
        Returns:
            cmd_list (list): Mutable list that can be appended to.
        '''
        self.command = command
        self.cmd_list = [f"{self.command}"]
        return self.cmd_list

# Define functions
def load_hemi_labels(file,wb_struct,map_number=1):
    '''working doc-string'''
    
    gii_label = 'data.label.gii'
    
    load_label = Command().init_cmd("wb_command"); load_label.append("-cifti-separate")
    
    load_label.append(file)
    load_label.append("COLUMN")
    load_label.append("-label"); load_label.append(wb_struct)
    load_label.append(gii_label)
    
    subprocess.call(load_label)
    
    gifti_img = nib.load(gii_label)
    
    atlas_data = gifti_img.get_arrays_from_intent('NIFTI_INTENT_LABEL')[1-1].data
    atlas_dict = gifti_img.get_labeltable().get_labels_as_dict()
    
    os.remove(gii_label)
    
    return atlas_data,atlas_dict

def load_gii_data(file,intent='NIFTI_INTENT_NORMAL'):
    '''working doc-string'''
    
    # Load surface data
    surf_dist_nib = nib.load(file)
    
    # Number of TRs in data
    num_da = surf_dist_nib.numDA
    
    # Read all arrays and concatenate temporally
    array1 = surf_dist_nib.get_arrays_from_intent(intent)[0]
    
    data = array1.data
    
    if num_da >= 1:
        for da in range(1,num_da):
            data = np.vstack((data,surf_dist_nib.get_arrays_from_intent(intent)[da].data))
            
    # Transpose data such that vertices are organized by TR
    data = np.transpose(data)
    
    # If output is 1D, make it 2D
    if len(data.shape) == 1:
        data = data.reshape(data.shape[0],1)
        
    return data

def load_hemi_data(file,wb_struct):
    '''working doc-string'''
    
    gii_data = 'data.func.gii'
    
    load_gii = Command().init_cmd("wb_command"); load_gii.append("-cifti-separate")
    
    load_gii.append(file)
    load_gii.append("COLUMN")
    load_gii.append("-metric"); load_gii.append(wb_struct)
    load_gii.append(gii_data)
    
    subprocess.call(load_gii)
    
    data = load_gii_data(gii_data)
    
    os.remove(gii_data)
    
    return data

def get_roi_name(cluster_data,atlas_data,atlas_dict):
    '''working doc-string'''
    
    # for idx,val in enumerate(cluster_data.astype(int)):
    for idx,val in enumerate(cluster_data):
        if cluster_data[idx] == 0:
            atlas_data[idx] = 0
    
    tmp_list = list()
    roi_list = list()
    
    for i in np.unique(atlas_data)[1:]:
        # print(atlas_dict[i])
        tmp_list = atlas_dict[i]
        roi_list.append(tmp_list)
    
    return roi_list

def find_clusters(file,left_surf,right_surf,thresh = 1.77,distance = 20):
    '''working doc-string'''
    
    cii_data = 'clusters.dscalar.nii'
    
    thresh = str(thresh)
    distance = str(distance)
    
    find_cluster = Command().init_cmd("wb_command"); find_cluster.append("-cifti-find-clusters")
    find_cluster.append(file)
    find_cluster.append(thresh); find_cluster.append(distance)
    find_cluster.append(thresh); find_cluster.append(distance)
    find_cluster.append("COLUMN")
    find_cluster.append(cii_data)
    find_cluster.append("-left-surface")
    find_cluster.append(left_surf)
    find_cluster.append("-right-surface")
    find_cluster.append(right_surf)
    
    subprocess.call(find_cluster)
    
    return cii_data

def write_spread(file,out_file,roi_list):
    '''
    Writes image filename, dimensions, and acquisition direction to a
    spreadsheet. If the spreadsheet already exists, then it is appended
    to.
    
    Arguments:
        nii_file (nifti file): NifTi image filename with absolute filepath.
        out_file (csv file): Output csv file name and path. This file need not exist at runtime.
        
    Returns: 
        out_file (csv file): Output csv file name and path.
    '''
    
    # Strip csv file extension from output file name
    if '.csv' in out_file:
        out_file = os.path.splitext(out_file)[0]
        out_file = out_file + '.csv'
    elif '.tsv' in out_file:
        out_file = os.path.splitext(out_file)[0]
        out_file = out_file + '.csv'
    elif '.txt' in out_file:
        out_file = os.path.splitext(out_file)[0]
        out_file = out_file + '.csv'
    else:
        pass
    
    # Construct image dictionary
    file = os.path.abspath(file)
    img_dict = {"File":file,
         "ROIs":[roi_list]}
    
    # Create dataframe from image dictionary
    df = pd.DataFrame.from_dict(img_dict,orient='columns')
    
    # Write output CSV file
    if os.path.exists(out_file):
        df.to_csv(out_file, sep=",", header=False, index=False, mode='a')
    else:
        df.to_csv(out_file, sep=",", header=True, index=False, mode='w')
    
    return out_file

def proc_hemi(gii_data, gii_atlas, wb_struct):
    '''working doc-string'''
    
    # Get atlas information
    [atlas_data,atlas_dict] = load_hemi_labels(gii_atlas,wb_struct)
    
    # Get cluster data
    cluster_data = load_hemi_data(gii_data, wb_struct)
    
    # Get ROI names from overlapping cluster(s)
    roi_list = get_roi_name(cluster_data,atlas_data,atlas_dict)
    
    return roi_list

def proc_stat_cluster(cii_file,cii_atlas,out_file,left_surf,right_surf,thresh=1.77,distance=20):
    '''working doc-string'''
    
    # Isolate cluster data
    cii_data = find_clusters(cii_file,left_surf,right_surf)
    
    # Significant cluster overlap ROI list
    roi_list = list()
    tmp_list = list()
    
    # Iterate through wb_structures
    wb_structs = ["CORTEX_LEFT","CORTEX_RIGHT"]
    
    for wb_struct in wb_structs:
        tmp_list= proc_hemi(cii_data,cii_atlas,wb_struct)
        # roi_list.append(tmp_list)
        roi_list.extend(tmp_list)
    
    os.remove(cii_data)
    
    # Write output spreadsheet of ROIs
    if len(roi_list) != 0:
        out_file = write_spread(cii_file,out_file,roi_list)
        
    return out_file                           

if __name__ == "__main__":

    # Argument parser
    parser = argparse.ArgumentParser(description='Finds cifti surface clusters and writes the overlapping ROIs to a CSV file.')

    # Parse Arguments
    # Required Arguments
    reqoptions = parser.add_argument_group('Required arguments')
    reqoptions.add_argument('-i', '-in', '--input',
                            type=str,
                            dest="cii_file",
                            metavar="STATS.dscalar.nii",
                            required=True,
                            help="Cifti image file.")
    reqoptions.add_argument('-o', '-out', '--output',
                            type=str,
                            dest="out_file",
                            metavar="OUTPUT.csv",
                            required=True,
                            help="Output spreadsheet name.")
    reqoptions.add_argument('-l', '-left', '--left-surface',
                        type=str,
                        dest="left_gii",
                        metavar="GII",
                        required=True,
                        help="Input left gifti surface.")
    reqoptions.add_argument('-r', '-right', '--right-surface',
                        type=str,
                        dest="right_gii",
                        metavar="GII",
                        required=True,
                        help="Input right gifti surface.")
    reqoptions.add_argument('-a', '-atlas', '--atlas',
                        type=str,
                        dest="atlas",
                        metavar="ATLAS.dlabel.nii",
                        required=True,
                        help="Cifti atlas file.")

    # Optional Arguments
    optoptions = parser.add_argument_group('Optional arguments')
    optoptions.add_argument('-t', '-thresh', '--thresh',
                        type=float,
                        dest="thresh",
                        metavar="FLOAT",
                        default=1.77,
                        required=False,
                        help="Cluster threshold.")
    optoptions.add_argument('-d', '-dist', '--distance',
                        type=float,
                        dest="dist",
                        metavar="FLOAT",
                        default=20,
                        required=False,
                        help="Minimum distance between clusters.")

    args = parser.parse_args()

    # Print help message in the case
    # of no arguments
    try:
        args = parser.parse_args()
    except SystemExit as err:
        if err.code == 2:
            parser.print_help()

    # Run
    args.out_file = proc_stat_cluster(cii_file=args.cii_file,cii_atlas=args.atlas,out_file=args.out_file,left_surf=args.left_gii,right_surf=args.right_gii,thresh=args.thresh,distance=args.dist)
