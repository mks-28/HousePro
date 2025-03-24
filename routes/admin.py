from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Service, Professional, Customer, ServiceRequest
from functools import wraps

admin_bp = Blueprint('admin', __name__)

# Admin role required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You need to be an admin to access this page')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Count statistics for dashboard
    total_customers = Customer.query.count()
    total_professionals = Professional.query.count()
    total_services = Service.query.count()
    total_requests = ServiceRequest.query.count()
    pending_approvals = Professional.query.filter_by(is_verified=False).count()
    
    return render_template('admin/dashboard.html', 
                          total_customers=total_customers,
                          total_professionals=total_professionals,
                          total_services=total_services,
                          total_requests=total_requests,
                          pending_approvals=pending_approvals)

# Service Management
@admin_bp.route('/services', methods=['GET'])
@login_required
@admin_required
def services():
    services = Service.query.all()
    return render_template('admin/manage_services.html', services=services)

@admin_bp.route('/services/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_service():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        time_required = request.form['time_required']
        description = request.form['description']
        
        # Check if service already exists
        if Service.query.filter_by(name=name).first():
            flash('Service already exists')
            return redirect(url_for('admin.services'))
        
        # Create new service
        service = Service(name=name, price=price, time_required=time_required, description=description)
        db.session.add(service)
        db.session.commit()
        
        flash('Service added successfully')
        return redirect(url_for('admin.services'))
    
    return render_template('admin/add_service.html')

@admin_bp.route('/services/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_service(id):
    service = Service.query.get_or_404(id)
    
    if request.method == 'POST':
        service.name = request.form['name']
        service.price = float(request.form['price'])
        service.time_required = request.form['time_required']
        service.description = request.form['description']
        
        db.session.commit()
        flash('Service updated successfully')
        return redirect(url_for('admin.services'))
    
    return render_template('admin/edit_service.html', service=service)

@admin_bp.route('/services/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_service(id):
    service = Service.query.get_or_404(id)
    
    # Check if service is being used by professionals or service requests
    if service.professionals or service.service_requests:
        flash('Cannot delete service that is in use')
        return redirect(url_for('admin.services'))
    
    db.session.delete(service)
    db.session.commit()
    
    flash('Service deleted successfully')
    return redirect(url_for('admin.services'))

# User Management
@admin_bp.route('/users', methods=['GET'])
@login_required
@admin_required
def users():
    role_filter = request.args.get('role', 'all')
    search_query = request.args.get('search', '')
    
    if role_filter == 'customer':
        users_query = Customer.query
        if search_query:
            users_query = users_query.filter(Customer.name.ilike(f'%{search_query}%'))
        users = users_query.all()
        return render_template('admin/manage_customers.html', customers=users, search=search_query)
    
    elif role_filter == 'professional':
        users_query = Professional.query
        if search_query:
            users_query = users_query.filter(Professional.name.ilike(f'%{search_query}%'))
        users = users_query.all()
        return render_template('admin/manage_professionals.html', professionals=users, search=search_query)
    
    else:  # all users
        users = User.query.all()
        return render_template('admin/manage_users.html', users=users)

@admin_bp.route('/professionals/approve/<int:id>', methods=['POST'])
@login_required
@admin_required
def approve_professional(id):
    professional = Professional.query.get_or_404(id)
    professional.is_verified = True
    db.session.commit()
    
    flash('Professional approved successfully')
    return redirect(url_for('admin.users', role='professional'))

@admin_bp.route('/users/toggle-status/<int:id>', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(id):
    user = User.query.get_or_404(id)
    
    # Cannot deactivate admin
    if user.role == 'admin':
        flash('Cannot deactivate admin user')
        return redirect(url_for('admin.users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {status} successfully')
    return redirect(url_for('admin.users'))