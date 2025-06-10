"""
Run script for the Xavier AI backend.
"""

import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the app
try:
    print("Importing app...")
    from xavier_back.app import app
    print("Successfully imported app")
    
    # Run the app
    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 5000))
        print(f"Starting app on port {port}...")
        app.run(host='0.0.0.0', port=port, debug=True)
except Exception as e:
    print(f"Error importing app: {str(e)}")
    import traceback
    traceback.print_exc()
