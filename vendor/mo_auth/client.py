# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#

from __future__ import absolute_import, division, unicode_literals

import sys
from io import StringIO

import requests
import rsa
from qrcode import QRCode

from mo_dots import wrap, Data
from mo_files import URL
from mo_json import value2json
from mo_kwargs import override
from mo_logs import Log
from mo_math import bytes2base64, int2base64
from mo_math.vendor import rsa_crypto
from mo_threads import Till
from mo_times import Date, Timer


class Auth0Client(object):
    @override
    def __init__(self, kwargs=None):
        # GENERATE PRIVATE KEY
        self.config = kwargs
        self.session = None
        with Timer("generate {{bits}} bits rsa key", {"bits": self.config.rsa.bits}):
            Log.note("This will take a while....")
            self.public_key, self.private_key = rsa.newkeys(self.config.rsa.bits)

    def login(self, please_stop=None):
        """
        :param please_stop: SIGNAL TO STOP EARLY
        :return: SESSION THAT CAN BE USED TO SEND AUTHENTICATED REQUESTS
        """
        # SEND PUBLIC KEY
        now = Date.now().unix
        self.session = requests.Session()
        signed = rsa_crypto.sign(
            Data(
                public_key={
                    "n": self.public_key.e,
                    "r": int2base64(self.public_key.n)
                },
                timestamp=now
            ),
            self.private_key
        )
        try:
            response = self.session.request(
                "POST",
                self.config.endpoints.register,
                json=value2json(signed)
            )
        except Exception as e:
            raise Log.error("problem registering device", cause=e)

        device = wrap(response.json())
        cookie = self.session.cookies[self.config.session.cookie.name]

        # SHOW URL AS QR CODE
        qr = QRCode()
        qr.add_data(response.url)
        qr_code = StringIO()
        qr.print_ascii(out=qr_code)
        sys.stdout.print(qr_code)

        while not please_stop:
            (Till(seconds=device.interval) | please_stop).wait()
            try:
                now = Date.now()
                signed = rsa_crypto.sign(
                    Data(
                        timestamp=now,
                        session=cookie
                    ),
                    self.private_key
                )
                response = self.session.request(
                    "POST",
                    URL(self.config.service) / self.config.endpoints.status,
                    json=value2json(signed)
                )
                status = wrap(response.json())
                if status.ok:
                    return self.session
            except Exception as e:
                Log.warning(
                    "problem calling {{url}}",
                    url=URL(self.config.service)/ self.config.endpoints.status,
                    cause=e,
                )

    def request(self, method, url, *args, **kwargs):
        """
        ENSURE THE SESSION IS USED (SO THAT COOKIE IS ATTACHED)
        """
        return self.session.request(method, url, *args, **kwargs)
