from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Service, ServiceRequest, Review, Customer
from functools import wraps
from sqlalchemy import or_

customer_bp = Blueprint('customer', __name__)

# Customer role required decorator
def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'customer':
            flash('You need to be a customer to access this page')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@customer_bp.route('/dashboard')
@login_required
@customer_required
def dashboard():
    # Get current customer
    customer = Customer.query.filter_by(user_id=current_user.id).first()
    
    # Get customer's service requests
    service_requests = ServiceRequest.query.filter_by(customer_id=customer.id).order_by(ServiceRequest.date_of_request.desc()).all()
    
    return render_template('customer/dashboard.html', 
                          customer=customer,
                          service_requests=service_requests)

@customer_bp.route('/services', methods=['GET'])
@login_required
@customer_required
def services():
    search_query = request.args.get('search', '')
    search_pin = request.args.get('pin_code', '')
    
    # Get all services
    services_query = Service.query
    
    # Apply search filters if provided
    if search_query:
        services_query = services_query.filter(Service.name.ilike(f'%{search_query}%'))
    
    services = services_query.all()
    
    # Filter by pin code if provided (done in Python as professionals are related to services)
    if search_pin:
        # For each service, check if there are professionals in that pin code area
        filtered_services = []
        for service in services:
            has_professionals_in_area = any(p.pin_code == search_pin for p in service.professionals if p.is_verified)
            if has_professionals_in_area:
                filtered_services.append(service)
        services = filtered_services
    
    return render_template('customer/view_services.html', 
                          services=services, 
                          search=search_query,
                          pin_code=search_pin)

@customer_bp.route('/request-service/<int:service_id>', methods=['GET', 'POST'])
@login_required
@customer_required
def request_service(service_id):
    service = Service.query.get_or_404(service_id)
    customer = Customer.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        location = request.form['location']
        pin_code = request.form['pin_code']
        remarks = request.form['remarks']
        
        # Create new service request
        service_request = ServiceRequest(
            service_id=service.id,
            customer_id=customer.id,
            service_status='requested',
            location=location,
            pin_code=pin_code,
            remarks=remarks
        )
        
        db.session.add(service_request)
        db.session.commit()
        
        flash('Service request submitted successfully')
        return redirect(url_for('customer.dashboard'))
    
    return render_template('customer/request_service.html', service=service, customer=customer)

@customer_bp.route('/request/edit/<int:request_id>', methods=['GET', 'POST'])
@login_required
@customer_required
def edit_request(request_id):
    customer = Customer.query.filter_by(user_id=current_user.id).first()
    service_request = ServiceRequest.query.get_or_404(request_id)
    
    # Check if the request belongs to the current customer
    if service_request.customer_id != customer.id:
        flash('Unauthorized access')
        return redirect(url_for('customer.dashboard'))
    
    # Only allow editing if the request is still in 'requested' status
    if service_request.service_status != 'requested':
        flash('Cannot edit request that has already been assigned or closed')
        return redirect(url_for('customer.dashboard'))
    
    if request.method == 'POST':
        service_request.location = request.form['location']
        service_request.pin_code = request.form['pin_code']
        service_request.remarks = request.form['remarks']
        
        db.session.commit()
        flash('Service request updated successfully')
        return redirect(url_for('customer.dashboard'))
    
    return render_template('customer/edit_request.html', 
                          service_request=service_request,
                          service=service_request.service)

@customer_bp.route('/request/close/<int:request_id>', methods=['GET', 'POST'])
@login_required
@customer_required
def close_request(request_id):
    customer = Customer.query.filter_by(user_id=current_user.id).first()
    service_request = ServiceRequest.query.get_or_404(request_id)
    
    # Check if the request belongs to the current customer
    if service_request.customer_id != customer.id:
        flash('Unauthorized access')
        return redirect(url_for('customer.dashboard'))
    
    # Only allow closing if the request is in 'assigned' status
    if service_request.service_status != 'assigned':
        flash('Cannot close request that has not been assigned or is already closed')
        return redirect(url_for('customer.dashboard'))
    
    if request.method == 'POST':
        # Update request status
        service_request.service_status = 'closed'
        service_request.date_of_completion = db.func.current_timestamp()
        
        # Add review if provided
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        
        if rating:
            review = Review(
                service_request_id=service_request.id,
                rating=int(rating),
                comment=comment
            )
            db.session.add(review)
        
        db.session.commit()
        flash('Service request closed successfully')
        return redirect(url_for('customer.dashboard'))
    
    return render_template('customer/close_request.html', service_request=service_request)