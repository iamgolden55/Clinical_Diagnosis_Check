# Clinical Diagnosis Check

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.13-green.svg)
![Framework](https://img.shields.io/badge/framework-Django%20+%20React-purple.svg)

## 🩺 Overview

Clinical Diagnosis Check is an advanced healthcare AI system that bridges the gap between unstructured patient communications and structured medical data. The system uses Bio_ClinicalBERT, a specialized clinical language model, alongside pattern-based approaches to identify medical entities, analyze patient emotions, and generate structured clinical summaries for healthcare professionals.

![System Overview](https://i.imgur.com/HDGnM7i.png)

## ✨ Key Features

- **Medical Entity Recognition**: Automatically extracts medications, symptoms, conditions, and vital signs from patient text
- **Attribute Detection**: Identifies severity, duration, and other contextual information about medical entities
- **Emotion Analysis**: Analyzes patient emotional state to enable more empathetic communication
- **Clinical Summary Generation**: Creates structured summaries for healthcare providers
- **Hybrid Approach**: Combines neural networks with pattern-matching for optimal accuracy and performance

## 🏗️ System Architecture

The system consists of:

1. **Frontend**: React-based UI for patient-doctor communication
2. **Backend**: Django REST API for processing requests and managing data
3. **NLP Pipeline**:
   - Medical Entity Recognition with Bio_ClinicalBERT
   - Emotion analysis using a pre-trained emotion classification model
   - Pattern-based entity extraction for medications, symptoms, conditions
4. **LLM Integration**: OpenAI GPT models for generating conversational responses and clinical summaries
5. **Database**: Storage for conversation history and extracted medical entities

## 🔧 Technologies Used

- **Django**: Backend API framework
- **React**: Frontend interface
- **Bio_ClinicalBERT**: Domain-specific language model fine-tuned on clinical text
- **Hugging Face Transformers**: For NLP and ML model implementation
- **LangChain**: For conversational AI integration
- **OpenAI API**: For advanced language model capabilities
- **Regular Expressions**: For pattern-based entity extraction

## 🚀 Installation

### Prerequisites
- Python 3.13+
- Node.js 16+
- Django 5.2+
- React 18+

### Backend Setup
```bash
# Clone the repository
git clone https://github.com/iamgolden55/Clinical_Diagnosis_Check.git
cd Clinical_Diagnosis_Check

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
pip install -r requirements.txt

# Apply migrations
cd backend
python manage.py migrate

# Start Django server
python manage.py runserver
```

### Frontend Setup
```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
npm install

# Start the development server
npm start
```

## 📊 Example Usage

### Patient Input:
```
I have been suffering from severe migraines for the past 2 weeks. They started after I changed my blood pressure medication from lisinopril 10mg to amlodipine 5mg daily. I have hypertension diagnosed 3 years ago. The pain is usually a throbbing sensation on the right side of my head, and it gets worse with light and noise. My most recent blood pressure reading was 145/85 yesterday.
```

### System Output:
```json
{
  "MEDICATION": ["lisinopril", "amlodipine", "10mg", "5mg"],
  "SYMPTOM": ["pain", "past 2 weeks"],
  "SEVERITY": ["worse"],
  "DURATION": ["past 2 weeks", "3 years ago"],
  "CONDITION": ["hypertension"],
  "VITALS": ["145", "85"]
}
```

## 📄 Documentation

For complete documentation, see [healthcare_ai_documentation.md](healthcare_ai_documentation.md) which includes:

- Detailed implementation explanation
- Medical entity recognition techniques
- Bio_ClinicalBERT integration
- System workflow diagrams
- API documentation
- Use cases and examples

## 🔮 Future Enhancements

- **Relation Extraction**: Identify relationships between medical entities
- **Temporal Reasoning**: Enhance understanding of symptom progression over time
- **Medical Knowledge Graph Integration**: Connect entities to standardized medical ontologies
- **Multi-modal Understanding**: Process images, wearable data, and voice
- **Fine-tuned Model Variants**: Create specialized versions for different medical domains

## 🧪 Testing

```bash
# Run backend tests
cd backend
python manage.py test

# Run frontend tests
cd ../frontend
npm test
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🙏 Acknowledgements

- [Emily Alsentzer](https://github.com/EmilyAlsentzer) for Bio_ClinicalBERT
- The Hugging Face team for Transformers library
- OpenAI for GPT models
- Django and React communities

## 📬 Contact

For questions and feedback, please open an issue on GitHub or contact the repository owner.
