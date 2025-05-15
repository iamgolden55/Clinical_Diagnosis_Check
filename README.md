# EleraAI Healthcare Voice Assistant

EleraAI Healthcare Voice Assistant is an advanced healthcare AI system that allows real-time voice conversations with patients, supporting multiple languages including Nigerian Pidgin, Yoruba, and Igbo.

## Project Structure

The project consists of two main components:

1. **Backend**: Django-based API server with LLM integration
2. **Frontend**: React-based UI for web interface with voice capabilities

## Features

- Real-time voice conversations using LiveKit
- Automatic speech recognition with OpenAI Whisper API
- Natural-sounding speech synthesis with ElevenLabs
- Multi-language support including Nigerian Pidgin, Yoruba, and Igbo
- Persistence of conversation history and transcripts
- Medical knowledge base integration
- Toggle between text and voice modes
- Visual indicators for speech activity

## Backend Setup

### Prerequisites

- Python 3.11+
- Django 5.2+
- PostgreSQL or SQLite
- LiveKit account (for real-time communications)
- OpenAI API key (for transcription)
- ElevenLabs API key (for voice synthesis)

### Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/EleraAI.git
cd EleraAI
```

2. Set up Python virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create environment variables file (`.env`) in the backend directory with the following:
```
# Django
SECRET_KEY=your_secret_key
DEBUG=True

# APIs
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# LiveKit
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Start the development server:
```bash
python manage.py runserver
```

## Frontend Setup

### Prerequisites

- Node.js 16+
- npm or yarn

### Installation

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create `.env` file with configuration:
```
REACT_APP_BACKEND_URL=http://localhost:8000
```

3. Start the development server:
```bash
npm start
```

## Using the Application

1. Start both backend and frontend servers following the setup instructions above
2. Open your browser to http://localhost:3000
3. You'll see the main interface with two modes:
   - **Text Mode**: Traditional text-based chat interface
   - **Voice Mode**: Real-time voice conversation with the AI assistant

### Voice Mode Features

- **Language Selection**: Choose from English, Nigerian Pidgin, Yoruba, or Igbo
- **Speak Button**: Click to start/stop speaking
- **Audio Controls**: Adjust microphone settings with the audio select button
- **Live Transcript**: See real-time transcriptions of your speech
- **Visual Indicators**: Shows when the assistant is speaking

## API Documentation

### Voice Service API Endpoints

#### LiveKit Token Generation
- POST `/voice/token/`
  - Request: `{ "conversation_id": "string", "user_identity": "string", "user_name": "string" }`
  - Response: `{ "token": "string", "room_name": "string", "livekit_url": "string", "voice_session_id": "number", "participant_id": "number" }`

#### Voice Session Management
- GET `/voice/sessions/` - List all active voice sessions
- GET `/voice/sessions/{id}/` - Get details of a specific voice session
- POST `/voice/sessions/` - Create a new voice session
- PUT `/voice/sessions/{id}/` - Update a voice session
- DELETE `/voice/sessions/{id}/` - Deactivate a voice session

#### Participants
- GET `/voice/sessions/{session_id}/participants/` - List all participants in a session
- GET `/voice/sessions/{session_id}/participants/{id}/` - Get details of a specific participant
- POST `/voice/sessions/{session_id}/participants/` - Add a participant to a session
- PUT `/voice/sessions/{session_id}/participants/{id}/` - Update a participant
- DELETE `/voice/sessions/{session_id}/participants/{id}/` - Mark a participant as inactive

#### Speech-to-Text
- POST `/voice/transcribe/`
  - Request: Multipart form with `voice_session_id`, `participant_id` (optional), `language` (optional), and `audio` file
  - Response: `{ "transcript": "string", "confidence": "number", "language": "string", "transcript_id": "number" }`

#### Text-to-Speech
- POST `/voice/synthesize/`
  - Request: `{ "voice_session_id": "number", "text": "string", "language_code": "string", "voice_id": "string" (optional) }`
  - Response: Audio file (MP3)

## LiveKit Integration

This project uses LiveKit for real-time voice communication. The backend serves as a token server and manages the rooms and participants, while the frontend uses the LiveKit SDK to establish WebRTC connections.

### Room Management

Rooms are automatically created when a new conversation is started. The room name is based on the conversation ID to ensure continuity.

### Token Generation

Tokens are generated with the appropriate permissions based on the user's role. The token includes the room name, user identity, and permissions to publish and subscribe to audio.

## Voice Processing

### Speech Recognition

The OpenAI Whisper API is used for speech recognition. The system supports multiple languages and automatically detects the language if not specified.

### Text-to-Speech Synthesis

ElevenLabs API is used for high-quality text-to-speech synthesis. Different voices are used based on the language of the text.

## Technical Implementation

The voice conversation system uses the following technologies and approaches:

1. **Frontend**: React with TypeScript, LiveKit WebRTC components
2. **Backend**: Django REST Framework, LiveKit server SDK
3. **Voice Processing**:
   - Client-side audio recording using MediaRecorder API
   - Server-side transcription with OpenAI Whisper
   - Natural speech generation with ElevenLabs
4. **Real-time Communication**: WebRTC through LiveKit

## Troubleshooting

- **Microphone Issues**: Make sure to grant microphone permissions in your browser
- **Connection Problems**: Check that both backend and frontend servers are running
- **Voice Not Working**: Verify your API keys for LiveKit, OpenAI, and ElevenLabs are correct

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

- OpenAI for Whisper API
- ElevenLabs for voice synthesis
- LiveKit for real-time communications
