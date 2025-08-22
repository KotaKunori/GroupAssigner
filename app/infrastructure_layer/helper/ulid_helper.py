from ulid import ULID
import re

class ULIDHelper:
    @staticmethod
    def generate():
        return str(ULID())
    
    @staticmethod
    def validate(ulid: str) -> bool:
        pattern = r'^[0-9a-hjkmnp-zA-HJKMNP-Z]{26}$'
        if not bool(re.match(pattern, ulid)):
            return False
        return True