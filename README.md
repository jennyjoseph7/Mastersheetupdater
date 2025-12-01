### This is the documentation for AutoCRM


AutoCRM, takes care of the entire customer lifecycle of a Car/Bike dealership

It supports, managing of leads, customers and automatically reaches out and tries to convert the customer. 



### Steps To get the SignUp API KEY ---
```python
from gryd_worker import gryd_routes as rts
rts.get_enterprise_object('autocrm')
```

### Steps to setup ##
```python
import app
app.SETUP()
```


### Steps to run core worker
```bash
cd core
worker -m core.py -n <number of workers>
```
