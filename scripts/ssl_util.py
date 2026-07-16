"""ssl_util.py — TPEx SSL compatibility utility.

Workaround for OpenShell 3.5 / Python 3.13 VERIFY_X509_STRICT flag
that rejects TPEx/DigiCert chain despite valid CA verification.

IMPORTANT: Only clears VERIFY_X509_STRICT. CA verification is PRESERVED.
Do not use verify=False.
"""
import ssl
import requests


class TLSAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        if hasattr(ssl, "VERIFY_X509_STRICT"):
            ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
        self._ssl_context = ctx
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self._ssl_context
        return super().init_poolmanager(*args, **kwargs)


def make_session():
    """Create a requests Session with TPEx-compatible SSL verification."""
    s = requests.Session()
    s.mount("https://", TLSAdapter())
    return s
