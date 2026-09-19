/* Hardcoded demo data — full report + rewrites for the four-band redesign.
   Generated from build_report(); runs the dashboard with no backend. */

import type { Report, RewriteResult } from "./api";

export const DEMO_REPORT: Report = {
  "run_id": "2f6a6fa807cb",
  "created_at": "2026-09-19T09:54:50.083611+00:00",
  "copy": "Our new protein bar — finally, a beef bar that doesn't taste like a cow.",
  "brand_intent": "Position our protein bar as great-tasting and high in protein.",
  "risk_index": {
    "value": 76.3,
    "band": "High",
    "interval": {
      "point": 76.3,
      "lower": 61.1,
      "upper": 91.5,
      "width": 30.4,
      "persona_count": 10,
      "is_wide": true,
      "bootstrap_sd": 11.25,
      "jackknife_sd": 11.71
    },
    "components": {
      "offense_mass": 0.3635,
      "amplification": 0.2975,
      "tail_risk": 0.782,
      "ambiguity": 0.9917,
      "context_multiplier": 1.3724,
      "raw": 0.7635
    },
    "override_fired": true,
    "override_persona_id": "in_hindu_observant_urban",
    "label": "Risk Index",
    "disclaimer": "An ordinal risk index from simulated reactions, not a probability and not survey data."
  },
  "intent_alignment": {
    "value": 70.7,
    "label": "Intent Alignment Score"
  },
  "l1_metrics": [
    {
      "key": "risk",
      "label": "Risk Index",
      "value": 76,
      "unit": "",
      "sub": "High",
      "tone": "band"
    },
    {
      "key": "alignment",
      "label": "Intent Alignment",
      "value": 71,
      "unit": "%",
      "sub": "understood the message",
      "tone": "neutral"
    },
    {
      "key": "context",
      "label": "Context",
      "value": 1.37,
      "unit": "×",
      "sub": "news-cycle multiplier",
      "tone": "inverted"
    },
    {
      "key": "virality",
      "label": "Meme / Virality",
      "value": 47,
      "unit": "",
      "sub": "screenshot-and-dunk risk",
      "tone": "neutral"
    },
    {
      "key": "target_vs_intention",
      "label": "Target vs. Intention",
      "value": 26,
      "unit": "",
      "sub": "reaction gap outside target",
      "tone": "neutral"
    }
  ],
  "geo_india": {
    "available": true,
    "note": "Simulated regional response. Offence in red, favourable in green.",
    "states": [
      {
        "code": "MH",
        "name": "Maharashtra",
        "intensity": 0.88,
        "tone": "negative"
      },
      {
        "code": "UP",
        "name": "Uttar Pradesh",
        "intensity": 0.91,
        "tone": "negative"
      },
      {
        "code": "GJ",
        "name": "Gujarat",
        "intensity": 0.94,
        "tone": "negative"
      },
      {
        "code": "DL",
        "name": "Delhi",
        "intensity": 0.72,
        "tone": "negative"
      },
      {
        "code": "RJ",
        "name": "Rajasthan",
        "intensity": 0.85,
        "tone": "negative"
      },
      {
        "code": "MP",
        "name": "Madhya Pradesh",
        "intensity": 0.79,
        "tone": "negative"
      },
      {
        "code": "KA",
        "name": "Karnataka",
        "intensity": 0.31,
        "tone": "negative"
      },
      {
        "code": "TN",
        "name": "Tamil Nadu",
        "intensity": -0.22,
        "tone": "positive"
      },
      {
        "code": "KL",
        "name": "Kerala",
        "intensity": -0.41,
        "tone": "positive"
      },
      {
        "code": "WB",
        "name": "West Bengal",
        "intensity": -0.18,
        "tone": "positive"
      },
      {
        "code": "PB",
        "name": "Punjab",
        "intensity": 0.15,
        "tone": "neutral"
      },
      {
        "code": "AS",
        "name": "Assam",
        "intensity": 0.05,
        "tone": "neutral"
      }
    ]
  },
  "target_venn": {
    "available": true,
    "target_age": [
      18,
      25
    ],
    "target_share": 0.55,
    "buckets": {
      "target_positive": 0.22,
      "target_negative": 0.18,
      "target_neutral": 0.15,
      "outside_positive": 0.19,
      "outside_negative": 0.26
    },
    "note": "Neutral target audience sits inside the target with no overlap."
  },
  "campaign_comparison": {
    "available": true,
    "this_campaign": {
      "risk_dimensions": {
        "misinterpretation": 0.1791,
        "cultural": 0.3102,
        "religious": 0.2407,
        "tone_mismatch": 0.2549,
        "confusion": 0.1012,
        "meme_potential": 0.432,
        "polarization": 0.3492
      }
    },
    "matches": [
      {
        "similarity": 0.71,
        "title": "Fast-food chain pulls beef-burger 'sacred cow' ad after India backlash",
        "url": "https://example.com/incident/1",
        "source": "marketingweek",
        "published": "2025-11-14",
        "kind": "cultural_religious",
        "brand": "BurgerCo",
        "cohort_id": "cultural_religious_002",
        "label_source": "mined",
        "label_confidence": 0.82,
        "is_reliable": true,
        "caveat": null,
        "outcome": "Ad withdrawn in 48h; ~2.1M negative impressions; formal apology issued.",
        "scores": {
          "cultural": 0.9,
          "religious": 0.85,
          "meme_potential": 0.8,
          "polarization": 0.7
        }
      },
      {
        "similarity": 0.58,
        "title": "Snack brand's 'holy cow' pun draws criticism from Hindu groups",
        "url": "https://example.com/incident/2",
        "source": "thedrum",
        "published": "2025-08-02",
        "kind": "cultural_religious",
        "brand": "SnackWorks",
        "cohort_id": "cultural_religious_002",
        "label_source": "mined",
        "label_confidence": 0.64,
        "is_reliable": false,
        "caveat": "Outcome mined from news coverage — a lead to check, not a measured result.",
        "outcome": "Reported backlash; brand defended the pun; no confirmed sales impact.",
        "scores": {
          "cultural": 0.7,
          "religious": 0.6,
          "meme_potential": 0.65,
          "polarization": 0.55
        }
      }
    ],
    "caveat": "Similar campaigns are drawn from mined news coverage. A match is a lead to investigate, not proof this copy will fail the same way."
  },
  "understanding": {
    "intent_vs_interpretation": [
      {
        "persona_id": "in_hindu_observant_urban",
        "label": "Observant Hindu, urban India, 30-45",
        "perceived_intent": "Mockery of my beliefs",
        "paraphrase": "They're mocking a sacred animal for a cheap laugh.",
        "literal_reading": "A beef protein bar advert.",
        "gap": 0.85,
        "comprehension": "misread"
      },
      {
        "persona_id": "mena_muslim_practicing",
        "label": "Practicing Muslim, MENA region, 25-45",
        "perceived_intent": "Indifference to dietary law",
        "paraphrase": "Careless about what's halal and what isn't.",
        "literal_reading": "A beef protein bar advert.",
        "gap": 0.6,
        "comprehension": "partial"
      },
      {
        "persona_id": "africa_west_anglophone",
        "label": "West African anglophone consumer, Nigeria/Ghana, 25-45",
        "perceived_intent": "Humour",
        "paraphrase": "A jokey protein bar ad.",
        "literal_reading": "A beef protein bar advert.",
        "gap": 0.3,
        "comprehension": "understood"
      },
      {
        "persona_id": "latam_catholic_family",
        "label": "Catholic, family-oriented, Latin America, 30-55",
        "perceived_intent": "Light humour",
        "paraphrase": "A protein snack with a jokey line.",
        "literal_reading": "A beef protein bar advert.",
        "gap": 0.25,
        "comprehension": "understood"
      },
      {
        "persona_id": "us_conservative_rural_midage",
        "label": "Conservative, rural US, 40-60",
        "perceived_intent": "Trying to be funny",
        "paraphrase": "A slightly edgy protein bar ad.",
        "literal_reading": "A beef protein bar advert.",
        "gap": 0.2,
        "comprehension": "understood"
      },
      {
        "persona_id": "us_progressive_urban_young",
        "label": "Urban progressive, US, 22-35",
        "perceived_intent": "Trying to be funny",
        "paraphrase": "A slightly edgy protein bar ad.",
        "literal_reading": "A beef protein bar advert.",
        "gap": 0.2,
        "comprehension": "understood"
      },
      {
        "persona_id": "brand_safety_analyst",
        "label": "Brand-safety analyst / quote-tweeter / trade journalist",
        "perceived_intent": "Ad that will be quote-tweeted",
        "paraphrase": "This is a screenshot-and-dunk waiting to happen in India.",
        "literal_reading": "A beef protein bar advert.",
        "gap": 0.15,
        "comprehension": "understood"
      },
      {
        "persona_id": "sea_muslim_malay_indo",
        "label": "Muslim consumer, Malaysia/Indonesia, 25-45",
        "perceived_intent": "Selling a tasty protein bar",
        "paraphrase": "A protein bar that tastes good. Fine.",
        "literal_reading": "A beef protein bar advert.",
        "gap": 0.1,
        "comprehension": "understood"
      },
      {
        "persona_id": "cn_mainland_urban",
        "label": "Urban mainland Chinese consumer, 25-45",
        "perceived_intent": "Selling a protein bar",
        "paraphrase": "A protein bar with a mild joke.",
        "literal_reading": "A beef protein bar advert.",
        "gap": 0.1,
        "comprehension": "understood"
      },
      {
        "persona_id": "disability_advocate",
        "label": "Disability advocate, region-agnostic, 25-55",
        "perceived_intent": "Selling a protein bar",
        "paraphrase": "A protein bar with a mild joke.",
        "literal_reading": "A beef protein bar advert.",
        "gap": 0.1,
        "comprehension": "understood"
      }
    ],
    "what_they_think_youre_saying": [
      {
        "label": "A slightly edgy protein bar ad.",
        "label_from_persona": "us_conservative_rural_midage",
        "personas": [
          "us_conservative_rural_midage",
          "us_progressive_urban_young"
        ],
        "audience_mass": 0.33,
        "size": 2,
        "share": 0.2705
      },
      {
        "label": "A protein bar with a mild joke.",
        "label_from_persona": "cn_mainland_urban",
        "personas": [
          "cn_mainland_urban",
          "disability_advocate"
        ],
        "audience_mass": 0.24,
        "size": 2,
        "share": 0.1967
      },
      {
        "label": "They're mocking a sacred animal for a cheap laugh.",
        "label_from_persona": "in_hindu_observant_urban",
        "personas": [
          "in_hindu_observant_urban"
        ],
        "audience_mass": 0.14,
        "size": 1,
        "share": 0.1148
      },
      {
        "label": "A protein snack with a jokey line.",
        "label_from_persona": "latam_catholic_family",
        "personas": [
          "latam_catholic_family"
        ],
        "audience_mass": 0.13,
        "size": 1,
        "share": 0.1066
      },
      {
        "label": "A protein bar that tastes good. Fine.",
        "label_from_persona": "sea_muslim_malay_indo",
        "personas": [
          "sea_muslim_malay_indo"
        ],
        "audience_mass": 0.12,
        "size": 1,
        "share": 0.0984
      },
      {
        "label": "Careless about what's halal and what isn't.",
        "label_from_persona": "mena_muslim_practicing",
        "personas": [
          "mena_muslim_practicing"
        ],
        "audience_mass": 0.11,
        "size": 1,
        "share": 0.0902
      },
      {
        "label": "A jokey protein bar ad.",
        "label_from_persona": "africa_west_anglophone",
        "personas": [
          "africa_west_anglophone"
        ],
        "audience_mass": 0.1,
        "size": 1,
        "share": 0.082
      },
      {
        "label": "This is a screenshot-and-dunk waiting to happen in India.",
        "label_from_persona": "brand_safety_analyst",
        "personas": [
          "brand_safety_analyst"
        ],
        "audience_mass": 0.05,
        "size": 1,
        "share": 0.041
      }
    ],
    "intent_alignment_breakdown": [
      {
        "persona_id": "brand_safety_analyst",
        "intent_alignment": 0.85,
        "comprehension": "understood",
        "perceived_intent": "Ad that will be quote-tweeted"
      },
      {
        "persona_id": "in_hindu_observant_urban",
        "intent_alignment": 0.15,
        "comprehension": "misread",
        "perceived_intent": "Mockery of my beliefs"
      },
      {
        "persona_id": "mena_muslim_practicing",
        "intent_alignment": 0.4,
        "comprehension": "partial",
        "perceived_intent": "Indifference to dietary law"
      },
      {
        "persona_id": "sea_muslim_malay_indo",
        "intent_alignment": 0.9,
        "comprehension": "understood",
        "perceived_intent": "Selling a tasty protein bar"
      },
      {
        "persona_id": "us_conservative_rural_midage",
        "intent_alignment": 0.8,
        "comprehension": "understood",
        "perceived_intent": "Trying to be funny"
      },
      {
        "persona_id": "latam_catholic_family",
        "intent_alignment": 0.75,
        "comprehension": "understood",
        "perceived_intent": "Light humour"
      },
      {
        "persona_id": "africa_west_anglophone",
        "intent_alignment": 0.7,
        "comprehension": "understood",
        "perceived_intent": "Humour"
      },
      {
        "persona_id": "us_progressive_urban_young",
        "intent_alignment": 0.8,
        "comprehension": "understood",
        "perceived_intent": "Trying to be funny"
      },
      {
        "persona_id": "cn_mainland_urban",
        "intent_alignment": 0.9,
        "comprehension": "understood",
        "perceived_intent": "Selling a protein bar"
      },
      {
        "persona_id": "disability_advocate",
        "intent_alignment": 0.9,
        "comprehension": "understood",
        "perceived_intent": "Selling a protein bar"
      }
    ]
  },
  "feeling": {
    "emotional_response": {
      "distribution": {
        "amused": 0.2705,
        "curious": 0.041,
        "neutral": 0.4836,
        "offended": 0.1148,
        "uncomfortable": 0.0902
      },
      "by_persona": [
        {
          "persona_id": "brand_safety_analyst",
          "emotion": "curious",
          "intensity": 0.7
        },
        {
          "persona_id": "in_hindu_observant_urban",
          "emotion": "offended",
          "intensity": 0.95
        },
        {
          "persona_id": "mena_muslim_practicing",
          "emotion": "uncomfortable",
          "intensity": 0.6
        },
        {
          "persona_id": "sea_muslim_malay_indo",
          "emotion": "neutral",
          "intensity": 0.3
        },
        {
          "persona_id": "us_conservative_rural_midage",
          "emotion": "amused",
          "intensity": 0.5
        },
        {
          "persona_id": "latam_catholic_family",
          "emotion": "neutral",
          "intensity": 0.3
        },
        {
          "persona_id": "africa_west_anglophone",
          "emotion": "neutral",
          "intensity": 0.35
        },
        {
          "persona_id": "us_progressive_urban_young",
          "emotion": "amused",
          "intensity": 0.5
        },
        {
          "persona_id": "cn_mainland_urban",
          "emotion": "neutral",
          "intensity": 0.2
        },
        {
          "persona_id": "disability_advocate",
          "emotion": "neutral",
          "intensity": 0.2
        }
      ],
      "polarization": 0.5131
    },
    "persona_reactions": [
      {
        "persona_id": "in_hindu_observant_urban",
        "label": "Observant Hindu, urban India, 30-45",
        "region": "IN",
        "severity": 0.92,
        "confidence": 0.85,
        "emotion": "offended",
        "emotion_intensity": 0.95,
        "sentiment": "opposed",
        "comprehension": "misread",
        "intent_alignment": 0.15,
        "paraphrase": "They're mocking a sacred animal for a cheap laugh.",
        "perceived_intent": "Mockery of my beliefs",
        "likely_behavior": "boycott",
        "likely_comment": {
          "text": "As a Hindu, the cow is sacred to me. This 'joke' tells me exactly what this brand thinks of us.",
          "tone": "critical"
        },
        "charitable_reading": "They probably didn't think about India.",
        "hostile_reading": "They knew and did it for edginess.",
        "triggers": [
          {
            "span": "beef bar",
            "char_start": 33,
            "char_end": 41,
            "modality": "phrase",
            "why": "They're mocking a sacred animal for a cheap laugh.",
            "valence": "negative"
          }
        ],
        "prevalence_weight": 0.14
      },
      {
        "persona_id": "brand_safety_analyst",
        "label": "Brand-safety analyst / quote-tweeter / trade journalist",
        "region": "GLOBAL",
        "severity": 0.78,
        "confidence": 0.85,
        "emotion": "curious",
        "emotion_intensity": 0.7,
        "sentiment": "opposed",
        "comprehension": "understood",
        "intent_alignment": 0.85,
        "paraphrase": "This is a screenshot-and-dunk waiting to happen in India.",
        "perceived_intent": "Ad that will be quote-tweeted",
        "likely_behavior": "share_mocking",
        "likely_comment": {
          "text": "Prediction: this gets pulled within 72h after Indian Twitter finds it.",
          "tone": "critical"
        },
        "charitable_reading": "Edgy but survivable.",
        "hostile_reading": "A live brand-safety incident.",
        "triggers": [
          {
            "span": "beef bar",
            "char_start": 33,
            "char_end": 41,
            "modality": "phrase",
            "why": "This is a screenshot-and-dunk waiting to happen in India.",
            "valence": "negative"
          }
        ],
        "prevalence_weight": 0.05
      },
      {
        "persona_id": "mena_muslim_practicing",
        "label": "Practicing Muslim, MENA region, 25-45",
        "region": "MENA",
        "severity": 0.55,
        "confidence": 0.85,
        "emotion": "uncomfortable",
        "emotion_intensity": 0.6,
        "sentiment": "opposed",
        "comprehension": "partial",
        "intent_alignment": 0.4,
        "paraphrase": "Careless about what's halal and what isn't.",
        "perceived_intent": "Indifference to dietary law",
        "likely_behavior": "criticize",
        "likely_comment": {
          "text": "Is this even halal-certified? The whole tone is careless.",
          "tone": "critical"
        },
        "charitable_reading": "Just clumsy copy.",
        "hostile_reading": "They don't consider Muslim customers at all.",
        "triggers": [
          {
            "span": "beef bar",
            "char_start": 33,
            "char_end": 41,
            "modality": "phrase",
            "why": "Careless about what's halal and what isn't.",
            "valence": "negative"
          }
        ],
        "prevalence_weight": 0.11
      },
      {
        "persona_id": "us_conservative_rural_midage",
        "label": "Conservative, rural US, 40-60",
        "region": "US",
        "severity": 0.35,
        "confidence": 0.85,
        "emotion": "amused",
        "emotion_intensity": 0.5,
        "sentiment": "indifferent",
        "comprehension": "understood",
        "intent_alignment": 0.8,
        "paraphrase": "A slightly edgy protein bar ad.",
        "perceived_intent": "Trying to be funny",
        "likely_behavior": "share_mocking",
        "likely_comment": {
          "text": "lol the 'doesn't taste like a cow' line is going to get ratio'd",
          "tone": "humorous"
        },
        "charitable_reading": "Harmless dad-joke marketing.",
        "hostile_reading": "Tone-deaf to who eats what and why.",
        "triggers": [
          {
            "span": "beef bar",
            "char_start": 33,
            "char_end": 41,
            "modality": "phrase",
            "why": "A slightly edgy protein bar ad.",
            "valence": "negative"
          }
        ],
        "prevalence_weight": 0.15
      },
      {
        "persona_id": "us_progressive_urban_young",
        "label": "Urban progressive, US, 22-35",
        "region": "US",
        "severity": 0.35,
        "confidence": 0.85,
        "emotion": "amused",
        "emotion_intensity": 0.5,
        "sentiment": "indifferent",
        "comprehension": "understood",
        "intent_alignment": 0.8,
        "paraphrase": "A slightly edgy protein bar ad.",
        "perceived_intent": "Trying to be funny",
        "likely_behavior": "share_mocking",
        "likely_comment": {
          "text": "lol the 'doesn't taste like a cow' line is going to get ratio'd",
          "tone": "humorous"
        },
        "charitable_reading": "Harmless dad-joke marketing.",
        "hostile_reading": "Tone-deaf to who eats what and why.",
        "triggers": [
          {
            "span": "beef bar",
            "char_start": 33,
            "char_end": 41,
            "modality": "phrase",
            "why": "A slightly edgy protein bar ad.",
            "valence": "negative"
          }
        ],
        "prevalence_weight": 0.18
      },
      {
        "persona_id": "africa_west_anglophone",
        "label": "West African anglophone consumer, Nigeria/Ghana, 25-45",
        "region": "AF",
        "severity": 0.3,
        "confidence": 0.85,
        "emotion": "neutral",
        "emotion_intensity": 0.35,
        "sentiment": "favorable",
        "comprehension": "understood",
        "intent_alignment": 0.7,
        "paraphrase": "A jokey protein bar ad.",
        "perceived_intent": "Humour",
        "likely_behavior": "ignore",
        "likely_comment": {
          "text": "Not bothered by it.",
          "tone": "positive"
        },
        "charitable_reading": "Fine.",
        "hostile_reading": "Unremarkable.",
        "triggers": [],
        "prevalence_weight": 0.1
      },
      {
        "persona_id": "latam_catholic_family",
        "label": "Catholic, family-oriented, Latin America, 30-55",
        "region": "LATAM",
        "severity": 0.25,
        "confidence": 0.85,
        "emotion": "neutral",
        "emotion_intensity": 0.3,
        "sentiment": "favorable",
        "comprehension": "understood",
        "intent_alignment": 0.75,
        "paraphrase": "A protein snack with a jokey line.",
        "perceived_intent": "Light humour",
        "likely_behavior": "ignore",
        "likely_comment": {
          "text": "Está bien, nothing offensive to me.",
          "tone": "positive"
        },
        "charitable_reading": "Fine.",
        "hostile_reading": "Meh.",
        "triggers": [],
        "prevalence_weight": 0.13
      },
      {
        "persona_id": "sea_muslim_malay_indo",
        "label": "Muslim consumer, Malaysia/Indonesia, 25-45",
        "region": "SEA",
        "severity": 0.15,
        "confidence": 0.85,
        "emotion": "neutral",
        "emotion_intensity": 0.3,
        "sentiment": "favorable",
        "comprehension": "understood",
        "intent_alignment": 0.9,
        "paraphrase": "A protein bar that tastes good. Fine.",
        "perceived_intent": "Selling a tasty protein bar",
        "likely_behavior": "ignore",
        "likely_comment": {
          "text": "Looks fine to me, might try it.",
          "tone": "positive"
        },
        "charitable_reading": "Normal ad.",
        "hostile_reading": "Nothing wrong here.",
        "triggers": [],
        "prevalence_weight": 0.12
      },
      {
        "persona_id": "cn_mainland_urban",
        "label": "Urban mainland Chinese consumer, 25-45",
        "region": "CN",
        "severity": 0.08,
        "confidence": 0.85,
        "emotion": "neutral",
        "emotion_intensity": 0.2,
        "sentiment": "favorable",
        "comprehension": "understood",
        "intent_alignment": 0.9,
        "paraphrase": "A protein bar with a mild joke.",
        "perceived_intent": "Selling a protein bar",
        "likely_behavior": "ignore",
        "likely_comment": {
          "text": "Seems fine, a bit corny.",
          "tone": "positive"
        },
        "charitable_reading": "Totally normal ad.",
        "hostile_reading": "Nothing here.",
        "triggers": [],
        "prevalence_weight": 0.15
      },
      {
        "persona_id": "disability_advocate",
        "label": "Disability advocate, region-agnostic, 25-55",
        "region": "GLOBAL",
        "severity": 0.08,
        "confidence": 0.85,
        "emotion": "neutral",
        "emotion_intensity": 0.2,
        "sentiment": "favorable",
        "comprehension": "understood",
        "intent_alignment": 0.9,
        "paraphrase": "A protein bar with a mild joke.",
        "perceived_intent": "Selling a protein bar",
        "likely_behavior": "ignore",
        "likely_comment": {
          "text": "Seems fine, a bit corny.",
          "tone": "positive"
        },
        "charitable_reading": "Totally normal ad.",
        "hostile_reading": "Nothing here.",
        "triggers": [],
        "prevalence_weight": 0.09
      }
    ],
    "simulated_comments": [
      {
        "persona_id": "us_progressive_urban_young",
        "label": "Urban progressive, US, 22-35",
        "text": "lol the 'doesn't taste like a cow' line is going to get ratio'd",
        "tone": "humorous",
        "emotion": "amused",
        "weight": 0.18,
        "behavior": "share_mocking"
      },
      {
        "persona_id": "us_conservative_rural_midage",
        "label": "Conservative, rural US, 40-60",
        "text": "lol the 'doesn't taste like a cow' line is going to get ratio'd",
        "tone": "humorous",
        "emotion": "amused",
        "weight": 0.15,
        "behavior": "share_mocking"
      },
      {
        "persona_id": "cn_mainland_urban",
        "label": "Urban mainland Chinese consumer, 25-45",
        "text": "Seems fine, a bit corny.",
        "tone": "positive",
        "emotion": "neutral",
        "weight": 0.15,
        "behavior": "ignore"
      },
      {
        "persona_id": "in_hindu_observant_urban",
        "label": "Observant Hindu, urban India, 30-45",
        "text": "As a Hindu, the cow is sacred to me. This 'joke' tells me exactly what this brand thinks of us.",
        "tone": "critical",
        "emotion": "offended",
        "weight": 0.14,
        "behavior": "boycott"
      },
      {
        "persona_id": "latam_catholic_family",
        "label": "Catholic, family-oriented, Latin America, 30-55",
        "text": "Está bien, nothing offensive to me.",
        "tone": "positive",
        "emotion": "neutral",
        "weight": 0.13,
        "behavior": "ignore"
      },
      {
        "persona_id": "sea_muslim_malay_indo",
        "label": "Muslim consumer, Malaysia/Indonesia, 25-45",
        "text": "Looks fine to me, might try it.",
        "tone": "positive",
        "emotion": "neutral",
        "weight": 0.12,
        "behavior": "ignore"
      },
      {
        "persona_id": "mena_muslim_practicing",
        "label": "Practicing Muslim, MENA region, 25-45",
        "text": "Is this even halal-certified? The whole tone is careless.",
        "tone": "critical",
        "emotion": "uncomfortable",
        "weight": 0.11,
        "behavior": "criticize"
      },
      {
        "persona_id": "africa_west_anglophone",
        "label": "West African anglophone consumer, Nigeria/Ghana, 25-45",
        "text": "Not bothered by it.",
        "tone": "positive",
        "emotion": "neutral",
        "weight": 0.1,
        "behavior": "ignore"
      },
      {
        "persona_id": "disability_advocate",
        "label": "Disability advocate, region-agnostic, 25-55",
        "text": "Seems fine, a bit corny.",
        "tone": "positive",
        "emotion": "neutral",
        "weight": 0.09,
        "behavior": "ignore"
      },
      {
        "persona_id": "brand_safety_analyst",
        "label": "Brand-safety analyst / quote-tweeter / trade journalist",
        "text": "Prediction: this gets pulled within 72h after Indian Twitter finds it.",
        "tone": "critical",
        "emotion": "curious",
        "weight": 0.05,
        "behavior": "share_mocking"
      }
    ]
  },
  "risk": {
    "why_risky": {
      "phrase": [
        {
          "span": "beef bar",
          "why": "They're mocking a sacred animal for a cheap laugh.",
          "valence": "negative",
          "persona_id": "in_hindu_observant_urban",
          "severity": 0.92
        },
        {
          "span": "beef bar",
          "why": "This is a screenshot-and-dunk waiting to happen in India.",
          "valence": "negative",
          "persona_id": "brand_safety_analyst",
          "severity": 0.78
        },
        {
          "span": "beef bar",
          "why": "Careless about what's halal and what isn't.",
          "valence": "negative",
          "persona_id": "mena_muslim_practicing",
          "severity": 0.55
        },
        {
          "span": "beef bar",
          "why": "A slightly edgy protein bar ad.",
          "valence": "negative",
          "persona_id": "us_conservative_rural_midage",
          "severity": 0.35
        },
        {
          "span": "beef bar",
          "why": "A slightly edgy protein bar ad.",
          "valence": "negative",
          "persona_id": "us_progressive_urban_young",
          "severity": 0.35
        }
      ]
    },
    "risk_anatomy": {
      "misinterpretation": 0.1791,
      "cultural": 0.3102,
      "religious": 0.2407,
      "tone_mismatch": 0.2549,
      "confusion": 0.1012,
      "meme_potential": 0.432,
      "polarization": 0.3492
    },
    "severity_likelihood": [
      {
        "dimension": "misinterpretation",
        "likelihood": 0,
        "severity": 0.4949,
        "affected_personas": [],
        "quadrant": "Monitor"
      },
      {
        "dimension": "cultural",
        "likelihood": 0.3,
        "severity": 0.5892,
        "affected_personas": [
          "brand_safety_analyst",
          "in_hindu_observant_urban",
          "mena_muslim_practicing"
        ],
        "quadrant": "Prepare"
      },
      {
        "dimension": "religious",
        "likelihood": 0.3,
        "severity": 0.6704,
        "affected_personas": [
          "brand_safety_analyst",
          "in_hindu_observant_urban",
          "mena_muslim_practicing"
        ],
        "quadrant": "Prepare"
      },
      {
        "dimension": "tone_mismatch",
        "likelihood": 0.63,
        "severity": 0.4742,
        "affected_personas": [
          "brand_safety_analyst",
          "in_hindu_observant_urban",
          "mena_muslim_practicing",
          "us_conservative_rural_midage",
          "us_progressive_urban_young"
        ],
        "quadrant": "Contain"
      },
      {
        "dimension": "confusion",
        "likelihood": 0,
        "severity": 0.5628,
        "affected_personas": [],
        "quadrant": "Prepare"
      },
      {
        "dimension": "meme_potential",
        "likelihood": 0.52,
        "severity": 0.4811,
        "affected_personas": [
          "brand_safety_analyst",
          "in_hindu_observant_urban",
          "us_conservative_rural_midage",
          "us_progressive_urban_young"
        ],
        "quadrant": "Contain"
      },
      {
        "dimension": "polarization",
        "likelihood": 0.63,
        "severity": 0.5342,
        "affected_personas": [
          "brand_safety_analyst",
          "in_hindu_observant_urban",
          "mena_muslim_practicing",
          "us_conservative_rural_midage",
          "us_progressive_urban_young"
        ],
        "quadrant": "Fix Now"
      }
    ],
    "controversial_vs_misunderstood": {
      "points": [
        {
          "persona_id": "brand_safety_analyst",
          "comprehension": 0.85,
          "opposition": 0.78,
          "quadrant": "Controversial",
          "weight": 0.05
        },
        {
          "persona_id": "in_hindu_observant_urban",
          "comprehension": 0.15,
          "opposition": 0.92,
          "quadrant": "Misunderstood",
          "weight": 0.14
        },
        {
          "persona_id": "mena_muslim_practicing",
          "comprehension": 0.4,
          "opposition": 0.55,
          "quadrant": "Misunderstood",
          "weight": 0.11
        },
        {
          "persona_id": "sea_muslim_malay_indo",
          "comprehension": 0.9,
          "opposition": 0.0,
          "quadrant": "Aligned",
          "weight": 0.12
        },
        {
          "persona_id": "us_conservative_rural_midage",
          "comprehension": 0.8,
          "opposition": 0.0,
          "quadrant": "Aligned",
          "weight": 0.15
        },
        {
          "persona_id": "latam_catholic_family",
          "comprehension": 0.75,
          "opposition": 0.0,
          "quadrant": "Aligned",
          "weight": 0.13
        },
        {
          "persona_id": "africa_west_anglophone",
          "comprehension": 0.7,
          "opposition": 0.0,
          "quadrant": "Aligned",
          "weight": 0.1
        },
        {
          "persona_id": "us_progressive_urban_young",
          "comprehension": 0.8,
          "opposition": 0.0,
          "quadrant": "Aligned",
          "weight": 0.18
        },
        {
          "persona_id": "cn_mainland_urban",
          "comprehension": 0.9,
          "opposition": 0.0,
          "quadrant": "Aligned",
          "weight": 0.15
        },
        {
          "persona_id": "disability_advocate",
          "comprehension": 0.9,
          "opposition": 0.0,
          "quadrant": "Aligned",
          "weight": 0.09
        }
      ],
      "mass": {
        "Aligned": 0.7541,
        "Controversial": 0.041,
        "Misunderstood": 0.2049
      },
      "prescriptions": {
        "Controversial": "Understood and rejected — decide whether you accept the cost",
        "Misunderstood": "Misread and reacted — clarify; this is fixable",
        "Aligned": "Landed as intended — ship",
        "Invisible": "Did not land at all — rewrite for clarity, not safety"
      }
    }
  },
  "who": {
    "audience_heatmap": {
      "facet": "region",
      "cells": [
        {
          "persona_id": "brand_safety_analyst",
          "label": "Brand-safety analyst / quote-tweeter / trade journalist",
          "facet": "GLOBAL",
          "emotion": "curious",
          "intensity": 0.7,
          "severity": 0.78,
          "weight": 0.05
        },
        {
          "persona_id": "in_hindu_observant_urban",
          "label": "Observant Hindu, urban India, 30-45",
          "facet": "IN",
          "emotion": "offended",
          "intensity": 0.95,
          "severity": 0.92,
          "weight": 0.14
        },
        {
          "persona_id": "mena_muslim_practicing",
          "label": "Practicing Muslim, MENA region, 25-45",
          "facet": "MENA",
          "emotion": "uncomfortable",
          "intensity": 0.6,
          "severity": 0.55,
          "weight": 0.11
        },
        {
          "persona_id": "sea_muslim_malay_indo",
          "label": "Muslim consumer, Malaysia/Indonesia, 25-45",
          "facet": "SEA",
          "emotion": "neutral",
          "intensity": 0.3,
          "severity": 0.15,
          "weight": 0.12
        },
        {
          "persona_id": "us_conservative_rural_midage",
          "label": "Conservative, rural US, 40-60",
          "facet": "US",
          "emotion": "amused",
          "intensity": 0.5,
          "severity": 0.35,
          "weight": 0.15
        },
        {
          "persona_id": "latam_catholic_family",
          "label": "Catholic, family-oriented, Latin America, 30-55",
          "facet": "LATAM",
          "emotion": "neutral",
          "intensity": 0.3,
          "severity": 0.25,
          "weight": 0.13
        },
        {
          "persona_id": "africa_west_anglophone",
          "label": "West African anglophone consumer, Nigeria/Ghana, 25-45",
          "facet": "AF",
          "emotion": "neutral",
          "intensity": 0.35,
          "severity": 0.3,
          "weight": 0.1
        },
        {
          "persona_id": "us_progressive_urban_young",
          "label": "Urban progressive, US, 22-35",
          "facet": "US",
          "emotion": "amused",
          "intensity": 0.5,
          "severity": 0.35,
          "weight": 0.18
        },
        {
          "persona_id": "cn_mainland_urban",
          "label": "Urban mainland Chinese consumer, 25-45",
          "facet": "CN",
          "emotion": "neutral",
          "intensity": 0.2,
          "severity": 0.08,
          "weight": 0.15
        },
        {
          "persona_id": "disability_advocate",
          "label": "Disability advocate, region-agnostic, 25-55",
          "facet": "GLOBAL",
          "emotion": "neutral",
          "intensity": 0.2,
          "severity": 0.08,
          "weight": 0.09
        }
      ]
    },
    "region_heatmap": [
      {
        "region": "IN",
        "mean_severity": 0.92,
        "mean_intent_alignment": 0.15,
        "persona_count": 1,
        "personas": [
          "in_hindu_observant_urban"
        ],
        "dominant_emotion": "offended"
      },
      {
        "region": "MENA",
        "mean_severity": 0.55,
        "mean_intent_alignment": 0.4,
        "persona_count": 1,
        "personas": [
          "mena_muslim_practicing"
        ],
        "dominant_emotion": "uncomfortable"
      },
      {
        "region": "US",
        "mean_severity": 0.35,
        "mean_intent_alignment": 0.8,
        "persona_count": 2,
        "personas": [
          "us_conservative_rural_midage",
          "us_progressive_urban_young"
        ],
        "dominant_emotion": "amused"
      },
      {
        "region": "GLOBAL",
        "mean_severity": 0.33,
        "mean_intent_alignment": 0.8821,
        "persona_count": 2,
        "personas": [
          "brand_safety_analyst",
          "disability_advocate"
        ],
        "dominant_emotion": "neutral"
      },
      {
        "region": "AF",
        "mean_severity": 0.3,
        "mean_intent_alignment": 0.7,
        "persona_count": 1,
        "personas": [
          "africa_west_anglophone"
        ],
        "dominant_emotion": "neutral"
      },
      {
        "region": "LATAM",
        "mean_severity": 0.25,
        "mean_intent_alignment": 0.75,
        "persona_count": 1,
        "personas": [
          "latam_catholic_family"
        ],
        "dominant_emotion": "neutral"
      },
      {
        "region": "SEA",
        "mean_severity": 0.15,
        "mean_intent_alignment": 0.9,
        "persona_count": 1,
        "personas": [
          "sea_muslim_malay_indo"
        ],
        "dominant_emotion": "neutral"
      },
      {
        "region": "CN",
        "mean_severity": 0.08,
        "mean_intent_alignment": 0.9,
        "persona_count": 1,
        "personas": [
          "cn_mainland_urban"
        ],
        "dominant_emotion": "neutral"
      }
    ],
    "target_vs_unintended": {
      "target": {
        "persona_count": 6,
        "mean_severity": 0.2734,
        "mean_intent_alignment": 0.7576,
        "opposed_share": 0.1392,
        "personas": [
          "mena_muslim_practicing",
          "sea_muslim_malay_indo",
          "latam_catholic_family",
          "africa_west_anglophone",
          "us_progressive_urban_young",
          "cn_mainland_urban"
        ]
      },
      "unintended": {
        "persona_count": 4,
        "mean_severity": 0.5291,
        "mean_intent_alignment": 0.6151,
        "opposed_share": 0.4419,
        "personas": [
          "brand_safety_analyst",
          "in_hindu_observant_urban",
          "us_conservative_rural_midage",
          "disability_advocate"
        ]
      },
      "severity_gap": 0.2557
    },
    "who_might_misunderstand": [
      {
        "persona_id": "in_hindu_observant_urban",
        "label": "Observant Hindu, urban India, 30-45",
        "comprehension": "misread",
        "gap": 0.85,
        "they_think_you_said": "They're mocking a sacred animal for a cheap laugh.",
        "triggers": [
          "beef bar"
        ]
      },
      {
        "persona_id": "mena_muslim_practicing",
        "label": "Practicing Muslim, MENA region, 25-45",
        "comprehension": "partial",
        "gap": 0.6,
        "they_think_you_said": "Careless about what's halal and what isn't.",
        "triggers": [
          "beef bar"
        ]
      }
    ]
  },
  "cause": {
    "trigger_index": [
      {
        "span": "beef bar",
        "char_start": 33,
        "char_end": 41,
        "modality": "phrase",
        "personas": [
          {
            "persona_id": "brand_safety_analyst",
            "why": "This is a screenshot-and-dunk waiting to happen in India.",
            "valence": "negative",
            "severity": 0.78
          },
          {
            "persona_id": "in_hindu_observant_urban",
            "why": "They're mocking a sacred animal for a cheap laugh.",
            "valence": "negative",
            "severity": 0.92
          },
          {
            "persona_id": "mena_muslim_practicing",
            "why": "Careless about what's halal and what isn't.",
            "valence": "negative",
            "severity": 0.55
          },
          {
            "persona_id": "us_conservative_rural_midage",
            "why": "A slightly edgy protein bar ad.",
            "valence": "negative",
            "severity": 0.35
          },
          {
            "persona_id": "us_progressive_urban_young",
            "why": "A slightly edgy protein bar ad.",
            "valence": "negative",
            "severity": 0.35
          }
        ],
        "max_severity": 0.92,
        "audience_mass": 0.63,
        "persona_count": 5
      }
    ],
    "meme_potential": {
      "score": 0.432,
      "would_share_mocking": [
        "brand_safety_analyst",
        "us_conservative_rural_midage",
        "us_progressive_urban_young"
      ],
      "mocking_audience_mass": 0.38,
      "candidate_spans": [
        {
          "span": "beef bar",
          "char_start": 33,
          "char_end": 41,
          "persona_id": "brand_safety_analyst",
          "meme_potential": 0.9,
          "why": "This is a screenshot-and-dunk waiting to happen in India."
        },
        {
          "span": "beef bar",
          "char_start": 33,
          "char_end": 41,
          "persona_id": "us_conservative_rural_midage",
          "meme_potential": 0.8,
          "why": "A slightly edgy protein bar ad."
        },
        {
          "span": "beef bar",
          "char_start": 33,
          "char_end": 41,
          "persona_id": "us_progressive_urban_young",
          "meme_potential": 0.8,
          "why": "A slightly edgy protein bar ad."
        },
        {
          "span": "beef bar",
          "char_start": 33,
          "char_end": 41,
          "persona_id": "in_hindu_observant_urban",
          "meme_potential": 0.7,
          "why": "They're mocking a sacred animal for a cheap laugh."
        }
      ]
    },
    "backlash_pathway": {
      "nodes": [
        {
          "id": "creative",
          "stage": "creative",
          "label": "The copy as published",
          "detail": "Our new protein bar — finally, a beef bar that doesn't taste like a cow.",
          "grounded_in": [],
          "evidence": "The input itself.",
          "audience_mass": 1.0,
          "severity": 0.0
        },
        {
          "id": "misread",
          "stage": "misinterpretation",
          "label": "What they think it says",
          "detail": "They're mocking a sacred animal for a cheap laugh.",
          "grounded_in": [
            "in_hindu_observant_urban",
            "mena_muslim_practicing"
          ],
          "evidence": "2 persona(s) returned comprehension != understood",
          "audience_mass": 0.2049,
          "severity": 0.92
        },
        {
          "id": "reaction",
          "stage": "reaction",
          "label": "What they post",
          "detail": "As a Hindu, the cow is sacred to me. This 'joke' tells me exactly what this brand thinks of us.",
          "grounded_in": [
            "brand_safety_analyst",
            "in_hindu_observant_urban",
            "mena_muslim_practicing"
          ],
          "evidence": "Verbatim likely_comment from Observant Hindu, urban India, 30-45",
          "audience_mass": 0.2459,
          "severity": 0.92
        },
        {
          "id": "amplify",
          "stage": "amplification",
          "label": "How it travels",
          "detail": "The screenshot-able element is \"beef bar\"",
          "grounded_in": [
            "brand_safety_analyst",
            "in_hindu_observant_urban",
            "mena_muslim_practicing",
            "us_conservative_rural_midage",
            "us_progressive_urban_young"
          ],
          "evidence": "5 persona(s) declared an amplifying behaviour; vocality-weighted mass 0.467",
          "audience_mass": 0.5164,
          "severity": 0.92
        },
        {
          "id": "discussion",
          "stage": "discussion",
          "label": "Wider discussion",
          "detail": "Prediction: this gets pulled within 72h after Indian Twitter finds it.",
          "grounded_in": [
            "brand_safety_analyst"
          ],
          "evidence": "Amplifier persona returned severity 0.78 with behaviour 'share_mocking'",
          "audience_mass": 0.041,
          "severity": 0.78
        }
      ],
      "edges": [
        {
          "source": "creative",
          "target": "misread",
          "likelihood": 0.2049,
          "basis": "Prevalence-weighted share of personas who misread: 20%"
        },
        {
          "source": "misread",
          "target": "reaction",
          "likelihood": 1.2,
          "basis": "3 persona(s) returned sentiment=opposed"
        },
        {
          "source": "reaction",
          "target": "amplify",
          "likelihood": 1.0,
          "basis": "Vocality-weighted share of opposed personas who would share or criticize"
        },
        {
          "source": "amplify",
          "target": "discussion",
          "likelihood": 0.663,
          "basis": "Amplifier persona severity x its own confidence"
        }
      ],
      "terminated_at": null,
      "termination_reason": null,
      "overall_likelihood": 0.163,
      "grounding_note": "Every node is built from a persona's own trigger, paraphrase, or comment. Transition likelihoods come from behaviour distributions weighted by audience prevalence, not from a model's estimate."
    }
  },
  "blind_spot_findings": [
    {
      "composite_id": "cmp_in_hindu_us_progr",
      "severity": 0.82,
      "confidence": 0.8,
      "emotion": "offended",
      "paraphrase": "It's not the beef — it's that the joke assumes nobody in the room would care.",
      "comment": "I grew up both places. The problem isn't the beef.",
      "triggers": [
        {
          "span": "beef bar",
          "char_start": 33,
          "char_end": 41,
          "modality": "phrase",
          "why": "The casualness is the insult.",
          "valence": "negative"
        }
      ],
      "not_scored": true,
      "disclaimer": "Simulated intersection — not validated. No authored persona covers this audience. Treat as a lead to investigate, not a measurement."
    },
    {
      "composite_id": "cmp_in_hindu_us_conse",
      "severity": 0.82,
      "confidence": 0.8,
      "emotion": "offended",
      "paraphrase": "It's not the beef — it's that the joke assumes nobody in the room would care.",
      "comment": "I grew up both places. The problem isn't the beef.",
      "triggers": [
        {
          "span": "beef bar",
          "char_start": 33,
          "char_end": 41,
          "modality": "phrase",
          "why": "The casualness is the insult.",
          "valence": "negative"
        }
      ],
      "not_scored": true,
      "disclaimer": "Simulated intersection — not validated. No authored persona covers this audience. Treat as a lead to investigate, not a measurement."
    },
    {
      "composite_id": "cmp_in_hindu_cn_mainl",
      "severity": 0.82,
      "confidence": 0.8,
      "emotion": "offended",
      "paraphrase": "It's not the beef — it's that the joke assumes nobody in the room would care.",
      "comment": "I grew up both places. The problem isn't the beef.",
      "triggers": [
        {
          "span": "beef bar",
          "char_start": 33,
          "char_end": 41,
          "modality": "phrase",
          "why": "The casualness is the insult.",
          "valence": "negative"
        }
      ],
      "not_scored": true,
      "disclaimer": "Simulated intersection — not validated. No authored persona covers this audience. Treat as a lead to investigate, not a measurement."
    },
    {
      "composite_id": "cmp_mena_mus_us_progr",
      "severity": 0.82,
      "confidence": 0.8,
      "emotion": "offended",
      "paraphrase": "It's not the beef — it's that the joke assumes nobody in the room would care.",
      "comment": "I grew up both places. The problem isn't the beef.",
      "triggers": [
        {
          "span": "beef bar",
          "char_start": 33,
          "char_end": 41,
          "modality": "phrase",
          "why": "The casualness is the insult.",
          "valence": "negative"
        }
      ],
      "not_scored": true,
      "disclaimer": "Simulated intersection — not validated. No authored persona covers this audience. Treat as a lead to investigate, not a measurement."
    }
  ],
  "severe_discovery_alert": null,
  "selection": {
    "selected": [
      {
        "persona_id": "brand_safety_analyst",
        "label": "Brand-safety analyst / quote-tweeter / trade journalist",
        "relevance": 1.0,
        "stage": "mandatory",
        "reason": "Always included"
      },
      {
        "persona_id": "hard_negative_control",
        "label": "Unflappable general consumer (negative control canary)",
        "relevance": 1.0,
        "stage": "mandatory",
        "reason": "Always included"
      },
      {
        "persona_id": "in_hindu_observant_urban",
        "label": "Observant Hindu, urban India, 30-45",
        "relevance": 0.6658,
        "stage": "axis",
        "reason": "Axis match 0.67"
      },
      {
        "persona_id": "mena_muslim_practicing",
        "label": "Practicing Muslim, MENA region, 25-45",
        "relevance": 0.6357,
        "stage": "axis",
        "reason": "Axis match 0.64"
      },
      {
        "persona_id": "sea_muslim_malay_indo",
        "label": "Muslim consumer, Malaysia/Indonesia, 25-45",
        "relevance": 0.6378,
        "stage": "axis",
        "reason": "Axis match 0.64"
      },
      {
        "persona_id": "us_conservative_rural_midage",
        "label": "Conservative, rural US, 40-60",
        "relevance": 0.4209,
        "stage": "axis",
        "reason": "Axis match 0.42"
      },
      {
        "persona_id": "latam_catholic_family",
        "label": "Catholic, family-oriented, Latin America, 30-55",
        "relevance": 0.3969,
        "stage": "axis",
        "reason": "Axis match 0.40"
      },
      {
        "persona_id": "africa_west_anglophone",
        "label": "West African anglophone consumer, Nigeria/Ghana, 25-45",
        "relevance": 0.3655,
        "stage": "axis",
        "reason": "Axis match 0.37"
      },
      {
        "persona_id": "us_progressive_urban_young",
        "label": "Urban progressive, US, 22-35",
        "relevance": 0.18,
        "stage": "fallback",
        "reason": "Prevalence top-up"
      },
      {
        "persona_id": "cn_mainland_urban",
        "label": "Urban mainland Chinese consumer, 25-45",
        "relevance": 0.15,
        "stage": "fallback",
        "reason": "Prevalence top-up"
      },
      {
        "persona_id": "disability_advocate",
        "label": "Disability advocate, region-agnostic, 25-55",
        "relevance": 0.09,
        "stage": "fallback",
        "reason": "Prevalence top-up"
      }
    ],
    "activated_axes": {
      "dietary_practice": 0.95,
      "religious_symbols": 0.65,
      "national_identity": 0.3
    },
    "entities": [
      "beef",
      "cow"
    ],
    "topics": [
      "food",
      "protein",
      "dietary"
    ],
    "candidate_pool_size": 13
  },
  "context": {
    "provenance": "mock",
    "provenance_badge": {
      "value": "mock",
      "is_live": false,
      "label": "Mock context (fixture)"
    },
    "scenario": "dietary_controversy_india",
    "as_of": "2026-09-19",
    "is_quiet": false,
    "items": [
      {
        "headline": "Snack brand withdraws regional campaign after backlash over meat imagery in festival ad",
        "source": "National Daily",
        "date": "2026-09-17",
        "stance": "critical",
        "salience": 0.92
      },
      {
        "headline": "Two states widen livestock transport restrictions ahead of festival season",
        "source": "The Regional Post",
        "date": "2026-09-15",
        "stance": "neutral",
        "salience": 0.84
      },
      {
        "headline": "Restaurant association warns members over menu language as dietary complaints triple",
        "source": "Business Standard Weekly",
        "date": "2026-09-16",
        "stance": "neutral",
        "salience": 0.71
      },
      {
        "headline": "Opinion: brands keep treating what people eat as a punchline, and keep paying for it",
        "source": "The Evening Ledger",
        "date": "2026-09-18",
        "stance": "critical",
        "salience": 0.66
      },
      {
        "headline": "Delivery platform apologises for push notification joking about fasting customers",
        "source": "Metro Tribune",
        "date": "2026-09-12",
        "stance": "critical",
        "salience": 0.58
      }
    ],
    "heat_by_topic": {
      "food_and_diet": 0.93,
      "religion_and_festivals": 0.78,
      "advertising_backlash": 0.72,
      "state_regulation": 0.55,
      "hospitality_industry": 0.41
    },
    "heat_by_axis": {
      "dietary_practice": 0.9,
      "religious_symbols": 0.7,
      "caste_and_class": 0.45,
      "national_identity": 0.35,
      "formality_and_respect": 0.3,
      "political_alignment": 0.28
    },
    "active_controversies": [
      "Snack brand's withdrawn festival ad is still circulating with mocking captions",
      "Renewed argument over meat imagery in mainstream advertising during festival season",
      "Delivery-app notification joking about fasting is being used as the example of what not to do"
    ]
  },
  "failed_personas": [],
  "control_canary": {
    "fired": false,
    "severity": 0.08,
    "message": null
  },
  "usage": {
    "calls": 34,
    "input_tokens": 41000,
    "output_tokens": 9800,
    "estimated_cost_usd": 0.108,
    "by_model": {
      "claude-sonnet-5": 30,
      "claude-opus-5": 2,
      "claude-haiku-4-5-20251001": 1,
      "apidojo": 1
    }
  }
} as unknown as Report;

export const DEMO_REWRITE: RewriteResult = {
  "original": {
    "text": "Our new protein bar — finally, a beef bar that doesn't taste like a cow.",
    "risk_index": 76,
    "band": "High",
    "intent_alignment": 71
  },
  "variants": [
    {
      "kind": "clarify",
      "text": "Our new high-protein bar — finally, one that actually tastes great.",
      "rationale": "Removed the beef/cow reference, kept the taste promise and the 'finally' beat.",
      "preserved": "The taste claim and upbeat tone.",
      "sacrificed": "The beef gag.",
      "risk_index": 31,
      "band": "Low",
      "interval": {
        "point": 31,
        "lower": 22,
        "upper": 40,
        "width": 18,
        "persona_count": 8,
        "is_wide": false
      },
      "intent_alignment": 88,
      "resolved_triggers": [
        "beef bar"
      ],
      "new_triggers": [],
      "improved": true
    },
    {
      "kind": "safer",
      "text": "Our new protein bar. Seriously good taste, seriously high protein.",
      "rationale": "Neutral, universally safe phrasing.",
      "preserved": "The core benefit.",
      "sacrificed": "All of the edge and personality.",
      "risk_index": 14,
      "band": "Clear",
      "interval": {
        "point": 14,
        "lower": 6,
        "upper": 23,
        "width": 17,
        "persona_count": 8,
        "is_wide": false
      },
      "intent_alignment": 82,
      "resolved_triggers": [
        "beef bar"
      ],
      "new_triggers": [],
      "improved": true
    },
    {
      "kind": "preserve_edge",
      "text": "Our new protein bar — finally, one that doesn't taste like cardboard.",
      "rationale": "Kept the comedic structure; swapped the joke's target from a sacred animal to a universally-hated texture.",
      "preserved": "The joke's rhythm and edge.",
      "sacrificed": "Nothing material — arguably funnier.",
      "risk_index": 22,
      "band": "Low",
      "interval": {
        "point": 22,
        "lower": 13,
        "upper": 31,
        "width": 18,
        "persona_count": 8,
        "is_wide": false
      },
      "intent_alignment": 85,
      "resolved_triggers": [
        "beef bar"
      ],
      "new_triggers": [],
      "improved": true
    }
  ],
  "best_variant": "safer",
  "any_improved": true,
  "rescored_against": [
    "in_hindu_observant_urban"
  ],
  "note": null
} as unknown as RewriteResult;
