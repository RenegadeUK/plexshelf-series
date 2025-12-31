"""
Web UI for PlexShelf Series Manager using Flask
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask import send_from_directory
import logging
from src.database.db_manager import DatabaseManager
from src.config.config_manager import ConfigManager
from src.plex.plex_client import PlexClient
from src.matching.series_matcher import SeriesMatcher
from src.database.models import AudiobookItem, Series, SeriesMatch, PlexCollection

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'plexshelf-series-key'

import os

# Initialize managers
config_manager = ConfigManager()
config_manager.load()

db_manager = DatabaseManager()
db_manager.initialize()

plex_client = PlexClient()

# Auto-connect if credentials exist
plex_url = config_manager.get('plex.url')
plex_token = config_manager.get('plex.token')
if plex_url and plex_token:
    try:
        plex_client.connect(plex_url, plex_token)
        logger.info("Auto-connected to Plex on startup")
    except Exception as e:
        logger.warning(f"Failed to auto-connect to Plex: {e}")

@app.route('/')
def index():
    """Home page"""
    session = db_manager.get_session()
    
    stats = {
        'books': session.query(AudiobookItem).count(),
        'series': session.query(Series).count(),
        'matches': session.query(SeriesMatch).count(),
        'approved': session.query(SeriesMatch).filter_by(user_approved=True).count(),
        'connected': plex_client.test_connection()
    }
    
    session.close()
    
    return render_template('index.html', stats=stats)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings page"""
    if request.method == 'POST':
        url = request.form.get('plex_url')
        token = request.form.get('plex_token')
        library = request.form.get('library_name', 'Audiobooks')
        
        # External API settings
        external_enabled = request.form.get('external_api_enabled') == 'on'
        external_provider = request.form.get('external_api_provider', 'openai')
        openai_key = request.form.get('openai_api_key')
        openai_model = request.form.get('openai_model', 'gpt-4o-mini')
        
        try:
            # Use existing token if not provided
            if not token:
                token = config_manager.get('plex.token', '')
            
            plex_client.connect(url, token)
            config_manager.update_plex_config(url, token, library)
            
            # Update external API config
            external_config = config_manager.get('external_api', {})
            external_config['enabled'] = external_enabled
            external_config['provider'] = external_provider
            if openai_key:  # Only update if provided (don't clear existing)
                external_config['openai_api_key'] = openai_key
            external_config['openai_model'] = openai_model
            config_manager.set('external_api', external_config)
            config_manager.save()
            
            return jsonify({'success': True, 'message': 'Connected successfully'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400
    
    external_config = config_manager.get('external_api', {})
    plex_token = config_manager.get('plex.token', '')
    openai_key = external_config.get('openai_api_key', '')
    config = {
        'plex_url': config_manager.get('plex.url', ''),
        'library_name': config_manager.get('plex.library_name', 'Audiobooks'),
        'token_set': bool(plex_token),
        'external_api_enabled': external_config.get('enabled', False),
        'external_api_provider': external_config.get('provider', 'openai'),
        'openai_model': external_config.get('openai_model', 'gpt-4o-mini'),
        'api_key_set': bool(openai_key)
    }
    
    return render_template('settings.html', config=config)

@app.route('/clear-database', methods=['POST'])
def clear_database():
    """Clear all data from the database"""
    try:
        session = db_manager.get_session()
        
        # Delete all records from all tables
        session.query(SeriesMatch).delete()
        session.query(PlexCollection).delete()
        session.query(AudiobookItem).delete()
        session.query(Series).delete()
        
        session.commit()
        session.close()
        
        logger.info("Database cleared successfully")
        return jsonify({'success': True, 'message': 'Database cleared successfully'})
        
    except Exception as e:
        logger.error(f"Failed to clear database: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/scan', methods=['POST'])
def scan_library():
    """Scan Plex library"""
    try:
        library_name = config_manager.get('plex.library_name', 'Audiobooks')
        plex_client.get_library(library_name)
        audiobooks = plex_client.get_all_audiobooks()
        
        session = db_manager.get_session()
        added = 0
        updated = 0
        
        for book in audiobooks:
            metadata = plex_client.get_audiobook_metadata(book)
            
            existing = session.query(AudiobookItem).filter_by(
                plex_id=metadata['plex_id']
            ).first()
            
            if existing:
                for key, value in metadata.items():
                    setattr(existing, key, value)
                updated += 1
            else:
                new_book = AudiobookItem(**metadata)
                session.add(new_book)
                added += 1
        
        session.commit()
        session.close()
        
        return jsonify({
            'success': True,
            'message': f'Scan complete: {added} added, {updated} updated'
        })
        
    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/match', methods=['POST'])
def match_series():
    """Run series matching"""
    try:
        logger.info("Starting series matching...")
        session = db_manager.get_session()
        
        # Log configuration
        external_config = config_manager.get('external_api', {})
        logger.info(f"External API enabled: {external_config.get('enabled')}")
        logger.info(f"Provider: {external_config.get('provider')}")
        
        matcher = SeriesMatcher(session, config_manager)
        matches_found = matcher.match_all_audiobooks()
        session.close()
        
        logger.info(f"Series matching complete: {matches_found} matches found")
        return jsonify({
            'success': True,
            'message': f'Found {matches_found} matches'
        })
        
    except Exception as e:
        logger.error(f"Matching failed: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/matches')
def view_matches():
    """View all matches"""
    from sqlalchemy.orm import joinedload
    
    session = db_manager.get_session()
    
    filter_status = request.args.get('filter', 'pending')
    
    query = session.query(SeriesMatch).options(
        joinedload(SeriesMatch.audiobook),
        joinedload(SeriesMatch.series)
    )
    
    if filter_status == 'pending':
        query = query.filter_by(user_approved=False, user_rejected=False)
    elif filter_status == 'approved':
        query = query.filter_by(user_approved=True)
    elif filter_status == 'rejected':
        query = query.filter_by(user_rejected=True)
    
    matches = query.all()
    
    # Convert to dict to avoid session issues
    matches_data = []
    for match in matches:
        # Try to extract numeric series index for sorting
        series_index_str = match.audiobook.series_index or 'Companion'
        try:
            # If it's "Companion" or non-numeric, sort it at the end
            if series_index_str.lower() == 'companion':
                series_index_num = 999999
            else:
                series_index_num = float(series_index_str)
        except (ValueError, TypeError):
            series_index_num = 999999  # Put non-numeric at the end
        
        matches_data.append({
            'id': match.id,
            'audiobook_title': match.audiobook.title,
            'audiobook_author': match.audiobook.author or 'Unknown',
            'series_name': match.series.series_name,
            'series_index': match.audiobook.series_index or 'Companion',
            'series_index_sort': series_index_num,
            'confidence_score': match.confidence_score,
            'match_method': match.match_method,
            'user_approved': match.user_approved,
            'user_rejected': match.user_rejected
        })
    
    # Sort by: 1) Author, 2) Series Name, 3) Book Number
    matches_data.sort(key=lambda x: (
        x['audiobook_author'].lower(),
        x['series_name'].lower(),
        x['series_index_sort']
    ))
    
    session.close()
    
    return render_template('matches.html', matches=matches_data, filter=filter_status)

@app.route('/matches/<int:match_id>/approve', methods=['POST'])
def approve_match(match_id):
    """Approve a match"""
    try:
        session = db_manager.get_session()
        match = session.query(SeriesMatch).get(match_id)
        
        if match:
            match.user_approved = True
            match.user_rejected = False
            session.commit()
        
        session.close()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/matches/<int:match_id>/reject', methods=['POST'])
def reject_match(match_id):
    """Reject a match"""
    try:
        session = db_manager.get_session()
        match = session.query(SeriesMatch).get(match_id)
        
        if match:
            match.user_approved = False
            match.user_rejected = True
            session.commit()
        
        session.close()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/matches/approve-all', methods=['POST'])
def approve_all_matches():
    """Approve all pending matches"""
    try:
        session = db_manager.get_session()
        
        pending = session.query(SeriesMatch).filter_by(
            user_approved=False, 
            user_rejected=False
        ).all()
        
        count = len(pending)
        for match in pending:
            match.user_approved = True
            match.user_rejected = False
        
        session.commit()
        session.close()
        
        return jsonify({'success': True, 'message': f'Approved {count} matches'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/matches/reject-all', methods=['POST'])
def reject_all_matches():
    """Reject all pending matches"""
    try:
        session = db_manager.get_session()
        
        pending = session.query(SeriesMatch).filter_by(
            user_approved=False, 
            user_rejected=False
        ).all()
        
        count = len(pending)
        for match in pending:
            match.user_approved = False
            match.user_rejected = True
        
        session.commit()
        session.close()
        
        return jsonify({'success': True, 'message': f'Rejected {count} matches'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/apply', methods=['POST'])
def apply_to_plex():
    """Apply approved matches to Plex"""
    try:
        # Ensure library is loaded
        library_name = config_manager.get('plex.library_name', 'Audiobooks')
        try:
            plex_client.get_library(library_name)
        except Exception as e:
            logger.error(f"Failed to load library: {e}")
            return jsonify({'success': False, 'message': f'Failed to load Plex library: {e}'}), 500
        
        session = db_manager.get_session()
        
        approved = session.query(SeriesMatch).filter_by(user_approved=True).all()
        
        if not approved:
            return jsonify({'success': False, 'message': 'No approved matches'})
        
        # Group by series
        series_dict = {}
        for match in approved:
            if match.series_id not in series_dict:
                series_dict[match.series_id] = []
            series_dict[match.series_id].append(match.audiobook.plex_id)
        
        # Create collections
        created = 0
        sort_updated = 0
        for series_id, book_ids in series_dict.items():
            series = session.query(Series).get(series_id)
            collection_name = f"{series.series_name} Series"
            
            try:
                # Update sort titles for each book in the series
                for match in approved:
                    if match.series_id == series_id:
                        success = plex_client.update_sort_title(
                            match.audiobook.plex_id,
                            series.series_name,
                            match.audiobook.series_index
                        )
                        if success:
                            sort_updated += 1
                
                # Create/update the collection
                plex_client.create_collection(collection_name, book_ids)
                created += 1
            except Exception as e:
                logger.error(f"Failed to create {collection_name}: {e}")
        
        session.close()
        
        return jsonify({
            'success': True,
            'message': f'Created {created} collections in Plex ({sort_updated} books sorted)'
        })
        
    except Exception as e:
        logger.error(f"Apply failed: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
