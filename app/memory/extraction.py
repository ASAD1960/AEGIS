
"""
Evidence-grounded personal memory extraction.

Only narrowly recognized first-person statements are eligible
for automatic storage. Ambiguous statements require confirmation.
"""

import re


MAX_MESSAGE_LENGTH = 5000

LANGUAGES = {
    "java": "Java",
    "python": "Python",
}


CORRECTION_PREFIX = re.compile(
    r"^\s*(?:correction|to clarify|i need to correct that)"
    r"\s*[:,\-]\s*",
    re.IGNORECASE,
)


# Patterns must begin at the start of the statement.
# This prevents matching quoted statements or claims embedded
# in third-person sentences.

PREFERENCE_PATTERN = re.compile(
    r"^\s*I\s+"
    r"(?:(?:do\s+not|don't)\s+)?"
    r"(?P<verb>enjoy|like|love|prefer)\s+"
    r"(?P<language>Java|Python)\b",
    re.IGNORECASE,
)


STUDY_PATTERN = re.compile(
    r"^\s*I\s+(?:have\s+)?studied\s+"
    r"(?P<language>Java|Python)\s+"
    r"(?:in|during)\s+"
    r"(?P<context>OOP|Object-Oriented Programming)\b",
    re.IGNORECASE,
)


COMBINED_JAVA_STUDY_PATTERN = re.compile(
    r"^\s*I\s+enjoy\s+Java\s+and\s+studied\s+it\s+"
    r"(?:in|during)\s+"
    r"(?P<context>OOP|Object-Oriented Programming)\b",
    re.IGNORECASE,
)


AMBIGUOUS_PATTERN = re.compile(
    r"^\s*I\s+(?:might|may|could)\s+learn\s+"
    r"(?P<language>Java|Python)\b"
    r"|^\s*I\s+am\s+thinking\s+of\s+learning\s+"
    r"(?P<language2>Java|Python)\b",
    re.IGNORECASE,
)


def _canonical_language(value):
    """Return a consistent language name."""

    return LANGUAGES[value.lower()]


def _make_candidate(
    memory_key,
    content,
    category,
    source_type,
    source_text,
    action="save",
):
    return {
        "memory_key": memory_key,
        "content": content,
        "category": category,
        "source_type": source_type,
        "source_text": source_text,
        "action": action,
    }


def extract_personal_memory_candidates(message):
    """
    Extract narrowly supported personal-memory candidates.

    This function does not write to the database.

    Returns:
        A list of dictionaries.

        action="save":
            Explicit first-person statement or correction.

        action="confirm":
            Ambiguous statement requiring user confirmation.

    Unsupported statements produce no candidates.
    """

    if not isinstance(message, str):
        return []

    message = message.strip()

    if not message or len(message) > MAX_MESSAGE_LENGTH:
        return []

    candidates = []

    # Keep original sentence text for provenance.
    sentences = re.split(r"(?<=[.!?])\s+|\n+", message)

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        # A question is not treated as a personal assertion.
        if sentence.endswith("?"):
            continue

        correction_match = CORRECTION_PREFIX.match(sentence)

        source_type = (
            "correction"
            if correction_match
            else "explicit_statement"
        )

        # Remove only the correction label for pattern matching.
        statement = (
            sentence[correction_match.end():].strip()
            if correction_match
            else sentence
        )

        # --------------------------------------------------
        # Explicit preferences.
        # --------------------------------------------------

        preference_match = PREFERENCE_PATTERN.search(statement)

        if preference_match:

            language = _canonical_language(
                preference_match.group("language")
            )

            verb = preference_match.group("verb").lower()

            prefix = statement[
                preference_match.start():
                preference_match.end()
            ].lower()

            negative = bool(
                re.search(r"\b(?:do not|don't)\b", prefix)
            )

            verb_forms = {
                "enjoy": "enjoys",
                "like": "likes",
                "love": "loves",
                "prefer": "prefers",
            }

            if negative:
                content = (
                    f"The user does not {verb} {language}."
                )
            else:
                content = (
                    f"The user {verb_forms[verb]} {language}."
                )

            candidates.append(
                _make_candidate(
                    memory_key=(
                        f"programming.{language.lower()}.preference"
                    ),
                    content=content,
                    category="programming",
                    source_type=source_type,
                    source_text=sentence,
                )
            )

        # --------------------------------------------------
        # Explicit study history.
        # --------------------------------------------------

        study_match = STUDY_PATTERN.search(statement)

        combined_study_match = (
            COMBINED_JAVA_STUDY_PATTERN.search(statement)
        )

        if study_match or combined_study_match:

            language = (
                _canonical_language(study_match.group("language"))
                if study_match
                else "Java"
            )

            content = (
                f"The user studied {language} in "
                "Object-Oriented Programming."
            )

            candidates.append(
                _make_candidate(
                    memory_key=(
                        f"education.{language.lower()}.oop_study"
                    ),
                    content=content,
                    category="education",
                    source_type=source_type,
                    source_text=sentence,
                )
            )

        # --------------------------------------------------
        # Ambiguous future intentions.
        # --------------------------------------------------

        ambiguous_match = AMBIGUOUS_PATTERN.search(statement)

        if ambiguous_match:

            language_value = (
                ambiguous_match.group("language")
                or ambiguous_match.group("language2")
            )

            language = _canonical_language(language_value)

            candidates.append(
                _make_candidate(
                    memory_key=(
                        f"programming.{language.lower()}.learning_intention"
                    ),
                    content=(
                        f"The user may be interested in learning "
                        f"{language}."
                    ),
                    category="programming",
                    source_type=None,
                    source_text=sentence,
                    action="confirm",
                )
            )

    return candidates
