import pandas as pd
from typing import List, Dict
from app.models.patient import PatientInput
from app.models.responses import STOPPFlag

class STOPPStartEngine:
    def __init__(self, stopp_df: pd.DataFrame, start_df: pd.DataFrame):
        self.stopp_df = stopp_df
        self.start_df = start_df

    def check_stopp_criteria(self, patient: PatientInput) -> List[STOPPFlag]:
        """Check STOPP v2 criteria - medications to avoid/stop"""
        flags = []

        for med in patient.medications:
            drug_lower = med.generic_name.lower()

            # Check each STOPP criterion
            for _, criterion in self.stopp_df.iterrows():
                if self._matches_drug(drug_lower, criterion['drug_class']):
                    if self._matches_condition(patient, criterion['condition']):
                        flags.append(STOPPFlag(
                            rule_id=criterion['criterion_id'],
                            drug_medication=med.generic_name,
                            condition_disease=criterion['condition'],
                            rationale=criterion['rationale'],
                            full_text=f"{criterion['criterion']} - Action: {criterion['action']}"
                        ))

        return flags

    def check_start_criteria(self, patient: PatientInput) -> List[Dict]:
        """Check START v2 criteria - potentially beneficial medications missing"""
        recommendations = []

        # Get list of current medications (lowercase)
        current_meds = [m.generic_name.lower() for m in patient.medications]

        for _, criterion in self.start_df.iterrows():
            # Check if patient meets the condition for this START criterion
            if self._matches_condition(patient, criterion['condition']):
                # Check if patient is NOT already on this medication class
                if not self._already_on_medication(current_meds, criterion['drug_class']):
                    recommendations.append({
                        'criterion_id': criterion['criterion_id'],
                        'system': criterion['system'],
                        'criterion': criterion['criterion'],
                        'drug_class': criterion['drug_class'],
                        'condition': criterion['condition'],
                        'indication': criterion['indication'],
                        'recommendation': criterion['recommendation'],
                        'evidence': criterion['evidence']
                    })

        return recommendations

    def _matches_drug(self, drug_name: str, drug_class_pattern: str) -> bool:
        """Check if drug matches the drug class pattern"""
        drug_lower = drug_name.lower()
        pattern_lower = drug_class_pattern.lower()

        # Direct substring match
        if drug_lower in pattern_lower or pattern_lower in drug_lower:
            return True

        # Common drug class mappings
        drug_mappings = {
            'benzodiazepine': ['alprazolam', 'lorazepam', 'diazepam', 'clonazepam', 'temazepam'],
            'z-drug': ['zolpidem', 'zopiclone', 'eszopiclone'],
            'nsaid': ['ibuprofen', 'naproxen', 'diclofenac', 'celecoxib', 'meloxicam'],
            'ppi': ['omeprazole', 'esomeprazole', 'lansoprazole', 'pantoprazole'],
            'ssri': ['fluoxetine', 'sertraline', 'paroxetine', 'citalopram', 'escitalopram'],
            'tricyclic': ['amitriptyline', 'nortriptyline', 'imipramine', 'doxepin'],
            'antihistamine': ['diphenhydramine', 'chlorpheniramine', 'hydroxyzine'],
            'digoxin': ['digoxin'],
            'thiazide': ['hydrochlorothiazide', 'chlorthalidone'],
            'loop diuretic': ['furosemide', 'torsemide', 'bumetanide'],
            'statin': ['atorvastatin', 'simvastatin', 'rosuvastatin', 'pravastatin'],
            'anticoagulant': ['warfarin', 'apixaban', 'rivaroxaban', 'dabigatran'],
            'antiplatelet': ['aspirin', 'clopidogrel'],
            'acei': ['lisinopril', 'enalapril', 'ramipril'],
            'arb': ['losartan', 'valsartan', 'irbesartan'],
            'beta-blocker': ['metoprolol', 'atenolol', 'bisoprolol', 'carvedilol']
        }

        for drug_class, medications in drug_mappings.items():
            if drug_class in pattern_lower:
                if any(med in drug_lower for med in medications):
                    return True
            if drug_lower in medications:
                if drug_class in pattern_lower:
                    return True

        return False

    def _matches_condition(self, patient: PatientInput, criterion_condition: str) -> bool:
        """Check if patient meets the condition criteria"""
        condition_lower = criterion_condition.lower()

        # Check comorbidities
        for condition in patient.comorbidities:
            condition_norm = condition.lower().strip()
            if condition_norm in condition_lower or condition_lower in condition_norm:
                return True

        # Check age-related conditions
        if 'age' in condition_lower:
            if '≥65' in condition_lower or '>= 65' in condition_lower or '>65' in condition_lower:
                return patient.age >= 65
            elif '≥85' in condition_lower or '>= 85' in condition_lower:
                return patient.age >= 85

        # Check for specific blood pressure conditions
        if 'sbp' in condition_lower or 'systolic' in condition_lower:
            if '>160' in condition_lower:
                return True  # Would need actual BP data

        # Check for diabetes
        if 'diabetes' in condition_lower:
            return 'Diabetes' in patient.comorbidities or 'diabetes' in [c.lower() for c in patient.comorbidities]

        # Check for hypertension
        if 'hypertension' in condition_lower:
            return 'Hypertension' in patient.comorbidities or 'hypertension' in [c.lower() for c in patient.comorbidities]

        # Check for heart conditions
        if 'heart failure' in condition_lower:
            return 'Heart failure' in patient.comorbidities or 'heart failure' in [c.lower() for c in patient.comorbidities]

        # Check for dementia
        if 'dementia' in condition_lower:
            return 'Dementia' in patient.comorbidities or 'dementia' in [c.lower() for c in patient.comorbidities]

        return False

    def _already_on_medication(self, current_medications: List[str], drug_class: str) -> bool:
        """Check if patient is already on medication from this class"""
        for med in current_medications:
            if self._matches_drug(med, drug_class):
                return True
        return False
