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

def get_past_week_stats():
    from datetime import timedelta
    today = date.today()
    start_date = today - timedelta(days=6)
    
    start_str = start_date.isoformat()
    end_str = today.isoformat()
    
    submissions = database.get_submissions_between_dates(start_str, end_str)
    
    user_counts = {}
    for sub in submissions:
        uid = sub[0]
        user_counts[uid] = user_counts.get(uid, 0) + 1
        
    all_users = database.get_all_users()
    report_data = []
    for user in all_users:
        uid = user['user_id']
        name = user['full_name']
        count = user_counts.get(uid, 0)
        report_data.append({'Name': name, 'Visits': count})
        
    report_data.sort(key=lambda x: x['Visits'], reverse=True)
    
    msg = f"📅 *पिछले 7 दिनों की रिपोर्ट ({start_str} से {end_str})*\n\n"
    for item in report_data:
        msg += f"- {item['Name']}: {item['Visits']} दिन\n"
        
    return msg

def generate_attendance_register(start_date, end_date):
    from datetime import timedelta
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    
    submissions = database.get_submissions_between_dates(start_str, end_str)
    all_users = database.get_all_users()
    
    delta = end_date - start_date
    date_list = [start_date + timedelta(days=i) for i in range(delta.days + 1)]
    date_columns = [d.isoformat() for d in date_list]
    
    submission_map = set()
    for sub in submissions:
        submission_map.add((sub[0], sub[1]))
        
    matrix_data = []
    
    for user in all_users:
        uid = user['user_id']
        name = user['full_name']
        
        row = {'Name': name}
        
        present_count = 0
        total_days = len(date_columns)
        
        for d_str in date_columns:
            if (uid, d_str) in submission_map:
                row[d_str] = 'P'
                present_count += 1
            else:
                row[d_str] = ''
                
        attendance_pct = (present_count / total_days) * 100 if total_days > 0 else 0
        
        row['Total Present'] = present_count
        row['Total Days'] = total_days
        row['Percentage'] = round(attendance_pct, 1)
        
        matrix_data.append(row)
        
    if not matrix_data:
        return None
        
    df = pd.DataFrame(matrix_data)
    df.sort_values(by='Percentage', ascending=True, inplace=True)
    
    cols = ['Name', 'Percentage', 'Total Present'] + date_columns
    df = df[cols]
    
    filename = f"attendance_register_anganwadi_{start_str}_to_{end_str}.xlsx"
    df.to_excel(filename, index=False)
    
    return filename
