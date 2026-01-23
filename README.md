About the project: this is a digital twin simulator that simulate a industrial wood saw. The machine learning aspect is still missing, as is making it more modular to allow for more machines or other types of machines. 

# Steps to run this project

## 1. Install

 - use `python -m venv venv` to create your environment 
 - activate your environment using `source .venv/bin/activate` 
 - next use `pip install -r requirements.txt`

## 2. Docker

  Its important that you have a docker installed in your machine to run the images

  - go at the /docker by terminal
  - you just need run the command `docker compose up -d`

## 3. Generate date 

  The height of that moment, provided nothing has gone wrong you just run `python gazebo/models/plugins/mqtt_bridge.py`. 
  
  - if this dont work run `python simulator/process_simulator.py` its should work
