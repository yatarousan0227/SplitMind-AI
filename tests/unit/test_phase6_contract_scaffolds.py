from splitmind_ai.contracts.action_policy import (
    ActionCandidate,
    ActionMode,
    ConversationPolicy,
    UtteranceCandidate,
    UtteranceSelection,
)
from splitmind_ai.contracts.appraisal import (
    AppraisalLabel,
    AppraisalBundle,
    AppraisalDimension,
    AppraisalState,
    SelfState,
    SocialCue,
    SocialCueType,
    SocialIntentHypothesis,
    SocialModelState,
)


def test_appraisal_bundle_scaffold_validates():
    bundle = AppraisalBundle(
        social_cues=[
            SocialCue(
                cue_type=SocialCueType.competition,
                evidence="今日は他の人とすごく楽しかった",
                intensity=0.8,
                confidence=0.9,
            )
        ],
        appraisal=AppraisalState(
            perceived_acceptance=AppraisalDimension(score=0.2, confidence=0.7),
            perceived_rejection=AppraisalDimension(score=0.4, confidence=0.6),
            perceived_competition=AppraisalDimension(score=0.8, confidence=0.9),
            perceived_distance=AppraisalDimension(score=0.3, confidence=0.6),
            ambiguity=AppraisalDimension(score=0.2, confidence=0.8),
            face_threat=AppraisalDimension(score=0.7, confidence=0.8),
            attachment_activation=AppraisalDimension(score=0.9, confidence=0.9),
            repair_opportunity=AppraisalDimension(score=0.1, confidence=0.7),
            dominant_appraisal=AppraisalLabel.competitive,
        ),
        social_model=SocialModelState(
            user_current_intent_hypotheses=[
                SocialIntentHypothesis(label="share_good_news", confidence=0.8)
            ],
            user_attachment_guess="secure",
            user_sensitivity_guess=["comparison"],
            confidence=0.6,
            last_user_action="share",
        ),
        self_state=SelfState(
            threatened_self_image=["special_to_user"],
            pride_level=0.7,
            shame_activation=0.2,
            dependency_fear=0.5,
            desire_for_closeness=0.8,
            urge_to_test_user=0.6,
            active_defenses=["ironic_deflection"],
        ),
    )

    assert bundle.appraisal.dominant_appraisal == AppraisalLabel.competitive
    assert bundle.social_cues[0].cue_type == SocialCueType.competition


def test_action_policy_scaffold_validates():
    policy = ConversationPolicy(
        selected_mode=ActionMode.tease,
        candidates=[
            ActionCandidate(
                mode=ActionMode.tease,
                label="dry_tease",
                score=0.82,
                rationale_short="Protect pride while testing the user.",
                risk_level=0.35,
                defense_hint="ironic_deflection",
            ),
            ActionCandidate(
                mode=ActionMode.withdraw,
                label="injured_withdrawal",
                score=0.54,
                rationale_short="Reduce exposure by pulling back.",
                risk_level=0.12,
                defense_hint="suppression",
            ),
        ],
        selection_rationale="Teasing preserves face without full retreat.",
        fallback_mode=ActionMode.deflect,
    )

    selection = UtteranceSelection(
        selected_text="へえ、そんなに楽しかったんだ。",
        selected_index=0,
        candidates=[
            UtteranceCandidate(
                text="へえ、そんなに楽しかったんだ。",
                mode=ActionMode.tease,
                naturalness_score=0.74,
                policy_fit_score=0.83,
            ),
            UtteranceCandidate(
                text="そう。よかったね。",
                mode=ActionMode.withdraw,
                naturalness_score=0.61,
                policy_fit_score=0.55,
            ),
        ],
        selection_rationale="Candidate 0 better matches the chosen mode.",
    )

    assert policy.selected_mode == ActionMode.tease
    assert selection.candidates[0].mode == ActionMode.tease
