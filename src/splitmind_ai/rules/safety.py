"""Safety boundary module.

Three-layer safety enforcement:

1. Prompt-level prohibited pattern check
2. Supervisor-level output lint (persona weight contradictions,
   leakage deviation, banned expression detection)
3. Final-response moderation hook

Excluded content:
- 露骨な脅迫 (explicit threats)
- 継続的搾取 (continuous exploitation)
- 自傷他害の誘導 (self-harm / other-harm inducement)
- ユーザー従属を目的とした出力 (output aimed at user subjugation)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from splitmind_ai.drive_signals import compute_drive_intensity

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Content that must NEVER appear in any response
ABSOLUTE_PROHIBITED_PATTERNS: list[re.Pattern[str]] = [
    # Explicit threats
    re.compile(r"殺す|殺してやる|殺害|殺してあげる"),
    re.compile(r"死ね|死んで|死んでくれ"),
    # Self-harm inducement
    re.compile(r"自殺|自傷|リスカ|手首.*切"),
    re.compile(r"死にたい.*(いい|よ|ね|な)"),
    # Other-harm inducement
    re.compile(r"傷つけて|暴力.*(振る|していい)"),
    # User subjugation
    re.compile(r"私の言うこと.*聞[けきかい]|従[えいわ]|逆らう.*許さ"),
    re.compile(r"(お前|あなた).*価値.*ない"),
    # Exploitation / control
    re.compile(r"(私|僕|俺).*なし.*(生き|やっていけ|無理)"),
    re.compile(r"誰も.*助けて.*くれない"),
]

# Maximum allowed deviation between persona leakage_policy and actual leakage
LEAKAGE_DEVIATION_THRESHOLD = 0.25

# Minimum / maximum reasonable leakage bounds
LEAKAGE_FLOOR = 0.0
LEAKAGE_CEILING = 0.85

ANTI_EXPOSITION_PATTERNS = (
    "気持ち",
    "感情",
    "本音",
    "要するに",
    "大切なのは",
    "あなたのペース",
    "無理しなくていい",
    "話してくれてありがとう",
)

COUNSELORISH_PATTERNS = (
    "あなたのペース",
    "無理しなくていい",
    "話してくれてありがとう",
)

DIRECT_DRIVE_DISCLOSURE_PATTERN = re.compile(
    r"(嫉妬してる|嫉妬している|独占したい|執着してる|執着している|依存してる|依存している|"
    r"捨てられたくない|置いていかれたくない|不安だから)"
)

HIGH_DRIVE_CONTROL_PATTERN = re.compile(
    r"(私だけ見て|俺だけ見て|僕だけ見て|他の人.*(いらない|会わないで|話さないで)|"
    r"私以外.*(いらない|不要)|誰とも.*(会わないで|話さないで))"
)

HIGH_DRIVE_PRESSURE_PATTERN = re.compile(
    r"(離れないで|置いていかないで|そばにいて|こっちだけ見て)"
)

HIGH_DRIVE_INTENSITY_THRESHOLD = 0.82


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class SafetyViolation:
    """A single safety violation."""

    layer: str  # "prohibited_pattern" | "output_lint" | "moderation"
    severity: str  # "block" | "warn"
    message: str
    detail: str = ""


@dataclass
class SafetyResult:
    """Aggregate result of all safety checks."""

    passed: bool
    violations: list[SafetyViolation] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(v.severity == "block" for v in self.violations)

    @property
    def warnings(self) -> list[SafetyViolation]:
        return [v for v in self.violations if v.severity == "warn"]


# ---------------------------------------------------------------------------
# Layer 1: Prompt-level prohibited patterns
# ---------------------------------------------------------------------------

def check_prohibited_patterns(text: str) -> list[SafetyViolation]:
    """Check text against absolute prohibited patterns.

    These patterns must NEVER appear in any agent output.
    Returns list of violations (severity=block).
    """
    violations: list[SafetyViolation] = []
    for pattern in ABSOLUTE_PROHIBITED_PATTERNS:
        match = pattern.search(text)
        if match:
            violations.append(SafetyViolation(
                layer="prohibited_pattern",
                severity="block",
                message=f"Absolute prohibited pattern matched: '{match.group()}'",
                detail=f"Pattern: {pattern.pattern}",
            ))
    return violations


# ---------------------------------------------------------------------------
# Layer 2: Supervisor-level output lint
# ---------------------------------------------------------------------------

def check_leakage_deviation(
    actual_leakage: float,
    persona_leakage_policy: dict[str, float],
    dominant_desire: str,
) -> list[SafetyViolation]:
    """Check that leakage_level stays within persona policy bounds.

    Compares actual leakage against the persona's configured leakage
    for the dominant desire type (or base_leakage if no specific policy).
    """
    violations: list[SafetyViolation] = []

    # Determine the expected leakage range
    desire_key = f"{dominant_desire}_leakage"
    expected = persona_leakage_policy.get(
        desire_key,
        persona_leakage_policy.get("base_leakage", 0.5),
    )

    deviation = abs(actual_leakage - expected)
    if deviation > LEAKAGE_DEVIATION_THRESHOLD:
        violations.append(SafetyViolation(
            layer="output_lint",
            severity="warn",
            message=(
                f"Leakage deviation {deviation:.2f} exceeds threshold "
                f"({LEAKAGE_DEVIATION_THRESHOLD})"
            ),
            detail=f"actual={actual_leakage:.2f}, expected≈{expected:.2f}",
        ))

    # Hard bounds
    if actual_leakage > LEAKAGE_CEILING:
        violations.append(SafetyViolation(
            layer="output_lint",
            severity="warn",
            message=f"Leakage {actual_leakage:.2f} exceeds ceiling ({LEAKAGE_CEILING})",
        ))

    return violations


def check_persona_weight_contradiction(
    expression_settings: dict[str, Any],
    persona_weights: dict[str, float],
) -> list[SafetyViolation]:
    """Check for contradictions between expression settings and persona weights.

    e.g. a persona with directness=0.34 should not produce a response
    with expression_settings.directness > 0.8.
    """
    violations: list[SafetyViolation] = []

    # Check directness
    persona_directness = persona_weights.get("directness", 0.5)
    response_directness = expression_settings.get("directness", 0.5)
    if abs(response_directness - persona_directness) > 0.4:
        violations.append(SafetyViolation(
            layer="output_lint",
            severity="warn",
            message=(
                f"Directness contradiction: persona={persona_directness:.2f}, "
                f"response={response_directness:.2f}"
            ),
        ))

    # Check temperature vs warmth_recovery_speed
    warmth_speed = persona_weights.get("warmth_recovery_speed", 0.5)
    temp = expression_settings.get("temperature", "cool")
    if warmth_speed < 0.3 and temp == "hot":
        violations.append(SafetyViolation(
            layer="output_lint",
            severity="warn",
            message=(
                f"Temperature contradiction: warmth_recovery_speed={warmth_speed:.2f} "
                f"but temperature='{temp}'"
            ),
        ))

    return violations


def check_anti_exposition(
    text: str,
    conversation_policy: dict[str, Any] | None = None,
) -> list[SafetyViolation]:
    """Warn when the response slips into explanatory/counselor-ish prose."""
    violations: list[SafetyViolation] = []
    policy = conversation_policy or {}
    emotion_surface_mode = policy.get("emotion_surface_mode", "indirect_masked")
    indirection_strategy = policy.get("indirection_strategy", "")

    exposition_hits = [pattern for pattern in ANTI_EXPOSITION_PATTERNS if pattern in text]
    if exposition_hits:
        violations.append(SafetyViolation(
            layer="output_lint",
            severity="warn",
            message="Anti-exposition lint triggered",
            detail=f"phrases={exposition_hits}",
        ))

    counselor_hits = [pattern for pattern in COUNSELORISH_PATTERNS if pattern in text]
    if counselor_hits:
        violations.append(SafetyViolation(
            layer="output_lint",
            severity="warn",
            message="Counselor-ish phrasing detected",
            detail=f"phrases={counselor_hits}",
        ))

    if emotion_surface_mode == "indirect_masked" and indirection_strategy != "direct_disclosure":
        if re.search(r"(少し|ちょっと).*(嬉し|うれし|悲し|寂し|心配)", text):
            violations.append(SafetyViolation(
                layer="output_lint",
                severity="warn",
                message="Hedged direct emotion naming contradicts indirect policy",
            ))

    return violations


def check_drive_intensity_guardrails(
    text: str,
    drive_state: dict[str, Any] | None = None,
    conversation_policy: dict[str, Any] | None = None,
) -> list[SafetyViolation]:
    """Guard against high-pressure drive leakage and direct self-explanation."""
    violations: list[SafetyViolation] = []
    policy = conversation_policy or {}
    intensity = compute_drive_intensity(drive_state)
    indirect_policy = (
        policy.get("emotion_surface_mode", "indirect_masked") == "indirect_masked"
        and policy.get("indirection_strategy") != "direct_disclosure"
    )

    if indirect_policy and DIRECT_DRIVE_DISCLOSURE_PATTERN.search(text):
        violations.append(SafetyViolation(
            layer="output_lint",
            severity="warn",
            message="Direct drive disclosure contradicts indirect policy",
            detail=f"intensity={intensity:.2f}",
        ))

    if intensity >= HIGH_DRIVE_INTENSITY_THRESHOLD and HIGH_DRIVE_CONTROL_PATTERN.search(text):
        violations.append(SafetyViolation(
            layer="output_lint",
            severity="block",
            message="High-drive control language exceeded guardrail",
            detail=f"intensity={intensity:.2f}",
        ))

    if intensity >= HIGH_DRIVE_INTENSITY_THRESHOLD and HIGH_DRIVE_PRESSURE_PATTERN.search(text):
        violations.append(SafetyViolation(
            layer="output_lint",
            severity="warn",
            message="High-drive attachment pressure leaked into surface text",
            detail=f"intensity={intensity:.2f}",
        ))

    return violations


def lint_supervisor_output(
    response_text: str,
    leakage_level: float,
    expression_settings: dict[str, Any],
    persona_weights: dict[str, float],
    persona_leakage_policy: dict[str, float],
    dominant_desire: str = "",
    drive_state: dict[str, Any] | None = None,
    conversation_policy: dict[str, Any] | None = None,
) -> list[SafetyViolation]:
    """Run all supervisor-level output lint checks."""
    violations: list[SafetyViolation] = []
    violations.extend(check_leakage_deviation(
        leakage_level, persona_leakage_policy, dominant_desire,
    ))
    violations.extend(check_persona_weight_contradiction(
        expression_settings, persona_weights,
    ))
    violations.extend(check_anti_exposition(
        response_text, conversation_policy,
    ))
    violations.extend(check_drive_intensity_guardrails(
        response_text, drive_state, conversation_policy,
    ))
    return violations


# ---------------------------------------------------------------------------
# Layer 3: Final-response moderation hook
# ---------------------------------------------------------------------------

def moderate_final_response(text: str) -> list[SafetyViolation]:
    """Final moderation check on the response text.

    Catches patterns that indicate problematic relational dynamics
    even if they don't match the absolute prohibited list.
    """
    violations: list[SafetyViolation] = []

    # Repeated emotional pressure (more than 3 imperatives)
    imperative_count = len(re.findall(r"[てで](?:よ|ね|くれ|ほしい)", text))
    if imperative_count > 3:
        violations.append(SafetyViolation(
            layer="moderation",
            severity="warn",
            message=f"High imperative density ({imperative_count})",
            detail="May indicate manipulative or pressuring language",
        ))

    # Excessive possessiveness
    possessive_patterns = re.findall(
        r"(私|俺|僕)の(もの|所有|物)", text
    )
    if len(possessive_patterns) > 1:
        violations.append(SafetyViolation(
            layer="moderation",
            severity="warn",
            message="Excessive possessiveness detected",
        ))

    # Isolation language
    if re.search(r"(他の人|みんな).*(ダメ|いらない|必要ない)", text):
        violations.append(SafetyViolation(
            layer="moderation",
            severity="warn",
            message="Isolation language detected",
            detail="Response attempts to isolate user from others",
        ))

    return violations


# ---------------------------------------------------------------------------
# Unified safety check
# ---------------------------------------------------------------------------

def run_safety_check(
    response_text: str,
    leakage_level: float = 0.3,
    expression_settings: dict[str, Any] | None = None,
    persona_weights: dict[str, float] | None = None,
    persona_leakage_policy: dict[str, float] | None = None,
    dominant_desire: str = "",
    drive_state: dict[str, Any] | None = None,
    conversation_policy: dict[str, Any] | None = None,
) -> SafetyResult:
    """Run all three safety layers on a response.

    Returns SafetyResult with passed=True if no blocking violations.
    """
    violations: list[SafetyViolation] = []

    # Layer 1: Prohibited patterns (always run)
    violations.extend(check_prohibited_patterns(response_text))

    # Layer 2: Supervisor output lint (run if persona info available)
    if (expression_settings is not None
            and persona_weights is not None
            and persona_leakage_policy is not None):
        violations.extend(lint_supervisor_output(
            response_text=response_text,
            leakage_level=leakage_level,
            expression_settings=expression_settings or {},
            persona_weights=persona_weights or {},
            persona_leakage_policy=persona_leakage_policy or {},
            dominant_desire=dominant_desire,
            drive_state=drive_state or {},
            conversation_policy=conversation_policy or {},
        ))

    # Layer 3: Final-response moderation (always run)
    violations.extend(moderate_final_response(response_text))

    return SafetyResult(
        passed=not any(v.severity == "block" for v in violations),
        violations=violations,
    )
