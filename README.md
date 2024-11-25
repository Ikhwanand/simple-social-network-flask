# Social Network Web Application

A Flask-based social network application with MongoDB integration.

## Features

- User authentication (login/signup)
- User profiles with avatars
- Post creation with image support
- Like and comment on posts
- Follow/unfollow users
- Real-time feed updates
- Responsive design

## Tech Stack

- Python 3.x
- Flask
- MongoDB
- Flask-Login
- HTML/CSS
- JavaScript

## Setup

1. Clone the repository:
```bash
git clone <your-repository-url>
cd <repository-name>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables in `.env`:
```
MONGODB_URI=your_mongodb_connection_string
SECRET_KEY=your_secret_key
```

4. Run the application:
```bash
python app.py
```

## Deployment

This application can be deployed on platforms like:
- Render
- Heroku
- DigitalOcean
- AWS

Make sure to set the appropriate environment variables on your deployment platform.
