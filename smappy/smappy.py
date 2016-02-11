__title__ = "smappy"
__version__ = "0.0.1"
__author__ = "EnergieID.be"
__license__ = "MIT"

import requests
import datetime as dt


URLS = {
    'token': 'https://app1pub.smappee.net/dev/v1/oauth2/token',
    'servicelocation': 'https://app1pub.smappee.net/dev/v1/servicelocation'
}


def authenticated(func):
    """
    Decorator to check if Smappee's authorization token has expired. If it has, use the refresh token to request a new
    authorization token
    """
    def wrapper(*args, **kwargs):
        self = args[0]
        if self.token_expiration_time >= dt.datetime.utcnow():
            self.re_authenticate()
        return func(*args, **kwargs)
    return wrapper


class Smappee(object):
    """
    Object containing Smappee's API-methods.
    See https://smappee.atlassian.net/wiki/display/DEVAPI/API+Methods
    """
    def __init__(self, client_id, client_secret):
        """
        To receive a client id and secret, you need to request via the Smappee support

        Parameters
        ----------
        client_id : str
        client_secret : str
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.refresh_token = None
        self.token_expiration_time = None

    def authenticate(self, username, password):
        """
        Uses a Smappee username and password to request an authorization token, refresh token and expiry date

        Parameters
        ----------
        username : str
        password : str

        Returns
        -------
        nothing
            access token is saved in self.access_token
            refresh token is saved in self.refresh_token
            expiration time is set in self.token_expiration_time as datetime.datetime
        """
        url = URLS['token']
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": username,
            "password": password
        }
        r = requests.post(url, data=data)
        j = r.json()
        self.access_token = j['access_token']
        self.refresh_token = j['refresh_token']
        self._set_token_expiration_time(expires_in=j['expires_in'])

    def _set_token_expiration_time(self, expires_in):
        """
        Saves the token expiration time by adding the 'expires in' parameter to the current datetime (in utc)

        Parameters
        ----------
        expires_in : int
            number of seconds from the time of the request until expiration

        Returns
        -------
        nothing
            saves expiration time in self.token_expiration_time as datetime.datetime
        """
        self.token_expiration_time = dt.datetime.utcnow() + dt.timedelta(0, expires_in)  # timedelta(days, seconds)

    def re_authenticate(self):
        """
        Uses the refresh token to request a new authorization token, refresh token and expiration date

        Returns
        -------
        nothing
            access token is saved in self.access_token
            refresh token is saved in self.refresh_token
            expiration time is set in self.token_expiration_time as datetime.datetime
        """
        url = URLS['token']
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        r = requests.post(url, data=data)
        j = r.json()
        self.access_token = j['access_token']
        self.refresh_token = j['refresh_token']
        self._set_token_expiration_time(expires_in=j['expires_in'])

    @authenticated
    def get_service_locations(self):
        """
        Request service locations

        Returns
        -------
        dict
        """
        url = URLS['servicelocation']
        headers = {"Authorization": "Bearer {}".format(self.access_token)}
        r = requests.get(url, headers=headers)
        return r.json()

    @authenticated
    def get_service_location_info(self, service_location_id):
        """
        Request service location info

        Parameters
        ----------
        service_location_id : int

        Returns
        -------
        dict
        """
        url = URLS['servicelocation'] + "/{}/info".format(service_location_id)
        headers = {"Authorization": "Bearer {}".format(self.access_token)}
        r = requests.get(url, headers=headers)
        return r.json()

    @authenticated
    def get_consumption(self, service_location_id, start, end, aggregation):
        """
        Request consumption for a given service location

        Parameters
        ----------
        service_location_id : int
        start : datetime-like object (supports epoch, datetime and Pandas Timestamp)
        end : datetime-like object (supports epoch, datetime and Pandas Timestamp)
        aggregation : int (1 to 5)
            1 = 5 min values (only available for the last 14 days)
            2 = hourly values
            3 = daily values
            4 = monthly values
            5 = quarterly values

        Returns
        -------
        dict
        """
        start = self._to_milliseconds(start)
        end = self._to_milliseconds(end)

        url = URLS['servicelocation'] + "/{}/consumption".format(service_location_id)
        headers = {"Authorization": "Bearer {}".format(self.access_token)}
        params = {
            "aggregation": aggregation,
            "from": start,
            "to": end
        }
        r = requests.get(url, headers=headers, params=params)
        return r.json()

    @authenticated
    def get_events(self, service_location_id, appliance_id, start, end, max_number=None):
        """
        Request events for a given appliance

        Parameters
        ----------
        service_location_id : int
        appliance_id : int
        start : datetime-like object (supports epoch, datetime and Pandas Timestamp)
        end : datetime-like object (supports epoch, datetime and Pandas Timestamp)
        max_number : int (optional)
            The maximum number of events that should be returned by this query
            Default returns all events in the selected period

        Returns
        -------
        dict
        """
        start = self._to_milliseconds(start)
        end = self._to_milliseconds(end)

        url = URLS['servicelocation'] + "/{}/events".format(service_location_id)
        headers = {"Authorization": "Bearer {}".format(self.access_token)}
        params = {
            "from": start,
            "to": end,
            "applianceId": appliance_id,
            "maxNumber": max_number
        }
        r = requests.get(url, headers=headers, params=params)
        return r.json()

    def actuator_on(self):
        """
        Not (yet) implemented
        See https://smappee.atlassian.net/wiki/display/DEVAPI/Actuator+ON
        """
        raise NotImplementedError()

    def actuator_off(self):
        """
        Not (yet) implemented
        See https://smappee.atlassian.net/wiki/display/DEVAPI/Actuator+OFF
        """
        raise NotImplementedError()

    def _to_milliseconds(self, time):
        """
        Converts a datetime-like object to epoch, in milliseconds

        Parameters
        ----------
        time : datetime-like object (works with datetime and Pandas Timestamp)

        Returns
        -------
        int (epoch)
        """
        if isinstance(time, dt.datetime):
            return int(time.timestamp() * 1e3)
        elif isinstance(time, int):
            return time
        else:
            raise NotImplementedError("Time format not supported. Use epochs, Datetime or Pandas Datetime")