import sys
import time
from PyQt6.QtCore import QObject, pyqtSignal

class StdoutRedirector:
    def __init__(self, logger_instance):
        self.logger_instance = logger_instance
        try:
            self.original_stdout = sys.stdout
        except Exception:
            self.original_stdout = None
        self.buffer = ""
        
    def write(self, text):
        try:
            if self.original_stdout and self.original_stdout != self:
                try:
                    self.original_stdout.write(text)
                except Exception:
                    pass
            
            if text.strip():
                self.logger_instance.log(text.strip(), "TERMINAL")
        except Exception:
            pass
            
    def flush(self):
        try:
            if self.original_stdout and self.original_stdout != self:
                self.original_stdout.flush()
        except Exception:
            pass

class AppLogger(QObject):
    log_signal = pyqtSignal(str, str, str) # timestamp, level, message
    
    def __init__(self):
        super().__init__()
        self.log_messages = []
        self.stdout_redirector = None
        
    def setup_redirection(self):
        try:
            self.stdout_redirector = StdoutRedirector(self)
            sys.stdout = self.stdout_redirector
        except Exception as e:
            print(f"Error setting up stdout redirection: {str(e)}")
            self.stdout_redirector = None

    def log(self, message, level="INFO"):
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_entry = {"timestamp": timestamp, "level": level, "message": message}
            self.log_messages.append(log_entry)
            
            self.log_signal.emit(timestamp, level, message)
            
            if level != "TERMINAL" and self.stdout_redirector and self.stdout_redirector.original_stdout:
                try:
                    self.stdout_redirector.original_stdout.write(f"[{timestamp}] [{level}] {message}\n")
                except Exception:
                    pass
        except Exception:
            pass
            
    def filter_logs(self, level=None):
        if not level or level == "ALL":
            return self.log_messages
        return [msg for msg in self.log_messages if msg['level'] == level]

    def get_statistics(self):
        stats = {"INFO": 0, "WARNING": 0, "ERROR": 0, "SUCCESS": 0, "TERMINAL": 0}
        for msg in self.log_messages:
            level = msg["level"]
            if level in stats:
                stats[level] += 1
        return stats

# Global logger instance
logger = AppLogger()
