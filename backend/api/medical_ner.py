from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
import logging
import re

logger = logging.getLogger(__name__)

# Initialize the medical NER pipeline
# Note: This will download the model on first use
def get_medical_ner_pipeline():
    try:
        # We'll use a Hugging Face pipeline for NER with Bio_ClinicalBERT as the base model
        # Since Bio_ClinicalBERT itself isn't specifically an NER model,
        # we're implementing a hybrid approach with regex patterns as fallback
        model_name = "emilyalsentzer/Bio_ClinicalBERT"
        logger.info(f"Using {model_name} for embedding medical text")
        
        # Return a pipeline that extracts entities
        # For the actual NER, we'll mostly rely on our regex-based approach
        # But we'll load the model to have its embeddings available for future improvements
        
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            # Just load the base model - we'll use it for embeddings, not direct NER
            _ = pipeline("feature-extraction", model=model_name, tokenizer=tokenizer)
            logger.info(f"Successfully loaded {model_name} model")
        except Exception as inner_e:
            logger.warning(f"Could not load full feature pipeline: {str(inner_e)}. Using regex fallback only.")
        
        # Always return True to indicate we're ready to extract with regex methods
        return True
    except Exception as e:
        logger.error(f"Error loading medical NER model: {str(e)}")
        # Return True anyway to use regex fallback
        return True

# Extract medical entities from patient text
def extract_medical_entities(text):
    try:
        # First initialize the model (or fall back to regex if model fails)
        get_medical_ner_pipeline()
        
        # Extract medications using regex
        medications = extract_medications(text)
        
        # Initialize the medical entities dictionary
        medical_entities = {}
        
        if medications:
            medical_entities["MEDICATION"] = medications
        
        # Add symptom detection with attributes
        symptoms = extract_symptoms(text)
        if symptoms:
            medical_entities["SYMPTOM"] = symptoms
            
            # Extract severity and duration as additional attributes
            severities = extract_severity(text)
            if severities:
                medical_entities["SEVERITY"] = severities
                
            durations = extract_duration(text)
            if durations:
                medical_entities["DURATION"] = durations
            
        # Add condition detection
        conditions = extract_conditions(text)
        if conditions:
            medical_entities["CONDITION"] = conditions
        
        # Extract vital signs if present
        vitals = extract_vitals(text)
        if vitals:
            medical_entities["VITALS"] = vitals
        
        return medical_entities
    except Exception as e:
        logger.error(f"Error extracting medical entities: {str(e)}")
        return {}

# Extract severity information
def extract_severity(text):
    try:
        severity_patterns = [
            # Severity with symptoms
            r'\b(mild|moderate|severe|extreme|excruciating) (pain|discomfort|fever|headache|cough|symptoms?)\b',
            r'\b(slight|significant|unbearable|manageable) (pain|discomfort|symptom)\b',
            # Pain scales
            r'\bpain (?:level|scale|score)? (?:of )?(\d+)(?: ?\/? ?\d+)?\b',
            r'\b(\d+)(?: ?\/? ?\d+)? (?:on|out of) (?:a |the )?pain (?:scale|level)\b',
            # General severity words
            r'\b(worsen(?:ing|ed)?|improv(?:ing|ed)?|better|worse|unchanged|intolerable)\b'
        ]
        
        severities = []
        text_lower = text.lower()
        
        for pattern in severity_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                severity = match.group(0)
                if severity not in severities:
                    severities.append(severity)
        
        return severities
    except Exception as e:
        logger.error(f"Error extracting severities: {str(e)}")
        return []

# Extract duration information
def extract_duration(text):
    try:
        duration_patterns = [
            # Time periods
            r'\b(for|since|over the last|past) \d+ (hours?|days?|weeks?|months?|years?)\b',
            r'\bstarted \d+ (hours?|days?|weeks?|months?|years?) ago\b',
            r'\b\d+ (hours?|days?|weeks?|months?|years?) (ago|duration|episode|history)\b',
            # Qualitative duration
            r'\b(chronic|acute|persistent|intermittent|constant|occasional|recurring|episodic)\b',
            # Since specific time
            r'\bsince (yesterday|this morning|last night|last week|last month)\b',
            # Other time patterns
            r'\b(comes and goes|on and off|all the time|constantly)\b'
        ]
        
        durations = []
        text_lower = text.lower()
        
        for pattern in duration_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                duration = match.group(0)
                if duration not in durations:
                    durations.append(duration)
        
        return durations
    except Exception as e:
        logger.error(f"Error extracting durations: {str(e)}")
        return []

# Extract vital signs
def extract_vitals(text):
    try:
        vital_patterns = [
            # Blood pressure
            r'\bBP\s*(?:of|is|was)?\s*(\d{2,3}\/\d{2,3})\b',
            r'\bblood pressure\s*(?:of|is|was)?\s*(\d{2,3}\/\d{2,3})\b',
            r'\bsystolic\s*(?:of|is|was)?\s*(\d{2,3})\b',
            r'\bdiastolic\s*(?:of|is|was)?\s*(\d{2,3})\b',
            # Heart rate
            r'\bHR\s*(?:of|is|was)?\s*(\d{2,3})\b',
            r'\bheart rate\s*(?:of|is|was)?\s*(\d{2,3})\b',
            r'\bpulse\s*(?:of|is|was)?\s*(\d{2,3})\b',
            # Temperature
            r'\btemp\s*(?:of|is|was)?\s*(\d{2,3}(?:\.\d)?)\s*[FC]?\b',
            r'\btemperature\s*(?:of|is|was)?\s*(\d{2,3}(?:\.\d)?)\s*[FC]?\b',
            r'\bfever\s*(?:of|is|was)?\s*(\d{2,3}(?:\.\d)?)\s*[FC]?\b',
            # Respiratory rate
            r'\bRR\s*(?:of|is|was)?\s*(\d{1,2})\b',
            r'\brespiratory rate\s*(?:of|is|was)?\s*(\d{1,2})\b',
            # Oxygen saturation
            r'\bO2 sat\s*(?:of|is|was)?\s*(\d{1,3})%?\b',
            r'\boxygen saturation\s*(?:of|is|was)?\s*(\d{1,3})%?\b',
            r'\bSpO2\s*(?:of|is|was)?\s*(\d{1,3})%?\b',
            # Blood glucose
            r'\bglucose\s*(?:of|is|was)?\s*(\d{2,4})\b',
            r'\bblood sugar\s*(?:of|is|was)?\s*(\d{2,4})\b',
            # Weight
            r'\bweight\s*(?:of|is|was)?\s*(\d{2,3}(?:\.\d)?)\s*(?:kg|lbs?)?\b',
            # Height
            r'\bheight\s*(?:of|is|was)?\s*(\d{1,3}(?:\.\d)?)\s*(?:cm|m|ft|inches)?\b',
            r'\b(\d{1}[\'\"]?\d{1,2}[\"\']?)\s*(?:cm|m|ft|inches|tall|height)?\b'
        ]
        
        vitals = []
        text_lower = text.lower()
        
        for pattern in vital_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                vital = match.group(0)
                if vital not in vitals:
                    vitals.append(vital)
        
        return vitals
    except Exception as e:
        logger.error(f"Error extracting vitals: {str(e)}")
        return []

# Initialize the emotion analysis pipeline
def get_emotion_pipeline():
    try:
        # Pre-trained emotion detection model
        return pipeline("text-classification", model="bhadresh-savani/distilbert-base-uncased-emotion")
    except Exception as e:
        logger.error(f"Error loading emotion model: {str(e)}")
        # Return a fallback function
        return lambda text: [{"label": "unknown", "score": 1.0}]

# Analyze patient emotion
def analyze_patient_emotion(text):
    try:
        # Add minimum length threshold to avoid misclassifications on short messages
        MIN_TEXT_LENGTH = 5  # Skip emotion detection for very short messages
        MIN_CONFIDENCE = 0.5  # Minimum confidence threshold for emotion detection
        
        if len(text.strip()) < MIN_TEXT_LENGTH:
            # Skip emotion analysis for greetings and very short messages
            return {"emotion": "unknown", "confidence": 0.0}
            
        emotion_classifier = get_emotion_pipeline()
        result = emotion_classifier(text)
        
        # Return the primary emotion and its confidence score
        emotion = result[0]
        
        # Only return a valid emotion if confidence is above threshold
        if emotion["score"] < MIN_CONFIDENCE:
            return {"emotion": "unknown", "confidence": emotion["score"]}
            
        return {
            "emotion": emotion["label"],
            "confidence": emotion["score"]
        }
    except Exception as e:
        logger.error(f"Error analyzing patient emotion: {str(e)}")
        return {"emotion": "unknown", "confidence": 0.0}

# Extract medications using regex patterns
def extract_medications(text):
    try:
        # Common medication names and patterns
        common_meds = [
            # Common over-the-counter medications
            r'\b(advil|tylenol|aspirin|ibuprofen|acetaminophen|paracetamol|naproxen|aleve)\b',
            # Common prescription medications
            r'\b(lisinopril|atorvastatin|metformin|levothyroxine|amlodipine|metoprolol|omeprazole)\b',
            r'\b(simvastatin|losartan|gabapentin|hydrochlorothiazide|sertraline|montelukast)\b',
            r'\b(pantoprazole|furosemide|fluticasone|escitalopram|amoxicillin|azithromycin)\b',
            r'\b(prednisone|fluoxetine|albuterol|citalopram|tamsulosin|rosuvastatin)\b',
            r'\b(warfarin|tramadol|bupropion|clopidogrel|carvedilol|hydrocodone)\b',
            # Medication classes and forms
            r'\b(insulin|ventolin|albuterol|inhaler|epipen|antibiotic|antihistamine)\b',
            r'\b(steroid|statin|beta.?blocker|calcium.?channel.?blocker|ace.?inhibitor|arb)\b',
            r'\b(ssri|snri|antidepressant|antipsychotic|antianxiety|sleeping.?pill)\b',
            r'\b(blood.?thinner|anticoagulant|pain.?killer|nsaid|opioid|narcotic)\b',
            # Dosage patterns
            r'\b\d+\s*mg\b',
            r'\b\d+\s*mcg\b',
            r'\b\d+\s*ml\b',
            r'\b\d+\s*tablets?\b',
            r'\b\d+\s*doses?\b',
            r'\b\d+\s*pills?\b',
            # Frequency patterns
            r'\b(once|twice|three times) (daily|a day)\b',
            r'\bq\d+h\b',  # medical shorthand like q8h (every 8 hours)
            r'\b(every|each) \d+ (hours?|days?|weeks?)\b',
            r'\b(in the|at) (morning|night|evening|afternoon)\b'
        ]
        
        medications = []
        for pattern in common_meds:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                med = match.group(0)
                if med not in medications:
                    medications.append(med)
        
        return medications
    except Exception as e:
        logger.error(f"Error extracting medications: {str(e)}")
        return []

# Extract symptoms using keyword matching
def extract_symptoms(text):
    try:
        symptoms_list = [
            # General symptoms
            r'\b(headache|migraine|pain|ache|fever|cough|nausea|vomiting|dizziness|fatigue|tired)\b',
            # Specific pains
            r'\b(chest pain|back pain|throat pain|stomach pain|abdominal pain|joint pain)\b',
            # Respiratory
            r'\b(shortness of breath|difficulty breathing|wheezing|phlegm|congestion)\b',
            r'\b(runny nose|stuffy nose|sore throat|hoarse voice|dry cough|wet cough)\b',
            # Digestive
            r'\b(diarrhea|constipation|indigestion|heartburn|bloating|gas)\b',
            r'\b(stomach ache|abdominal cramping|bloody stool|black stool|nausea|vomiting)\b',
            # Neurological
            r'\b(numbness|tingling|weakness|confusion|memory loss|seizure)\b',
            r'\b(dizziness|fainting|lightheaded|vertigo|headache|migraine|concussion)\b',
            # Cardiovascular
            r'\b(palpitations|irregular heartbeat|fast heart rate|slow heart rate)\b',
            r'\b(chest tightness|shortness of breath|cyanosis|edema|swelling)\b',
            # Skin
            r'\b(rash|swelling|bleeding|bruising|itching|lump|bump)\b',
            r'\b(hives|welts|blisters|redness|scaling|peeling)\b',
            # Sensory
            r'\b(blurry vision|double vision|hearing loss|ringing in ears)\b',
            r'\b(eye pain|ear pain|loss of taste|loss of smell)\b',
            # Sleep
            r'\b(insomnia|trouble sleeping|sleep apnea|snoring)\b',
            r'\b(nightmares|night sweats|restless leg|teeth grinding)\b',
            # Mental Health
            r'\b(anxiety|depression|panic attack|stress|mood swings)\b',
            r'\b(irritability|difficulty concentrating|racing thoughts)\b',
            # Severity patterns
            r'\b(mild|moderate|severe|extreme|excruciating) (pain|discomfort|fever|headache|cough)\b',
            r'\b(slight|significant|unbearable|manageable) (pain|discomfort|symptom)\b',
            # Duration patterns
            r'\b(for|since|over the last|past) \d+ (hours?|days?|weeks?|months?|years?)\b',
            r'\b(chronic|acute|persistent|intermittent|constant|occasional)\b',
            r'\bstarted \d+ (hours?|days?|weeks?|months?) ago\b'
        ]
        
        symptoms = []
        text_lower = text.lower()
        
        for pattern in symptoms_list:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                symptom = match.group(0)
                if symptom not in symptoms:
                    symptoms.append(symptom)
        
        return symptoms
    except Exception as e:
        logger.error(f"Error extracting symptoms: {str(e)}")
        return []

# Extract medical conditions
def extract_conditions(text):
    try:
        conditions_list = [
            # Common chronic conditions
            r'\b(diabetes|hypertension|high blood pressure|asthma|copd|cancer)\b',
            r'\b(arthritis|depression|anxiety|insomnia|allergies|migraine)\b',
            r'\b(heart disease|heart attack|stroke|seizure|epilepsy)\b',
            # Chronic conditions
            r'\b(chronic pain|chronic fatigue|fibromyalgia|lupus|ms|multiple sclerosis)\b',
            r'\b(osteoporosis|parkinson|alzheimer|dementia|hypothyroidism|hyperthyroidism)\b',
            # Infections
            r'\b(infection|pneumonia|bronchitis|sinusitis|flu|influenza|cold)\b',
            r'\b(uti|urinary tract infection|strep throat|viral infection|bacterial infection)\b',
            r'\b(covid|coronavirus|covid-19|mono|mononucleosis|lyme disease)\b',
            # Digestive conditions
            r'\b(gerd|acid reflux|ibs|irritable bowel|crohn|ulcerative colitis|celiac)\b',
            r'\b(gallstones|diverticulitis|pancreatitis|hepatitis|cirrhosis|gastritis)\b',
            # Skin conditions
            r'\b(eczema|psoriasis|rosacea|acne|dermatitis|shingles|hives)\b',
            # Respiratory conditions
            r'\b(asthma|copd|emphysema|bronchitis|sleep apnea|pulmonary fibrosis)\b',
            # Cardiovascular conditions
            r'\b(hypertension|high blood pressure|afib|atrial fibrillation|coronary artery disease|arrhythmia)\b',
            r'\b(tachycardia|bradycardia|heart failure|congestive heart failure|aneurysm)\b',
            # Endocrine
            r'\b(thyroid|hypothyroidism|hyperthyroidism|diabetes|type 1|type 2|cushings|addisons)\b',
            # Mental health
            r'\b(depression|anxiety|bipolar|schizophrenia|ocd|ptsd|adhd|add)\b',
            # Other
            r'\b(anemia|kidney disease|liver disease|osteoporosis)\b',
            r'\b(glaucoma|cataracts|macular degeneration|retinopathy)\b'
        ]
        
        conditions = []
        text_lower = text.lower()
        
        for pattern in conditions_list:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                condition = match.group(0)
                if condition not in conditions:
                    conditions.append(condition)
        
        return conditions
    except Exception as e:
        logger.error(f"Error extracting conditions: {str(e)}")
        return [] 