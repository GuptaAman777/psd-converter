import requests
from PyQt6.QtCore import QThread, pyqtSignal

def compare_versions(v1, v2):
    """
    Compare semantic versions.
    Returns:
      -1 if v1 < v2
       0 if v1 == v2
       1 if v1 > v2
    """
    try:
        # Strip any leading 'v'
        v1 = str(v1).lstrip('v')
        v2 = str(v2).lstrip('v')
        
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]
        
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        for i in range(max_len):
            if v1_parts[i] < v2_parts[i]: return -1
            elif v1_parts[i] > v2_parts[i]: return 1
        return 0
    except Exception:
        # Fallback to simple string comparison if parsing fails
        if v1 < v2: return -1
        if v1 > v2: return 1
        return 0

class UpdateCheckerThread(QThread):
    update_result = pyqtSignal(dict, bool, str)
    
    def __init__(self, current_version, releases_url):
        super().__init__()
        self.current_version = current_version
        self.releases_url = releases_url
        
    def run(self):
        try:
            response = requests.get(self.releases_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get('tag_name', '').lstrip('v')
                release_notes = data.get('body', 'No release notes available.')
                release_url = data.get('html_url', '')
                
                update_available = compare_versions(self.current_version, latest_version) < 0
                
                self.update_result.emit({
                    'latest_version': latest_version,
                    'release_notes': release_notes,
                    'release_url': release_url
                }, update_available, "")
            else:
                self.update_result.emit({}, False, f"Failed to check for updates: HTTP {response.status_code}")
        except Exception as e:
            self.update_result.emit({}, False, f"Error checking for updates: {str(e)}")
