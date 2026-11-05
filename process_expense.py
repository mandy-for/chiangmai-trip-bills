import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Fixed Exchange Rate: 1 HKD = 4.3 THB (You can adjust this later)
HKD_TO_THB = 4.3

def convert_to_hkd(amount, currency):
    if currency.upper() == 'HKD':
        return amount
    elif currency.upper() == 'THB':
        return amount / HKD_TO_THB
    return amount

def main():
    # 1. Load the incoming transaction payload sent by the web form
    new_expense_str = os.environ.get('NEW_EXPENSE')
    if not new_expense_str:
        print("No new expense payload found.")
        return
    
    new_expense = json.loads(new_expense_str)
    
    # 2. Append the new expense to our repository's local log history
    expenses = []
    if os.path.exists('expenses.json'):
        with open('expenses.json', 'r', encoding='utf-8') as f:
            try:
                expenses = json.load(f)
            except:
                expenses = []
                
    expenses.append(new_expense)
    
    with open('expenses.json', 'w', encoding='utf-8') as f:
        json.dump(expenses, f, indent=2, ensure_ascii=False)

    # 3. Calculate everyone's running totals
    travelers = ['Mandy', 'Winifred', 'Mark']
    total_paid = {t: 0.0 for t in travelers}
    total_owed = {t: 0.0 for t in travelers}
    
    for exp in expenses:
        payee = exp['paid_by']
        amt_hkd = convert_to_hkd(exp['amount'], exp['currency'])
        
        if payee in total_paid:
            total_paid[payee] += amt_hkd
            
        split_type = exp['split_type']
        details = exp['split_details']
        
        if split_type == 'equally':
            share = amt_hkd / len(travelers)
            for t in travelers:
                total_owed[t] += share
        elif split_type == 'by_amount':
            for t, person_amt in details.items():
                total_owed[t] += convert_to_hkd(float(person_amt), exp['currency'])
        elif split_type == 'by_percentage':
            for t, pct in details.items():
                total_owed[t] += amt_hkd * (float(pct) / 100.0)

    # 4. Generate the Google Sheet Rows
    summary_rows = [["Name", "Total Paid (HKD)", "Should Pay (HKD)", "Net Balance (HKD)"]]
    for t in travelers:
        balance = total_paid[t] - total_owed[t]
        summary_rows.append([t, f"{total_paid[t]:.2f}", f"{total_owed[t]:.2f}", f"{balance:.2f}"])

    # 5. Connect and push data to Google Sheets
    creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_dict)
    service = build('sheets', 'v4', credentials=creds)
    spreadsheet_id = os.environ['SPREADSHEET_ID']
    
    # Overwrite Sheet1 with fresh real-time numbers
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, range="Sheet1!A1",
        valueInputOption="RAW", body={'values': summary_rows}
    ).execute()
    
    print("Google Sheets engine recalculation completely fresh and compiled!")

if __name__ == "__main__":
    main()
