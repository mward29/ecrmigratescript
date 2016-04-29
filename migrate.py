#!/usr/bin/env python
# Must have python 2.7 installed
# This script is Cert based to access your registry. Will need to be amended if you aren't using cert based auth.
# Must already be logged into Registries from run location
#      ie aws ecr get-login --region us-east-1
#      docker login -u AWS -p LONG_CRED
# Must have plenty of disk space.
# Must be v2 to v2 registry
# Also THIS CAN FILL A DISK QUICKLY. Make sure you have enough local disk for this operation.

import requests
import json
import logging
import ast
import subprocess
import os

os.path.abspath('/')

# Make sure you have these env vars set so we can use them
os.environ.get('REGION')
os.environ.get('AWS_ACCESS_KEY_ID')
os.environ.get('AWS_SECRET_ACCESS_KEY')

# ECR policy file to set permissions
with open("policy.json", "r") as myfile:
    policy = myfile.read()


class MigrateToEcr():
# Init some urls and paths for migration then call _get_catalog
    def __init__(self):
        self.REG_URL = '........registry...........local:5000/'
        self.ECR_URL = '815........3.dkr.ecr.us-east-1.amazonaws.com/'
        self.dockerpath = '/usr/bin/docker'
        self.awspath = '/usr/local/bin/aws'
        self._get_catalog()

# Get a catalog of repos from your existing repository
    def _get_catalog(self):
        r = requests.get('https://' + self.REG_URL + 'v2/_catalog')
        logging.debug("Test get Catalog: %r", r)
        io = json.dumps(r.text)
        n = json.loads(io)
        line = ast.literal_eval(n)
        mylist = line['repositories']
        self._log = logging.debug("Test run: %r", mylist)
        self._run(mylist)

# primary run function to execute every thing else
    def _run(self, mylist):
        for line in mylist:
            self._ensure_new_repo_exists(line)

        for line in mylist:
            command = self.awspath + ' ecr list-images --repository-name ' + line
            checktags = subprocess.check_output(command, shell=True)
            taglist = self._get_tags(line)
            for tag in taglist:
                tagvalue = self._check_tag(line, tag, checktags)
                if tagvalue is False:
                    self._download_images(line, tag)
                    self._set_tag(line, tag)
                    self._upload_image(line, tag)
                else:
                    print("Found" + line + ' ' + tag + " is already uploaded. Skipping")
                    continue

# Get version tags from existing repository so we can migrate all of them
    def _get_tags(self, line):
        command = 'https://' + self.REG_URL + 'v2/' + line + '/tags/list'
        checktags = requests.get(command)
        io = json.dumps(checktags.text)
        n = json.loads(io)
        tagline = ast.literal_eval(n)
        taglist = tagline['tags']
        return taglist

# Check if the version tag exists in new repository
    def _check_tag(self, line, tag, checktags):
        if tag in checktags:
            return True
        else:
            return False

# Create new repo in Registry if does not exist
    def _ensure_new_repo_exists(self, line):
        command = self.awspath + ' ecr describe-repositories'
        checkrepo = subprocess.check_output(command, shell=True)
        if line not in checkrepo:
            command = self.awspath + ' ecr create-repository --repository-name ' + line
            subprocess.Popen(command, shell=True)
            command = self.awspath + ' ecr set-repository-policy --repository-name ' + line + ' --policy-text ' + policy
            subprocess.Popen(command, shell=True)

# Download images from existing registry
    def _download_images(self, line, tag):
        print "######### Downloading " + line + ':' + tag + " image from bitesize registry ##########################"
        try:
            command = self.dockerpath + ' pull ' + self.REG_URL + line + ':' + tag
            subprocess.check_output(command, shell=True)
        except:
            return

# Tag image for new registry
    def _set_tag(self, line, tag):
        print "######### TAGGING " + line + ':' + tag + " IMAGE FOR UPLOAD ################"
        try:
            command = self.dockerpath + ' tag -f ' + self.REG_URL + line + ':' + tag + ' ' + self.ECR_URL + line + ':' + tag
            subprocess.check_output(command, shell=True)
        except:
            return

# Upload image to new registry
    def _upload_image(self, line, tag):
        print "############### STARTING " + line + ':' + tag + " IMAGE UPLOAD TO NEW REPO ###################"
        try:
            command = self.dockerpath + ' push ' + self.ECR_URL + line + ':' + tag
            subprocess.check_output(command, shell=True)
        except:
            return


MigrateToEcr()
