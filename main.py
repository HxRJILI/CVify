import os
import sys

# Ensure the root project directory is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.database import init_db
from ui.app import run_app

def main():
    """Entry point for the CVify application."""
    # Ensure database tables are created
    init_db()
    
    # Run the PyQt6 application
    run_app()

if __name__ == "__main__":
    main()
