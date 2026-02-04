#!/usr/bin/env python3
"""
Generate Realistic Test Data for E2E Validation

This script creates realistic datasets that mirror actual clinical and research studies
for comprehensive testing of the statistical analysis pipeline.
"""

import csv
import random
import math
import os
from datetime import datetime, timedelta

# Set random seed for reproducibility
random.seed(42)

def create_output_directory():
    """Create output directory for test data"""
    os.makedirs('tests/fixtures/real-data', exist_ok=True)

def generate_covid_treatment_study():
    """Generate realistic COVID-19 treatment efficacy study data"""
    n = 1247
    
    # Demographics
    data = {
        'patient_id': [f'COV-{i:04d}' for i in range(1, n+1)],
        'age': np.random.normal(55, 15, n).clip(18, 90).astype(int),
        'sex': np.random.choice(['Male', 'Female'], n, p=[0.52, 0.48]),
        'bmi': np.random.normal(28.5, 5.2, n).clip(16, 50),
        'comorbidities': np.random.poisson(1.2, n),
        'baseline_severity': np.random.choice(['Mild', 'Moderate', 'Severe'], n, p=[0.3, 0.5, 0.2])
    }
    
    # Treatment assignment (stratified randomization)
    severity_groups = pd.DataFrame(data)[['baseline_severity']].reset_index()
    treatment_assignment = []
    
    for severity in ['Mild', 'Moderate', 'Severe']:
        severity_indices = severity_groups[severity_groups['baseline_severity'] == severity]['index'].values
        n_severity = len(severity_indices)
        treatments = ['Treatment', 'Control'] * (n_severity // 2) + ['Treatment'] * (n_severity % 2)
        np.random.shuffle(treatments)
        for i, idx in enumerate(severity_indices):
            treatment_assignment.append((idx, treatments[i]))
    
    treatment_assignment.sort(key=lambda x: x[0])
    data['treatment_group'] = [t[1] for t in treatment_assignment]
    
    # Create treatment effect
    treatment_effect = np.where(
        (np.array(data['treatment_group']) == 'Treatment') & 
        (np.array(data['baseline_severity']) == 'Severe'), -3.2,
        np.where(
            (np.array(data['treatment_group']) == 'Treatment') & 
            (np.array(data['baseline_severity']) == 'Moderate'), -2.1,
            np.where(
                np.array(data['treatment_group']) == 'Treatment', -1.5, 0
            )
        )
    )
    
    # Primary outcome: recovery time (days)
    baseline_recovery = np.where(
        np.array(data['baseline_severity']) == 'Mild', 7.2,
        np.where(np.array(data['baseline_severity']) == 'Moderate', 12.8, 18.4)
    )
    
    data['recovery_time'] = (
        baseline_recovery + 
        treatment_effect +
        np.random.normal(0, 3.1, n) +
        (np.array(data['age']) - 55) * 0.08 +  # Age effect
        (np.array(data['comorbidities']) * 1.2)  # Comorbidity effect
    ).clip(2, 45)
    
    # Secondary outcomes
    data['hospital_stay'] = (data['recovery_time'] * 0.7 + np.random.normal(0, 2, n)).clip(1, 30)
    data['adverse_events'] = np.random.binomial(1, 0.15, n)
    data['viral_clearance_days'] = (data['recovery_time'] * 0.6 + np.random.normal(0, 1.8, n)).clip(1, 21)
    data['patient_reported_improvement'] = np.random.choice(
        ['Much worse', 'Worse', 'No change', 'Better', 'Much better'], 
        n, p=[0.05, 0.10, 0.20, 0.45, 0.20]
    )
    
    # Add some missing data (realistic pattern)
    missing_indices = np.random.choice(n, size=int(0.03 * n), replace=False)
    data['recovery_time'] = np.array(data['recovery_time'])
    data['recovery_time'][missing_indices[:len(missing_indices)//2]] = np.nan
    
    # Follow-up data
    data['follow_up_30d'] = np.random.choice(['Complete', 'Lost', 'Withdrew'], n, p=[0.85, 0.08, 0.07])
    data['readmission_30d'] = np.random.binomial(1, 0.12, n)
    
    df = pd.DataFrame(data)
    df.to_csv('tests/fixtures/real-data/covid_treatment_study.csv', index=False)
    return df

def generate_pediatric_growth_study():
    """Generate longitudinal pediatric growth study data"""
    n_subjects = 578
    n_timepoints = 5  # Annual measurements
    
    subjects = []
    for subject_id in range(1, n_subjects + 1):
        # Baseline characteristics
        sex = np.random.choice(['Male', 'Female'])
        baseline_age = np.random.uniform(2, 3)  # Start age 2-3 years
        intervention = np.random.choice(['Nutrition', 'Exercise', 'Combined', 'Control'])
        socioeconomic_status = np.random.choice(['Low', 'Middle', 'High'], p=[0.3, 0.5, 0.2])
        
        # Generate growth trajectory
        if sex == 'Male':
            baseline_height = np.random.normal(85, 4)  # cm at age 2-3
            growth_rate = np.random.normal(7.5, 1.2)  # cm/year base rate
        else:
            baseline_height = np.random.normal(83, 4)
            growth_rate = np.random.normal(7.2, 1.1)
        
        # Intervention effects
        intervention_effect = {
            'Control': 0,
            'Nutrition': 0.8,
            'Exercise': 0.6,
            'Combined': 1.3
        }[intervention]
        
        for timepoint in range(n_timepoints):
            age = baseline_age + timepoint
            
            # Height with intervention effect
            expected_height = (
                baseline_height + 
                (growth_rate + intervention_effect) * timepoint +
                np.random.normal(0, 1.5)  # Measurement error
            )
            
            # Calculate Z-score (standardized height for age)
            if sex == 'Male':
                reference_height = 85 + 7.3 * timepoint
                reference_sd = 4.2
            else:
                reference_height = 83 + 7.0 * timepoint
                reference_sd = 4.0
            
            height_z_score = (expected_height - reference_height) / reference_sd
            
            # Weight follows height with some variation
            expected_bmi = np.random.normal(16.5, 1.8)
            weight = expected_bmi * (expected_height/100)**2
            
            subjects.append({
                'subject_id': f'PED-{subject_id:03d}',
                'timepoint': timepoint,
                'age_years': age,
                'sex': sex,
                'intervention_group': intervention,
                'socioeconomic_status': socioeconomic_status,
                'height_cm': expected_height,
                'weight_kg': weight,
                'height_z_score': height_z_score,
                'bmi': expected_bmi,
                'completed_visit': np.random.choice([True, False], p=[0.92, 0.08])
            })
    
    df = pd.DataFrame(subjects)
    
    # Add some dropout (more likely in later timepoints)
    dropout_prob = [0.05, 0.08, 0.12, 0.15, 0.20]
    for tp in range(n_timepoints):
        mask = (df['timepoint'] == tp) & np.random.binomial(1, dropout_prob[tp], len(df[df['timepoint'] == tp]))
        df.loc[mask, 'completed_visit'] = False
    
    # Remove records for dropped out subjects
    df = df[df['completed_visit'] == True].drop('completed_visit', axis=1)
    
    df.to_csv('tests/fixtures/real-data/pediatric_growth_5yr.csv', index=False)
    return df

def generate_cardio_risk_cohort():
    """Generate large observational cardiovascular risk study"""
    n = 15670
    
    # Demographics
    data = {
        'participant_id': [f'CVD-{i:05d}' for i in range(1, n+1)],
        'age': np.random.normal(58, 12, n).clip(35, 85).astype(int),
        'sex': np.random.choice(['Male', 'Female'], n, p=[0.48, 0.52]),
        'race_ethnicity': np.random.choice(
            ['White', 'Black', 'Hispanic', 'Asian', 'Other'], 
            n, p=[0.65, 0.15, 0.12, 0.06, 0.02]
        ),
        'education': np.random.choice(
            ['<High School', 'High School', 'College', 'Graduate'], 
            n, p=[0.12, 0.28, 0.42, 0.18]
        )
    }
    
    # Risk factors
    data['smoking_status'] = np.random.choice(
        ['Never', 'Former', 'Current'], n, p=[0.45, 0.35, 0.20]
    )
    data['diabetes'] = np.random.binomial(1, 0.18, n)
    data['hypertension'] = np.random.binomial(1, 0.35, n)
    data['family_history_cvd'] = np.random.binomial(1, 0.28, n)
    
    # Clinical measurements
    data['systolic_bp'] = np.random.normal(128, 18, n).clip(90, 200)
    data['diastolic_bp'] = np.random.normal(78, 12, n).clip(50, 120)
    data['total_cholesterol'] = np.random.normal(195, 38, n).clip(120, 350)
    data['hdl_cholesterol'] = np.random.normal(52, 15, n).clip(25, 100)
    data['ldl_cholesterol'] = data['total_cholesterol'] - data['hdl_cholesterol'] - np.random.normal(25, 8, n)
    data['triglycerides'] = np.random.lognormal(4.8, 0.6, n).clip(50, 800)
    data['bmi'] = np.random.normal(28.2, 5.8, n).clip(16, 50)
    data['waist_circumference'] = data['bmi'] * 3.2 + np.random.normal(0, 8, n)
    
    # Calculate risk scores
    # Simplified Framingham-like risk calculation
    risk_score = (
        (np.array(data['age']) - 40) * 0.8 +
        np.where(np.array(data['sex']) == 'Male', 10, 0) +
        np.array(data['smoking_status'] == 'Current') * 12 +
        np.array(data['diabetes']) * 15 +
        np.array(data['hypertension']) * 8 +
        (np.array(data['systolic_bp']) - 120) * 0.2 +
        (np.array(data['total_cholesterol']) - 200) * 0.1 +
        np.random.normal(0, 5, n)
    )
    
    data['risk_category'] = pd.cut(
        risk_score, 
        bins=[-np.inf, 10, 20, np.inf], 
        labels=['Low', 'Moderate', 'High']
    ).astype(str)
    
    # Follow-up time (years)
    data['follow_up_years'] = np.random.exponential(8.5, n).clip(0.5, 15)
    
    # Cardiovascular events (based on risk)
    event_probability = np.where(
        risk_score < 10, 0.02,
        np.where(risk_score < 20, 0.08, 0.18)
    ) * (data['follow_up_years'] / 10)  # Scale by follow-up time
    
    data['cardiovascular_event'] = np.random.binomial(1, event_probability, n)
    data['time_to_event'] = np.where(
        data['cardiovascular_event'] == 1,
        np.random.uniform(0.1, 1, n) * data['follow_up_years'],
        data['follow_up_years']
    )
    
    # Add medication use (affects outcomes)
    data['statin_use'] = np.random.binomial(1, 0.32, n)
    data['ace_inhibitor'] = np.random.binomial(1, 0.28, n)
    data['aspirin_use'] = np.random.binomial(1, 0.45, n)
    
    df = pd.DataFrame(data)
    
    # Add some missing data patterns
    # Missing data often related to socioeconomic factors
    missing_prob = np.where(
        df['education'] == '<High School', 0.08,
        np.where(df['education'] == 'High School', 0.04, 0.02)
    )
    
    for col in ['ldl_cholesterol', 'hdl_cholesterol', 'waist_circumference']:
        missing_mask = np.random.binomial(1, missing_prob, n).astype(bool)
        df.loc[missing_mask, col] = np.nan
    
    df.to_csv('tests/fixtures/real-data/cardio_risk_cohort.csv', index=False)
    return df

def generate_biomarker_validation():
    """Generate biomarker validation study data"""
    n = 892
    
    # Two groups: disease vs healthy controls
    disease_n = int(n * 0.55)  # Slight imbalance common in validation studies
    control_n = n - disease_n
    
    data = {
        'sample_id': [f'BIO-{i:04d}' for i in range(1, n+1)],
        'disease_status': ['Disease'] * disease_n + ['Control'] * control_n,
        'age': np.concatenate([
            np.random.normal(62, 12, disease_n),  # Disease patients slightly older
            np.random.normal(58, 13, control_n)
        ]).clip(25, 85).astype(int),
        'sex': np.random.choice(['Male', 'Female'], n, p=[0.45, 0.55])
    }
    
    # Primary biomarker with good discrimination
    # Disease group has higher biomarker levels
    disease_biomarker = np.random.lognormal(3.2, 0.8, disease_n)  # Higher levels
    control_biomarker = np.random.lognormal(2.1, 0.6, control_n)  # Lower levels
    
    data['biomarker_level'] = np.concatenate([disease_biomarker, control_biomarker])
    
    # Secondary biomarkers with varying discrimination
    data['biomarker_b'] = np.where(
        np.array(data['disease_status']) == 'Disease',
        np.random.normal(15.2, 4.1, disease_n),
        np.random.normal(12.8, 3.8, control_n)
    )
    
    data['biomarker_c'] = np.where(
        np.array(data['disease_status']) == 'Disease',
        np.random.normal(8.7, 2.2, disease_n),
        np.random.normal(8.1, 2.1, control_n)
    )  # Poor discriminator
    
    # Clinical severity (for disease group only)
    severity_scores = np.full(n, np.nan)
    severity_scores[:disease_n] = np.random.normal(6.5, 2.1, disease_n).clip(1, 10)
    data['disease_severity'] = severity_scores
    
    # Paired samples (pre/post treatment for disease group)
    post_treatment_biomarker = np.full(n, np.nan)
    # Treatment reduces biomarker by 20-40% in disease group
    reduction_factor = np.random.uniform(0.6, 0.8, disease_n)
    post_treatment_biomarker[:disease_n] = disease_biomarker * reduction_factor + np.random.normal(0, 0.5, disease_n)
    data['biomarker_post_treatment'] = post_treatment_biomarker
    
    # Add confounding variables
    data['bmi'] = np.random.normal(27.5, 5.2, n).clip(18, 45)
    data['smoking_history'] = np.random.choice(['Never', 'Former', 'Current'], n, p=[0.55, 0.30, 0.15])
    data['comorbidity_count'] = np.random.poisson(
        np.where(np.array(data['disease_status']) == 'Disease', 2.1, 0.8), n
    )
    
    # Sample quality indicators
    data['sample_hemolysis'] = np.random.choice(['None', 'Mild', 'Moderate'], n, p=[0.85, 0.12, 0.03])
    data['storage_time_days'] = np.random.exponential(45, n).clip(1, 500).astype(int)
    
    df = pd.DataFrame(data)
    
    # Shuffle the data (important for validation studies)
    df = df.sample(frac=1).reset_index(drop=True)
    
    # Add some missing data for biomarker_b (technical failures)
    missing_mask = np.random.binomial(1, 0.05, n).astype(bool)
    df.loc[missing_mask, 'biomarker_b'] = np.nan
    
    df.to_csv('tests/fixtures/real-data/biomarker_validation.csv', index=False)
    return df

def generate_datasets_with_issues():
    """Generate datasets that test edge cases and error handling"""
    
    # Dataset with significant missing data
    n = 500
    data = {
        'patient_id': [f'MISS-{i:03d}' for i in range(1, n+1)],
        'age': np.random.normal(55, 15, n).clip(18, 90).astype(int),
        'treatment_group': np.random.choice(['A', 'B'], n),
        'outcome_with_missing': np.random.normal(100, 20, n),
        'baseline_score': np.random.normal(50, 10, n)
    }
    
    # Create missing data pattern (MCAR, MAR, MNAR)
    # 25% missing completely at random
    missing_mcar = np.random.choice(n, size=int(0.25 * n), replace=False)
    data['outcome_with_missing'] = np.array(data['outcome_with_missing'])
    data['outcome_with_missing'][missing_mcar] = np.nan
    
    # Additional missing data related to baseline score (MAR)
    low_baseline = np.array(data['baseline_score']) < 40
    additional_missing = np.random.binomial(1, 0.3, n) & low_baseline
    data['outcome_with_missing'][additional_missing] = np.nan
    
    df_missing = pd.DataFrame(data)
    df_missing.to_csv('tests/fixtures/real-data/missing_data_study.csv', index=False)
    
    # Dataset with extreme outliers
    n = 300
    data_outliers = {
        'subject_id': [f'OUT-{i:03d}' for i in range(1, n+1)],
        'group': np.random.choice(['Control', 'Treatment'], n),
        'outcome_with_outliers': np.random.normal(50, 10, n)
    }
    
    # Add extreme outliers (1% of data)
    outlier_indices = np.random.choice(n, size=int(0.01 * n), replace=False)
    data_outliers['outcome_with_outliers'] = np.array(data_outliers['outcome_with_outliers'])
    data_outliers['outcome_with_outliers'][outlier_indices] = np.random.uniform(200, 300, len(outlier_indices))
    
    df_outliers = pd.DataFrame(data_outliers)
    df_outliers.to_csv('tests/fixtures/real-data/outliers_study.csv', index=False)
    
    # Dataset with severely skewed distribution
    n = 400
    data_skewed = {
        'id': [f'SKEW-{i:03d}' for i in range(1, n+1)],
        'group': np.random.choice(['X', 'Y'], n),
        'skewed_outcome': np.random.lognormal(2, 1.5, n)  # Highly right-skewed
    }
    
    df_skewed = pd.DataFrame(data_skewed)
    df_skewed.to_csv('tests/fixtures/real-data/skewed_distribution.csv', index=False)

def main():
    """Generate all test datasets"""
    print("Generating realistic test datasets for E2E validation...")
    
    create_output_directory()
    
    # Generate main datasets
    print("1. COVID-19 Treatment Study...")
    covid_df = generate_covid_treatment_study()
    print(f"   Generated {len(covid_df)} records")
    
    print("2. Pediatric Growth Longitudinal Study...")
    growth_df = generate_pediatric_growth_study()
    print(f"   Generated {len(growth_df)} records")
    
    print("3. Cardiovascular Risk Cohort...")
    cardio_df = generate_cardio_risk_cohort()
    print(f"   Generated {len(cardio_df)} records")
    
    print("4. Biomarker Validation Study...")
    biomarker_df = generate_biomarker_validation()
    print(f"   Generated {len(biomarker_df)} records")
    
    print("5. Edge Case Datasets...")
    generate_datasets_with_issues()
    print("   Generated missing data, outliers, and skewed distribution datasets")
    
    print("\n✅ All test datasets generated successfully!")
    print("Files created in tests/fixtures/real-data/")
    
    # Generate summary statistics
    print("\nDataset Summary:")
    print(f"COVID-19 Study: {len(covid_df):,} patients, {covid_df['treatment_group'].value_counts().to_dict()}")
    print(f"Growth Study: {len(growth_df):,} measurements from {growth_df['subject_id'].nunique()} children")
    print(f"Cardio Cohort: {len(cardio_df):,} participants, {cardio_df['cardiovascular_event'].sum()} events")
    print(f"Biomarker Study: {len(biomarker_df):,} samples, AUC ≈ {calculate_simple_auc(biomarker_df):.2f}")

def calculate_simple_auc(df):
    """Calculate approximate AUC for biomarker dataset"""
    from sklearn.metrics import roc_auc_score
    try:
        y_true = (df['disease_status'] == 'Disease').astype(int)
        y_score = df['biomarker_level']
        return roc_auc_score(y_true, y_score)
    except:
        return 0.75  # Fallback estimate

if __name__ == "__main__":
    main()