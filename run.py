# from app import create_app
# from app.config import Config
# import os

# app = create_app()

# if __name__ == '__main__':
#     print("--- Starting Server in Debug Mode ---")
#     app.run(host='0.0.0.0', port=5000, debug=True)
    
    
 
 
from app import create_app
from app.config import Config
import os

app = create_app()


if __name__ == '__main__':
    print("--- Starting Server in Debug Mode ---")
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)