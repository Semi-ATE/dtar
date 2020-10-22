#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 14:56:40 2020

@author: hoeren

This script will repack the given .tar.gz or .tgz file in chunks no bigger
than denoted by the 

"""
import argparse
import os
import sys
import tarfile
import gzip
import json
import hashlib
from tqdm import tqdm

dtar_file_name = '.dtar'
tar_file_name = 'dtar.tar'
rm_file_name_base = 'dtar_rm'

reference_format = {'unchanged' : {}, 'changed' : {}, 'removed' : {}}

def create_rm_script(start_point):
    
    
    # if os = windows:
    #     rm_file_name = f"{rm_file_name_base}.bar"
    pass



def holds_dtar(start_point):
    '''
    This function returns True if 'start_point' holds a reference_file_name file,
    False otherwhise.
    '''
    return os.path.exists(os.path.join(start_point, dtar_file_name))
    
def create_dtar(start_point):
    retval = {'unchanged' : {}, 'changed' : {}, 'removed' : {}}
    dtar_file = os.path.join(start_point, dtar_file_name)
    tar_file = os.path.join(start_point, tar_file_name)
    total_size = 0
    if holds_dtar(start_point):
        # Load the dtar
        print("Loading dtar ... ", end='', flush=True)
        with open(dtar_file, 'r') as fd:
            previous_state = json.load(fd)
        print("Done.", flush=True)
        # Updating dtar
        for Root, Dirs, Files in os.walk(start_point):
            for File in Files:
                full_path = os.path.join(Root, File)
                rel_path = full_path.replace(start_point, '')[1:]
                size = os.path.getsize(full_path)
                total_size += size
                
                
                
                
                retval['changed'][rel_path] = None
            
        # finding differences (=create dtar)
        
        # Create tar
        
        # give info
            
        pass
    else: # start from scratch
        # Create as fast as possible the list of all files
        for Root, Dirs, Files in os.walk(start_point):
            for File in Files:
                full_path = os.path.join(Root, File)
                rel_path = full_path.replace(start_point, '')[1:]
                size = os.path.getsize(full_path)
                total_size += size
                retval['changed'][rel_path] = None
        # Calculate the MD5 on all files wile showing progress
        with tqdm(total=total_size, unit='B',  unit_scale=True, desc=f"Creating '{dtar_file_name}'   ") as pbar:
            for rel_path in retval['changed']:
                full_path = os.path.join(start_point, rel_path)
                size = os.path.getsize(full_path)
                MD5 = hashlib.md5(open(full_path,'rb').read()).hexdigest()
                retval['changed'][rel_path] = (size, MD5)
                pbar.update(size)
        # Save the dtar_file
        with open(dtar_file, 'w') as fd:
            json.dump(retval, fd)
        # Create the tar_file (note: dtar_file is **NOT** a part of the tar_file)
        total_files = 0
        with tarfile.open(tar_file, "w") as td:    
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"Creating '{tar_file_name}'") as pbar:
                for rel_path in retval['changed']:
                    full_path = os.path.join(start_point, rel_path)
                    size = os.path.getsize(full_path)
                    td.add(full_path)
                    total_files += 1
                    pbar.update(size)
        # Give some info
        if total_size > 1024 * 1024 * 1024:  # > 1GB
            scale = 1024 * 1024 * 1024
            units = ' GB'
        elif total_size > 1024 * 1024:  # > 1MB
            scale = 1024 * 1024
            units = ' MB'
        elif total_size > 1024:
            scale = 1024
            units = ' KB'
        else:
            scale = 1
            units = ' Bytes'
        scaled_size = total_size/scale
        info = f"\nPacked {total_files} files for a total of "
        if scale == 1:
            info += f"{total_size}{units}"
        else:
            info += f"{scaled_size:.2f}{units} "
        info += f"in '{os.path.join(start_point, tar_file_name)}'"
        print(info)


if __name__ == "__main__":
    start_point = r'C:\Users\hoeren\Desktop\Repos\Semi-ATE\SCT8-Board'
    create_dtar(start_point)    
    
    
    # parser = argparse.ArgumentParser(description='Pack a directory or re-pack a .tag(.gz) file in smaller .tar(.gz) chunks.')

    # parser.add_argument('-s', '--size',
    #                     required=True,
    #                     help='maximum size (eg. 5GB or 3.14MB)')

    # parser.add_argument('-c', '--compress',
    #                     action='store_true',
    #                     default=False,
    #                     help="compress the resulting .tar files into .tar.gz")

    # parser.add_argument('SOURCE',
    #                     help='path to either a .tar(.gz) file or a directory')

    # parser.add_argument('DESTINATION',
    #                     nargs='?',
    #                     default=os.getcwd(),
    #                     help='destination directory (default is current working directory)')
    
    # args = parser.parse_args()
    
    # starz(args)
