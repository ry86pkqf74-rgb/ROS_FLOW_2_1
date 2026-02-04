export const syntheticStudyData = {
  study: {
    title: "Synthetic Clinical Trial for E2E Testing",
    type: "randomized_controlled_trial",
    hypothesis: "Treatment X improves outcome Y compared to placebo",
    pi_name: "Dr. Test Researcher",
    institution: "Test University"
  },
  config: {
    governance_mode: "DEMO",
    phi_mode: "SYNTHETIC",
    seed: 42,
    deterministic: true
  },
  dataset: {
    name: "synthetic_trial_data.csv",
    participants: 100,
    variables: [
      { name: "participant_id", type: "string" },
      { name: "age", type: "number", min: 18, max: 85 },
      { name: "treatment_group", type: "categorical", values: ["treatment", "placebo"] },
      { name: "baseline_score", type: "number", min: 0, max: 100 },
      { name: "final_score", type: "number", min: 0, max: 100 },
      { name: "adverse_events", type: "number", min: 0, max: 5 }
    ]
  }
};

export const expectedOutputs = {
  stage_03: ["irb_application_draft.docx", "consent_form_template.docx"],
  stage_12: ["manuscript_draft.md", "abstract.md"],
  stage_15: ["artifact_bundle.zip", "manifest.json"],
  stage_19: ["submission_package.zip"],
  stage_20: ["conference_slides.pptx", "poster.pdf"]
};
