import pandas as pd
from datetime import date
import database
import os

def generate_missing_workers_excel():
    today_str = date.today().isoformat()
    all_users = database.get_all_users() # list of dicts
    submitted_ids = database.get_submitted_users_today() # set of ids
    
    missing_workers = []
    for user in all_users:
        if user['user_id'] not in submitted_ids:
            missing_workers.append({
                'Name': user['full_name'],
                'Telegram ID': user['user_id']
            })
            
    if not missing_workers:
        return None
        
    df = pd.DataFrame(missing_workers)
    filename = f"missing_workers_{today_str}.xlsx"
    df.to_excel(filename, index=False)
    return filename

def get_performance_report_text():
    # Top 5 streaks
    top_streaks = database.get_top_streaks(5)
    
    msg = "🏆 *आज के सितारे (Top Streaks)* 🏆\n\n"
    if top_streaks:
        for i, (name, streak) in enumerate(top_streaks, 1):
            msg += f"{i}. {name} - {streak} 🔥\n"
        msg += "\nसभी विजेताओं को बहुत-बहुत बधाई! 👏🎊"
    else:
        msg += "अभी तक कोई स्ट्रीक नहीं बनी है।"
        
    return msg
