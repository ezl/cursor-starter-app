from flask import Flask
import atexit
from datetime import datetime, timedelta

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('config.Config')
    
    # Ensure secret key is set for sessions
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'dev-key-please-change-in-production'
    
    # Initialize database
    from app.database import init_db
    init_db(app)
    
    # Import models to ensure they're registered with SQLAlchemy
    from app.database.models import User, Post, AuthToken, Trip, Recommendation, Activity
    
    # Register CLI commands
    from app.cli import init_app as init_cli
    init_cli(app)
    
    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)
    
    # Register auth blueprint
    from app.auth import auth
    app.register_blueprint(auth)
    
    # Add context processor for template variables
    from datetime import datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}
    
    # Setup token cleanup on app shutdown
    from app.database import db
    def cleanup_expired_tokens():
        try:
            with app.app_context():
                now = datetime.utcnow()
                # Check if auth_tokens table exists
                engine = db.engine
                inspector = db.inspect(engine)
                if 'auth_tokens' in inspector.get_table_names():
                    AuthToken.query.filter(
                        (AuthToken.expires_at < now) | (AuthToken.used == True)
                    ).delete()
                    db.session.commit()
        except Exception as e:
            # Just log the error and continue - don't crash the app
            print(f"Error during token cleanup: {e}")
    
    # Register cleanup function to run on app shutdown
    atexit.register(cleanup_expired_tokens)
    
    return app 