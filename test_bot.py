import database
import reports
import os
import shutil

def test_flow():
    print("Testing 1: Initialize DB")
    if os.path.exists("anganwadi.db"):
        os.remove("anganwadi.db")
    database.init_db()
    
    print("Testing 2: Add Users")
    database.add_user_if_not_exists(101, "Sita Devi")
    database.add_user_if_not_exists(102, "Gita Sharma")
    database.add_user_if_not_exists(103, "Rani Verma")
    
    print("Testing 3: Log Submissions")
    status, streak = database.log_submission(101)
    print(f"User 101 submitted. Status: {status}, Streak: {streak}")
    assert status == 'new_submission'
    assert streak == 1
    
    status, streak = database.log_submission(101)
    print(f"User 101 submitted again. Status: {status}, Streak: {streak}")
    assert status == 'already_submitted'
    
    print("Testing 4: Check Stats")
    count = database.get_submitted_today_count()
    print(f"Submitted today: {count}")
    assert count == 1
    
    print("Testing 5: Generate Reports")
    report_text = reports.get_performance_report_text()
    print("Report Text:")
    print(report_text)
    
    excel_file = reports.generate_missing_workers_excel()
    if excel_file:
        print(f"Excel file generated: {excel_file}")
        # Verify Excel content (optional, just checking existence)
        assert os.path.exists(excel_file)
        os.remove(excel_file)
    else:
        print("No Excel file generated (All users submitted?)")
        
    print("ALL TESTS PASSED!")

if __name__ == "__main__":
    test_flow()
