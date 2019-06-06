from toscatranslator.common.exception import FulfillRequirementError, UnavailableNodeFilterError
from toscaparser.common.exception import ExceptionCollector


class ProviderRequirement (object):

    NAME_SUFFIX = '_name'
    ID_SUFFIX = '_id'
    DEFAULT_REQUIRED_PARAMS = ['name', 'id']

    def __init__(self, name, key, data, node_filter_class=None):
        self.name = name
        self.key = key
        self.data = data
        self.node_filter_class = node_filter_class
        self.value = None

        self.requires = self.DEFAULT_REQUIRED_PARAMS
        if self.name[-5:] == self.NAME_SUFFIX:
            self.requires = ['name']
        elif self.name[-3:] == self.ID_SUFFIX:
            self.requires = ['id']

        self.filter()

    def filter(self):
        """
        Search for required parameters
        :return:
        """
        # NOTE: only node_filter supported
        self.data = self.data.get('node_filter')
        if self.data is None:
            ExceptionCollector.appendException(UnavailableNodeFilterError(
                what=self.name
            ))
        capabilities = self.data.get('capabilities', {})
        for requires in self.requires:
            self.value = self.data.get('properties', {}).get(requires)
            if self.value:
                return

            for cap_name, cap_val in capabilities.items():
                self.value = cap_val.get('properties', {}).get(requires)
                if self.value:
                    return

        if self.node_filter_class and not self.value:
            node_filter = self.node_filter_class(self.key)
            self.value = node_filter.get_required_value(self.data, self.requires)

        if not self.value:
            raise ExceptionCollector.appendException(FulfillRequirementError(
                what=self.name
            ))

    def get_value(self):
        return self.value