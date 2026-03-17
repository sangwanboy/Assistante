import inspect
import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.getcwd())

try:
    from app.services.chat_service import ChatService
    sig = inspect.signature(ChatService.stream_chat)
    print(f"ChatService.stream_chat signature: {sig}")
    
    # Check if 'model_string' is in parameters
    if 'model_string' in sig.parameters:
        print("SUCCESS: 'model_string' is a valid argument.")
    else:
        print("FAILURE: 'model_string' is MISSING from parameters.")
        print(f"Parameters found: {list(sig.parameters.keys())}")
except Exception as e:
    print(f"Error importing ChatService: {e}")
