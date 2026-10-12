"""Cloud web-tools compatibility: settings from environment; no disk writes."""
import os

def setting(name, default=None):
    return bool(os.getenv('BRAVE_API_KEY')) if name == 'web_enabled' else default

def secret(name, environment=''):
    return os.getenv(environment, '')

def record(kind, payload):
    return None
