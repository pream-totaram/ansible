# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Matt Martz <matt@sivel.net>
# Copyright (C) 2015 Rackspace US, Inc.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
from voluptuous import ALLOW_EXTRA, PREVENT_EXTRA, All, Any, Length, Invalid, Required, Schema, Self
from ansible.module_utils.six import string_types
from ansible.module_utils.common.collections import is_iterable
list_string_types = list(string_types)
any_string_types = Any(*string_types)

# Valid DOCUMENTATION.author lines
# Based on Ansibulbot's extract_github_id()
#   author: First Last (@name) [optional anything]
#     "Ansible Core Team" - Used by the Bot
#     "Michael DeHaan" - nop
#     "Name (!UNKNOWN)" - For the few untraceable authors
author_line = re.compile(r'^\w.*(\(@([\w-]+)\)|!UNKNOWN)(?![\w.])|^Ansible Core Team$|^Michael DeHaan$')


def sequence_of_sequences(min=None, max=None):
    return All(
        Any(
            None,
            [Length(min=min, max=max)],
            tuple([Length(min=min, max=max)]),
        ),
        Any(
            None,
            [Any(list, tuple)],
            tuple([Any(list, tuple)]),
        ),
    )


ansible_module_kwargs_schema = Schema(
    {
        'argument_spec': dict,
        'bypass_checks': bool,
        'no_log': bool,
        'check_invalid_arguments': Any(None, bool),
        'mutually_exclusive': sequence_of_sequences(min=2),
        'required_together': sequence_of_sequences(min=2),
        'required_one_of': sequence_of_sequences(min=2),
        'add_file_common_args': bool,
        'supports_check_mode': bool,
        'required_if': sequence_of_sequences(min=3),
    }
)

suboption_schema = Schema(
    {
        Required('description'): Any(list_string_types, *string_types),
        'required': bool,
        'choices': list,
        'aliases': Any(list_string_types),
        'version_added': Any(float, *string_types),
        'default': Any(None, float, int, bool, list, dict, *string_types),
        # Note: Types are strings, not literal bools, such as True or False
        'type': Any(None, 'str', 'list', 'dict', 'bool', 'int', 'float', 'path', 'raw', 'jsonarg', 'json', 'bytes', 'bits'),
        # Recursive suboptions
        'suboptions': Any(None, *list({str_type: Self} for str_type in string_types)),
    },
    extra=PREVENT_EXTRA
)

# This generates list of dicts with keys from string_types and suboption_schema value
# for example in Python 3: {str: suboption_schema}
list_dict_suboption_schema = [{str_type: suboption_schema} for str_type in string_types]

option_schema = Schema(
    {
        Required('description'): Any(list_string_types, *string_types),
        'required': bool,
        'choices': list,
        'aliases': Any(list_string_types),
        'version_added': Any(float, *string_types),
        'default': Any(None, float, int, bool, list, dict, *string_types),
        'suboptions': Any(None, *list_dict_suboption_schema),
        # Note: Types are strings, not literal bools, such as True or False
        'type': Any(None, 'str', 'list', 'dict', 'bool', 'int', 'float', 'path', 'raw', 'jsonarg', 'json', 'bytes', 'bits'),
    },
    extra=PREVENT_EXTRA
)

# This generates list of dicts with keys from string_types and option_schema value
# for example in Python 3: {str: option_schema}
list_dict_option_schema = [{str_type: option_schema} for str_type in string_types]


def return_contains(v):
    schema = Schema(
        {
            Required('contains'): Any(dict, list, *string_types)
        },
        extra=ALLOW_EXTRA
    )
    if v.get('type') == 'complex':
        return schema(v)
    return v


return_schema = Any(
    All(
        Schema(
            {
                any_string_types: {
                    Required('description'): Any(list_string_types, *string_types),
                    Required('returned'): Any(*string_types),
                    Required('type'): Any('string', 'list', 'boolean', 'dict', 'complex', 'bool', 'float', 'int', 'dictionary', 'str'),
                    'version_added': Any(float, *string_types),
                    'sample': Any(None, list, dict, int, float, *string_types),
                    'example': Any(None, list, dict, int, float, *string_types),
                    'contains': object,
                }
            }
        ),
        Schema({any_string_types: return_contains})
    ),
    Schema(type(None)),
)


deprecation_schema = Schema(
    {
        # Only list branches that are deprecated or may have docs stubs in
        # Deprecation cycle changed at 2.4 (though not retroactively)
        # 2.3 -> removed_in: "2.5" + n for docs stub
        # 2.4 -> removed_in: "2.8" + n for docs stub
        Required('removed_in'): Any("2.2", "2.3", "2.4", "2.5", "2.6", "2.8", "2.9", "2.10", "2.11", "2.12"),
        Required('why'): Any(*string_types),
        Required('alternative'): Any(*string_types),
        'removed': Any(True),
    },
    extra=PREVENT_EXTRA
)


def author(value):

    if not is_iterable(value):
        value = [value]

    for line in value:
        m = author_line.search(line)
        if not m:
            raise Invalid("Invalid author")


def doc_schema(module_name):
    deprecated_module = False

    if module_name.startswith('_'):
        module_name = module_name[1:]
        deprecated_module = True
    doc_schema_dict = {
        Required('module'): module_name,
        Required('short_description'): Any(*string_types),
        Required('description'): Any(list_string_types, *string_types),
        Required('version_added'): Any(float, *string_types),
        Required('author'): All(Any(None, list_string_types, *string_types), author),
        'notes': Any(None, list_string_types),
        'requirements': list_string_types,
        'todo': Any(None, list_string_types, *string_types),
        'options': Any(None, *list_dict_option_schema),
        'extends_documentation_fragment': Any(list_string_types, *string_types)
    }

    if deprecated_module:
        deprecation_required_scheme = {
            Required('deprecated'): Any(deprecation_schema),
        }

        doc_schema_dict.update(deprecation_required_scheme)
    return Schema(
        doc_schema_dict,
        extra=PREVENT_EXTRA
    )


def metadata_1_0_schema(deprecated):
    valid_status = Any('stableinterface', 'preview', 'deprecated', 'removed')
    if deprecated:
        valid_status = Any('deprecated')

    return Schema(
        {
            Required('status'): [valid_status],
            Required('metadata_version'): '1.0',
            Required('supported_by'): Any('core', 'community', 'curated')
        }
    )


def metadata_1_1_schema():
    valid_status = Any('stableinterface', 'preview', 'deprecated', 'removed')

    return Schema(
        {
            Required('status'): [valid_status],
            Required('metadata_version'): '1.1',
            Required('supported_by'): Any('core', 'community', 'certified', 'network')
        }
    )


# Things to add soon
####################
# 1) Recursively validate `type: complex` fields
#    This will improve documentation, though require fair amount of module tidyup

# Possible Future Enhancements
##############################

# 1) Don't allow empty options for choices, aliases, etc
# 2) If type: bool ensure choices isn't set - perhaps use Exclusive
# 3) both version_added should be quoted floats

#  Tool that takes JSON and generates RETURN skeleton (needs to support complex structures)
