import os
import uuid
import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, abort, jsonify
from app.database import db
from app.database.models import User, Trip, Recommendation, Activity, TripSubscription
from app.services.ai_service import AIService

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/create-trip', methods=['POST'])
def create_trip():
    destination = request.form.get('destination')
    traveler_name = request.form.get('name')
    
    if not destination:
        flash('Please enter a destination', 'error')
        return redirect(url_for('main.index'))
    
    if not traveler_name:
        flash('Please enter your name', 'error')
        return redirect(url_for('main.index'))
    
    # Generate a unique share token
    share_token = str(uuid.uuid4())[:8]
    
    # Generate slug
    slug = Trip.generate_slug(destination, traveler_name)
    
    # Check if slug already exists and modify if needed
    base_slug = slug
    counter = 1
    while Trip.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    # Check if user is logged in
    user_id = session.get('user_id')
    
    # If not logged in, create or get the anonymous user
    if not user_id:
        anon_user = User.query.filter_by(email='anonymous@example.com').first()
        if not anon_user:
            anon_user = User(email='anonymous@example.com', name='Anonymous User')
            db.session.add(anon_user)
            db.session.commit()
        user_id = anon_user.id
    
    # Create trip
    trip = Trip(
        destination=destination,
        traveler_name=traveler_name,
        share_token=share_token,
        slug=slug,
        user_id=user_id
    )
    
    db.session.add(trip)
    db.session.commit()
    
    return redirect(url_for('main.view_trip', slug=trip.slug))

@main.route('/trip/<slug>')
def view_trip(slug):
    trip = Trip.query.filter_by(slug=slug).first_or_404()
    return render_template('trip.html', trip=trip)

@main.route('/trip/<slug>/add', methods=['GET'])
def add_recommendation(slug):
    trip = Trip.query.filter_by(slug=slug).first_or_404()
    return render_template('add_recommendation.html', trip=trip)

@main.route('/trip/<slug>/process', methods=['POST'])
def process_recommendation(slug):
    trip = Trip.query.filter_by(slug=slug).first_or_404()
    
    # Get unstructured recommendations from form
    unstructured_recommendations = request.form.get('unstructured_recommendations', '')
    recommender_name = request.form.get('recommender_name', '')
    
    if not unstructured_recommendations:
        flash('Please provide some recommendations', 'error')
        return redirect(url_for('main.add_recommendation', slug=slug))
    
    try:
        # Call OpenAI API to extract structured recommendations
        extracted_recommendations = AIService.extract_recommendations(unstructured_recommendations, trip.destination)
        
        # Render confirmation template with extracted recommendations
        return render_template(
            'confirm_recommendations.html', 
            trip=trip, 
            extracted_recommendations=extracted_recommendations,
            recommender_name=recommender_name
        )
    except ValueError as e:
        flash(f'API Configuration Error: {str(e)}', 'error')
        return redirect(url_for('main.add_recommendation', slug=slug))
    except Exception as e:
        flash(f'Error processing recommendations: {str(e)}', 'error')
        return redirect(url_for('main.add_recommendation', slug=slug))

@main.route('/trip/<slug>/save', methods=['POST'])
def save_recommendations(slug):
    trip = Trip.query.filter_by(slug=slug).first_or_404()
    
    recommendations = request.form.getlist('recommendations[]')
    descriptions = request.form.getlist('descriptions[]')
    place_types = request.form.getlist('place_types[]')
    website_urls = request.form.getlist('website_urls[]')
    recommender_name = request.form.get('recommender_name')
    
    if not recommendations or len(recommendations) == 0:
        flash('Please add at least one recommendation', 'error')
        return redirect(url_for('main.add_recommendation', slug=slug))
    
    if not recommender_name:
        flash('Please provide your name', 'error')
        return redirect(url_for('main.process_recommendation', slug=slug))
    
    # Check if user is logged in
    user_id = session.get('user_id')
    
    # If not logged in, use the anonymous user or create temporary user
    if not user_id:
        # If the recommender provided a name, create a temporary user with that name
        if recommender_name:
            temp_email = f"temp_{uuid.uuid4().hex[:8]}@example.com"
            temp_user = User(email=temp_email, name=recommender_name)
            db.session.add(temp_user)
            db.session.commit()
            user_id = temp_user.id
        else:
            anon_user = User.query.filter_by(email='anonymous@example.com').first()
            if not anon_user:
                anon_user = User(email='anonymous@example.com', name='Anonymous User')
                db.session.add(anon_user)
                db.session.commit()
            user_id = anon_user.id
    
    # Create recommendations
    for i in range(len(recommendations)):
        if not recommendations[i]:  # Skip empty recommendations
            continue
            
        # First find or create the Activity
        activity = Activity.get_or_create(
            name=recommendations[i],
            category=place_types[i] if i < len(place_types) and place_types[i] else None,
            website_url=website_urls[i] if i < len(website_urls) and website_urls[i] else None
        )
        
        # Then create the Recommendation which links this Activity to the Trip
        recommendation = Recommendation(
            activity_id=activity.id,
            description=descriptions[i] if i < len(descriptions) and descriptions[i] else None,
            author_id=user_id,
            trip_id=trip.id
        )
        
        db.session.add(recommendation)
    
    db.session.commit()
    
    # Redirect to thank you page
    return redirect(url_for('main.thank_you_page', slug=trip.slug))

@main.route('/trip/<slug>/thank-you')
def thank_you_page(slug):
    """
    Thank you page for recommendation submissions
    """
    trip = Trip.query.filter_by(slug=slug).first_or_404()
    return render_template('thank_you.html', trip=trip)

@main.route('/trip/<slug>/save-email', methods=['POST'])
def save_recommender_email(slug):
    """
    Save email address of recommender who wants to be notified
    """
    trip = Trip.query.filter_by(slug=slug).first_or_404()
    email = request.form.get('email')
    
    if not email:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": "Please provide an email address"}), 400
        flash('Please provide an email address', 'error')
        return redirect(url_for('main.thank_you_page', slug=slug))
    
    # Get or create user with this email
    user = User.get_or_create(email)
    
    # Check if this user is already subscribed to this trip
    existing = TripSubscription.query.filter_by(trip_id=trip.id, user_id=user.id).first()
    if not existing:
        # Create new subscription
        subscription = TripSubscription(
            trip_id=trip.id,
            user_id=user.id
        )
        db.session.add(subscription)
        db.session.commit()
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            "success": True,
            "message": "Thank you! We'll notify you when all recommendations are in."
        })
    
    # For regular form submissions
    flash('Thank you! We\'ll notify you when all recommendations are in.', 'success')
    return redirect(url_for('main.view_trip', slug=slug))

# Legacy route to handle old share_token links
@main.route('/recommendations/<token>')
def recommendation_request(token):
    trip = Trip.query.filter_by(share_token=token).first_or_404()
    return redirect(url_for('main.view_trip', slug=trip.slug))

@main.route('/my-trips')
def my_trips():
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login', next=url_for('main.my_trips')))
    
    trips = Trip.query.filter_by(user_id=user_id).order_by(Trip.created_at.desc()).all()
    return render_template('my_trips.html', trips=trips)

@main.context_processor
def inject_now():
    return {'now': datetime.now()}

@main.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """
    Endpoint to handle audio transcription and process it into recommendations
    """
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files['audio']
    destination = request.form.get('destination', '')
    
    if not destination:
        return jsonify({"error": "No destination provided"}), 400
    
    if audio_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        # Create a temporary file to store the audio
        temp_filepath = f"/tmp/{uuid.uuid4()}.webm"
        audio_file.save(temp_filepath)
        
        # Call OpenAI to transcribe the audio
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return jsonify({"error": "API key not configured"}), 500
        
        # Use OpenAI Whisper API for transcription
        import requests
        
        with open(temp_filepath, 'rb') as f:
            response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": f},
                data={"model": "whisper-1"}
            )
        
        # Clean up the temporary file
        os.remove(temp_filepath)
        
        if response.status_code != 200:
            return jsonify({"error": f"OpenAI API error: {response.text}"}), 500
        
        transcription = response.json().get("text", "")
        
        if not transcription:
            return jsonify({"error": "Failed to transcribe audio"}), 500
        
        # Process the transcription to extract recommendations
        extracted_recommendations = AIService.extract_recommendations(transcription, destination)
        
        return jsonify({
            "status": "success",
            "recommendations": extracted_recommendations
        }), 200
    
    except Exception as e:
        # Clean up temporary file if it exists
        if 'temp_filepath' in locals() and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        
        return jsonify({"error": str(e)}), 500

@main.route('/trip/<slug>/process-audio', methods=['POST'])
def process_audio_recommendation(slug):
    """
    Endpoint to process pre-extracted recommendations from audio
    """
    trip = Trip.query.filter_by(slug=slug).first_or_404()
    
    try:
        # Get the pre-extracted recommendations from the request body
        data = request.json
        
        if not data or not isinstance(data, list):
            return jsonify({"error": "Invalid recommendations data"}), 400
        
        # Log the data for debugging
        print(f"Storing {len(data)} recommendations in session: {data}")
        
        # Store in session for the confirmation page
        session['extracted_recommendations'] = data
        
        # Return URL to redirect to
        return jsonify({
            "status": "success",
            "redirect_url": url_for('main.confirm_audio_recommendations', slug=slug)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/trip/<slug>/confirm-audio', methods=['GET'])
def confirm_audio_recommendations(slug):
    """
    Show confirmation page for audio recommendations
    """
    trip = Trip.query.filter_by(slug=slug).first_or_404()
    
    # Get recommendations from session
    extracted_recommendations = session.get('extracted_recommendations', [])
    
    # Log for debugging
    print(f"Retrieved from session: {extracted_recommendations}")
    
    # Check if it's empty or not a valid list
    if not extracted_recommendations or not isinstance(extracted_recommendations, list) or len(extracted_recommendations) == 0:
        print("No recommendations found in session!")
        flash('No recommendations found. Please try again.', 'error')
        return redirect(url_for('main.add_recommendation', slug=slug))
    
    # Clear from session to avoid persistence issues
    session.pop('extracted_recommendations', None)
    
    # Render the same template as text recommendations
    return render_template(
        'confirm_recommendations.html', 
        trip=trip, 
        extracted_recommendations=extracted_recommendations,
        recommender_name=''
    )

@main.route('/trip/<slug>/audio-error', methods=['GET'])
def audio_error(slug):
    """Handle audio processing errors with flash messages"""
    error_message = request.args.get('message', 'There was an error processing your audio. Please try again or use text input instead.')
    flash(error_message, 'error')
    return '', 204  # Return no content with 204 status code

@main.route('/how-it-works')
def how_it_works():
    """How it works page explaining the recommendation system"""
    return render_template('how_it_works.html') 