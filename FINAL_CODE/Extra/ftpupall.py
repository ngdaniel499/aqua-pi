from ftplib import FTP
import ConfigParser
from os import listdir
from os.path import isfile, join
import os
import time
import sys
import traceback

def ftpupload(listnew,server_ip,ftp_dir,username,password):
    ftp = FTP(server_ip)
    # Log in to the server
    ftp.login(username,password)
    # This is the directory that we want to go to
    # change to ftp_dir
    ftp.cwd(ftp_dir)
    # upload the files
    newuploaded = []
    for i in listnew:
        fpathf = os.path.join(fpath,i)
        ftp.storbinary('STOR '+ str(i), open(fpathf), blocksize=8192)
        newuploaded.append(i)
    ftp.close()
    return newuploaded

#Begin Main Program here
try:
    config = ConfigParser.ConfigParser()    
    configfilewithpath =  './Upconfig.cfg'
    config.read(configfilewithpath)
    config_file = configfilewithpath.split('\\')[-1]
    fpath = config.get('Section1', 'fpath')
    server_ip = config.get('Section1', 'server_ip')
    username = config.get('Section1', 'username')
    password = config.get('Section1', 'password')
    ftp_dir = config.get('Section1', 'ftp_dir')
    stationid = config.get('Section1', 'stationid')
    #Currentfile (this hour)
    outfile = stationid + '_' + time.strftime("%Y_%m_%d_%H")+'H.csv'
    #get list of all files in data folder
    filelist = [ f for f in listdir(fpath) if isfile(join(fpath,f)) ]
    # remove current file from list
    if outfile in filelist: filelist.remove(outfile)
    print 'filelist', filelist
    # open and read file containing list of already uploaded files
    fuploaded = open('uploaded.txt', 'r')
    prvcompletedlist = fuploaded.read().splitlines()
    fuploaded.close()
    print 'prvcompletedlist', prvcompletedlist
    #Convert to set for faster searching and generate list of only new files
    s = set(prvcompletedlist)
    listnew = [x for x in filelist if x not in s]
    print 'listnew', listnew
    #attempt upload new files
    newuploaded = ftpupload(listnew,server_ip,ftp_dir,username,password)
    print 'newly uploaded', newuploaded
    fuploaded = open('uploaded.txt', 'a')
    for item in newuploaded:
        fuploaded.write("%s\n" % item)
    fuploaded.close()
except:
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    error_msg = tbinfo + " " + str(sys.exc_info()[1])
    print error_msg
    pass
