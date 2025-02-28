from flask import Flask, render_template, request, jsonify, session  # Add session import
from flask_cors import CORS
from rag import load_pdf, split_documents, create_vector_store, create_qa_chain
import os
import shutil
import traceback
import logging
import chromadb  # Add this import

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, supports_credentials=True)  # Update CORS configuration
# Removed MAX_CONTENT_LENGTH config to allow unlimited file size
app.secret_key = os.urandom(24)  # Add secret key for session management

def get_user_upload_dir():
    """Generate unique upload directory for each session"""
    if 'user_id' not in session:
        session['user_id'] = os.urandom(16).hex()
    return os.path.join('uploads', session['user_id'])

def cleanup_uploads():
    """Clean up the uploads directory and ChromaDB data"""
    user_dir = get_user_upload_dir()
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)
        os.makedirs(user_dir)
    global qa_chain, pdf_name
    
    # Reset global variables
    qa_chain = None
    pdf_name = None
    
    # Clean uploads directory
    if os.path.exists('uploads'):
        shutil.rmtree('uploads')
        os.makedirs('uploads')
    
    # Clean ChromaDB persistence directory
    if os.path.exists('.chroma'):
        try:
            # Create a ChromaDB client and reset it
            client = chromadb.PersistentClient(path=".chroma")
            client.reset()
            # Close any open connections
            del client
            
            # Now try to remove the directory
            shutil.rmtree('.chroma')
        except Exception as e:
            logger.error(f"Error cleaning ChromaDB: {e}")
            # If deletion fails, wait a bit and try again
            import time
            time.sleep(1)
            try:
                shutil.rmtree('.chroma')
            except Exception as e2:
                logger.error(f"Failed to clean ChromaDB after retry: {e2}")
    
    logger.debug("Cleaned up uploads and ChromaDB directories")

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Handle cleanup when page is closed"""
    try:
        cleanup_uploads()
        return jsonify({'message': 'Cleanup successful'})
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    global qa_chain, pdf_name
    logger.debug("Upload endpoint called")
    logger.debug(f"Files in request: {request.files}")
    logger.debug(f"Request headers: {request.headers}")
    
    try:
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({'error': 'No file part'}), 400
        
        # Clean up existing uploads before saving new file
        cleanup_uploads()
        
        file = request.files['file']
        logger.debug(f"Received file: {file.filename}")
        logger.debug(f"File content type: {file.content_type}")
        
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400
        
        if file and file.filename.endswith('.pdf'):
            # Create uploads directory if it doesn't exist
            os.makedirs('uploads', exist_ok=True)
            
            # Save the uploaded file
            upload_path = os.path.join('uploads', file.filename)
            logger.debug(f"Saving file to: {upload_path}")
            file.save(upload_path)
            
            if not os.path.exists(upload_path):
                logger.error("File was not saved successfully")
                return jsonify({'error': 'File save failed'}), 500
                
            pdf_name = file.filename
            
            # Process the PDF
            logger.debug("Processing PDF")
            documents = load_pdf(upload_path)
            if not documents:
                logger.error("Error loading PDF")
                return jsonify({'error': 'Error loading PDF'}), 400
            
            logger.debug("Splitting documents")
            split_docs = split_documents(documents)
            logger.debug("Creating vector store")
            vector_store = create_vector_store(split_docs)
            logger.debug("Creating QA chain")
            qa_chain = create_qa_chain(vector_store)
            
            logger.debug("PDF processing completed successfully")
            return jsonify({'message': 'PDF processed successfully', 'filename': file.filename})
        
        logger.error("Invalid file type")
        return jsonify({'error': 'Invalid file type'}), 400
    except Exception as e:
        logger.error(f"Error in upload_file: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/query', methods=['POST'])
def query():
    global qa_chain
    logger.debug("Query endpoint called")
    
    try:
        if not qa_chain:
            logger.error("No QA chain available")
            return jsonify({'error': 'Please upload a PDF first'}), 400
        
        data = request.json
        logger.debug(f"Received query data: {data}")
        
        question = data.get('question')
        if not question:
            logger.error("No question provided")
            return jsonify({'error': 'No question provided'}), 400
        
        logger.debug(f"Processing question: {question}")
        result = qa_chain({"query": question})
        answer = result['result']
        
        logger.debug("Query processed successfully")
        return jsonify({
            'answer': answer,
            'pdf_name': pdf_name
        })
    except Exception as e:
        logger.error(f"Error in query: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/')
def index():
    logger.debug("Serving index page")
    return render_template('index.html')

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True, host='0.0.0.0', port=8000)  # Try port 8000 instead
