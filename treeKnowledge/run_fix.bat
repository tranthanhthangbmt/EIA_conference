@echo off
d:
cd \MY_CODE\treeKnowledge
echo Starting script... > log_bat.txt
python rebuild_csv.py >> log_bat.txt 2>&1
echo Script finished with errorlevel %errorlevel% >> log_bat.txt
