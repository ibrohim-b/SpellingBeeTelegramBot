#kill previous process
pkill SpellingBeeBot
#Activate venv
source .venv/bin/activate
#Install dependencies
python3 -m pip install --upgrade pip
if  [ -f requirements.txt ]; then pip install -r /home/python-projects/SpellingBeeTelegramBot/requirements.txt; fi
#Launch main.py with nohup
nohup python3 main.py >/dev/null 2>&1 &