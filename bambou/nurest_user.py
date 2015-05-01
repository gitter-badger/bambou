# -*- coding: utf-8 -*-
# Copyright (c) 2011-2012 Alcatel, Alcatel-Lucent, Inc. All Rights Reserved.
#
# This source code contains confidential information which is proprietary to Alcatel.
# No part of its contents may be used, copied, disclosed or conveyed to any party
# in any manner whatsoever without prior written permission from Alcatel.
#
# Alcatel-Lucent is a trademark of Alcatel-Lucent, Inc.


import json

from .nurest_connection import HTTP_METHOD_PUT, HTTP_METHOD_GET
from .nurest_request import NURESTRequest
from .nurest_object import NURESTObject
from .nurest_session import _NURESTSessionCurrentContext

from .utils import Sha1


class NURESTBasicUser(NURESTObject):
    """ NURESTBasicUser defines a user that can log in.

        Only one NURESTBasicUser can be connected at a time.
    """

    __default_user = None

    def __init__(self):
        """ Initializes user """

        super(NURESTBasicUser, self).__init__()

        self._api_url = None
        self._new_password = None
        self._enterprise = None

        self._user_name = None
        self._password = None
        self._api_key = None

        self.expose_attribute(local_name='user_name', remote_name='userName', attribute_type=str)
        self.expose_attribute(local_name='password', attribute_type=str)
        self.expose_attribute(local_name='api_key', remote_name='APIKey', attribute_type=str)

    # Properties

    @property
    def user_name(self):
        """ Get user_name """

        return self._user_name

    @user_name.setter
    def user_name(self, user_name):
        """ Set user_name """

        self._user_name = user_name

    @property
    def password(self):
        """ Get password """

        return self._password

    @password.setter
    def password(self, password):
        """ Set password """

        self._password = password

    @property
    def api_key(self):
        """ Get API Key """

        return self._api_key

    @api_key.setter
    def api_key(self, api_key):
        """ Set API Key """

        self._api_key = api_key

    # @property
    # def api_url(self):
    #     """ Get API URL """
    #
    #     return self._api_url
    #
    # @api_url.setter
    # def api_url(self, api_url):
    #     """ Set API Key """
    #
    #     self._api_url = api_url

    @property
    def enterprise(self):
        """ Get API URL """

        return self._enterprise

    @enterprise.setter
    def enterprise(self, enterprise):
        """ Set API Key """

        self._enterprise = enterprise


    # Class Methods

    @classmethod
    def get_default_user(cls):
        """ Get default user """

        if not cls.__default_user:
            NURESTBasicUser.__default_user = cls()

        return NURESTBasicUser.__default_user

    # Methods

    def prepare_change_password(self, new_password):
        """ Prepares password modification """

        self._new_password = new_password

    def save(self, async=False, callback=None):
        """ Updates the user and perform the callback method """

        if self._new_password:
            self.password = Sha1.encrypt(self._new_password)

        controller = _NURESTSessionCurrentContext.session.login_controller
        controller.password = self._new_password
        controller.api_key = None

        data = json.dumps(self.to_dict())
        request = NURESTRequest(method=HTTP_METHOD_PUT, url=self.get_resource_url(), data=data)

        if async:
            return self.send_request(request=request, async=async, local_callback=self._did_save, remote_callback=callback)
        else:
            connection = self.send_request(request=request)
            return self._did_save(connection)

    def _did_save(self, connection):
        """ Launched when save has been successfully executed """

        self._new_password = None

        controller = _NURESTSessionCurrentContext.session.login_controller
        controller.password = None
        controller.api_key = self.api_key

        if connection.async:
            callback = connection.callbacks['remote']

            if connection.user_info:
                callback(connection.user_info, connection)
            else:
                callback(self, connection)
        else:
            return (self, connection)

    def fetch(self, async=False, callback=None):
        """ Fetch all information about the current object

            Args:
                async (bool): Boolean to make an asynchronous call. Default is False
                callback (function): Callback method that will be triggered in case of asynchronous call

            Returns:
                tuple: (current_fetcher, callee_parent, fetched_bjects, connection)

            Example:
                >>> entity = NUEntity(id="xxx-xxx-xxx-xxx")
                >>> entity.fetch() # will get the entity with id "xxx-xxx-xxx-xxx"
                >>> print entity.name
                "My Entity"
        """
        request = NURESTRequest(method=HTTP_METHOD_GET, url=self.get_resource_url())

        if async:
            return self.send_request(request=request, async=async, local_callback=self._did_fetch, remote_callback=callback)
        else:
            connection = self.send_request(request=request)
            return self._did_retrieve(connection)
