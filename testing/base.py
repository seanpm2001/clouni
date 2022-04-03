from toscatranslator.common.translator_to_configuration_dsl import translate as common_translate
from shell_clouni import shell
import os
import yaml
import copy
import difflib

from toscatranslator.common.utils import deep_update_dict
from toscatranslator.common.tosca_reserved_keys import PROVIDERS, ANSIBLE, TYPE, \
    TOSCA_DEFINITIONS_VERSION, PROPERTIES, CAPABILITIES, REQUIREMENTS, TOPOLOGY_TEMPLATE, NODE_TEMPLATES, INTERFACES

TEST = 'test'


class BaseAnsibleProvider:
    TESTING_TEMPLATE_FILENAME_TO_JOIN = ['examples', 'testing-example.yaml']
    NODE_NAME = 'tosca_server_example'
    DEFAULT_TEMPLATE = {
        TOSCA_DEFINITIONS_VERSION: "tosca_simple_yaml_1_0",
        TOPOLOGY_TEMPLATE: {
            NODE_TEMPLATES: {
                NODE_NAME: {
                    TYPE: "tosca.nodes.Compute"
                }
            }
        }
    }

    def testing_template_filename(self):
        r = None
        for i in self.TESTING_TEMPLATE_FILENAME_TO_JOIN:
            if r == None:
                r = i
            else:
                r = os.path.join(r, i)
        return r

    def read_template(self, filename=None):
        if not filename:
            filename = self.testing_template_filename()
        with open(filename, 'r') as f:
            return f.read()

    def write_template(self, template, filename=None):
        if not filename:
            filename = self.testing_template_filename()
        with open(filename, 'w') as f:
            f.write(template)

    def delete_template(self, filename=None):
        if not filename:
            filename = self.testing_template_filename()
        if os.path.exists(filename):
            os.remove(filename)

    def parse_yaml(self, content):
        r = yaml.load(content, Loader=yaml.Loader)
        return r

    def parse_all_yaml(self, content):
        r = yaml.full_load_all(content)
        return r

    def prepare_yaml(self, content):
        r = yaml.dump(content)
        return r

    def test_provider(self):
        assert hasattr(self, 'PROVIDER') is not None
        assert self.PROVIDER in PROVIDERS

    def get_ansible_create_output(self, template, template_filename=None, extra=None, delete_template=True):
        if not template_filename:
            template_filename = self.testing_template_filename()
        self.write_template(self.prepare_yaml(template))
        r = common_translate(template_filename, False, self.PROVIDER, ANSIBLE, TEST, False, extra=extra,
                             log_level='debug')
        print(r)
        if delete_template:
            self.delete_template(template_filename)
        playbook = self.parse_yaml(r)
        return playbook

    def get_ansible_delete_output(self, template, template_filename=None, extra=None, delete_template=True):
        if not template_filename:
            template_filename = self.testing_template_filename()
        self.write_template(self.prepare_yaml(template))
        r = common_translate(template_filename, False, self.PROVIDER, ANSIBLE, TEST, True, extra=extra)
        print(r)
        if delete_template:
            self.delete_template(template_filename)
        playbook = self.parse_yaml(r)
        return playbook

    def get_ansible_delete_output_from_file(self, template, template_filename=None, extra=None):
        if not template_filename:
            template_filename = self.testing_template_filename()
        r = common_translate(template_filename, False, self.PROVIDER, ANSIBLE, TEST, True, extra=extra)
        print(r)
        playbook = self.parse_yaml(r)
        return playbook

    def get_k8s_output(self, template, template_filename=None):
        if not template_filename:
            template_filename = self.testing_template_filename()
        self.write_template(self.prepare_yaml(template))
        r = common_translate(template_filename, False, self.PROVIDER, 'kubernetes', TEST, False, log_level='debug')
        print(r)
        manifest = list(self.parse_all_yaml(r))
        return manifest

    def update_node_template(self, template, node_name, update_value, param_type):
        update_value = {
            TOPOLOGY_TEMPLATE: {
                NODE_TEMPLATES: {
                    node_name: {
                        param_type: update_value
                    }
                }
            }
        }
        return deep_update_dict(template, update_value)

    def update_template_property(self, template, node_name, update_value):
        return self.update_node_template(template, node_name, update_value, PROPERTIES)

    def update_template_attribute(self, template, node_name, update_value):
        return self.update_node_template(template, node_name, update_value, PROPERTIES)

    def update_template_capability(self, template, node_name, update_value):
        return self.update_node_template(template, node_name, update_value, CAPABILITIES)

    def update_template_capability_properties(self, template, node_name, capability_name, update_value):
        uupdate_value = {
            capability_name: {
                PROPERTIES: update_value
            }
        }
        return self.update_template_capability(template, node_name, uupdate_value)

    def update_template_requirement(self, template, node_name, update_value):
        return self.update_node_template(template, node_name, update_value, REQUIREMENTS)

    def update_template_operation(self, template, node_name, interface_name, operation_name, update_value):
        uupdate_value = {
            interface_name: {
                operation_name: update_value
            }
        }
        return self.update_node_template(template, node_name, uupdate_value, INTERFACES)

    def diff_files(self, file_name1, file_name2):
        with open(file_name1, 'r') as file1, open(file_name2, 'r') as file2:
            text1 = file1.readlines()
            text2 = file2.readlines()
            for line in difflib.unified_diff(text1, text2):
                print(line)


class TestAnsibleProvider(BaseAnsibleProvider):
    def test_full_translating(self):
        file_path = os.path.join('examples', 'tosca-server-example.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--cluster-name', 'test'])

    def test_meta(self, extra=None):
        if hasattr(self, 'check_meta'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_value = "master=true"
            testing_parameter = {
                "meta": testing_value
            }
            template = self.update_template_property(template, self.NODE_NAME, testing_parameter)
            playbook = self.get_ansible_create_output(template, extra=extra)

            assert next(iter(playbook), {}).get('tasks')
            tasks = playbook[0]['tasks']

            if extra:
                self.check_meta(tasks, testing_value=testing_value, extra=extra)
            else:
                self.check_meta(tasks, testing_value=testing_value)

            playbook = self.get_ansible_delete_output(template, extra=extra)

    def test_private_address(self):
        if hasattr(self, 'check_private_address'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_value = "192.168.12.26"
            testing_parameter = {
                "private_address": testing_value
            }
            template = self.update_template_property(template, self.NODE_NAME, testing_parameter)
            playbook = self.get_ansible_create_output(template)

            assert next(iter(playbook), {}).get('tasks')
            tasks = playbook[0]['tasks']

            self.check_private_address(tasks, testing_value)

    def test_public_address(self):
        if hasattr(self, 'check_public_address'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_value = "10.10.18.217"
            testing_parameter = {
                "public_address": testing_value
            }
            template = self.update_template_property(template, self.NODE_NAME, testing_parameter)
            playbook = self.get_ansible_create_output(template)

            assert next(iter(playbook), {}).get('tasks')

            tasks = playbook[0]['tasks']
            self.check_public_address(tasks, testing_value)

    def test_network_name(self):
        if hasattr(self, 'check_network_name'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_value = "test-two-routers"
            testing_parameter = {
                "networks": {
                    "default": {
                        "network_name": testing_value
                    }
                }
            }
            template = self.update_template_property(template, self.NODE_NAME, testing_parameter)
            playbook = self.get_ansible_create_output(template)

            assert next(iter(playbook), {}).get('tasks')

            tasks = playbook[0]['tasks']
            self.check_network_name(tasks, testing_value)

    def test_host_capabilities(self):
        if hasattr(self, 'check_host_capabilities'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_parameter = {
                "num_cpus": 1,
                "disk_size": "5 GiB",
                "mem_size": "1024 MiB"
            }
            template = self.update_template_capability_properties(template, self.NODE_NAME, "host", testing_parameter)
            playbook = self.get_ansible_create_output(template)

            assert next(iter(playbook), {}).get('tasks')

            tasks = playbook[0]['tasks']
            self.check_host_capabilities(tasks)

    def test_endpoint_capabilities(self):
        if hasattr(self, 'check_endpoint_capabilities'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_parameter = {
                "endpoint": {
                    "properties": {
                        "protocol": "tcp",
                        "port": 22,
                        "initiator": "target",
                        "ip_address": "0.0.0.0"
                    }
                }
            }
            template = self.update_template_capability(template, self.NODE_NAME, testing_parameter)
            playbook = self.get_ansible_create_output(template)
            assert next(iter(playbook), {}).get('tasks')

            tasks = playbook[0]['tasks']
            self.check_endpoint_capabilities(tasks)

    def test_os_capabilities(self):
        if hasattr(self, 'check_os_capabilities'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_parameter = {
                "architecture": "x86_64",
                "type": "ubuntu",
                "distribution": "xenial",
                "version": 16.04
            }
            template = self.update_template_capability_properties(template, self.NODE_NAME, "os", testing_parameter)
            playbook = self.get_ansible_create_output(template)
            assert next(iter(playbook), {}).get('tasks')

            tasks = playbook[0]['tasks']
            self.check_os_capabilities(tasks)

    def test_scalable_capabilities(self):
        if hasattr(self, 'check_scalable_capabilities'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_parameter = {
                "min_instances": 1,
                "default_instances": 2,
                "max_instances": 2
            }
            template = self.update_template_capability_properties(template, self.NODE_NAME, "scalable",
                                                                  testing_parameter)
            playbook = self.get_ansible_create_output(template)
            assert next(iter(playbook), {}).get('tasks')

            tasks = playbook[0]['tasks']
            self.check_scalable_capabilities(tasks)

    def test_host_of_software_component(self):
        if hasattr(self, "check_host_of_software_component"):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_parameter = {
                "public_address": "10.100.149.15",
                "networks": {
                    "default": {
                        "network_name": "net-for-intra-sandbox"
                    }
                }
            }
            template = self.update_template_property(template, self.NODE_NAME, testing_parameter)
            template['node_types'] = {
                'clouni.nodes.ServerExample': {
                    'derived_from': 'tosca.nodes.SoftwareComponent'
                }
            }
            template['topology_template']['node_templates']['service_1'] = {
                'type': 'clouni.nodes.ServerExample',
                'properties': {
                    'component_version': 0.1
                },
                'requirements': [{
                    'host': self.NODE_NAME
                }],
                'interfaces':{
                    'Standard': {
                        'create': {
                            'implementation': 'examples/ansible-server-example.yaml',
                            'inputs': {
                                'version': { 'get_property': ['service_1', 'component_version'] }
                            }
                        }
                    }
                }
            }
            playbook = self.get_ansible_create_output(template)

            self.assertEqual(len(playbook), 2)
            self.assertIsNotNone(playbook[0].get('tasks'))
            self.assertIsNotNone(playbook[1].get('tasks'))
            self.assertEqual(playbook[1].get('hosts'), self.NODE_NAME)

            tasks1 = playbook[0]['tasks']
            tasks2 = playbook[1]['tasks']
            self.check_host_of_software_component(tasks1, tasks2)

    def test_get_input(self):
        if hasattr(self, 'check_get_input'):
            testing_value = "10.100.157.20"
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            template['topology_template']['inputs'] = {
                'public_address': {
                    'type': 'string',
                    'default': testing_value
                }
            }
            testing_parameter = {
                "public_address": {
                    "get_input": "public_address"
                }
            }
            template = self.update_template_property(template, self.NODE_NAME, testing_parameter)
            playbook = self.get_ansible_create_output(template)
            self.assertIsNotNone(next(iter(playbook), {}).get('tasks'))

            tasks = playbook[0]['tasks']
            self.check_get_input(tasks, testing_value)

    def test_get_property(self):
        if hasattr(self, 'check_get_property'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_value = "master=true"
            testing_parameter = {
                "meta": testing_value
            }
            template = self.update_template_property(template, self.NODE_NAME, testing_parameter)
            template['topology_template']['node_templates'][self.NODE_NAME + '_2'] = {
                'type': 'tosca.nodes.Compute',
                'properties': {
                    'meta': {
                        'get_property': [
                            self.NODE_NAME,
                            'meta'
                        ]
                    }
                }
            }
            playbook = self.get_ansible_create_output(template)
            self.assertIsNotNone(next(iter(playbook), {}).get('tasks'))

            tasks = playbook[0]['tasks']
            self.check_get_property(tasks, testing_value)

    def test_get_attribute(self):
        if hasattr(self, 'check_get_attribute'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_value = "master=true"
            testing_parameter = {
                "meta": testing_value
            }
            template = self.update_template_property(template, self.NODE_NAME, testing_parameter)
            template['topology_template']['node_templates'][self.NODE_NAME + '_2'] = {
                'type': 'tosca.nodes.Compute',
                'properties': {
                    'meta': {
                        'get_attribute': [
                            self.NODE_NAME,
                            'meta'
                        ]
                    }
                }
            }
            playbook = self.get_ansible_create_output(template)
            self.assertIsNotNone(next(iter(playbook), {}).get('tasks'))

            tasks = playbook[0]['tasks']
            self.check_get_attribute(tasks, testing_value)

    def test_outputs(self):
        if hasattr(self, "check_outputs"):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_value = "10.10.18.217"
            testing_parameter = {
                "public_address": testing_value
            }
            template = self.update_template_property(template, self.NODE_NAME, testing_parameter)
            template['topology_template']['outputs'] = {
                "server_address": {
                    "description": "Public IP address for the provisioned server.",
                    "value": {
                        "get_attribute": [ self.NODE_NAME, "public_address" ] }
                }
            }
            playbook = self.get_ansible_create_output(template)

            assert next(iter(playbook), {}).get('tasks')

            tasks = playbook[0]['tasks']
            self.check_outputs(tasks, testing_value)

    def test_operations(self):
        if hasattr(self, "check_operations"):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_value = "configure_server.sh"
            testing_parameter = {
                "implementation": testing_value
            }
            template = self.update_template_operation(template, self.NODE_NAME, "Standard", "configure",
                                                      testing_parameter)
            playbook = self.get_ansible_create_output(template)

            self.assertEqual(len(playbook), 2)
            self.assertIsNotNone(playbook[0].get('tasks'))
            self.assertIsNotNone(playbook[1].get('tasks'))
            self.assertEqual(playbook[0].get('hosts'), 'localhost')
            self.assertEqual(playbook[1].get('hosts'), self.NODE_NAME)

            tasks1 = playbook[0]['tasks']
            tasks2 = playbook[1]['tasks']
            self.check_operations(tasks2, testing_value)
