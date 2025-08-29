#!/usr/bin/env python3
"""
Change Tracker Algorithm
Compares two phone list CSV files to detect small changes in existing users' data
Ignores resignees and new joiners, focuses only on changes in existing users
"""

import csv
import pandas as pd
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Any
import json
import os
from datetime import datetime


class ChangeTracker:
    def __init__(self, old_csv_path: str, new_csv_path: str):
        """
        Initialize the change tracker with paths to old and new CSV files.
        
        Args:
            old_csv_path: Path to the old phone list CSV (hopelotuscsv.csv)
            new_csv_path: Path to the new phone list CSV (corpchin.csv)
        """
        self.old_csv_path = old_csv_path
        self.new_csv_path = new_csv_path
        self.old_data = None
        self.new_data = None
        self.changes = []
        self.statistics = {
            'total_old_records': 0,
            'total_new_records': 0,
            'common_users': 0,
            'new_joiners': 0,
            'resignees': 0,
            'users_with_changes': 0,
            'total_field_changes': 0
        }
    
    def normalize_name(self, name: str) -> str:
        """
        Normalize name for comparison by removing extra spaces, 
        standardizing capitalization, and removing punctuation variations.
        """
        if pd.isna(name) or name == '':
            return ''
        
        # Remove extra spaces and strip
        name = ' '.join(name.split())
        
        # Convert to uppercase for comparison
        name = name.upper()
        
        # Remove common punctuation variations
        name = name.replace(',', '').replace('.', '').replace('-', ' ')
        
        return name.strip()
    
    def create_user_key(self, row: pd.Series) -> str:
        """
        Create a unique key for each user based on their name and Chinese name.
        This helps identify the same person across both lists.
        """
        # Use combination of normalized English name and Chinese name
        eng_name = self.normalize_name(str(row.get('Name', '')))
        chi_name = str(row.get('Chi Name', '')).strip() if pd.notna(row.get('Chi Name')) else ''
        
        # Primary key is normalized English name
        # If Chinese name exists, use it as additional identifier
        if chi_name:
            return f"{eng_name}|{chi_name}"
        return eng_name
    
    def load_data(self):
        """Load CSV files into pandas DataFrames."""
        print(f"Loading old phone list from: {self.old_csv_path}")
        self.old_data = pd.read_csv(self.old_csv_path)
        self.statistics['total_old_records'] = len(self.old_data)
        
        print(f"Loading new phone list from: {self.new_csv_path}")
        self.new_data = pd.read_csv(self.new_csv_path)
        self.statistics['total_new_records'] = len(self.new_data)
        
        print(f"Old records: {self.statistics['total_old_records']}")
        print(f"New records: {self.statistics['total_new_records']}")
    
    def find_common_users(self) -> Dict[str, Tuple[pd.Series, pd.Series]]:
        """
        Find users that exist in both old and new lists.
        Returns a dictionary mapping user keys to (old_record, new_record) tuples.
        """
        # Create dictionaries with user keys
        old_users = {}
        for idx, row in self.old_data.iterrows():
            key = self.create_user_key(row)
            if key:  # Skip empty keys
                old_users[key] = row
        
        new_users = {}
        for idx, row in self.new_data.iterrows():
            key = self.create_user_key(row)
            if key:  # Skip empty keys
                new_users[key] = row
        
        # Find common users
        common_keys = set(old_users.keys()) & set(new_users.keys())
        common_users = {
            key: (old_users[key], new_users[key]) 
            for key in common_keys
        }
        
        # Update statistics
        self.statistics['common_users'] = len(common_users)
        self.statistics['new_joiners'] = len(set(new_users.keys()) - set(old_users.keys()))
        self.statistics['resignees'] = len(set(old_users.keys()) - set(new_users.keys()))
        
        print(f"\nFound {len(common_users)} common users")
        print(f"New joiners (ignored): {self.statistics['new_joiners']}")
        print(f"Resignees (ignored): {self.statistics['resignees']}")
        
        return common_users
    
    def similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity score between two strings."""
        if pd.isna(str1) or pd.isna(str2):
            str1 = '' if pd.isna(str1) else str(str1)
            str2 = '' if pd.isna(str2) else str(str2)
        
        return SequenceMatcher(None, str(str1), str(str2)).ratio()
    
    def detect_field_change(self, old_value: Any, new_value: Any, field_name: str) -> Dict:
        """
        Detect if a field has changed and return change details.
        """
        # Handle None/NaN values
        old_str = '' if pd.isna(old_value) else str(old_value).strip()
        new_str = '' if pd.isna(new_value) else str(new_value).strip()
        
        # Normalize case, hyphens, and commas for comparison (ignore capitalization, hyphen, and comma differences)
        old_str_normalized = old_str.lower().replace('-', ' ').replace(',', ' ').replace('  ', ' ').strip()
        new_str_normalized = new_str.lower().replace('-', ' ').replace(',', ' ').replace('  ', ' ').strip()
        
        # Check if values are different (ignoring case)
        if old_str_normalized != new_str_normalized:
            # Calculate similarity to detect minor changes vs major changes
            similarity = self.similarity_score(old_str_normalized, new_str_normalized)
            
            # Categorize the change
            if old_str == '' and new_str != '':
                change_type = 'Added'
            elif old_str != '' and new_str == '':
                change_type = 'Removed'
            elif similarity > 0.8:
                change_type = 'Minor Change (Possible Typo)'
            elif similarity > 0.5:
                change_type = 'Moderate Change'
            else:
                change_type = 'Major Change'
            
            return {
                'field': field_name,
                'old_value': old_str,
                'new_value': new_str,
                'change_type': change_type,
                'similarity': round(similarity, 2)
            }
        
        return None
    
    def compare_users(self, common_users: Dict[str, Tuple[pd.Series, pd.Series]]):
        """
        Compare field values for common users and detect changes.
        """
        fields_to_compare = ['Name', 'Title', 'Phone', 'Fax', 'Location']
        
        users_with_changes = set()
        
        for user_key, (old_record, new_record) in common_users.items():
            user_changes = []
            
            # Compare each field
            for field in fields_to_compare:
                change = self.detect_field_change(
                    old_record.get(field),
                    new_record.get(field),
                    field
                )
                
                if change:
                    user_changes.append(change)
                    self.statistics['total_field_changes'] += 1
            
     
            if user_changes:
                users_with_changes.add(user_key)
                self.changes.append({
                    'user': old_record.get('Name', ''),
                    'chinese_name': old_record.get('Chi Name', ''),
                    'changes': user_changes
                })
        
        self.statistics['users_with_changes'] = len(users_with_changes)
        print(f"\nFound {len(users_with_changes)} users with changes")
        print(f"Total field changes detected: {self.statistics['total_field_changes']}")
    
    def analyze_changes(self):
        """
        Main method to run the complete analysis.
        """
        print("=" * 60)
        print("PHONE LIST CHANGE TRACKER")
        print("=" * 60)
        
        # Load data
        self.load_data()
        
        # Find common users
        common_users = self.find_common_users()
        
        # Compare common users
        self.compare_users(common_users)
        
        print("\n" + "=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)
    
    def cleanup_old_reports(self):
        """Remove old report files before generating new ones."""
        report_files = [
            'change_tracking_report.json',
            'change_tracking_report.txt', 
            'change_tracking_report.html'
        ]
        
        for report_file in report_files:
            if os.path.exists(report_file):
                try:
                    os.remove(report_file)
                    print(f"Removed old report: {report_file}")
                except OSError as e:
                    print(f"Warning: Could not remove {report_file}: {e}")
    
    def generate_report(self, output_format='all'):
        """
        Generate a detailed report of all detected changes.
        
        Args:
            output_format: 'json', 'text', 'html', or 'all'
        """
        # Clean up old reports first
        self.cleanup_old_reports()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if output_format in ['json', 'all']:
            self._generate_json_report(timestamp)
        
        if output_format in ['text', 'all']:
            self._generate_text_report(timestamp)
        
        if output_format in ['html', 'all']:
            self._generate_html_report(timestamp)
    
    def _generate_json_report(self, timestamp: str):
        """Generate JSON report."""
        report = {
            'timestamp': timestamp,
            'statistics': self.statistics,
            'changes': self.changes
        }
        
        with open('change_tracking_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"JSON report saved to: change_tracking_report.json")
    
    def _generate_text_report(self, timestamp: str):
        """Generate human-readable text report."""
        with open('change_tracking_report.txt', 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("PHONE LIST CHANGE TRACKING REPORT\n")
            f.write(f"Generated: {timestamp}\n")
            f.write("=" * 80 + "\n\n")
            
            # Statistics
            f.write("SUMMARY STATISTICS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total records in old list: {self.statistics['total_old_records']}\n")
            f.write(f"Total records in new list: {self.statistics['total_new_records']}\n")
            f.write(f"Common users (analyzed): {self.statistics['common_users']}\n")
            f.write(f"New joiners (ignored): {self.statistics['new_joiners']}\n")
            f.write(f"Resignees (ignored): {self.statistics['resignees']}\n")
            f.write(f"Users with changes: {self.statistics['users_with_changes']}\n")
            f.write(f"Total field changes: {self.statistics['total_field_changes']}\n")
            f.write("\n")
            
            # Detailed changes
            f.write("DETAILED CHANGES BY USER:\n")
            f.write("=" * 80 + "\n\n")
            
            for i, user_change in enumerate(self.changes, 1):
                f.write(f"{i}. {user_change['user']}")
                if user_change['chinese_name']:
                    f.write(f" ({user_change['chinese_name']})")
                f.write("\n")
                f.write("-" * 40 + "\n")
                
                for change in user_change['changes']:
                    f.write(f"   Field: {change['field']}\n")
                    f.write(f"   Type: {change['change_type']}\n")
                    f.write(f"   Old: '{change['old_value']}'\n")
                    f.write(f"   New: '{change['new_value']}'\n")
                    f.write(f"   Similarity: {change['similarity']}\n")
                    f.write("\n")
                
                f.write("\n")
        
        print(f"Text report saved to: change_tracking_report.txt")
    
    def _generate_html_report(self, timestamp: str):
        """Generate HTML report with better visualization."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Phone List Change Tracking Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px;
        }}
        .statistics {{
            background-color: white;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .stat-item {{
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 3px;
        }}
        .changes {{
            background-color: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .user-change {{
            margin: 20px 0;
            padding: 15px;
            border-left: 4px solid #3498db;
            background-color: #f9f9f9;
        }}
        .change-detail {{
            margin: 10px 0;
            padding: 10px;
            background-color: white;
            border-radius: 3px;
        }}
        .change-type {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }}
        .type-added {{ background-color: #27ae60; color: white; }}
        .type-removed {{ background-color: #e74c3c; color: white; }}
        .type-minor {{ background-color: #f39c12; color: white; }}
        .type-moderate {{ background-color: #e67e22; color: white; }}
        .type-major {{ background-color: #c0392b; color: white; }}
        .old-value {{ color: #e74c3c; }}
        .new-value {{ color: #27ae60; }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            text-align: left;
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #34495e;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Phone List Change Tracking Report</h1>
        <p>Generated: {timestamp}</p>
        <p>Comparing: lotus.csv (old) → corp.csv (new)</p>
    </div>
    
    <div class="statistics">
        <h2>Summary Statistics</h2>
        <div class="stat-grid">
            <div class="stat-item">
                <strong>Old List Records:</strong> {self.statistics['total_old_records']}
            </div>
            <div class="stat-item">
                <strong>New List Records:</strong> {self.statistics['total_new_records']}
            </div>
            <div class="stat-item">
                <strong>Common Users:</strong> {self.statistics['common_users']}
            </div>
            <div class="stat-item">
                <strong>Users with Changes:</strong> {self.statistics['users_with_changes']}
            </div>
            <div class="stat-item">
                <strong>Total Changes:</strong> {self.statistics['total_field_changes']}
            </div>
            <div class="stat-item">
                <strong>New Joiners (Ignored):</strong> {self.statistics['new_joiners']}
            </div>
            <div class="stat-item">
                <strong>Resignees (Ignored):</strong> {self.statistics['resignees']}
            </div>
        </div>
    </div>
    
    <div class="changes">
        <h2>Detected Changes in Existing Users</h2>
        """
        
        for user_change in self.changes:
            html += f"""
        <div class="user-change">
            <h3>{user_change['user']} {f"({user_change['chinese_name']})" if user_change['chinese_name'] else ''}</h3>
            """
            
            for change in user_change['changes']:
                change_class = change['change_type'].lower().replace(' ', '-').replace('(possible-typo)', '').strip()
                if 'added' in change_class:
                    badge_class = 'type-added'
                elif 'removed' in change_class:
                    badge_class = 'type-removed'
                elif 'minor' in change_class:
                    badge_class = 'type-minor'
                elif 'moderate' in change_class:
                    badge_class = 'type-moderate'
                else:
                    badge_class = 'type-major'
                
                html += f"""
            <div class="change-detail">
                <span class="change-type {badge_class}">{change['change_type']}</span>
                <strong> {change['field']}</strong>
                <table>
                    <tr>
                        <td width="100">Old Value:</td>
                        <td class="old-value">'{change['old_value'] if change['old_value'] else '(empty)'}'</td>
                    </tr>
                    <tr>
                        <td>New Value:</td>
                        <td class="new-value">'{change['new_value'] if change['new_value'] else '(empty)'}'</td>
                    </tr>
                    <tr>
                        <td>Similarity:</td>
                        <td>{change['similarity'] * 100:.0f}%</td>
                    </tr>
                </table>
            </div>
                """
            
            html += """
        </div>
            """
        
        html += """
    </div>
</body>
</html>
        """
        
        with open('change_tracking_report.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"HTML report saved to: change_tracking_report.html")


def main():
    """Main function to run the change tracking analysis."""
    # Paths to CSV files
    old_csv = 'phonelistfiles/lotus.csv'  
    new_csv = 'phonelistfiles/corp.csv'   
    
    # Create tracker instance
    tracker = ChangeTracker(old_csv, new_csv)
    
    # Run analysis
    tracker.analyze_changes()
    
    # Generate reports in all formats
    tracker.generate_report('all')
    
    print("\n" + "=" * 60)
    print("All reports have been generated successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
