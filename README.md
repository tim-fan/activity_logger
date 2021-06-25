# Get Active Time

Quick project to keep track of laptop activity throughout the day.

## Setup

This is put in crontab for recording idle times:

```
* * * * * env DISPLAY=:0.0 /home/tim/bin/update_idle_log.sh
```

Then run `run_ui.sh` to get the dashboard. This seems to need a venv setup, I suppose it needs the packages in `requirements.txt`

## Notes

The binary `getIdle` is responsible for determining idle times. This was compiled based on some stack overflow instructions (TODO: find link). Would be good to document how to compile this. Alternatively, I believe there are python packages which can achieve the same result - may be worth switching to use these.
