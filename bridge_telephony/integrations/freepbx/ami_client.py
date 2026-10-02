"""
Asterisk Manager Interface (AMI) Client
Provides TCP socket-based communication with FreePBX / Asterisk
"""

import socket
import time
import uuid
import frappe


class AMIException(Exception):
    """Exception raised for Asterisk Manager Interface errors"""
    pass


class AMIClient:
    """Lightweight, reliable Asterisk Manager Interface client"""

    def __init__(self, host=None, port=None, username=None, secret=None, timeout=10.0):
        self.host = host
        self.port = int(port) if port else 5038
        self.username = username
        self.secret = secret
        self.timeout = timeout
        self.socket = None
        self.banner = None
        self.is_connected = False
        self.is_authenticated = False

    def __enter__(self):
        self.connect()
        if self.username and self.secret:
            self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        """Establish TCP connection to Asterisk AMI and read banner"""
        if self.is_connected and self.socket:
            return

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))

            # Read initial Asterisk banner line
            self.banner = self._read_line().strip()
            self.is_connected = True
        except Exception as e:
            self.close()
            raise AMIException(f"Failed to connect to Asterisk AMI at {self.host}:{self.port} - {str(e)}")

    def login(self, username=None, secret=None):
        """Authenticate with Asterisk AMI"""
        user = username or self.username
        sec = secret or self.secret

        if not user or not sec:
            raise AMIException("AMI username and secret are required for login")

        action = {
            "Action": "Login",
            "Username": user,
            "Secret": sec,
        }

        response = self.send_action(action)
        if response.get("Response", "").lower() != "success":
            msg = response.get("Message", "Authentication failed")
            raise AMIException(f"AMI login failed: {msg}")

        self.is_authenticated = True
        return response

    def logoff(self):
        """Send Logoff action and close connection"""
        if self.is_connected and self.is_authenticated:
            try:
                self.send_action({"Action": "Logoff"})
            except Exception:
                pass
        self.close()

    def close(self):
        """Close socket connection"""
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        self.is_connected = False
        self.is_authenticated = False

    def ping(self):
        """Send Ping action to verify active session"""
        response = self.send_action({"Action": "Ping"})
        return response.get("Response", "").lower() == "success"

    def core_status(self):
        """Fetch Asterisk Core Status"""
        return self.send_action({"Action": "CoreStatus"})

    def originate(
        self,
        channel,
        exten,
        context="from-internal",
        priority=1,
        caller_id=None,
        timeout_ms=30000,
        async_call=True,
        variables=None,
        account=None
    ):
        """
        Originate an outbound call.
        Rings the agent's channel (e.g. PJSIP/1001), and when answered,
        bridges into exten in context at priority.

        Args:
            channel (str): Agent channel, e.g., 'PJSIP/1001' or 'Local/1001@from-internal'
            exten (str): Outbound destination phone number / extension
            context (str): Dialplan context to route call through (default 'from-internal')
            priority (int): Dialplan priority (default 1)
            caller_id (str): Caller ID to display to agent/callee
            timeout_ms (int): Dial timeout in milliseconds
            async_call (bool): Whether to return immediately once call is queued
            variables (dict): Key-value pairs to set on the channel
            account (str): Account code for CDR

        Returns:
            dict: AMI response dictionary
        """
        action = {
            "Action": "Originate",
            "Channel": channel,
            "Exten": str(exten),
            "Context": context,
            "Priority": str(priority),
            "Timeout": str(timeout_ms),
            "Async": "true" if async_call else "false",
        }

        if caller_id:
            action["CallerID"] = str(caller_id)

        if account:
            action["Account"] = str(account)

        # Set variables if provided
        if variables and isinstance(variables, dict):
            action["Variable"] = [f"{k}={v}" for k, v in variables.items()]

        response = self.send_action(action)
        return response

    def send_action(self, action_dict):
        """
        Send an action and read the response block.
        Automatically attaches an ActionID for tracking.
        """
        if not self.is_connected or not self.socket:
            self.connect()

        action_id = str(uuid.uuid4())
        action_dict["ActionID"] = action_id

        # Construct AMI message packet
        payload_lines = []
        for key, value in action_dict.items():
            if isinstance(value, (list, tuple)):
                for item in value:
                    payload_lines.append(f"{key}: {item}")
            else:
                payload_lines.append(f"{key}: {value}")
        payload_lines.append("\r\n")  # AMI packet delimiter is empty line

        payload = "\r\n".join(payload_lines)
        self.socket.sendall(payload.encode("utf-8"))

        # Read response blocks until we find the response matching our ActionID
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            block = self._read_response_block()
            if not block:
                continue

            parsed = self._parse_block(block)
            # Check if this block corresponds to our ActionID
            if parsed.get("ActionID") == action_id:
                return parsed
            elif "Response" in parsed and "ActionID" not in parsed:
                # Sometimes responses omit ActionID if error happens early
                return parsed

        raise AMIException(f"Timed out waiting for response to action {action_dict.get('Action')}")

    def _read_line(self):
        """Read a single line terminated by \\n"""
        chars = []
        while True:
            char = self.socket.recv(1)
            if not char:
                break
            chars.append(char)
            if char == b"\n":
                break
        return b"".join(chars).decode("utf-8", errors="ignore")

    def _read_response_block(self):
        """Read a full response packet ending with double CRLF (\\r\\n\\r\\n)"""
        buffer = b""
        while b"\r\n\r\n" not in buffer and b"\n\n" not in buffer:
            chunk = self.socket.recv(1024)
            if not chunk:
                break
            buffer += chunk

        return buffer.decode("utf-8", errors="ignore")

    def _parse_block(self, text):
        """Parse key-value headers in an AMI response block"""
        data = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                data[key.strip()] = val.strip()
        return data
