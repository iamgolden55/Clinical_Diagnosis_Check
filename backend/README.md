# Healthcare AI Backend

## Setup

1. Make sure you have Python 3.10+ installed
2. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```
3. Create a `.env` file in the backend directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
   Get an API key from [OpenAI Platform](https://platform.openai.com/account/api-keys)

4. Start the development server:
   ```
   python manage.py runserver
   ```

## API Endpoints

- **POST /api/chat/**
  - Request: `{ "message": "User message here", "session_id": "optional_session_id" }`
  - Response: `{ "reply": "AI assistant reply", "session_id": "session_id" }`

- **POST /api/chat/summary/**
  - Request: `{ "session_id": "existing_session_id" }`
  - Response: `{ "summary": "Clinical summary for doctor", "session_id": "session_id" }`

- **GET /api/tasks/** - List all tasks
- **POST /api/tasks/** - Create a new task
- **GET /api/tasks/{id}/** - Retrieve a task
- **PUT /api/tasks/{id}/** - Update a task
- **DELETE /api/tasks/{id}/** - Delete a task 