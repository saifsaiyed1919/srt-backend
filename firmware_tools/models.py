# firmware_tools/models.py
from mongoengine import Document, StringField, FloatField, DateTimeField
import datetime

class FirmwareLog(Document):
    # MongoDB automatically '_id' assign karta hai, humein likhne ki zaroorat nahi
    file_name = StringField(required=True, max_length=200)
    file_size_mb = FloatField(required=True)
    tool_used = StringField(default="ME Analyzer")
    status = StringField(default="Success")
    created_at = DateTimeField(default=datetime.datetime.utcnow)

    # Collection ka naam define kar rahe hain
    meta = {'collection': 'firmware_logs'}