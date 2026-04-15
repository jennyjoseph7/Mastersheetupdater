### This is the documentation for AutoCRM


AutoCRM, takes care of the entire customer lifecycle of a Car/Bike dealership

It supports, managing of leads, customers and automatically reaches out and tries to convert the customer. 



### Steps To get the SignUp API KEY ---
```python
from gryd_worker import gryd_routes as rts
from config import AUTOCRM_APP_ENTERPRISE_ID
rts.get_enterprise_object(AUTOCRM_APP_ENTERPRISE_ID)
```

### Steps to setup ##
```python
import app
app.SETUP()
```

### Steps to create a new worker
Create an environment variable in config.py
```python3.10
AUTOCRM_MY_NEW_SERVICE_NAME = os.environ.get('AUTOCRM_MY_NEW_SERVICE_NAME', 'my-new-service')
```
import config by adding 
```python3.10
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_MY_NEW_SERVICE_NAME
```

### Steps to run core worker
```bash
cd core
worker -m core.py -n <number of workers>
```
