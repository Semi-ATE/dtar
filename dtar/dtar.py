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


reference_format = {'unchanged' : {}, 'changed' : {}, 'removed' : {}}

# references : 
#   https://docs.python.org/3/library/tarfile.html#tarfile-objects


class dtar(object):
    
    catalog_file_name = '.dtar'
    default_tar_file_name_base = 'diff'
    default_rm_script_name = 'dtar_rm.sh'
    
    def __init__(self, start_point=None, tar_name=None):
        if not self.is_linux():
            raise Exception('Only linux platform is currently implemented.')

        if not self.is_root():
            raise Exception(f'{__file__} needs to be run as root.')

        if start_point is None:
            self.start_point = os.getcwd()
        elif os.path.exists(start_point) and os.path.isdir(start_point):
            self.start_point = start_point
        else:
            self.start_point = os.getcwd()

        if tar_name is None:
            self.tar_file_name = f"{self.default_tar_file_name_base}.tar"
        else:
            self.tar_file_name = f"{tar_name}.tar"

    def is_linux(self):
        '''
        This method will check if we are executing on a linux system, if so
        it returns True and False otherwhise.
        '''
        return 'LINUX' in sys.platform.upper()

    def is_root(self):
        '''
        This mentod will check if the effective user ID is 0, in other words
        if we are root, if so it returns True and False otherwhise.
        '''
        return os.geteuid() == 0

    def has_catalog(self):
        '''
        This method will check if self.start_point holds a self.dtar_file_name,
        if so True is returned and False otherwhise.
        '''
        return os.path.isfile(os.path.join(self.start_point, self.dtar_file_name))
            
    def file_type(self, abs_path):
        '''
        Given an absolute path to a file (or directory), this method will return
        the type to fill in to TarInfo.type.
        
        ... might need some reverse engineering ...
        
        '''
        return 'type'
        
        
    def file_linkname(self, abs_path):
        '''
        Given the absolute path to a file or directory, this method will return
        the linkname to fill in to the TarInfo.type.
        '''
        return 'linktype'
        
    def file_attributes(self, abs_path):
        '''
        Given the absolute path to a file or directory, this method will return 
        the 10 element tuple needed in the catalog.
        '''
        return (
            os.stat(abs_path).st_mode,  # file permissions
            os.stat(abs_path).st_uid,  # file owner user id (numeric) 
            os.stat(abs_path).st_gid,  # group id of the file (numeric)
            os.stat(abs_path).st_size,  # file size in bytes 
            int(os.stat(abs_path).st_mtime),  # file's modification time rounded to int
            self.file_type(abs_path),  
            self.file_linkname(abs_path),  
            pwd.getpwuid(uid).pw_name,  # file owner user name
            pwd.getgrgid(gid).gr_name,  # file's group name 
            hashlib.md5(open(abs_path,'rb').read()).hexdigest()
            )
        
    def create_rm_script(self, rm_list):
        '''
        Given a rm_list, this method will create a file 'self.rm_file_name' in
        the self.start_point directory. The file is a bash script that 
        removes files that need removing.
        
        Note that the elements in rm_list are tuples (name, type), where name
        is a relative path (that **DOES NOT** start with a './') and the type
        is either tarfile.DIRTYPE for a directory or tarfile.REGTYPE for a file.
        
        To be sure that files **CAN** be removed, the script will insist that
        it is run as root (sudo).
        
        The method returns True if a script is generated and False if no script
        is generated (read: the rm_list is empty)
        '''
        if not isinstance(rm_list, list):
            raise TypeError(f"rm_list must be a list")
        if rm_list:  # is not an empty list
            with open(os.path.join(self.start_point, self.rm_file_name), 'w') as fd:
                fd.write('#!/usr/bin/env bash\n')
                fd.write('if [ "$EUID" -ne 0 ]\n')
                fd.write('  then echo "Please run as root"\n')
                fd.write('  exit\n')
                fd.write('fi\n')
                for (item_to_delete, type_to_delete) in rm_list:
                    rel_path = os.path.join('./', item_to_delete)
                    if type_to_delete == tarfile.DIRTYPE:
                        fd.write(f'rm -rf {rel_path}\n')
                    elif type_to_delete == tarfile.REGTYPE:
                        fd.write(f'rm -f {rel_path}\n')
                    else:
                        raise TypeError(f"unsupported type '{type_to_delete}'")
            return True
        return False

    def is_catalog(self, catalog):
        '''
        This method will check if 'catalog' is properly formatted, if so True
        is returned, if not False is returned.
        '''
        if not isinstance(catalog, dict):
            return False
        
        if not catalog:  # emtpty dictionary
            return False
        
        if 'start_point' not in catalog:
            return False
        else:
            if not isinstance(catalog['start_point'], str):
                return False
        
        if 'uids' not in catalog:
            return False
        else:
            if not isinstance(catalog['uids'], list):
                return False
            else:
                for element in catalog['uids']:
                    if not isinstance(element, tuple):
                        return False
                    elif len(element) != 2:
                        return False
                    
        if 'gids' not in catalog:
            return False
        else:
            if not isinstance(catalog['gids'], list):
                return False
            else:
                for element in catalog['gids']:
                    if not isinstance(element, tuple):
                        return False
                    elif len(element) != 2:
                        return False
        
        if 'files' not in catalog:
            return False
        else:
            if not isinstance(catalog['files'], dict):
                return False
            else:
                for key in catalog['files']:
                    if not isinstance(catalog['files'][key], tuple):
                        return False
                    elif len(catalog['files'][key]) != 10:
                        return False
        
        return True
    
    def is_empty_catalog(self, catalog):
        '''
        This method will check if the (presumed well formatted) catalog is
        empty, if so, True is returned, otherwhise False is returned.
        '''
        return not not catalog['files']

    def is_good_catalog(self, catalog):
        '''
        Given a catalog, this method will verify if the catalog is good, if so
        True is returned, else False.
        
        Things that this method checks:
            - symlinks to outside
            - broken symlinks
        '''
        for File in catalog['files']:
            pass
        return True

    def empty_catalog(self):
        return {
            'start_point' : self.start_point,
            'uids' : [],
            'gids' : [],
            'files' : {}
            }

    def make_catalog(self):
        '''
        This method will return a dictionary of the form :

            {'start_point' : <str>,
             'uids' : [(uid, uname) used in the 'files'],
             'gids' : [(gid, gname) used in the 'files'],
             'files' : {
                 relative_path_to_file : (mode = os.stat(abs_path).st_mode
                                          uid = os.stat(abs_path).st_uid
                                          gid = os.stat(abs_path).st_gid
                                          size = os.stat(abs_path).st_size
                                          mtime = os.stat(abs_path).st_mtime
                                          type,  
                                          linkname, 
                                          uname = pwd.getpwuid(uid).pw_name
                                          gname = pwd.getgrgid(gid).gr_name
                                          md5 = hashlib.md5(open(abs_path,'rb').read()).hexdigest()
                                          ),
                 }
             }
            
        staring from self.start_point
            
        ... links must be supported ... hardlink & softlink !
            
        '''
        retval = self.empty_catalog()
        total_size = 0
        total_files =0
        
        # Create as fast as possible the list of all files
        for Root, Dirs, Files in os.walk(self.start_point):
            for File in Files:
                abs_path = os.path.join(Root, File)
                rel_path = abs_path.replace(self.start_point, '')[1:]
                size = os.path.getsize(abs_path)
                total_size += size
                retval['files'][rel_path] = None

        # Add the file attributes (is mutch slower) with progress bar
        with tqdm(total=total_size, unit='B',  unit_scale=True, desc="Creating catalog") as pbar:
            for rel_path in retval['files']:
                total_files += 1
                abs_path = os.path.join(start_point, rel_path)
                retval['files'][rel_path] = self.file_attributes(abs_path)
                size = retval['files'][rel_path][3]
                uid = retval['files'][rel_path][1]
                uname = retval['files'][rel_path][7]
                gid = retval['files'][rel_path][2]
                gname = retval['files'][rel_path][8]
                if (uid, uname) not in retval['uids']:
                    retval['uids'].append((uid, uname))
                if (gid, gname) not in retval['gids']:
                    retval['gids'].append((gid, gname))
                pbar.update(size)
        return retval





    
    def load_catalog(self):
        '''
        This method will load the self.dtar_file_name JSON file form self.start_point.
        If no such file exists, it will return an empty dictionary, a filled one
        will be returned when the file exists.
        '''
        retval = {}
        if self.has_catalog():
            try:
                catalog_file = os.path.join(self.start_point, self.dtar_file_name) 
                with open(catalog_file, 'r') as fd:
                    retval = json.load(fd)
            except:
                retval = {}
        return retval
    
    def save_catalog(self, catalog):
        '''
        Given a catalog, this method will save it in JSON format in the directory
        self.start_point under the name self.dtar_file_name.
        
        On successfull write, the method returns True, if something went wrong
        False is returned.
        '''
        if self.is_catalog(catalog):
            try:
                catalog_file = os.path.join(self.start_point, self.dtar_file_name) 
                with open(catalog_file, 'w') as fd:
                    json.dump(catalog, fd)
            except:
                if os.path.exists(catalog_file):
                    os.remove(catalog_file)
                return False
            else:
                return True
        else:
            return False

    def delete_catalog(self):
        '''
        This method will remove the file self.catalog_file_name from 
        the self.start_point directory.
        '''
        os.remove(os.path.join(self.start_point, self.catalog_file_name))
        
        
        
    def start_points_ok(self, old_catalog, new_catalog):
        '''
        Given 2 catalogs (presumed to be OK), this method returns True
        if both starting points are identical, False otherwhise.
        '''
        return old_catalog['start_point'] == new_catalog['start_point']
        
    def state_changed(self, old_state, new_state):
        '''
        Given two 10-bit state tuples, return True if the state is changed,
        and False if the state is not changed.
        '''
        pass
    
    def catalog_diff(self, old_catalog, new_catalog):
        '''
        Given old_catalog and new_catalog, this method will calculate the
        difference and returns it as a dictionary.
        
        If the two catalogs don't have the same start_point, an empty dictionary
        is returned.
        '''
        if not self.start_points_ok(old_catalog, new_catalog):
            return {}    
        with tqdm(total=1, unit='files', desc='Calculating differences') as pbar:
            retval = {
                'start_point' : new_catalog['start_point'],
                'changed' : {},
                'added' : {},
                'removed' : [],
                'unchanged' : [],
                }
            all_files = {}
            for File in old_catalog['files']:
                all_files[File] = (True, False)
            for File in new_catalog['files']:
                if File in all_files:
                    all_files[File] = (True, True)
                else:
                    all_files[File] = (False, True)
            files_to_process = len(all_files)
            pbar.total = files_to_process + 1
            pbar.update()
            for File in all_files:
                state = all_files[File]
                if state == (True, True):  # existing, changed or unchanged ?
                    if self.state_changed(old_catalog['files'][File], new_catalog['files'][File]):
                        retval['changed'][File] = new_catalog['files'][File]
                    else:
                        retval['unchanged'].append(File)
                elif state == (True, False):  # removed
                    retval['removed'].append(File)
                    pass
                else:  # added
                    retval['added'][File] = new_catalog['files'][File]
                pbar.update()
        return retval
                
    def make_tar_file(self):
        '''
        This method will create the tar file.
        '''
        
        
        




        changed_files = 0
        new_files = 0
        removed_files = 0
        unchanged_files = 0
        
        # get the old catalog
        if self.has_catalog:
            try:
                old_catalog = self.load_catalog()
            except:
                self.delete_catalog()
                old_catalog = self.empty_catalog()
        else:
            old_catalog = self.empty_catalog()
                
        # get the new catalog           
        new_catalog = self.make_catalog()
        
                



        # Create the tar_file (note: dtar_file is **NOT** a part of the tar_file)
        total_files = 0
        with tarfile.open(tar_file, "w") as td:    
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"Creating '{tar_file_name}'") as pbar:
                for rel_path in catalog['files']:
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
        print(info, flush=True)

        

if __name__ == "__main__":
    # start_point = r'C:\Users\hoeren\Desktop\Repos\Semi-ATE\SCT8-Board'
    start_point = r'/home/nerohmot/Repos/Semi-ATE/SCT8-Board'
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
