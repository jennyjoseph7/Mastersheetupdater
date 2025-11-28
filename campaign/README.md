# File Structure - 

project/
│
├── campaign/
│   ├── campaign_worker.py     # Main worker entry file
│   ├── campaign_workflow.py
│   ├── campaign_manager.py                 
│  
│
├── trigger_campaign_new.py             # Script to trigger a campaign
├── setup.sh                   # Environment variables loader
└── README.md                  

-----------------------------------------------------------------------
# To test and trigger a campaign -

Run a python file trigger_campaign_new.py 

-------------------------------------------------------------------------
# To start the worker - 

go to your environment variable 
run setup.sh
worker -m campaign/campaign_worker.py