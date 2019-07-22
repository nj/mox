# Copyright (C) 2015-2019 Magenta ApS, https://magenta.dk.
# Contact: info@magenta.dk.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .oio_base import OIORestObject, OIOStandardHierarchy


class Aktivitet(OIORestObject):
    """
    Implement an Aktivitet  - manage access to database layer from the API.
    """
    pass


class AktivitetsHierarki(OIOStandardHierarchy):
    """Implement the Klassifikation Standard."""

    _name = "Aktivitet"
    _classes = [Aktivitet]
