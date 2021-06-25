"""
Util for processing idle log to determine total activity, daily activity, remaining work etc.
"""

from collections import namedtuple
import pandas as pd
import numpy as np
import datetime

ActivityInfo = namedtuple('ActivityInfo', [
    'report_str',
    'midnight',
    'timeseries_today',
    'activity_timeseries',
    'daily_activity',
    'weekly_activity',
])


def process_idle_log(logpath):
    idle_data = pd.read_csv(logpath,
                            names=['timestamp', 'idle_time_ms'],
                            dtype=np.int64)
    #use idle data to determine active times
    idle_data['idle_time_s'] = idle_data.idle_time_ms / 1000
    active_timestamps = idle_data.timestamp - idle_data.idle_time_s
    active_timestamps = active_timestamps.round().drop_duplicates(
    ).reset_index(drop=True)
    active_times = active_timestamps.apply(datetime.datetime.fromtimestamp)

    #bin into minutes
    minutes = pd.DatetimeIndex(
        np.arange(start=min(active_times).floor('min'),
                  stop=pd.Timestamp.now(),
                  step=datetime.timedelta(minutes=1)))

    #timeseries, active or not by minute
    activity_timeseries = pd.DataFrame(dict(timestamp=minutes,
                                            is_active=[False] * minutes.size),
                                       index=minutes)

    #set active minutes based on activity timestamps
    def set_active(active_times, activity_timeseries):
        for activity_timestamp in active_times:
            activity_timeseries.loc[
                pd.Timestamp(activity_timestamp).floor('min'),
                'is_active'] = True

    set_active(active_times, activity_timeseries)

    # manually add active times (e.g. when working away from linux laptop)
    # these manual overrides are read in from csv

    def manually_set_active(from_t, to_t, timeseries):
        set_active(
            np.arange(start=from_t,
                      stop=to_t,
                      step=pd.Timedelta(1, unit='minutes')), timeseries)

    manual_overrides = pd.read_csv("activity_overrides.csv", index_col=False)

    for _, override in manual_overrides.iterrows():
        manually_set_active(from_t=pd.Timestamp(year=override.year,
                                                month=override.month,
                                                day=override.day,
                                                hour=override.start_hour,
                                                minute=override.start_minute),
                            to_t=pd.Timestamp(year=override.year,
                                              month=override.month,
                                              day=override.day,
                                              hour=override.stop_hour,
                                              minute=override.stop_minute),
                            timeseries=activity_timeseries)

    # fill in activity gaps less than 10 minutes
    activity_timeseries['interval_group'] = (
        activity_timeseries.is_active !=
        activity_timeseries.is_active.shift()).cumsum()
    activity_timeseries['interval_length'] = activity_timeseries.groupby(
        'interval_group')['is_active'].transform(len)
    activity_timeseries.loc[activity_timeseries.interval_length < 10,
                            'is_active'] = True

    def time_to_datetime(time):
        """
        Plotly plots against 'datetime.time' objects are not working (incorrect ordering)
        Converting to datetimes with false dates, to see if plotly is happier plotting against those
        """
        if pd.isnull(time):
            return pd.NaT
        else:
            return datetime.datetime(year=1970,
                                     month=1,
                                     day=1,
                                     hour=int(time.hour),
                                     minute=int(time.minute))

    activity_timeseries['date'] = activity_timeseries.timestamp.dt.date
    activity_timeseries[
        'time_of_day'] = activity_timeseries.timestamp.dt.time.apply(
            time_to_datetime)
    currently_active = activity_timeseries.iloc[-1].is_active

    #sum up active hours by day
    active_hours_by_day = activity_timeseries.is_active.groupby(
        activity_timeseries.index.date).sum() / 60
    active_hours_by_day.name = 'active_hours'
    daily_activity = pd.DataFrame(active_hours_by_day)

    #sum up active hours by week
    active_hours_by_week = activity_timeseries.is_active.groupby(
        activity_timeseries.to_period(freq='w').index).sum() / 60
    active_hours_by_week.name = 'active_hours'
    weekly_activity = pd.DataFrame(active_hours_by_week)

    #determine remaining work today
    now = datetime.datetime.now()
    midnight = datetime.datetime.combine(now.date(), datetime.time())
    timeseries_today = activity_timeseries[
        activity_timeseries.timestamp > midnight].copy()
    timeseries_today[
        'cumulative_activity'] = timeseries_today.is_active.cumsum()
    timeseries_today[
        'remaining_time'] = 8 - timeseries_today.cumulative_activity / 60
    remaining_time = pd.Timedelta(timeseries_today.remaining_time[-1],
                                  unit='h')
    hours_remaining, rem = divmod(remaining_time.seconds, 3600)
    minutes_remaining, _ = divmod(rem, 60)
    total_active_minutes_today = timeseries_today.cumulative_activity[-1]
    hours_active_today, minutes_active_today = divmod(
        total_active_minutes_today, 60)
    expected_completion_time = (timeseries_today.index[-1] +
                                remaining_time).time()

    #Create a report string
    report_str = ("### Today's status:\n"
                  "**Current state**: {s}\n"
                  "**Active time today**: {ha} hours {ma} minutes\n"
                  "**To complete 8 hour work day**:\n"
                  "* remaining time: {hr} hours {mr} minutes\n"
                  "* expected completion time: {t}\n").format(
                      s='ACTIVE' if currently_active else 'IDLE',
                      ha=hours_active_today,
                      ma=minutes_active_today,
                      hr=hours_remaining,
                      mr=minutes_remaining,
                      t=expected_completion_time,
                  )

    return ActivityInfo(
        report_str=report_str,
        midnight=midnight,
        timeseries_today=timeseries_today,
        activity_timeseries=activity_timeseries,
        daily_activity=daily_activity,
        weekly_activity=weekly_activity,
    )
