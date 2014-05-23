# -*- coding: utf-8 -*-

import json

from requests.exceptions import Timeout
from requests_futures.sessions import FuturesSession

from restnuage.http_exceptions import HTTPTimeoutException
from restnuage.nurest_login_controller import NURESTLoginController
from restnuage.nurest_response import NURESTResponse


HTTP_CODE_ZERO = 0
HTTP_CODE_CONNECTION_TIMEOUT = 43
HTTP_CODE_SUCCESS = 200
HTTP_CODE_CREATED = 201
HTTP_CODE_EMPTY = 204
HTTP_CODE_MULTIPLE_CHOICES = 300
HTTP_CODE_BAD_REQUEST = 400
HTTP_CODE_UNAUTHORIZED = 401
HTTP_CODE_PERMISSION_DENIED = 403
HTTP_CODE_NOT_FOUND = 404
HTTP_CODE_METHOD_NOT_ALLOWED = 405
HTTP_CODE_CONFLICT = 409
HTTP_CODE_PRECONDITION_FAILED = 412
HTTP_CODE_INTERNAL_SERVER_ERROR = 500
HTTP_CODE_SERVICE_UNAVAILABLE = 503


class NURESTConnection(object):
    """ Enhances requests """

    def __init__(self, request, callback=None, callbacks=dict()):
        """ Intializes a new connection for a request
            :param request: the NURESTRequest to send
            :param callback: the method that will be fired after sending
            :param callbacks: a dictionary of user callbacks. Should contains local and remote callbacks
        """

        self._uses_authentication = True
        self._has_timeouted = False
        self._is_cancelled = False
        self._ignore_request_idle = False
        self._xhr_timeout = 300000
        self._response = None
        self._error_message = None

        self._request = request
        self._response = None
        self._callback = callback
        self._callbacks = callbacks
        self._user_info = None

    # Properties

    def _get_callbacks(self):
        """ Get callbacks """
        return self._callbacks

    callbacks = property(_get_callbacks, None)

    def _get_response(self):
        """ Get response """
        return self._response

    response = property(_get_response, None)

    def _get_user_info(self):
        """ Get user info """
        return self._user_info

    def _set_user_info(self, info):
        """ Set user info """
        self._user_info = info

    user_info = property(_get_user_info, _set_user_info)

    def _get_timeout(self):
        """ Get timeout """
        return self._xhr_timeout

    def _set_timeout(self, timeout):
        """ Set timeout """
        self._xhr_timeout = timeout

    timeout = property(_get_timeout, _set_timeout)

    def _get_ignore_request_idle(self):
        """ Get ignore request idle """
        return self._ignore_request_idle

    def _set_ignore_request_idle(self, timeout):
        """ Set ignore request idle """
        self._ignore_request_idle = timeout

    ignore_request_idle = property(_get_ignore_request_idle, _set_ignore_request_idle)

    # Methods

    def has_callbacks(self):
        """ Returns YES if there is a local or remote callbacks """

        return len(self._callbacks) > 0

    def has_response_success(self, should_post=False):
        """ Return True if the response has succeed, False otherwise """

        status_code = self._response.status_code
        # TODO : Get errors in response data after bug fix : http://mvjira.mv.usa.alcatel.com/browse/VSD-2735

        data = self._response.data
        if 'errors' in data:
            error_name = data['errors'][0]['descriptions'][0]['title']
            error_description = data['errors'][0]['descriptions'][0]['description']

        if status_code in [HTTP_CODE_SUCCESS, HTTP_CODE_CREATED, HTTP_CODE_EMPTY]:
            return True

        if status_code == HTTP_CODE_MULTIPLE_CHOICES:
            self._print_information(error_name, error_description)
            return False

        if status_code in [HTTP_CODE_PERMISSION_DENIED, HTTP_CODE_UNAUTHORIZED]:

            if not should_post:
                return True

            error_name = "Permission denied"
            error_description = "You are not allowed to access this resource."

            self._print_information(error_name, error_description)
            return False

        if status_code in [HTTP_CODE_CONFLICT, HTTP_CODE_NOT_FOUND, HTTP_CODE_BAD_REQUEST, HTTP_CODE_METHOD_NOT_ALLOWED, HTTP_CODE_PRECONDITION_FAILED, HTTP_CODE_SERVICE_UNAVAILABLE]:
            if not should_post:
                return True

            self._print_information(error_name, error_description)
            return False

        if status_code == HTTP_CODE_INTERNAL_SERVER_ERROR:

            error_name = "[CRITICAL] Internal Server Error"
            error_description = "Please check the log and report this error to the server team"

            self._print_information(error_name, error_description)
            return False

        if status_code == HTTP_CODE_ZERO:
            print "NURESTConnection: Connection error with code 0. Sending NUNURESTConnectionFailureNotification notification and exiting."
            self._print_information(error_name, error_description)
            return False

        print "NURESTConnection: Report this error, because this should not happen: %s" % self._response
        return False

    def _print_information(self, error_name, error_description):
        """ Prints information instead of sending a confirmation """

        print "NURESTConnection: Print error Name=%s with Description=%s" % (error_name, error_description)

    # HTTP Calls

    def _did_receive_response(self, session, response):
        """ Called when a response is received """

        print "NURESTConnection receive response [%s] %s" % (response.status_code, response.reason)

        try:
            data = response.json()
        except:
            print "** Reponse could not be decoded\n%s\n** End response\n" % response.text
            data = None

        self._response = NURESTResponse(status_code=response.status_code, headers=response.headers, data=data, reason=response.reason)

        if self._callback:
            self._callback(self)

    def _did_timeout(self):
        """ Called when a resquest has timeout """

        self._has_timeouted = True
        raise HTTPTimeoutException()

    def start(self):  # TODO : Use Timeout here and _ignore_request_idle
        """ Make an HTTP request with a specific method """

        # Add specific headers
        controller = NURESTLoginController()

        if self._uses_authentication:
            self._request.set_header('X-Nuage-Organization', controller.company)
            self._request.set_header('Authorization', controller.get_authentication_header())

        if controller.is_impersonating:
            self._request.set_header('X-Nuage-Proxy', controller.impersonation)

        headers = self._request.get_headers()

        url = "%s%s" % (controller.url, self._request.url)

        # Prepare callback
        self._has_timeouted = False
        print "** Launch %s %s" % (self._request.method, url)

        print "** DATA SENT\n%s" % self._request.data

        # HTTP Call
        session = FuturesSession()
        promise = session.request(method=self._request.method,
                                  url=url,
                                  #params=self._request.params,
                                  data=json.dumps(self._request.data),
                                  headers=headers,
                                  verify=False,
                                  background_callback=self._did_receive_response,
                                  timeout=self.timeout)

        print "[%s] Waiting for response..." % self._request.method


        promise.result()
        # try:
        #     promise.result()
        # except KeyError as exc:  # TODO : Find a better way to retrieve response when call failed
        #     response = NURESTResponse(status_code=0, reason=exc.message, headers=[])
        #     response.text = exc
        #     self._did_receive_response(None, response)
        # except Timeout:
        #     self._did_timeout()

        # TODO : Manage following exceptions
        # [401] Unauthorized