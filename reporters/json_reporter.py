from typing import Any, Dict
import json
import os
from datetime import datetime

class JSONReporter:
    @staticmethod 
    def export_to_json(scan_results: Dict[str, Any], analysis: Dict[str, Any], region: str, filename: str) -> None:
        """Export scan results to a JSON file."""
        try:
            os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        except (OSError, TypeError):
            pass  
        
        output_data = {
            'scan_date': datetime.now().isoformat(),
            'region': region, 
            'analysis': analysis,
            'scan_results': scan_results
        }

        try:
            with open(filename, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
        except IOError as e:
            raise IOError(f"Failed to write JSON file '{filename}': {e}") from e