from enum import Enum


class ErrorCodes(str, Enum):
    UPLOAD_VALIDATION_FAILED = "UPLOAD_001"
    RESUME_PARSE_FAILED = "PARSE_001"
    EXTRACTION_FAILED = "AI_001"
    PAYLOAD_BUILD_FAILED = "PAYLOAD_001"
    VENDOR_SUBMISSION_FAILED = "VENDOR_001"
    VENDOR_RESULT_TIMEOUT = "VENDOR_002"
    RESULT_NORMALIZATION_FAILED = "RESULT_001"
    DASHBOARD_DELIVERY_FAILED = "DASHBOARD_001"
    SCHEDULE_JOB_FAILED = "SCHEDULE_001"
    WORKFLOW_FAILED = "WORKFLOW_001"


ERROR_DETAILS = {
    ErrorCodes.UPLOAD_VALIDATION_FAILED: {
        "category": "upload",
        "severity": "WARNING",
        "message": "Upload validation failed",
    },
    ErrorCodes.RESUME_PARSE_FAILED: {
        "category": "parsing",
        "severity": "ERROR",
        "message": "Resume parsing failed",
    },
    ErrorCodes.EXTRACTION_FAILED: {
        "category": "ai_extraction",
        "severity": "ERROR",
        "message": "AI extraction failed",
    },
    ErrorCodes.PAYLOAD_BUILD_FAILED: {
        "category": "payload",
        "severity": "ERROR",
        "message": "Payload build failed",
    },
    ErrorCodes.VENDOR_SUBMISSION_FAILED: {
        "category": "vendor",
        "severity": "ERROR",
        "message": "Vendor submission failed",
    },
    ErrorCodes.VENDOR_RESULT_TIMEOUT: {
        "category": "vendor",
        "severity": "WARNING",
        "message": "Vendor result retrieval timed out",
    },
    ErrorCodes.RESULT_NORMALIZATION_FAILED: {
        "category": "results",
        "severity": "ERROR",
        "message": "Result normalization failed",
    },
    ErrorCodes.DASHBOARD_DELIVERY_FAILED: {
        "category": "dashboard",
        "severity": "ERROR",
        "message": "Dashboard delivery failed",
    },
    ErrorCodes.SCHEDULE_JOB_FAILED: {
        "category": "schedule",
        "severity": "ERROR",
        "message": "Scheduled job failed",
    },
    ErrorCodes.WORKFLOW_FAILED: {
        "category": "workflow",
        "severity": "ERROR",
        "message": "Workflow failed",
    },
}


def error_detail(code: ErrorCodes | str) -> dict[str, str]:
    try:
        normalized = ErrorCodes(code)
        return ERROR_DETAILS[normalized]
    except ValueError:
        return {
            "category": "workflow",
            "severity": "ERROR",
            "message": "Unregistered workflow error",
        }
