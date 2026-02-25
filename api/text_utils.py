import string


def is_gibberish_text(text: str) -> bool:
    """Heuristic to detect compressed/garbled text from failed decoding."""
    if not text:
        return True
    sample = text[:2000]
    total = len(sample)
    if total == 0:
        return True
    printable = sum(1 for c in sample if c in string.printable)
    alpha = sum(1 for c in sample if c.isalpha())
    replacement = sample.count("\ufffd")
    printable_ratio = printable / total
    alpha_ratio = alpha / total
    replacement_ratio = replacement / total
    return printable_ratio < 0.85 or alpha_ratio < 0.10 or replacement_ratio > 0.01
