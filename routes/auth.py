from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Customer, Professional, Service
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            
            # Redirect based on user role
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'professional':
                return redirect(url_for('professional.dashboard'))
            else:  # customer
                return redirect(url_for('customer.dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    services = Service.query.all()
    
    if request.method == 'POST':
        role = request.form['role']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template('auth/register.html', services=services)
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return render_template('auth/register.html', services=services)
        
        # Create user
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # To get the user ID
        
        # Create role-specific profile
        if role == 'customer':
            name = request.form['name']
            address = request.form['address']
            pin_code = request.form['pin_code']
            phone_number = request.form['phone_number']
            
            customer = Customer(user_id=user.id, name=name, address=address, 
                               pin_code=pin_code, phone_number=phone_number)
            db.session.add(customer)
        
        elif role == 'professional':
            name = request.form['name']
            service_id = request.form['service_id']
            experience = request.form['experience']
            description = request.form['description']
            address = request.form['address']
            pin_code = request.form['pin_code']
            phone_number = request.form['phone_number']
            
            professional = Professional(user_id=user.id, name=name, service_id=service_id,
                                     experience=experience, description=description,
                                     address=address, pin_code=pin_code, phone_number=phone_number)
            db.session.add(professional)
        
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', services=services)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out')
    return redirect(url_for('index'))