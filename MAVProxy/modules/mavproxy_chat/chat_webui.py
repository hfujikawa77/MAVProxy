"""
Web UI for MAVProxy chat module.

This script provides a web-based chat interface for the MAVProxy chat module,
enabling real-time communication and interaction via a web browser.

Setup:
    Install the required Python dependencies:
        pip install flask flask-socketio eventlet

Usage:
    1. Load the MAVProxy chat module:
        module load chat

    2. Start the web UI:
        chat webui

    3. Access the web interface in your browser:
        http://localhost:5000

"""



from flask import Flask, render_template
from flask_socketio import SocketIO
from threading import Thread
from MAVProxy.modules.mavproxy_chat.chat_openai import chat_openai

import threading

class chat_webui():
    def __init__(self, mpstate):
        self.mpstate = mpstate
        self.app = Flask(__name__, template_folder="templates")
        self.socketio = SocketIO(self.app)
        self.web_thread = None

        # Initialize OpenAI integration
        self.chat_openai = chat_openai(mpstate, status_cb=self.send_status, reply_cb=self.process_reply)

        # Buffer and timer for integrating responses
        self.response_buffer = ""
        self.response_timer = None
        self.RESPONSE_TIMEOUT = 1.0  # Timeout duration (seconds)

        # Define Flask route
        @self.app.route('/')
        def index():
            return render_template('chat.html')

        # WebSocket event
        @self.socketio.on('send_message')
        def handle_message(data):
            print(f"Web UI received: {data}")
            self.response_buffer = ""  # Clear the response buffer
            self.chat_openai.send_to_assistant(data)  # Send message to OpenAI
            self.reset_timer()  # Start the timer

    def start_server(self):
        """Start the web server"""
        if self.web_thread and self.web_thread.is_alive():
            print("Web UI server already running")
            return
        self.web_thread = Thread(target=self.run_server, daemon=True)
        self.web_thread.start()

    def run_server(self):
        """Run the web server"""
        self.socketio.run(self.app, host='0.0.0.0', port=5000)

    def send_status(self, status):
        """Send status updates to the Web UI"""
        self.socketio.emit('status_update', status)

    def process_reply(self, text):
        """Integrate responses from OpenAI and send them to the Web UI"""
        print(f"Received reply part: {text}")  # Debug log

        if text.strip():
            self.response_buffer += text  # Integrate the response
            print(f"Buffer updated: {self.response_buffer}")  # Debug log
            self.reset_timer()  # Reset the timer as new response parts arrive

    def reset_timer(self):
        """Reset the response integration timer"""
        if self.response_timer:
            self.response_timer.cancel()  # Cancel the existing timer
        self.response_timer = threading.Timer(self.RESPONSE_TIMEOUT, self.finalize_response)
        self.response_timer.start()

    def finalize_response(self):
        """Finalize and send the response"""
        if self.response_buffer.strip():
            print(f"Final response: {self.response_buffer}")  # Debug log
            self.socketio.emit('receive_message', self.response_buffer.strip())  # Send the integrated response
        self.response_buffer = ""  # Clear the buffer
