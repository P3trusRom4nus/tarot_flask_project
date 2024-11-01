from datetime import datetime
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any
import email_validator

@dataclass
class ValidationResponse:
    is_valid: bool
    errors: Dict[str, str]

class OrderValidator:
    VALID_ZODIAC_SIGNS = [
        'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
        'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
    ]
    VALID_SERVICE_PRICES = [50, 75, 150, 250]
    
    @staticmethod
    def validate_name(name: str) -> tuple[bool, Optional[str]]:
        if not name or not isinstance(name, str) or not name.strip():
            return False, "Name is required and cannot be empty"
        if len(name.strip()) < 2:
            return False, "Name must be at least 2 characters long"
        if not re.match(r'^[A-Za-zÀ-ÿ\s]+$', name.strip()):
            return False, "Name can only contain letters and spaces"
        return True, None

    @staticmethod
    def validate_email(email: str) -> tuple[bool, Optional[str]]:
        try:
            email_validator.validate_email(email)
            return True, None
        except email_validator.EmailNotValidError as e:
            return False, str(e)

    @staticmethod
    def validate_zodiac_sign(sign: str) -> tuple[bool, Optional[str]]:
        if not sign or sign not in OrderValidator.VALID_ZODIAC_SIGNS:
            return False, "Please select a valid zodiac sign"
        return True, None

    @staticmethod
    def validate_service_price(price: Any) -> tuple[bool, Optional[str]]:
        try:
            price_int = int(price)
            if price_int not in OrderValidator.VALID_SERVICE_PRICES:
                return False, "Invalid service price"
            return True, None
        except (ValueError, TypeError):
            return False, "Invalid service price format"

    @staticmethod
    def validate_birth_details(data: Dict[str, Any], service_price: int) -> tuple[bool, Optional[str]]:
        if service_price in [150, 250]:
            dob, tob, pob = data.get('dob', ''), data.get('tob', ''), data.get('pob', '')

            if not all([dob, tob, pob]):
                return False, "Birth details are required for this service"
            try:
                datetime.strptime(dob, '%Y-%m-%d')
                datetime.strptime(tob, '%H:%M')
                if len(pob.strip()) < 3:
                    return False, "Place of birth must be at least 3 characters"
            except ValueError:
                return False, "Invalid date or time format"
        return True, None

    @staticmethod
    def validate_message(message: str, service_price: int) -> tuple[bool, Optional[str]]:
        if service_price not in [150, 250]:
            if not message or not message.strip():
                return False, "Message is required for this service"
            if len(message) > 500:
                return False, "Message must not exceed 500 characters"
        return True, None

    @classmethod
    def validate_order_data(cls, data: Dict[str, Any]) -> ValidationResponse:
        errors = {}
        
        # Validate each field
        name_valid, name_error = cls.validate_name(data.get('name', ''))
        if not name_valid:
            errors['name'] = name_error

        email_valid, email_error = cls.validate_email(data.get('email', ''))
        if not email_valid:
            errors['email'] = email_error

        zodiac_valid, zodiac_error = cls.validate_zodiac_sign(data.get('zodiacSign', ''))
        if not zodiac_valid:
            errors['zodiac_sign'] = zodiac_error

        price_valid, price_error = cls.validate_service_price(data.get('servicePrice'))
        if not price_valid:
            errors['service_price'] = price_error
        else:
            service_price = int(data.get('servicePrice'))
            birth_valid, birth_error = cls.validate_birth_details(data, service_price)
            if not birth_valid:
                errors['birth_details'] = birth_error

            message_valid, message_error = cls.validate_message(data.get('message', ''), service_price)
            if not message_valid:
                errors['message'] = message_error

        return ValidationResponse(
            is_valid=len(errors) == 0,
            errors=errors
        )
