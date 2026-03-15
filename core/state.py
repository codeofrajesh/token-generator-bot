# In-memory dictionary to store active verification attempts.
# It will map the unique verification UUID to the user's details and timestamps.
# Example format: 
# { 
#   "verify_12345abc": {
#       "telegram_user_id": 987654321, 
#       "start_time": 1700000000.0, 
#       "flow_type": "app", # or "demo"
#       "app_user_id": "app_User123" # Only present if flow_type is "app"
#   } 
# }

active_verifications = {}