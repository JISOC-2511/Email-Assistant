import re

PERSONAL_INFO = {
    "email_address": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    "phone_number":  r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
    "credit_card":   r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
    "SSN":           r'\b\d{3}-\d{2}-\d{4}\b',
    "TFN":           r'\b\d{3} \d{3} \d{3}\b',
}

RISK_KEYWORDS = [
    "lawsuit", "legal action", "breach", "overdue", "urgent",
    "confidential", "invoice dispute", "compliance violation",
    "under investigation", "arbitration", "fraud", "penalty",
]

def detect_personal_info(text: str) -> dict[str, int]:
    for key, pattern in PERSONAL_INFO.items():
        matches = re.findall(pattern, text)
        if matches:
            print(f"Detected {len(matches)} {key}(s): {matches}")
    return {key: len(matches) for key, pattern in PERSONAL_INFO.items()
        if (matches := re.findall(pattern, text))}

def detect_risk_keywords(text: str) -> list[str]:
    flags = []
    for keyword in RISK_KEYWORDS:
        if keyword in text.lower():
            print(f"Detected risk keyword: {keyword}")
            flags.append(keyword)
    return flags


def calculate_risk_score(keywords: list[str], pi: dict) -> str:
    if pi or len(keywords) >= 2:
        return "High Risk"
    elif len(keywords) == 1:
        return "Medium Risk"
    else:
        return "Low Risk"
    
def analyse_text(text: str) -> dict:
    pi = detect_personal_info(text)
    keywords = detect_risk_keywords(text)
    risk_score = calculate_risk_score(keywords, pi)
    return {
        "risk_score": risk_score,
        "personal_info": pi,
        "risk_keywords": keywords,
        "flagged": risk_score in ["High Risk", "Medium Risk"]
    }