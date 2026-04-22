import logging
import os
from datetime import datetime

# Setup a dedicated logger for alerts
alert_logger = logging.getLogger("system_alerts")
alert_logger.setLevel(logging.INFO)

# Create a file handler for persistent alert history
log_file = os.path.join(os.path.dirname(__file__), "..", "alerts.log")
fh = logging.FileHandler(log_file)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
alert_logger.addHandler(fh)

class NotificationService:
    @staticmethod
    def send_critical_alert(severity: str, category: str, observation: str):
        """
        Broadcasting logic for critical system anomalies.
        Currently logs to console and a dedicated alerts.log file.
        Can be extended to SMTP, Slack, or SMS.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert_msg = f"\n[!!! CRITICAL SYSTEM ALERT !!!]\nTime: {timestamp}\nCategory: {category}\nObservation: {observation}\n{'='*30}\n"
        
        # High-visibility console print
        print(alert_msg)
        
        # Log to file
        alert_logger.error(f"[{category}] {observation}")
        
        return True

notification_service = NotificationService()
