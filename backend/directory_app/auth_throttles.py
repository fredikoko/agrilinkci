from rest_framework.throttling import AnonRateThrottle


class OtpRequestThrottle(AnonRateThrottle):
    scope = "otp_request"


class OtpVerifyThrottle(AnonRateThrottle):
    scope = "otp_verify"


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class PasswordResetThrottle(AnonRateThrottle):
    scope = "password_reset"
