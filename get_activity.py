#!/usr/bin/env python

from idle_log_processing import process_idle_log
activity_info = process_idle_log('/export/bulk/tmp/idle.log')
print(activity_info.report_str)
