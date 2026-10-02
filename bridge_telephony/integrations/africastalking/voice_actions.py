"""
Voice Actions XML Builder for Africa's Talking
Builds XML responses for call flow control
"""

from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


class VoiceActionsBuilder:
    """
    Builder class for constructing Africa's Talking Voice Actions XML

    Usage:
        builder = VoiceActionsBuilder()
        builder.say("Hello, welcome to our service")
        builder.getDigits(num_digits=1, timeout=30)
        builder.dial(["+234XXXXXXXXXX"], record=True)
        xml = builder.build()
    """

    def __init__(self):
        self.root = Element("Response")
        self.actions = []

    def say(self, text, voice="woman", play_beep=False):
        """
        Text-to-speech action

        Args:
            text: Text to be spoken
            voice: Voice type - 'man' or 'woman' (default: 'woman')
            play_beep: Play beep before speaking (default: False)

        Returns:
            self for chaining
        """
        say_elem = SubElement(self.root, "Say")
        say_elem.text = text

        if voice:
            say_elem.set("voice", voice)

        if play_beep:
            say_elem.set("playBeep", "true")

        self.actions.append("say")
        return self

    def play(self, url):
        """
        Play audio file from URL

        Args:
            url: Public URL of audio file (mp3, wav)

        Returns:
            self for chaining
        """
        play_elem = SubElement(self.root, "Play")
        play_elem.text = url

        self.actions.append("play")
        return self

    def get_digits(self, num_digits=1, timeout=30, finish_on_key="#", callback_url=None):
        """
        Get DTMF input from caller

        Args:
            num_digits: Number of digits to collect (default: 1)
            timeout: Timeout in seconds (default: 30)
            finish_on_key: Key to finish input (default: '#')
            callback_url: URL to POST the digits to

        Returns:
            self for chaining
        """
        get_digits_elem = SubElement(self.root, "GetDigits")
        get_digits_elem.set("numDigits", str(num_digits))
        get_digits_elem.set("timeout", str(timeout))
        get_digits_elem.set("finishOnKey", finish_on_key)

        if callback_url:
            get_digits_elem.set("callbackUrl", callback_url)

        self.actions.append("getDigits")
        return self

    def dial(self, phone_numbers, record=False, sequential=False, caller_id=None,
             ring_tone=None, max_duration=None):
        """
        Dial phone numbers

        Args:
            phone_numbers: List of phone numbers to dial
            record: Record the call (default: False)
            sequential: Try numbers sequentially vs simultaneously (default: False)
            caller_id: Caller ID to display
            ring_tone: URL of custom ring tone
            max_duration: Maximum call duration in seconds

        Returns:
            self for chaining
        """
        dial_elem = SubElement(self.root, "Dial")

        if record:
            dial_elem.set("record", "true")

        if sequential:
            dial_elem.set("sequential", "true")

        if caller_id:
            dial_elem.set("callerId", caller_id)

        if ring_tone:
            dial_elem.set("ringbackTone", ring_tone)

        if max_duration:
            dial_elem.set("maxDuration", str(max_duration))

        # Add phone numbers
        for number in phone_numbers:
            number_elem = SubElement(dial_elem, "Number")
            number_elem.text = str(number)

        self.actions.append("dial")
        return self

    def conference(self, room_name, muted=False, start_on_enter=True, end_on_exit=False):
        """
        Add caller to conference room

        Args:
            room_name: Name of conference room
            muted: Start muted (default: False)
            start_on_enter: Start conference when caller enters (default: True)
            end_on_exit: End conference when caller exits (default: False)

        Returns:
            self for chaining
        """
        conference_elem = SubElement(self.root, "Conference")
        conference_elem.text = room_name

        if muted:
            conference_elem.set("muted", "true")

        if start_on_enter:
            conference_elem.set("startConferenceOnEnter", "true")

        if end_on_exit:
            conference_elem.set("endConferenceOnExit", "true")

        self.actions.append("conference")
        return self

    def record(self, finish_on_key="#", max_length=60, timeout=5,
               trim_silence=False, callback_url=None):
        """
        Record audio from caller

        Args:
            finish_on_key: Key to stop recording (default: '#')
            max_length: Maximum recording length in seconds (default: 60)
            timeout: Silence timeout in seconds (default: 5)
            trim_silence: Trim silence from recording (default: False)
            callback_url: URL to POST recording to

        Returns:
            self for chaining
        """
        record_elem = SubElement(self.root, "Record")
        record_elem.set("finishOnKey", finish_on_key)
        record_elem.set("maxLength", str(max_length))
        record_elem.set("timeout", str(timeout))

        if trim_silence:
            record_elem.set("trimSilence", "true")

        if callback_url:
            record_elem.set("callbackUrl", callback_url)

        self.actions.append("record")
        return self

    def enqueue(self, hold_music_url=None, queue_name="default"):
        """
        Add caller to queue

        Args:
            hold_music_url: URL of hold music to play
            queue_name: Name of the queue (default: 'default')

        Returns:
            self for chaining
        """
        enqueue_elem = SubElement(self.root, "Enqueue")
        enqueue_elem.set("name", queue_name)

        if hold_music_url:
            enqueue_elem.set("holdMusic", hold_music_url)

        self.actions.append("enqueue")
        return self

    def dequeue(self, phone_number, queue_name="default"):
        """
        Dequeue a call and connect to agent

        Args:
            phone_number: Agent's phone number
            queue_name: Name of the queue (default: 'default')

        Returns:
            self for chaining
        """
        dequeue_elem = SubElement(self.root, "Dequeue")
        dequeue_elem.set("name", queue_name)
        dequeue_elem.text = phone_number

        self.actions.append("dequeue")
        return self

    def reject(self, reason="busy"):
        """
        Reject the call

        Args:
            reason: Rejection reason - 'rejected' or 'busy' (default: 'busy')

        Returns:
            self for chaining
        """
        reject_elem = SubElement(self.root, "Reject")

        if reason:
            reject_elem.set("reason", reason)

        self.actions.append("reject")
        return self

    def redirect(self, url):
        """
        Redirect to another Voice Actions URL

        Args:
            url: URL to redirect to

        Returns:
            self for chaining
        """
        redirect_elem = SubElement(self.root, "Redirect")
        redirect_elem.text = url

        self.actions.append("redirect")
        return self

    def sip_dial(self, sip_uri, username=None, password=None, record=False):
        """
        Dial a SIP endpoint

        Args:
            sip_uri: SIP URI to dial (e.g., sip:user@domain.com)
            username: SIP username for authentication
            password: SIP password for authentication
            record: Record the call (default: False)

        Returns:
            self for chaining
        """
        dial_elem = SubElement(self.root, "Dial")

        if record:
            dial_elem.set("record", "true")

        sip_elem = SubElement(dial_elem, "Sip")
        sip_elem.text = sip_uri

        if username:
            sip_elem.set("username", username)

        if password:
            sip_elem.set("password", password)

        self.actions.append("sip_dial")
        return self

    def build(self, pretty=True):
        """
        Build and return the Voice Actions XML

        Args:
            pretty: Return pretty-formatted XML (default: True)

        Returns:
            XML string
        """
        xml_str = tostring(self.root, encoding='unicode')

        if pretty:
            dom = minidom.parseString(xml_str)
            return dom.toprettyxml(indent="  ")

        return xml_str

    def clear(self):
        """Clear all actions and reset builder"""
        self.root = Element("Response")
        self.actions = []
        return self


# Convenience functions for common scenarios

def build_simple_ivr(welcome_message, menu_options, callback_url):
    """
    Build a simple IVR menu

    Args:
        welcome_message: Welcome message to play
        menu_options: Dict of digit: action pairs
        callback_url: URL to handle digit input

    Returns:
        XML string
    """
    builder = VoiceActionsBuilder()
    builder.say(welcome_message)
    builder.get_digits(
        num_digits=1,
        timeout=30,
        callback_url=callback_url
    )
    return builder.build()


def build_queue_response(queue_music_url=None, queue_name="default"):
    """
    Build a response to queue a caller

    Args:
        queue_music_url: URL of hold music
        queue_name: Queue name

    Returns:
        XML string
    """
    builder = VoiceActionsBuilder()
    builder.say("Thank you for calling. You are being placed in the queue.")
    builder.enqueue(hold_music_url=queue_music_url, queue_name=queue_name)
    return builder.build()


def build_agent_connect(agent_numbers, record=True):
    """
    Build a response to connect to agent(s)

    Args:
        agent_numbers: List of agent phone numbers
        record: Record the call

    Returns:
        XML string
    """
    builder = VoiceActionsBuilder()
    builder.say("Connecting you to an agent. Please wait.")
    builder.dial(agent_numbers, record=record)
    return builder.build()


def build_voicemail(max_length=60, callback_url=None):
    """
    Build a voicemail recording response

    Args:
        max_length: Maximum recording length
        callback_url: URL to receive recording

    Returns:
        XML string
    """
    builder = VoiceActionsBuilder()
    builder.say(
        "Please leave a message after the beep. Press hash when done.", play_beep=True)
    builder.record(
        max_length=max_length,
        finish_on_key="#",
        callback_url=callback_url
    )
    builder.say("Thank you for your message. Goodbye.")
    return builder.build()


def build_busy_response():
    """
    Build a response for when all agents are busy

    Returns:
        XML string
    """
    builder = VoiceActionsBuilder()
    builder.say(
        "Sorry, all our agents are currently busy. Please try again later.")
    builder.reject(reason="busy")
    return builder.build()


def build_error_response():
    """
    Build an error response

    Returns:
        XML string
    """
    builder = VoiceActionsBuilder()
    builder.say(
        "We're experiencing technical difficulties. Please try again later.")
    builder.reject(reason="rejected")
    return builder.build()
