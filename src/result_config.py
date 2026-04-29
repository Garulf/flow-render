from typing import TypedDict

from datauri import DataURI
import requests


class ResultConfig(TypedDict):
    title: str
    subtitle: str
    icon: str


def is_url(icon: str) -> bool:
    return icon.startswith('http://') or icon.startswith('https://')


def get_icon(icon: str) -> str:
    # download icon and convert to data uri
    response = requests.get(icon)
    mime_type = response.headers.get('content-type')
    data = response.content
    data_uri = DataURI.make(mime_type, None, True, data)
    return data_uri