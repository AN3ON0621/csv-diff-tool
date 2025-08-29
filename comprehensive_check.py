#!/usr/bin/env python3
"""
Comprehensive check to ensure NO modifications are missed
This will verify EVERY person marked as "unchanged"
"""

import pandas as pd
import json
from change_tracker import ChangeTracker

def comprehensive_verification():
    print("=" * 70)
    print("COMPREHENSIVE VERIFICATION - CHECKING ALL 'UNCHANGED' USERS")
    print("=" * 70)
    
    # Load the change tracker results
    with open('change_tracking_report.json', 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    # Create tracker to use its logic
    tracker = ChangeTracker('phonelistfiles/lotus.csv', 'phonelistfiles/corp.csv')
    tracker.load_data()
    
    # Get all users who had changes reported
    changed_users_keys = set()
    for change in report['changes']:
        # Recreate the key the same way the tracker does
        name = change['user']
        chinese_name = change.get('chinese_name', '')
        if chinese_name:
            key = f"{tracker.normalize_name(name)}|{chinese_name}"
        else:
            key = tracker.normalize_name(name)
        changed_users_keys.add(key)
    
    print(f"Users reported as changed: {len(changed_users_keys)}")
    
    # Get ALL common users
    common_users = tracker.find_common_users()
    print(f"Total common users: {len(common_users)}")
    
    # Find users marked as "unchanged"
    unchanged_users = {}
    for user_key, (old_record, new_record) in common_users.items():
        if user_key not in changed_users_keys:
            unchanged_users[user_key] = (old_record, new_record)
    
    print(f"Users marked as 'unchanged': {len(unchanged_users)}")
    print(f"Verification: {len(changed_users_keys)} + {len(unchanged_users)} = {len(changed_users_keys) + len(unchanged_users)} (should equal {len(common_users)})")
    
    # Now check EVERY "unchanged" user for missed modifications
    print(f"\nChecking ALL {len(unchanged_users)} 'unchanged' users...")
    print("This may take a moment...\n")
    
    fields_to_check = ['Name', 'Title', 'Phone', 'Fax', 'Location']
    missed_changes = []
    checked_count = 0
    
    for user_key, (old_record, new_record) in unchanged_users.items():
        checked_count += 1
        if checked_count % 200 == 0:
            print(f"  Checked {checked_count}/{len(unchanged_users)} users...")
        
        user_missed_changes = []
        
        for field in fields_to_check:
            old_val = str(old_record.get(field, '')).strip()
            new_val = str(new_record.get(field, '')).strip()
            
            # Use EXACT same normalization as the tracker
            old_normalized = old_val.lower().replace('-', ' ').replace(',', ' ').replace('  ', ' ').strip()
            new_normalized = new_val.lower().replace('-', ' ').replace(',', ' ').replace('  ', ' ').strip()
            
            if old_normalized != new_normalized:
                # This is a REAL missed change!
                similarity = tracker.similarity_score(old_normalized, new_normalized)
                
                # Classify the change the same way the tracker does
                if old_val == '' and new_val != '':
                    change_type = 'Added'
                elif old_val != '' and new_val == '':
                    change_type = 'Removed'
                elif similarity > 0.8:
                    change_type = 'Minor Change (Possible Typo)'
                elif similarity > 0.5:
                    change_type = 'Moderate Change'
                else:
                    change_type = 'Major Change'
                
                user_missed_changes.append({
                    'field': field,
                    'old_value': old_val,
                    'new_value': new_val,
                    'change_type': change_type,
                    'similarity': round(similarity, 2)
                })
        
        if user_missed_changes:
            missed_changes.append({
                'user_key': user_key,
                'user_name': old_record.get('Name', ''),
                'chinese_name': old_record.get('Chi Name', ''),
                'changes': user_missed_changes
            })
    
    print(f"  Checked all {checked_count} users.\n")
    
    # Report results
    print("=" * 70)
    print("COMPREHENSIVE VERIFICATION RESULTS")
    print("=" * 70)
    
    if len(missed_changes) == 0:
        print("🎉 EXCELLENT! No missed changes found!")
        print("✅ The change tracker caught ALL modifications!")
        print("✅ All 'unchanged' users are truly unchanged!")
    else:
        print(f"⚠️  FOUND {len(missed_changes)} users with missed changes!")
        print("\nDETAILS OF MISSED CHANGES:")
        print("-" * 50)
        
        for i, missed_user in enumerate(missed_changes, 1):
            print(f"\n{i}. {missed_user['user_name']}")
            if missed_user['chinese_name']:
                print(f"   Chinese Name: {missed_user['chinese_name']}")
            print(f"   Key: {missed_user['user_key']}")
            
            for change in missed_user['changes']:
                print(f"   📝 Field: {change['field']}")
                print(f"      Type: {change['change_type']}")
                print(f"      Old: '{change['old_value']}'")
                print(f"      New: '{change['new_value']}'")
                print(f"      Similarity: {change['similarity']}")
                print()
    
    # Summary statistics
    total_field_changes_missed = sum(len(user['changes']) for user in missed_changes)
    
    print(f"\nFINAL SUMMARY:")
    print(f"- Total common users: {len(common_users)}")
    print(f"- Users with reported changes: {len(changed_users_keys)}")
    print(f"- Users marked as unchanged: {len(unchanged_users)}")
    print(f"- Users with missed changes: {len(missed_changes)}")
    print(f"- Total missed field changes: {total_field_changes_missed}")
    
    if len(missed_changes) == 0:
        print(f"\n🎯 CONFIDENCE LEVEL: 100%")
        print(f"   The tool is COMPLETELY ACCURATE!")
    else:
        accuracy = ((len(unchanged_users) - len(missed_changes)) / len(unchanged_users)) * 100
        print(f"\n📊 ACCURACY RATE: {accuracy:.1f}%")
        print(f"   Missed {len(missed_changes)} out of {len(unchanged_users)} 'unchanged' users")

if __name__ == "__main__":
    comprehensive_verification()
