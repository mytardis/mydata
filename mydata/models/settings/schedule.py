"""
Model class for the settings displayed in the Schedule tab
of the settings dialog and saved to disk in MyData.cfg
"""
from datetime import datetime
from datetime import timedelta


class ScheduleSettingsModel(object):
    """
    Model class for the settings displayed in the Schedule tab
    of the settings dialog and saved to disk in MyData.cfg
    """
    def __init__(self):
        # Saved in MyData.cfg:
        self.mydataConfig = dict()

        self.fields = [
            'schedule_type',
            'scheduled_date',
            'scheduled_time',
            'monday_checked',
            'tuesday_checked',
            'wednesday_checked',
            'thursday_checked',
            'friday_checked',
            'saturday_checked',
            'sunday_checked',
            'timer_from_time',
            'timer_to_time',
            'timer_minutes'
        ]

    @property
    def scheduleType(self):
        """
        Get schedule type
        """
        return self.mydataConfig['schedule_type']

    @scheduleType.setter
    def scheduleType(self, scheduleType):
        """
        Set schedule type
        """
        self.mydataConfig['schedule_type'] = scheduleType

    @property
    def mondayChecked(self):
        """
        Return True if Monday is ticked
        """
        return self.mydataConfig['monday_checked']

    @mondayChecked.setter
    def mondayChecked(self, checked):
        """
        Set this to True to tick the Monday checkbox in the Schedule tab.
        """
        self.mydataConfig['monday_checked'] = checked

    @property
    def tuesdayChecked(self):
        """
        Return True if Tuesday is ticked
        """
        return self.mydataConfig['tuesday_checked']

    @tuesdayChecked.setter
    def tuesdayChecked(self, checked):
        """
        Set this to True to tick the Tuesday checkbox in the Schedule tab.
        """
        self.mydataConfig['tuesday_checked'] = checked

    @property
    def wednesdayChecked(self):
        """
        Return True if Wednesday is ticked
        """
        return self.mydataConfig['wednesday_checked']

    @wednesdayChecked.setter
    def wednesdayChecked(self, checked):
        """
        Set this to True to tick the Wednesday checkbox in the Schedule tab.
        """
        self.mydataConfig['wednesday_checked'] = checked

    @property
    def thursdayChecked(self):
        """
        Return True if Thursday is ticked
        """
        return self.mydataConfig['thursday_checked']

    @thursdayChecked.setter
    def thursdayChecked(self, checked):
        """
        Set this to True to tick the Thursday checkbox in the Schedule tab.
        """
        self.mydataConfig['thursday_checked'] = checked

    @property
    def fridayChecked(self):
        """
        Return True if Friday is ticked
        """
        return self.mydataConfig['friday_checked']

    @fridayChecked.setter
    def fridayChecked(self, checked):
        """
        Set this to True to tick the Friday checkbox in the Schedule tab.
        """
        self.mydataConfig['friday_checked'] = checked

    @property
    def saturdayChecked(self):
        """
        Return True if Saturday is ticked
        """
        return self.mydataConfig['saturday_checked']

    @saturdayChecked.setter
    def saturdayChecked(self, checked):
        """
        Set this to True to tick the Saturday checkbox in the Schedule tab.
        """
        self.mydataConfig['saturday_checked'] = checked

    @property
    def sundayChecked(self):
        """
        Return True if Sunday is ticked
        """
        return self.mydataConfig['sunday_checked']

    @sundayChecked.setter
    def sundayChecked(self, checked):
        """
        Set this to True to tick the Sunday checkbox in the Schedule tab.
        """
        self.mydataConfig['sunday_checked'] = checked

    @property
    def scheduledDate(self):
        """
        Get scheduled date
        """
        return self.mydataConfig['scheduled_date']

    @scheduledDate.setter
    def scheduledDate(self, scheduledDate):
        """
        Set scheduled date
        """
        self.mydataConfig['scheduled_date'] = scheduledDate

    @property
    def scheduledTime(self):
        """
        Get scheduled time
        """
        return self.mydataConfig['scheduled_time']

    @scheduledTime.setter
    def scheduledTime(self, scheduledTime):
        """
        Set scheduled time
        """
        self.mydataConfig['scheduled_time'] = scheduledTime

    @property
    def timerMinutes(self):
        """
        Get timer interval in minutes
        """
        return self.mydataConfig['timer_minutes']

    @timerMinutes.setter
    def timerMinutes(self, timerMinutes):
        """
        Set timer interval in minutes
        """
        self.mydataConfig['timer_minutes'] = timerMinutes

    @property
    def timerFromTime(self):
        """
        Get time when timer begins
        """
        return self.mydataConfig['timer_from_time']

    @timerFromTime.setter
    def timerFromTime(self, timerFromTime):
        """
        Set time when timer begins
        """
        self.mydataConfig['timer_from_time'] = timerFromTime

    @property
    def timerToTime(self):
        """
        Get time when timer stops
        """
        return self.mydataConfig['timer_to_time']

    @timerToTime.setter
    def timerToTime(self, timerToTime):
        """
        Set time when timer stops
        """
        self.mydataConfig['timer_to_time'] = timerToTime

        self.mydataConfig['api_key'] = ""

    def SetDefaults(self):
        """
        Set default values for configuration parameters
        that will appear in MyData.cfg for fields in the
        Settings Dialog's Schedule tab
        """
        self.mydataConfig['schedule_type'] = "Manually"
        self.mydataConfig['scheduled_date'] = datetime.date(datetime.now())
        self.mydataConfig['scheduled_time'] = \
            datetime.time(datetime.now().replace(microsecond=0) +
                          timedelta(minutes=1))
        self.mydataConfig['monday_checked'] = False
        self.mydataConfig['tuesday_checked'] = False
        self.mydataConfig['wednesday_checked'] = False
        self.mydataConfig['thursday_checked'] = False
        self.mydataConfig['friday_checked'] = False
        self.mydataConfig['saturday_checked'] = False
        self.mydataConfig['sunday_checked'] = False
        self.mydataConfig['timer_from_time'] = \
            datetime.time(datetime.strptime("12:00 AM", "%I:%M %p"))
        self.mydataConfig['timer_to_time'] = \
            datetime.time(datetime.strptime("11:59 PM", "%I:%M %p"))
        self.mydataConfig['timer_minutes'] = 15
