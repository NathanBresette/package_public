#!/usr/bin/env python3
"""
Enhanced Admin Dashboard for RStudio AI
Provides comprehensive user management, cost tracking, and monitoring
"""

import requests
import json
from tabulate import tabulate
from datetime import datetime, timedelta
import argparse
import sys

# Configuration
BACKEND_URL = "http://127.0.0.1:8001"
ADMIN_ACCESS_CODE = "ADMIN_SECRET_123"  # Change this in production!

def make_request(endpoint, method="GET", data=None):
    """Make authenticated request to backend"""
    url = f"{BACKEND_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    try:
        if method == "GET":
            response = requests.get(url, params=data, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, json=data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def show_user_list():
    """Display all users with their statistics"""
    print("🔍 RStudio AI - User Management Dashboard")
    print("=" * 60)
    
    data = make_request("/users/list", data={"admin_access_code": ADMIN_ACCESS_CODE})
    if not data:
        print("Failed to fetch user data")
        return
    
    users = data.get("users", [])
    if not users:
        print("No users found")
        return
    
    # Prepare table data
    table_data = []
    for user in users:
        last_activity = user.get("last_activity", "")
        if last_activity:
            try:
                dt = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                last_activity = dt.strftime('%Y-%m-%d %H:%M')
            except:
                last_activity = "Unknown"
        
        status = "🟢 Active" if user.get("is_active", True) else "🔴 Disabled"
        
        table_data.append([
            user.get("access_code", ""),
            user.get("user_name", ""),
            user.get("email", ""),
            status,
            user.get("total_requests", 0),
            f"${user.get('total_cost', 0):.2f}",
            user.get("today_requests", 0),
            f"${user.get('today_cost', 0):.2f}",
            last_activity
        ])
    
    headers = ["Access Code", "Name", "Email", "Status", "Total Requests", 
               "Total Cost", "Today Requests", "Today Cost", "Last Activity"]
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"\nTotal Users: {len(users)}")

def show_system_analytics(days=30):
    """Display system-wide analytics"""
    print(f"📊 System Analytics (Last {days} days)")
    print("=" * 60)
    
    data = make_request("/admin/analytics", 
                       data={"admin_access_code": ADMIN_ACCESS_CODE, "days": days})
    if not data:
        print("Failed to fetch analytics")
        return
    
    print(f"Total Requests: {data.get('total_requests', 0)}")
    print(f"Total Cost: ${data.get('total_cost', 0):.2f}")
    print(f"Total Tokens: {data.get('total_tokens', 0):,}")
    print(f"Success Rate: {data.get('success_rate', 0):.1%}")
    print(f"Avg Cost/Request: ${data.get('avg_cost_per_request', 0):.4f}")
    print(f"Avg Tokens/Request: {data.get('avg_tokens_per_request', 0):.0f}")
    
    # Daily breakdown
    daily_stats = data.get('daily_breakdown', {})
    if daily_stats:
        print(f"\n📈 Daily Breakdown (Last {days} days):")
        daily_data = []
        for date, stats in sorted(daily_stats.items()):
            daily_data.append([
                date,
                stats.get('requests', 0),
                f"${stats.get('cost', 0):.2f}",
                stats.get('tokens', 0)
            ])
        
        daily_headers = ["Date", "Requests", "Cost", "Tokens"]
        print(tabulate(daily_data, headers=daily_headers, tablefmt="grid"))

def create_user():
    """Create a new user"""
    print("👤 Create New User")
    print("=" * 30)
    
    access_code = input("Access Code: ").strip()
    user_name = input("User Name: ").strip()
    email = input("Email (optional): ").strip()
    
    try:
        daily_limit = int(input("Daily Request Limit (default 100): ") or "100")
        monthly_budget = float(input("Monthly Budget USD (default 10.0): ") or "10.0")
    except ValueError:
        print("Invalid number format")
        return
    
    data = {
        "access_code": access_code,
        "user_name": user_name,
        "email": email,
        "daily_limit": daily_limit,
        "monthly_budget": monthly_budget
    }
    
    admin_data = {"admin_access_code": ADMIN_ACCESS_CODE}
    
    result = make_request("/users/create", method="POST", 
                         data={**data, **admin_data})
    
    if result and result.get("success"):
        print(f"✅ User {user_name} created successfully!")
    else:
        print("❌ Failed to create user")

def update_user():
    """Update user settings"""
    print("✏️ Update User")
    print("=" * 30)
    
    access_code = input("Access Code: ").strip()
    
    print("Enter new values (press Enter to skip):")
    user_name = input("User Name: ").strip() or None
    email = input("Email: ").strip() or None
    
    try:
        daily_limit = input("Daily Request Limit: ").strip()
        daily_limit = int(daily_limit) if daily_limit else None
        
        monthly_budget = input("Monthly Budget USD: ").strip()
        monthly_budget = float(monthly_budget) if monthly_budget else None
        
        rate_limit = input("Rate Limit (requests/min): ").strip()
        rate_limit = int(rate_limit) if rate_limit else None
    except ValueError:
        print("Invalid number format")
        return
    
    notes = input("Notes: ").strip() or None
    
    updates = {}
    if user_name: updates["user_name"] = user_name
    if email: updates["email"] = email
    if daily_limit: updates["daily_limit"] = daily_limit
    if monthly_budget: updates["monthly_budget"] = monthly_budget
    if rate_limit: updates["rate_limit"] = rate_limit
    if notes: updates["notes"] = notes
    
    if not updates:
        print("No updates provided")
        return
    
    admin_data = {"admin_access_code": ADMIN_ACCESS_CODE}
    
    result = make_request(f"/users/{access_code}", method="PUT", 
                         data={**updates, **admin_data})
    
    if result and result.get("success"):
        print(f"✅ User {access_code} updated successfully!")
    else:
        print("❌ Failed to update user")

def toggle_user_status():
    """Enable or disable user"""
    print("🔄 Toggle User Status")
    print("=" * 30)
    
    access_code = input("Access Code: ").strip()
    action = input("Action (enable/disable): ").strip().lower()
    
    if action not in ["enable", "disable"]:
        print("Invalid action. Use 'enable' or 'disable'")
        return
    
    admin_data = {"admin_access_code": ADMIN_ACCESS_CODE}
    endpoint = f"/users/{access_code}/{action}"
    
    result = make_request(endpoint, method="POST", data=admin_data)
    
    if result and result.get("success"):
        print(f"✅ User {access_code} {action}d successfully!")
    else:
        print(f"❌ Failed to {action} user")

def delete_user():
    """Delete user and all their data"""
    print("🗑️ Delete User")
    print("=" * 30)
    
    access_code = input("Access Code: ").strip()
    confirm = input(f"Are you sure you want to delete user {access_code}? (yes/no): ").strip().lower()
    
    if confirm != "yes":
        print("Deletion cancelled")
        return
    
    admin_data = {"admin_access_code": ADMIN_ACCESS_CODE}
    
    result = make_request(f"/users/{access_code}", method="DELETE", data=admin_data)
    
    if result and result.get("success"):
        print(f"✅ User {access_code} deleted successfully!")
    else:
        print("❌ Failed to delete user")

def show_user_details():
    """Show detailed user information"""
    print("👤 User Details")
    print("=" * 30)
    
    access_code = input("Access Code: ").strip()
    
    data = make_request(f"/usage/{access_code}")
    if not data:
        print("Failed to fetch user data")
        return
    
    user_profile = data.get("user_profile", {})
    
    print(f"Access Code: {user_profile.get('access_code', '')}")
    print(f"Name: {user_profile.get('user_name', '')}")
    print(f"Email: {user_profile.get('email', '')}")
    print(f"Status: {'🟢 Active' if user_profile.get('is_active', True) else '🔴 Disabled'}")
    print(f"Created: {user_profile.get('created_at', '')}")
    print(f"Last Activity: {user_profile.get('last_activity', '')}")
    print(f"Total Requests: {user_profile.get('total_requests', 0)}")
    print(f"Total Cost: ${user_profile.get('total_cost', 0):.2f}")
    print(f"Total Tokens: {user_profile.get('total_tokens', 0):,}")
    print(f"Daily Limit: {user_profile.get('daily_limit', 0)}")
    print(f"Monthly Budget: ${user_profile.get('monthly_budget', 0):.2f}")
    print(f"Rate Limit: {user_profile.get('rate_limit', 0)}/min")
    
    # Current usage
    print(f"\n📊 Current Usage:")
    print(f"Today Requests: {data.get('today_requests', 0)}")
    print(f"Today Cost: ${data.get('today_cost', 0):.2f}")
    print(f"Monthly Requests: {data.get('monthly_requests', 0)}")
    print(f"Monthly Cost: ${data.get('monthly_cost', 0):.2f}")
    print(f"Daily Limit Remaining: {data.get('daily_limit_remaining', 0)}")
    print(f"Monthly Budget Remaining: ${data.get('monthly_budget_remaining', 0):.2f}")
    print(f"Rate Limit Remaining: {data.get('rate_limit_remaining', 0)}")

def main():
    """Main admin dashboard"""
    parser = argparse.ArgumentParser(description="RStudio AI Admin Dashboard")
    parser.add_argument("--action", choices=[
        "list", "analytics", "create", "update", "toggle", "delete", "details"
    ], help="Action to perform")
    parser.add_argument("--days", type=int, default=30, help="Days for analytics")
    
    args = parser.parse_args()
    
    if args.action:
        if args.action == "list":
            show_user_list()
        elif args.action == "analytics":
            show_system_analytics(args.days)
        elif args.action == "create":
            create_user()
        elif args.action == "update":
            update_user()
        elif args.action == "toggle":
            toggle_user_status()
        elif args.action == "delete":
            delete_user()
        elif args.action == "details":
            show_user_details()
    else:
        # Interactive mode
        while True:
            print("\n🔧 RStudio AI Admin Dashboard")
            print("=" * 40)
            print("1. List Users")
            print("2. System Analytics")
            print("3. Create User")
            print("4. Update User")
            print("5. Toggle User Status")
            print("6. Delete User")
            print("7. User Details")
            print("8. Exit")
            
            choice = input("\nSelect option (1-8): ").strip()
            
            if choice == "1":
                show_user_list()
            elif choice == "2":
                days = input("Days for analytics (default 30): ").strip()
                days = int(days) if days.isdigit() else 30
                show_system_analytics(days)
            elif choice == "3":
                create_user()
            elif choice == "4":
                update_user()
            elif choice == "5":
                toggle_user_status()
            elif choice == "6":
                delete_user()
            elif choice == "7":
                show_user_details()
            elif choice == "8":
                print("Goodbye!")
                break
            else:
                print("Invalid option")

if __name__ == "__main__":
    main() 