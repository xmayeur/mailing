#!/bin/sh

git fetch --all --prune
git checkout master
git pull origin master --rebase
git checkout beta
git pull origin beta --rebase
echo "Please check if you have any stale branches that need to be deleted locally."
git branch -a
# echo "Deleting stale branches..."
# git branch -vv | grep ': gone]' | awk '{print $1}' | xargs git branch -d

echo "Updating dependencies to latest compatible versions..."
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
