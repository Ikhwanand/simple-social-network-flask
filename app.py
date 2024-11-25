from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from bson import ObjectId
from datetime import datetime
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MongoDB setup
password = os.environ.get('MONGODB_PASSWORD')
encoded_password = quote_plus(password)
MONGODB_URI = f"mongodb+srv://xokent:{encoded_password}@cluster0.pjrei.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGODB_URI)
db = client.social_app

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'avatars'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'posts'), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# User class with additional fields
class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data
        self.id = str(user_data['_id'])
        self.username = user_data.get('username', '')
        self.email = user_data.get('email', '')
        self.avatar = user_data.get('avatar', 'default.jpg')
        self.bio = user_data.get('bio', '')
        self.following = user_data.get('following', [])
        self.followers = user_data.get('followers', [])
        self.created_at = user_data.get('created_at', datetime.utcnow())

    def get_id(self):
        return self.id

    def get_following_count(self):
        return len(self.following) if self.following else 0

    def get_followers_count(self):
        return len(self.followers) if self.followers else 0

    def follow(self, user_id):
        if user_id not in self.following and user_id != self.id:
            db.accounts.update_one(
                {'_id': ObjectId(self.id)},
                {'$push': {'following': user_id}}
            )
            db.accounts.update_one(
                {'_id': ObjectId(user_id)},
                {'$push': {'followers': self.id}}
            )
            return True
        return False

    def unfollow(self, user_id):
        if user_id in self.following:
            db.accounts.update_one(
                {'_id': ObjectId(self.id)},
                {'$pull': {'following': user_id}}
            )
            db.accounts.update_one(
                {'_id': ObjectId(user_id)},
                {'$pull': {'followers': self.id}}
            )
            return True
        return False

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    user_data = db.accounts.find_one({'_id': ObjectId(user_id)})
    return User(user_data) if user_data else None

# Routes for existing functionality (login, signup, etc.) remain the same
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        if db.accounts.find_one({'email': email}):
            flash('Email already registered', 'error')
            return render_template('signup.html')
        
        # Hash the password before storing
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password  # Store the hashed password
        }
        
        result = db.accounts.insert_one(user_data)
        user = User(db.accounts.find_one({'_id': ObjectId(str(result.inserted_id))}))
        login_user(user)
        flash('Successfully registered!', 'success')
        return redirect(url_for('home'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user_data = db.accounts.find_one({'email': email})
        
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))

# New route for user profile
@app.route('/profile/<username>')
def profile(username):
    user_data = db.accounts.find_one({'username': username})
    if user_data:
        profile_user = User(user_data)
        posts = list(db.posts.find({'user_id': str(user_data['_id'])}).sort('created_at', -1))
        return render_template('profile.html', 
                             user=profile_user, 
                             posts=posts,
                             followers_count=profile_user.get_followers_count(),
                             following_count=profile_user.get_following_count())
    flash('User not found', 'error')
    return redirect(url_for('home'))

# Route for editing profile
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        bio = request.form.get('bio', '')
        avatar = request.files.get('avatar')
        
        update_data = {'bio': bio}
        
        if avatar and allowed_file(avatar.filename):
            filename = secure_filename(f"{current_user.id}_{avatar.filename}")
            avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars', filename)
            avatar.save(avatar_path)
            update_data['avatar'] = f"avatars/{filename}"
        
        db.accounts.update_one(
            {'_id': ObjectId(current_user.id)},
            {'$set': update_data}
        )
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile', username=current_user.username))
    
    return render_template('edit_profile.html')

# Route for creating posts
@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content')
    image = request.files.get('image')
    
    post_data = {
        'user_id': current_user.id,
        'username': current_user.username,
        'content': content,
        'created_at': datetime.utcnow(),
        'likes': [],
        'comments': []
    }
    
    if image and allowed_file(image.filename):
        filename = secure_filename(f"{datetime.utcnow().timestamp()}_{image.filename}")
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'posts', filename)
        image.save(image_path)
        post_data['image'] = f"posts/{filename}"
    
    db.posts.insert_one(post_data)
    flash('Post created successfully!', 'success')
    return redirect(url_for('home'))

# Route for liking/unliking posts
@app.route('/like_post/<post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if post:
        if current_user.id in post.get('likes', []):
            db.posts.update_one(
                {'_id': ObjectId(post_id)},
                {'$pull': {'likes': current_user.id}}
            )
        else:
            db.posts.update_one(
                {'_id': ObjectId(post_id)},
                {'$push': {'likes': current_user.id}}
            )
    return redirect(request.referrer or url_for('home'))

# Route for adding comments
@app.route('/add_comment/<post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content')
    if content:
        comment = {
            'user_id': current_user.id,
            'username': current_user.username,
            'content': content,
            'created_at': datetime.utcnow()
        }
        db.posts.update_one(
            {'_id': ObjectId(post_id)},
            {'$push': {'comments': comment}}
        )
    return redirect(request.referrer or url_for('home'))

# Route for following/unfollowing users
@app.route('/follow/<user_id>', methods=['POST'])
@login_required
def follow(user_id):
    if current_user.follow(user_id):
        flash('Successfully followed user!', 'success')
    return redirect(request.referrer or url_for('home'))

@app.route('/unfollow/<user_id>', methods=['POST'])
@login_required
def unfollow(user_id):
    if current_user.unfollow(user_id):
        flash('Successfully unfollowed user!', 'success')
    return redirect(request.referrer or url_for('home'))

# Updated home route to show posts
@app.route('/')
def home():
    if current_user.is_authenticated:
        # Get posts from followed users and own posts
        following_ids = current_user.following + [current_user.id]
        posts = list(db.posts.find({
            'user_id': {'$in': following_ids}
        }).sort('created_at', -1))
        
        # Get user info for each post
        for post in posts:
            user = db.accounts.find_one({'_id': ObjectId(post['user_id'])})
            if user:
                post['user_avatar'] = user.get('avatar', 'default.jpg')
        
        suggested_users = list(db.accounts.find({
            '_id': {'$nin': [ObjectId(id) for id in following_ids]},
            '_id': {'$ne': ObjectId(current_user.id)}
        }).limit(5))
        
        return render_template('home.html', 
                             posts=posts, 
                             suggested_users=suggested_users,
                             current_user=current_user)
    return render_template('home.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    if os.environ.get('ENVIRONMENT') == 'production':
        app.run(host='0.0.0.0', port=port)
    else:
        app.run(debug=True, host='0.0.0.0', port=port)