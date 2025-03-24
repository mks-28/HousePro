from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Professional, ServiceRequest, Review
from functools import wraps
from sqlalchemy import and_

professional_bp = Blueprint('professional', __name__)

# Professional role required decorator
def professional_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'professional':
            flash('You need to be a service professional to access this page')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@professional_bp.route('/dashboard')
@login_required
@professional_required
def dashboard():
    # Get current professional
    professional = Professional.query.filter_by(user_id=current_user.id).first()
    
    # Check if professional is verified
    if not professional.is_verified:
        return render_template('professional/pending_approval.html')
    
    # Get professional's service requests
    assigned_requests = ServiceRequest.query.filter_by(
        professional_id=professional.id
    ).filter(
        ServiceRequest.service_status != 'closed'
    ).all()
    
    # Get service requests that match the professional's service and location
    available_requests = ServiceRequest.query.filter(
        ServiceRequest.service_id == professional.service_id,
        ServiceRequest.service_status == 'requested',
        ServiceRequest.professional_id == None,  # Not assigned yet
        ServiceRequest.pin_code == professional.pin_code  # Same location
    ).all()
    
    # Get completed service requests
    completed_requests = ServiceRequest.query.filter(
        ServiceRequest.professional_id == professional.id,
        ServiceRequest.service_status == 'closed'
    ).all()
    
    # Calculate average rating
    reviews = Review.query.join(ServiceRequest).filter(
        ServiceRequest.professional_id == professional.id
    ).all()
    
    avg_rating = 0
    if reviews:
        avg_rating = sum(review.rating for review in reviews) / len(reviews)
    
    return render_template('professional/dashboard.html',
                          professional=professional,
                          assigned_requests=assigned_requests,
                          available_requests=available_requests,
                          completed_requests=completed_requests,
                          avg_rating=avg_rating)

@professional_bp.route('/requests/accept/<int:request_id>', methods=['POST'])
@login_required
@professional_required
def accept_request(request_id):
    professional = Professional.query.filter_by(user_id=current_user.id).first()
    
    # Check if professional is verified
    if not professional.is_verified:
        flash('Your account is not yet verified')
        return redirect(url_for('professional.dashboard'))
    
    service_request = ServiceRequest.query.get_or_404(request_id)
    
    # Check if request is still available
    if service_request.service_status != 'requested' or service_request.professional_id is not None:
        flash('This service request is no longer available')
        return redirect(url_for('professional.dashboard'))
    
    # Assign request to professional
    service_request.professional_id = professional.id
    service_request.service_status = 'assigned'
    db.session.commit()
    
    flash('Service request accepted successfully')
    return redirect(url_for('professional.dashboard'))

@professional_bp.route('/requests/reject/<int:request_id>', methods=['POST'])
@login_required
@professional_required
def reject_request(request_id):
    professional = Professional.query.filter_by(user_id=current_user.id).first()
    service_request = ServiceRequest.query.get_or_404(request_id)
    
    # Check if the request is assigned to this professional
    if service_request.professional_id != professional.id:
        flash('Unauthorized action')
        return redirect(url_for('professional.dashboard'))
    
    # Unassign request
    service_request.professional_id = None
    service_request.service_status = 'requested'
    db.session.commit()
    
    flash('Service request rejected successfully')
    return redirect(url_for('professional.dashboard'))

@professional_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@professional_required
def profile():
    professional = Professional.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        professional.name = request.form['name']
        professional.experience = request.form['experience']
        professional.description = request.form['description']
        professional.phone_number = request.form['phone_number']
        professional.address = request.form['address']
        professional.pin_code = request.form['pin_code']
        
        db.session.commit()
        flash('Profile updated successfully')
        return redirect(url_for('professional.dashboard'))
    
    return render_template('professional/profile.html', professional=professional)