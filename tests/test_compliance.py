import pytest
from compliance import detect_personal_info, detect_risk_keywords, calculate_risk_score, analyse_text


# ── detect_personal_info ──────────────────────────────────────────────────────

def test_detects_email_address():
    result = detect_personal_info("Contact us at alice@company.com for details.")
    assert "email_address" in result
    assert result["email_address"] == 1

def test_detects_multiple_emails():
    result = detect_personal_info("From alice@corp.com to bob@corp.com")
    assert result["email_address"] == 2

def test_detects_phone_number():
    result = detect_personal_info("Call me on 555-123-4567 anytime.")
    assert "phone_number" in result
    assert result["phone_number"] == 1

def test_detects_credit_card():
    result = detect_personal_info("Card ending in 4111-1111-1111-1111 was charged.")
    assert "credit_card" in result

def test_detects_ssn():
    result = detect_personal_info("Employee SSN is 123-45-6789 on file.")
    assert "SSN" in result
    assert result["SSN"] == 1

def test_detects_tfn():
    result = detect_personal_info("Australian TFN provided: 123 456 789.")
    assert "TFN" in result
    assert result["TFN"] == 1

def test_detects_multiple_ssns():
    result = detect_personal_info("SSNs on file: 123-45-6789 and 987-65-4321")
    assert result["SSN"] == 2

def test_detects_multiple_tfns():
    result = detect_personal_info("TFNs: 123 456 789 and 987 654 321")
    assert result["TFN"] == 2

def test_no_pii_returns_empty_dict():
    """Clean text should return an empty dict, not keys with zero counts."""
    result = detect_personal_info("This is a normal business update with no personal data.")
    assert result == {}

def test_only_includes_found_keys():
    """Should not include keys for PII types that weren't found."""
    result = detect_personal_info("Email me at test@example.com")
    assert "phone_number" not in result
    assert "credit_card" not in result
    assert "SSN" not in result
    assert "TFN" not in result

def test_detects_multiple_pii_types():
    result = detect_personal_info("alice@corp.com called on 555-123-4567, SSN 123-45-6789")
    assert "email_address" in result
    assert "phone_number" in result
    assert "SSN" in result

def test_all_five_pii_types():
    text = (
        "Email: alice@corp.com "
        "Phone: 555-123-4567 "
        "Card: 4111-1111-1111-1111 "
        "SSN: 123-45-6789 "
        "TFN: 123 456 789"
    )
    result = detect_personal_info(text)
    assert "email_address" in result
    assert "phone_number" in result
    assert "credit_card" in result
    assert "SSN" in result
    assert "TFN" in result


# ── detect_risk_keywords ──────────────────────────────────────────────────────

def test_detects_single_keyword():
    result = detect_risk_keywords("This matter is urgent and needs attention.")
    assert "urgent" in result

def test_detects_multiple_keywords():
    result = detect_risk_keywords("There is a lawsuit pending and fraud suspected.")
    assert "lawsuit" in result
    assert "fraud" in result

def test_case_insensitive():
    result = detect_risk_keywords("This is URGENT and involves a BREACH.")
    assert "urgent" in result
    assert "breach" in result

def test_no_keywords_returns_empty_list():
    result = detect_risk_keywords("Quarterly earnings were up 12 percent this period.")
    assert result == []

def test_returns_keyword_not_full_text():
    """Must return the keyword string, not the full document text."""
    result = detect_risk_keywords("This is an overdue invoice.")
    assert all(len(k) < len("This is an overdue invoice.") for k in result)
    assert "overdue" in result

def test_multi_word_keyword():
    result = detect_risk_keywords("This is under investigation by the board.")
    assert "under investigation" in result


# ── calculate_risk_score ──────────────────────────────────────────────────────

def test_no_keywords_no_pii_is_low():
    assert calculate_risk_score([], {}) == "Low Risk"

def test_one_keyword_no_pii_is_medium():
    assert calculate_risk_score(["urgent"], {}) == "Medium Risk"

def test_two_keywords_no_pii_is_high():
    assert calculate_risk_score(["urgent", "fraud"], {}) == "High Risk"

def test_pii_alone_is_high():
    """Any PII should trigger High Risk even with no risk keywords."""
    assert calculate_risk_score([], {"email_address": 1}) == "High Risk"

def test_ssn_alone_is_high():
    assert calculate_risk_score([], {"SSN": 1}) == "High Risk"

def test_tfn_alone_is_high():
    assert calculate_risk_score([], {"TFN": 1}) == "High Risk"

def test_pii_and_keywords_is_high():
    assert calculate_risk_score(["lawsuit"], {"phone_number": 2}) == "High Risk"


# ── analyse_text ──────────────────────────────────────────────────────────────

def test_analyse_text_correct_keys():
    result = analyse_text("Normal business update.")
    assert "risk_score" in result
    assert "personal_info" in result
    assert "risk_keywords" in result
    assert "flagged" in result

def test_analyse_text_low_risk_not_flagged():
    result = analyse_text("Quarterly update: everything is on track.")
    assert result["risk_score"] == "Low Risk"
    assert result["flagged"] is False

def test_analyse_text_high_risk_flagged():
    result = analyse_text("Urgent: breach detected, lawsuit expected.")
    assert result["risk_score"] == "High Risk"
    assert result["flagged"] is True

def test_analyse_text_medium_risk_flagged():
    result = analyse_text("This payment is overdue.")
    assert result["risk_score"] == "Medium Risk"
    assert result["flagged"] is True

def test_analyse_text_ssn_triggers_high_risk():
    result = analyse_text("Employee SSN 123-45-6789 was found in the report.")
    assert result["risk_score"] == "High Risk"
    assert result["flagged"] is True

def test_analyse_text_tfn_triggers_high_risk():
    result = analyse_text("Client TFN 123 456 789 must not be shared externally.")
    assert result["risk_score"] == "High Risk"
    assert result["flagged"] is True

def test_analyse_text_returns_correct_keywords():
    result = analyse_text("There is fraud and a breach in this document.")
    assert "fraud" in result["risk_keywords"]
    assert "breach" in result["risk_keywords"]