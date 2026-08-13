"""Constants for FritzCallMonitor."""
DOMAIN = "callmonitor_test"
PLATFORMS = ["sensor"]
CONF_HOST = "host"
CONF_PORT = "port"
CONF_ANSWERING_MACHINE_EXTENSION = "answering_machine_extension"
CONF_MAX_STORED_CALLS = "max_stored_calls"
DEFAULT_HOST = "192.168.178.1"
DEFAULT_PORT = 1012
DEFAULT_ANSWERING_MACHINE_EXTENSION = "40"
DEFAULT_MAX_STORED_CALLS = 50
STORAGE_VERSION = 1
STORAGE_KEY = "callmonitor_test.calls"
STATIC_URL = "/local_callmonitor_test"

SERVICE_CLEAR_CALLS = "clear_calls"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_COUNTRY_CODE = "country_code"
DEFAULT_COUNTRY_CODE = "49"
SERVICE_SYNC_PHONEBOOK = "sync_phonebook"

SERVICE_ADD_CONTACT = "add_contact"
PHONEBOOK_SYNC_HOURS = 6

SERVICE_DELETE_CALL = "delete_call"
SERVICE_SYNC_ANSWERING_MACHINE = "sync_answering_machine"
ANSWERING_MACHINE_SYNC_MINUTES = 5

SERVICE_DELETE_VOICEMAIL = "delete_voicemail"

EVENT_FRITZCALLMONITOR = f"{DOMAIN}_event"
EVENT_TYPE_NEW_VOICEMAIL = "new_voicemail"

VOICEMAIL_KNOWN_STORAGE_VERSION = 1
VOICEMAIL_KNOWN_STORAGE_KEY = "callmonitor_test.voicemail_known"
