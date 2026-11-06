# Data dictionary

## `divinatory_terms_taxonomy.csv`

| Column | Meaning |
|---|---|
| `term_id` | Stable concept identifier. |
| `term_fr` | French concept label. |
| `term_en` | English concept label. |
| `category` | Main category of the concept. |
| `subcategory` | More precise thematic group. |
| `definition_fr` | French definition. |
| `definition_en` | English definition. |
| `related_terms` | Semicolon-separated related concepts. |
| `professional_context` | Use or meaning in a professional consultation / research-oriented context. |
| `ethical_note` | Caution, boundary or ethical framing. |
| `source_type` | Type of source used for this row; here: conceptual taxonomy. |

## `tarot_major_arcana_symbolic_taxonomy.csv`

| Column | Meaning |
|---|---|
| `arcana_number` | Major arcana number. |
| `arcana_fr` | French card name. |
| `arcana_en` | English card name. |
| `symbolic_family` | Main symbolic family for exploratory grouping. |
| `main_themes_fr` | Semicolon-separated French themes. |
| `main_themes_en` | Semicolon-separated English themes. |
| `decision_context` | Typical decision-oriented context. |
| `emotional_context` | Typical emotional context. |
| `professional_context` | Responsible use in consultation or symbolic analysis. |
| `ethical_caution` | Professional caution associated with interpretation. |
| `interpretation_boundary` | Limit to avoid deterministic or harmful readings. |

## `ethical_boundaries_divinatory_practice.csv`

| Column | Meaning |
|---|---|
| `boundary_id` | Stable boundary identifier. |
| `domain` | Area of concern: health, law, minors, emotional distress, etc. |
| `risk_type` | Main professional or ethical risk. |
| `example_request_fr` | Example of a client request in French. |
| `responsible_response_fr` | Responsible response framing in French. |
| `ethical_principle` | Core ethical principle involved. |
| `excluded_claims` | Claims or promises to exclude. |
| `recommended_action` | Responsible action: refusal, recadrage, orientation, etc. |

## `digital_trust_signals_divinatory_practices.csv`

| Column | Meaning |
|---|---|
| `signal_id` | Stable signal identifier. |
| `trust_signal` | Trust signal label. |
| `category` | Signal category. |
| `description_fr` | French explanation. |
| `description_en` | English explanation. |
| `user_value` | Why this signal matters for users. |
| `verification_level` | Approximate verification strength: High, Medium, Low. |
| `risk_if_absent` | Main risk if the signal is missing. |
| `digital_context` | Where the signal appears: website, booking, academic profile, etc. |
