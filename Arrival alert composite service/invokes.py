import requests
from requests.exceptions import RequestException

# Only allow standard HTTP methods supported by this wrapper.
SUPPORTED_HTTP_METHODS = {
    "GET", "OPTIONS", "HEAD", "POST", "PUT", "PATCH", "DELETE"
}


def invoke_http(url, method='GET', json=None, **kwargs):
    """
    A simple HTTP client wrapper around requests.

    Design contract:
    - Always returns (data, status_code)
    - Expects JSON responses from services
    - Non-JSON responses are treated as errors
    - Network or invocation failures return a synthetic 500 error

    Parameters:
    - url: target service URL
    - method: HTTP method (GET, POST, etc.)
    - json: request payload to be sent as JSON (if any)
    - kwargs: additional arguments passed to requests (e.g. headers)
    """

    # Normalize and validate HTTP method
    method = method.upper()
    if method not in SUPPORTED_HTTP_METHODS:
        return {
            "code": 400,
            "message": f"Unsupported HTTP method: {method}"
        }, 400

    try:
        # Make the HTTP request
        # The 'json' parameter is explicitly passed to requests
        response = requests.request(
            method=method,
            url=url,
            json=json,
            **kwargs
        )

        try:
            # Attempt to parse response body as JSON
            data = response.json()
            return data, response.status_code

        except ValueError as e:
            # Response body is not valid JSON
            return {
                "code": 500,
                "message": (
                    f"Invalid JSON output from service: {url}. {str(e)}"
                )
            }, 500

    except RequestException as e:
        # Handles all request-level failures
        return {
            "code": 500,
            "message": f"invocation of service fails: {url}. {str(e)}"
        }, 500
