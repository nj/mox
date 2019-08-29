#
# Copyright (c) 2017-2018, Magenta ApS
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


import contextlib
import json
import mock
import os
import pprint
import uuid
import copy
import types
import typing

import flask_testing

from oio_rest import app
from oio_rest.db import db_structure, management as db_mgmt

TESTS_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.dirname(TESTS_DIR)
TOP_DIR = os.path.dirname(BASE_DIR)
FIXTURE_DIR = os.path.join(TESTS_DIR, 'fixtures')


def get_fixture(fixture_name, mode='rt', as_text=True):
    """Reads data from fixture folder. If the file name ends with
    ``.json``, we parse it, otherwise, we just return it as text.
    """
    with open(os.path.join(FIXTURE_DIR, fixture_name), mode) as fp:
        if os.path.splitext(fixture_name)[1] == '.json' and as_text:
            return json.load(fp)
        else:
            return fp.read()


class _BaseTestCase(flask_testing.TestCase):
    """Basic testcase without database support, but with various helper functions.

    """

    def setup(self):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)

        for p in [
            mock.patch("oio_rest.settings.FILE_UPLOAD_FOLDER", "./mox-upload"),
            mock.patch("oio_rest.settings.LOG_AMQP_SERVER", None),
        ]:
            stack.enter_context(p)

    def get_lora_app(self):
        app.config['DEBUG'] = False
        app.config['TESTING'] = True
        app.config['LIVESERVER_PORT'] = 0
        app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False

        return app

    def create_app(self):
        return self.get_lora_app()

    def assertRequestResponse(self, path, expected, message=None,
                              status_code=None, drop_keys=(), **kwargs):
        '''Issue a request and assert that it succeeds (and does not
        redirect) and yields the expected output.

        **kwargs is passed directly to the test client -- see the
        documentation for werkzeug.test.EnvironBuilder for details.

        One addition is that we support a 'json' argument that
        automatically posts the given JSON data.

        '''

        r = self.perform_request(path, **kwargs)

        actual = (
            json.loads(r.get_data(as_text=True))
            if r.mimetype == 'application/json'
            else r.get_data(as_text=True)
        )

        for k in drop_keys:
            try:
                actual.pop(k)
            except (IndexError, KeyError, TypeError):
                pass

        if not message:
            status_message = 'request {!r} failed with status {}'.format(
                path, r.status,
            )
            content_message = 'request {!r} yielded an expected result'.format(
                path,
            )
        else:
            status_message = content_message = message

        try:
            if status_code is None:
                self.assertOK(r, status_message)
            else:
                self.assertEqual(r.status_code, status_code, status_message)

            self.assertEqual(expected, actual, content_message)

        except AssertionError:
            print(path)
            print(r.status)
            pprint.pprint(actual)

            raise

    def assertRequestFails(self, path, code, message=None, **kwargs):
        '''Issue a request and assert that it succeeds (and does not
        redirect) and yields the expected output.

        **kwargs is passed directly to the test client -- see the
        documentation for werkzeug.test.EnvironBuilder for details.

        One addition is that we support a 'json' argument that
        automatically posts the given JSON data.
        '''
        message = message or "request {!r} didn't fail properly".format(path)

        r = self.perform_request(path, **kwargs)

        self.assertEqual(r.status_code, code, message)

    def perform_request(self, path, **kwargs):
        if 'json' in kwargs:
            kwargs.setdefault('method', 'POST')
            kwargs.setdefault('data', json.dumps(kwargs.pop('json'), indent=2))
            kwargs.setdefault('headers', {'Content-Type': 'application/json'})

        return self.client.open(path, **kwargs)

    def assertRegistrationsEqual(self, expected, actual, message=None):
        def sort_inner_lists(obj):
            """Sort all inner lists and tuples by their JSON string value,
            recursively. This is quite stupid and slow, but works!

            This is purely to help comparison tests, as we don't care about the
            list ordering

            """
            if isinstance(obj, dict):
                return {
                    k: sort_inner_lists(v)
                    for k, v in obj.items()
                }
            elif isinstance(obj, (list, tuple)):
                return sorted(
                    map(sort_inner_lists, obj),
                    key=(lambda p: json.dumps(p, sort_keys=True)),
                )
            else:
                return obj

        # drop lora-generated timestamps & users
        if isinstance(expected, dict):
            expected.pop('fratidspunkt', None)
            expected.pop('tiltidspunkt', None)
            expected.pop('brugerref', None)

        if isinstance(actual, dict):
            actual.pop('fratidspunkt', None)
            actual.pop('tiltidspunkt', None)
            actual.pop('brugerref', None)

        # Sort all inner lists and compare
        self.assertEqual(
            sort_inner_lists(expected),
            sort_inner_lists(actual),
            message,
        )

    def assertOK(self, response, message=None):
        self.assertTrue(
            200 <= response.status_code < 300,
            message or 'request failed with {}!'.format(response.status)
        )

    def assertUUID(self, s):
        try:
            uuid.UUID(s)
        except (TypeError, ValueError):
            self.fail('{!r} is not a uuid!'.format(s))

    def assert201(self, response):
        """
        Verify that the response from LoRa is 201 and contains the correct
        JSON.
        :param response: Response from LoRa when creating a new object
        """
        self.assertEqual(201, response.status_code)
        self.assertEqual(1, len(response.json))
        self.assertUUID(response.json['uuid'])

    def get(self, path, **params):
        r = self.perform_request(path, query_string=params)

        self.assertOK(r)

        d = r.json['results'][0]

        if not d or not all(isinstance(v, dict) for v in d):
            return d

        self.assertEqual(len(d), 1)

        registrations = d[0]['registreringer']

        if set(params.keys()) & {'registreretfra', 'registrerettil',
                                 'registreringstid'}:
            return registrations
        else:
            self.assertEqual(len(registrations), 1)
            return registrations[0]

    def put(self, path, json):
        r = self.perform_request(path, json=json, method="PUT")
        self.assertOK(r)

        return r.json['uuid']

    def patch(self, path, json):
        r = self.perform_request(path, json=json, method="PATCH")
        self.assertOK(r)

        return r.json['uuid']

    def post(self, path, json):
        r = self.perform_request(path, json=json, method="POST")
        self.assertOK(r)

        return r.json['uuid']

    def assertQueryResponse(self, path, expected, **params):
        """Perform a request towards LoRa, and assert that it yields the
        expected output.

        Results are unpacked from the LoRa result structure and filtered of
        metadata before comparison

        **params are passed as part of the query string in the request.
        """

        actual = self.get(path, **params)

        print(json.dumps(actual, indent=2))

        self.assertRegistrationsEqual(expected, actual)

    def load_fixture(self, path, fixture_name, uuid=None):
        """Load a fixture, i.e. a JSON file in the 'fixtures' directory,
        into LoRA at the given path & UUID.
        """
        if uuid:
            method = 'PUT'
            path = '{}/{}'.format(path, uuid)
        else:
            method = 'POST'

        r = self.perform_request(
            path, json=get_fixture(fixture_name), method=method,
        )

        msg = 'write of {!r} to {!r} failed!'.format(fixture_name, path)

        try:
            self.assertOK(r, msg)

            objid = r.json.get('uuid')

            self.assertTrue(objid)
        except AssertionError:
            print(path)
            print(r.status)
            print(r.get_data(as_text=True))

            raise

        return objid


class ExtTestCase(_BaseTestCase):
    """Testcase with extension helper functions, but no database access. For an
    extension test class with database access use ExtDBTestCase.

    """

    @classmethod
    @contextlib.contextmanager
    def patch_db_struct(cls, new: typing.Union[types.ModuleType, dict]):
        """Context manager for overriding db_structures"""

        patches = [
            mock.patch("oio_rest.db.db_helpers._attribute_fields", {}),
            mock.patch("oio_rest.db.db_helpers._attribute_names", {}),
            mock.patch("oio_rest.db.db_helpers._relation_names", {}),
            mock.patch("oio_rest.validate.SCHEMAS", {}),
        ]

        if isinstance(new, types.ModuleType):
            patches.append(
                mock.patch(
                    "oio_rest.db.db_structure.REAL_DB_STRUCTURE",
                    new=new.REAL_DB_STRUCTURE,
                )
            )
        else:
            patches.append(
                mock.patch(
                    "oio_rest.db.db_structure.REAL_DB_STRUCTURE", new=new
                )
            )

        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)

            yield

    @classmethod
    @contextlib.contextmanager
    def extend_db_struct(cls, new: dict):
        """Context manager for extending db_structures"""

        dbs = copy.deepcopy(db_structure.DATABASE_STRUCTURE)
        real_dbs = copy.deepcopy(db_structure.REAL_DB_STRUCTURE)

        patches = [
            mock.patch("oio_rest.db.db_helpers._attribute_fields", {}),
            mock.patch("oio_rest.db.db_helpers._attribute_names", {}),
            mock.patch("oio_rest.db.db_helpers._relation_names", {}),
            mock.patch("oio_rest.validate.SCHEMAS", {}),
            mock.patch("oio_rest.db.db_structure.DATABASE_STRUCTURE", new=dbs),
            mock.patch(
                "oio_rest.db.db_structure.REAL_DB_STRUCTURE", new=real_dbs
            ),
        ]

        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)

            db_structure.load_db_extensions(new)

            yield


class DBTestCase(_BaseTestCase):
    """Testcase with database access. Will create a new database from a template
    for each test. Requires the setting `[testing] enabled=True` during
    database initialization to create the template.

    This class does not support extending the database structure. For extension
    tests use ExtDBtTestCase.

    """

    def setUp(self):
        super().setUp()
        self.addCleanup(db_mgmt.testdb_reset)

    @classmethod
    def setUpClass(cls):
        db_mgmt.testdb_setup()

    @classmethod
    def tearDownClass(cls):
        db_mgmt.testdb_teardown()


class ExtDBTestCase(ExtTestCase):
    """Testcase with database and extension support. Will initialize a new database
    from scratch for every class and is therefore quite slow. For a faster
    alternative without extension support use DBTestCase.

    """

    db_structure_extensions = None

    def setUp(self):
        super().setUp()

        self.addCleanup(db_mgmt.testdb_reset, from_scratch=True)

    @classmethod
    def setUpClass(cls):
        cls.__class_stack = contextlib.ExitStack()
        cls.__class_stack.enter_context(
            cls.extend_db_struct(cls.db_structure_extensions)
        )
        db_mgmt.testdb_setup(from_scratch=True)

    @classmethod
    def tearDownClass(cls):
        cls.__class_stack.close()
        db_mgmt.testdb_teardown()
