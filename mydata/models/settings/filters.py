"""
Model class for the settings displayed in the Filters tab
of the settings dialog and saved to disk in MyData.cfg
"""
from .base import BaseSettingsModel


class FiltersSettingsModel(BaseSettingsModel):
    """
    Model class for the settings displayed in the Filters tab
    of the settings dialog and saved to disk in MyData.cfg
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        # Saved in MyData.cfg:
        self.mydataConfig = dict()

        self.fields = [
            'user_filter',
            'dataset_filter',
            'experiment_filter',
            'ignore_old_datasets',
            'ignore_interval_number',
            'ignore_interval_unit',
            'ignore_new_files',
            'ignore_new_files_minutes',
            'use_includes_file',
            'includes_file',
            'use_excludes_file',
            'excludes_file'
        ]

        self.default = dict(
            user_filter="",
            dataset_filter="",
            experiment_filter="",
            ignore_old_datasets=False,
            ignore_interval_number=0,
            ignore_interval_unit="months",
            ignore_new_files=True,
            ignore_new_files_minutes=1,
            use_includes_file=False,
            includes_file="",
            use_excludes_file=False,
            excludes_file=""
        )

    @property
    def userFilter(self):
        """
        Get glob for matching user folders
        """
        return self.mydataConfig['user_filter']

    @userFilter.setter
    def userFilter(self, userFilter):
        """
        Set glob for matching user folders
        """
        self.mydataConfig['user_filter'] = userFilter

    @property
    def datasetFilter(self):
        """
        Get glob for matching dataset folders
        """
        return self.mydataConfig['dataset_filter']

    @datasetFilter.setter
    def datasetFilter(self, datasetFilter):
        """
        Set glob for matching dataset folders
        """
        self.mydataConfig['dataset_filter'] = datasetFilter

    @property
    def experimentFilter(self):
        """
        Get glob for matching experiment folders
        """
        return self.mydataConfig['experiment_filter']

    @experimentFilter.setter
    def experimentFilter(self, experimentFilter):
        """
        Set glob for matching experiment folders
        """
        self.mydataConfig['experiment_filter'] = experimentFilter

    @property
    def ignoreOldDatasets(self):
        """
        Returns True if MyData should ignore old dataset folders
        """
        return self.mydataConfig['ignore_old_datasets']

    @ignoreOldDatasets.setter
    def ignoreOldDatasets(self, ignoreOldDatasets):
        """
        Set this to True if MyData should ignore old dataset folders
        """
        self.mydataConfig['ignore_old_datasets'] = ignoreOldDatasets

    @property
    def ignoreOldDatasetIntervalNumber(self):
        """
        Return the number of days/weeks/months used to define an old dataset
        """
        return self.mydataConfig['ignore_interval_number']

    @ignoreOldDatasetIntervalNumber.setter
    def ignoreOldDatasetIntervalNumber(self, ignoreOldDatasetIntervalNumber):
        """
        Set the number of days/weeks/months used to define an old dataset
        """
        self.mydataConfig['ignore_interval_number'] = \
            ignoreOldDatasetIntervalNumber

    @property
    def ignoreOldDatasetIntervalUnit(self):
        """
        Return the time interval unit (days/weeks/months)
        used to define an old dataset
        """
        return self.mydataConfig['ignore_interval_unit']

    @ignoreOldDatasetIntervalUnit.setter
    def ignoreOldDatasetIntervalUnit(self, ignoreOldDatasetIntervalUnit):
        """
        Set the time interval unit (days/weeks/months)
        used to define an old dataset
        """
        self.mydataConfig['ignore_interval_unit'] = \
            ignoreOldDatasetIntervalUnit

    @property
    def ignoreNewFiles(self):
        """
        Returns True if MyData should ignore recently modified files
        """
        return self.mydataConfig['ignore_new_files']

    @ignoreNewFiles.setter
    def ignoreNewFiles(self, ignoreNewFiles):
        """
        Set this to True if MyData should ignore recently modified files
        """
        self.mydataConfig['ignore_new_files'] = ignoreNewFiles

    @property
    def ignoreNewFilesMinutes(self):
        """
        Return the number of minutes used to define a recently modified file
        """
        return self.mydataConfig['ignore_new_files_minutes']

    @ignoreNewFilesMinutes.setter
    def ignoreNewFilesMinutes(self, ignoreNewFilesMinutes):
        """
        Set the number of minutes used to define a recently modified file
        """
        self.mydataConfig['ignore_new_files_minutes'] = ignoreNewFilesMinutes

    @property
    def useIncludesFile(self):
        """
        Return True if using an includes file to only upload files matching
        glob patterns listed in the includes file.
        """
        return self.mydataConfig['use_includes_file']

    @useIncludesFile.setter
    def useIncludesFile(self, useIncludesFile):
        """
        Set to True if using an includes file to only upload files matching
        glob patterns listed in the includes file.
        """
        self.mydataConfig['use_includes_file'] = useIncludesFile

    @property
    def includesFile(self):
        """
        Return path to an includes file, used to only upload files matching
        glob patterns listed in the includes file.
        """
        return self.mydataConfig['includes_file']

    @includesFile.setter
    def includesFile(self, includesFile):
        """
        Set path to an includes file, used to only upload files matching
        glob patterns listed in the includes file.
        """
        self.mydataConfig['includes_file'] = includesFile

    @property
    def useExcludesFile(self):
        """
        Return True if using an excludes file to prevent uploads of files
        matching glob patterns listed in the excludes file.
        """
        return self.mydataConfig['use_excludes_file']

    @useExcludesFile.setter
    def useExcludesFile(self, useExcludesFile):
        """
        Set to True if using an excludes file to prevent uploads of files
        matching glob patterns listed in the excludes file.
        """
        self.mydataConfig['use_excludes_file'] = useExcludesFile

    @property
    def excludesFile(self):
        """
        Return path to an excludes file, used to only upload files matching
        glob patterns listed in the excludes file.
        """
        return self.mydataConfig['excludes_file']

    @excludesFile.setter
    def excludesFile(self, excludesFile):
        """
        Set path to an excludes file, used to only upload files matching
        glob patterns listed in the excludes file.
        """
        self.mydataConfig['excludes_file'] = excludesFile
