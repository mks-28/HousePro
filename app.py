from flask import Flask, render_template
from flask_login import LoginManager
from models import db, User
from config import Config
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.customer import customer_bp
from routes.professional import professional_bp
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    
    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(professional_bp, url_prefix='/professional')
    
    # Homepage route
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@example.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    
    return app

if __name__ == '__main__':
    # Running the app
    app = create_app()
    app.run(debug=True)