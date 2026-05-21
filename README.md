# LinguaDuo Backend

A real-time multilingual chat backend built with Django, Channels, and WebSockets. Every message is automatically translated into each recipient's preferred language — so people can chat naturally without a language barrier.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.2 + Django REST Framework |
| Real-time | Django Channels + Daphne (ASGI) |
| Database | PostgreSQL (Neon) |
| Cache / WebSocket layer | Redis (Upstash) |
| Translation | Google Cloud Translation API v2 (with unofficial + MyMemory fallbacks) |
| Auth | JWT (SimpleJWT) |
| Deployment | Render (Free tier, Oregon US West) |

---

## Features

- Real-time group and direct message chat via WebSockets
- Per-user language preference — every message translated on delivery
- 130+ supported languages
- Group chat with admin roles (add/remove members, promote admins)
- JWT authentication
- Translation caching — avoids re-translating the same message twice
- Graceful fallback chain: Official Google API → Unofficial Google → MyMemory

---

## Project Structure

```
linguaduo-backend/
├── backend/
│   ├── settings.py
│   ├── asgi.py
│   └── urls.py
├── chat/
│   ├── consumers.py       # WebSocket consumers
│   ├── translation.py     # Translation logic + fallbacks
│   ├── models.py          # Message, Group, Translation models
│   ├── views.py           # REST API views
│   ├── urls.py
│   └── routing.py         # WebSocket URL routing
├── accounts/              # User auth, registration, language preference
├── requirements.txt
├── manage.py
└── render.yaml
```

---

## Local Setup

### Prerequisites
- Python 3.11+
- PostgreSQL database
- Redis instance

### Steps

```bash
# Clone the repo
git clone https://github.com/SanaAdeelKhan/linguaduo-backend.git
cd linguaduo-backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Fill in your values (see Environment Variables below)

# Run migrations
python manage.py migrate

# Start the server
daphne -b 0.0.0.0 -p 8000 backend.asgi:application
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your_django_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=postgresql://user:password@host/dbname
REDIS_URL=redis://your_redis_url

GOOGLE_TRANSLATE_API_KEY=your_google_cloud_api_key
```

### Render Environment Variables
Add the same variables in your Render dashboard under **Environment** tab. The `GOOGLE_TRANSLATE_API_KEY` is especially important — without it, the app falls back to the unofficial API.

---

## Translation Logic

Translation lives in `chat/translation.py` and works as follows:

1. When a message is sent, it is stored with the sender's original language
2. When a recipient fetches or receives the message via WebSocket, it is translated into their `preferred_language`
3. Translations are cached in the `Translation` model to avoid redundant API calls
4. Fallback chain: **Official Google API** → **Unofficial Google** → **MyMemory**

---

## API Overview

| Endpoint | Method | Description |
|---|---|---|
| `/api/auth/register/` | POST | Register new user |
| `/api/auth/login/` | POST | Obtain JWT tokens |
| `/api/chat/conversations/` | GET | List DMs and groups |
| `/api/chat/groups/` | POST | Create a group |
| `/api/chat/groups/:id/members/` | GET | List group members |
| `/api/chat/groups/:id/add-member/` | POST | Add member (admin only) |
| `/api/chat/groups/:id/remove-member/:uid/` | DELETE | Remove member (admin only) |
| `/api/chat/users/` | GET | List all users |

### WebSocket

```
ws://your-domain/ws/chat/{room_name}/?token=<JWT>
```

Room name format: `dm_{user_id}` or `group_{group_id}`

---

## Deployment (Render)

The app is deployed on Render using Daphne as the ASGI server.

**Start command:**
```
daphne -b 0.0.0.0 -p $PORT backend.asgi:application
```

**Build command:**
```
pip install -r requirements.txt
```

Live URL: `https://linguaduo-backend.onrender.com`

---

## Contributing

Pull requests are welcome! For major changes, open an issue first to discuss what you'd like to change.

---

## License

MIT License — feel free to use, modify, and distribute.

---

*Built with ❤️ by Sana Adeel Khan — LinguaDuo: Chat without language barriers.*
