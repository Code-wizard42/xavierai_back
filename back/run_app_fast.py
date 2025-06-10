"""
Fast development startup script for Xavier AI.
This script sets environment variables to disable heavy startup components.
"""

import os
import sys

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set environment variables to disable heavy components
os.environ['FAST_MODE'] = 'true'
os.environ['DISABLE_NLTK'] = 'true'
os.environ['DISABLE_FIREBASE'] = 'true'
os.environ['DISABLE_VECTOR_DB'] = 'true'
os.environ['DISABLE_SCHEDULER'] = 'true'
os.environ['DISABLE_REDIS'] = 'true'
os.environ['SKIP_ENV_CHECKS'] = 'true'
os.environ['MINIMAL_LOGGING'] = 'true'

try:
    print("🚀 Starting Xavier AI in FAST MODE")
    print("⚡ Heavy components disabled for faster startup")
    
    # Import the fast app
    from xavier_back.app_fast import app
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Server starting at http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
    
except Exception as e:
    print(f"❌ Error starting fast app: {str(e)}")
    import traceback
    traceback.print_exc() 