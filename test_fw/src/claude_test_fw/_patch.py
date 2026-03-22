"""Patch SDK message parser to skip unknown message types.

Prevents crashes on unknown message types (e.g. rate_limit_event)
by returning a SystemMessage instead of raising MessageParseError.
"""

from claude_agent_sdk._errors import MessageParseError
from claude_agent_sdk import _internal as _sdk_internal

_original_parse_message = _sdk_internal.message_parser.parse_message


def _patched_parse_message(data):
    try:
        return _original_parse_message(data)
    except MessageParseError:
        from claude_agent_sdk import SystemMessage
        return SystemMessage(subtype=data.get("type", "unknown"), data=data)


_sdk_internal.message_parser.parse_message = _patched_parse_message
# Also patch the import in client.py which may have already cached the reference
import claude_agent_sdk._internal.client as _client_mod
_client_mod.parse_message = _patched_parse_message
