#!/usr/bin/env python3
"""
    apply-templates.py
    ~~~~~~~~~~~~~~~~~~

    This script generates a bunch of sql files from jinja2 templates.

    More information in `../db/db-templating/`.

    Example usage:
        $ ./apply-template.py  # from a Python 3 environment
"""

import importlib
import sys
from collections import OrderedDict
import copy
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader


DIR = (Path(__file__).absolute().parent.parent / "db" / "db-templating")
TEMPLATE_DIR = DIR / "templates"

TEMPLATES = (
    "dbtyper-specific",
    "tbls-specific",
    "_remove_nulls_in_array",
    "_as_get_prev_registrering",
    "_as_create_registrering",
    "as_update",
    "as_create_or_import",
    "as_list",
    "as_read",
    "as_search",
    "json-cast-functions",
    "_as_sorted",
    "_as_filter_unauth",
)


@click.option('-o', '--output', type=click.File('w'), default='-',
              help='store output in the given file rather than stdout')
@click.option('-m', '--module-name',
              help='module to read settings from',
              default='oio_common.db_structure',
              envvar='APPLY_TEMPLATES_MODULE',
              show_default=True,
              show_envvar=True)
@click.command(context_settings={
    'help_option_names': ['-h', '--help'],
})
def main(output, module_name):
    structmod = importlib.import_module(module_name)

    template_env = Environment(loader=FileSystemLoader([str(TEMPLATE_DIR)]))

    for oio_type in sorted(structmod.DATABASE_STRUCTURE):
        for template_name in TEMPLATES:
            template_file = "%s.jinja.sql" % template_name
            template = template_env.get_template(template_file)

            context = copy.deepcopy(structmod.DATABASE_STRUCTURE[oio_type])
            context["script_signature"] = "apply-template.py %s %s" % (
                oio_type,
                template_file,
            )
            # it is important that the order is stable, as some templates rely on this
            context["tilstande"] = OrderedDict(context["tilstande"])
            context["attributter"] = OrderedDict(context["attributter"])
            context["oio_type"] = oio_type.lower()
            # create version of 'tilstande' and 'attributter' in reverse order
            context["tilstande_revorder"] = OrderedDict(
                reversed(context["tilstande"].items())
            )
            context["attributter_revorder"] = OrderedDict(
                reversed(context["attributter"].items())
            )

            try:
                context["include_mixin"] = (
                    structmod.DB_TEMPLATE_EXTRA_OPTIONS
                    [oio_type][template_file]["include_mixin"]
                )
            except KeyError:
                context["include_mixin"] = "empty.jinja"

            template.stream(context).dump(output)
            output.write('\n')


if __name__ == '__main__':
    main()
