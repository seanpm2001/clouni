import yaml
import copy
from toscatranslator.providers.combined.combine_requirements import PROVIDER_REQUIREMENTS


class ProviderResource(object):

    MAX_NUM_PRIORITIES = 5

    def __init__(self, node):
        """

        :param node: class NodeTemplate from toscaparser
        """
        assert self.PRIORITY is not None
        assert self.ANSIBLE_DESCRIPTION is not None
        assert self.ANSIBLE_MODULE is not None
        # NOTE: added as a parameter in toscatranslator.providers.common.tosca_template:ProviderToscaTemplate
        assert self.PROVIDER is not None

        # NOTE: filling the parameters from openstack definition to parse from input template
        node_type = node.type_definition  # toscaparser.elements.nodetype.NodeType
        self.definitions_by_name = None
        self.requirement_definitions = None
        self.set_definitions_by_name(node_type)
        self.attribute_keys = self.attribute_definitions_by_name().keys()
        self.property_keys = self.property_definitions_by_name().keys()
        self.requirement_keys = self.requirement_definitions_by_name().keys()
        self.artifact_keys = self.artifact_definitions_by_name().keys()
        self.capability_keys = self.capability_definitions_by_name().keys()

        # NOTE: Get the parameters from template using provider definition
        self.ansible_args = dict()
        # NOTE: node is NodeTemplate instance
        for key in self.property_keys:
            value = node.get_property_value(key)
            if value is not None:
                self.ansible_args[key] = value

        for key in self.attribute_keys:
            value = node.get_property_value(key)
            if value is not None:
                self.ansible_args[key] = value

        capability_defs = self.capability_definitions_by_name()
        for cap_key, cap_def in capability_defs.items():
            properties = node.get_capabilities().get(cap_key)
            definition_property_keys = cap_def.get('properties', {}).keys()
            if properties:
                for def_prop_key in definition_property_keys:
                    value = properties.get_property_value(def_prop_key)
                    if value:
                        self.ansible_args[def_prop_key] = value

        if hasattr(node, 'artifacts'):
            # TODO: oneliner
            for key, value in node.artifacts:
                self.ansible_args[key] = value

        provider_requirements = PROVIDER_REQUIREMENTS[self.PROVIDER](self.requirement_definitions)
        self.requirements = provider_requirements.get_requirements(node)
        for key, req in self.requirements.items():
            if type(req) is list:
                self.ansible_args[key] = list(v.to_ansible() for v in req)
            else:
                self.ansible_args[key] = req.to_ansible()

        self.ansible_task = None
        self.ansible_task_as_dict = None

    def set_definitions_by_name(self, node_type):
        """
        Get the definitions from ToscaTemplate of toscaparser
        Refactor the requirements as its definition is list, not dict
        :param node_type: class NodeTemplate of toscaparser
        :return: dict of key = name of category and value is a dict
        """
        requirement_defs_list = node_type.get_value(node_type.REQUIREMENTS, None, True) or []
        requirement_defs_dict = {}
        requirement_defs_list_with_name_added = []
        for req_def in requirement_defs_list:
            for req_name, req_params in req_def.items():
                cur_req_def = requirement_defs_dict.get(req_name)
                if cur_req_def:
                    if isinstance(cur_req_def, list):
                        requirement_defs_dict[req_name].append(req_params)
                    else:
                        requirement_defs_dict[req_name] = [cur_req_def, req_params]
                else:
                    requirement_defs_dict[req_name] = req_params
                copy_req_def = copy.copy(req_params)
                copy_req_def['name'] = req_name
                requirement_defs_list_with_name_added.append(copy_req_def)

        # Fulfill the definitions
        self.definitions_by_name = dict(
            attributes=node_type.get_value(node_type.ATTRIBUTES) or {},
            properties=node_type.get_value(node_type.PROPERTIES) or {},
            capabilities=node_type.get_value(node_type.CAPABILITIES, None, True) or {},
            requirements=requirement_defs_dict,
            interfaces=node_type.get_value(node_type.INTERFACES) or {},
            artifacts=node_type.get_value(node_type.ARTIFACTS) or {}
        )
        self.requirement_definitions = requirement_defs_list_with_name_added

    def get_definitions_by_name(self, name):
        return self.definitions_by_name.get(name)

    def capability_definitions_by_name(self):
        return self.get_definitions_by_name('capabilities')

    def property_definitions_by_name(self):
        return self.get_definitions_by_name('properties')

    def attribute_definitions_by_name(self):
        return self.get_definitions_by_name('attributes')

    def requirement_definitions_by_name(self):
        return self.get_definitions_by_name('requirements')

    def artifact_definitions_by_name(self):
        return self.get_definitions_by_name('artifacts')

    def get_ansible_task_for_create(self, additional_args=None):
        """
        Fulfill the dict with ansible task arguments to create infrastructure
        :param additional_args: dict of arguments to add
        :return: string of ansible task to place in playbook
        """
        if additional_args is None:
            additional_args = {}
        ansible_args = copy.copy(self.ansible_args)
        ansible_args['state'] = 'present'
        ansible_args.update(additional_args)
        self.ansible_task_as_dict = dict()
        self.ansible_task_as_dict['name'] = self.ANSIBLE_DESCRIPTION
        self.ansible_task_as_dict[self.ANSIBLE_MODULE] = self.ansible_args
        self.ansible_task = yaml.dump(self.ansible_task_as_dict)

        return self.ansible_task