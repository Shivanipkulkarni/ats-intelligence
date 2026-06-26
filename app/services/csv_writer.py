"""
CSV Writer for Hackathon Submission

Generates properly formatted CSV output that meets submission requirements:
- Exactly 100 rows + 1 header
- Columns: candidate_id, rank, score, reasoning
- Scores non-increasing (rank 1 >= rank 2 >= ... >= rank 100)
- UTF-8 encoding
"""

import csv
from typing import List, Dict, Any
from pathlib import Path


class SubmissionCSVWriter:
    """
    Writes screening results to hackathon-compliant CSV format.
    """
    
    def __init__(self, output_path: str):
        """
        Args:
            output_path: Path to output CSV file
        """
        self.output_path = Path(output_path)
    
    def write(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Write candidates to CSV in submission format.
        
        Args:
            candidates: List of candidate dicts with keys:
                - resume_id (or candidate_id)
                - rank
                - overall_score
                - reasoning (optional, will be generated if missing)
        
        Returns:
            Dict with validation results and stats
        """
        # Validate we have exactly 100 candidates
        if len(candidates) != 100:
            raise ValueError(f"Must have exactly 100 candidates, got {len(candidates)}")
        
        # Sort by rank to ensure correct order
        candidates_sorted = sorted(candidates, key=lambda x: x.get('rank', 999))
        
        # Validation checks
        validation = self._validate_candidates(candidates_sorted)
        
        if not validation['valid']:
            raise ValueError(f"Validation failed: {validation['errors']}")
        
        # Write CSV
        with open(self.output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            
            # Header
            writer.writerow(['candidate_id', 'rank', 'score', 'reasoning'])
            
            # Data rows
            for candidate in candidates_sorted:
                candidate_id = candidate.get('resume_id') or candidate.get('candidate_id')
                rank = candidate.get('rank')
                score = candidate.get('overall_score', 0) / 100  # Normalize to 0-1
                reasoning = candidate.get('reasoning', '')
                
                # Escape reasoning if it contains special chars
                reasoning_clean = reasoning.replace('"', "'").replace('\n', ' ').replace('\r', '')
                
                writer.writerow([
                    candidate_id,
                    rank,
                    f"{score:.4f}",  # 4 decimal places
                    reasoning_clean
                ])
        
        return {
            'success': True,
            'output_path': str(self.output_path),
            'rows_written': len(candidates_sorted),
            'validation': validation
        }
    
    def _validate_candidates(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate candidates meet submission requirements.
        
        Returns:
            Dict with 'valid' bool and 'errors' list
        """
        errors = []
        warnings = []
        
        # Check 1: Exactly 100 candidates
        if len(candidates) != 100:
            errors.append(f"Must have exactly 100 candidates, got {len(candidates)}")
        
        # Check 2: All ranks 1-100 present exactly once
        ranks = [c.get('rank') for c in candidates]
        expected_ranks = set(range(1, 101))
        actual_ranks = set(ranks)
        
        if actual_ranks != expected_ranks:
            missing = expected_ranks - actual_ranks
            extra = actual_ranks - expected_ranks
            if missing:
                errors.append(f"Missing ranks: {sorted(missing)[:10]}")
            if extra:
                errors.append(f"Extra/invalid ranks: {sorted(extra)[:10]}")
        
        # Check for duplicate ranks
        if len(ranks) != len(set(ranks)):
            duplicates = [r for r in ranks if ranks.count(r) > 1]
            errors.append(f"Duplicate ranks found: {set(duplicates)}")
        
        # Check 3: All candidate_ids present and unique
        candidate_ids = [
            c.get('resume_id') or c.get('candidate_id') 
            for c in candidates
        ]
        
        if len(candidate_ids) != len(set(candidate_ids)):
            errors.append("Duplicate candidate_ids found")
        
        if any(not cid for cid in candidate_ids):
            errors.append("Some candidates missing candidate_id")
        
        # Check 4: Scores are non-increasing
        scores = [c.get('overall_score', 0) for c in candidates]
        
        for i in range(len(scores) - 1):
            if scores[i] < scores[i + 1]:
                errors.append(
                    f"Score not non-increasing: rank {candidates[i]['rank']} "
                    f"score {scores[i]:.2f} < rank {candidates[i+1]['rank']} "
                    f"score {scores[i+1]:.2f}"
                )
                break
        
        # Check 5: Reasoning quality warnings
        reasonings = [c.get('reasoning', '') for c in candidates]
        
        # Empty reasoning
        empty_count = sum(1 for r in reasonings if not r.strip())
        if empty_count > 0:
            warnings.append(f"{empty_count} candidates have empty reasoning")
        
        # All identical reasoning
        if len(set(reasonings)) == 1 and reasonings:
            warnings.append("All reasoning strings are identical (will be penalized)")
        
        # Very short reasoning
        short_count = sum(1 for r in reasonings if len(r.strip()) < 20)
        if short_count > 10:
            warnings.append(f"{short_count} candidates have very short reasoning (<20 chars)")
        
        # Check 6: Score format (should be 0-100 or 0-1)
        max_score = max(scores) if scores else 0
        if max_score > 1.5:  # Assume 0-100 scale
            # This is fine, we'll normalize in write()
            pass
        elif max_score <= 1.0:  # Already normalized
            pass
        else:
            warnings.append(f"Unusual score range: max={max_score}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'stats': {
                'total_candidates': len(candidates),
                'unique_ranks': len(set(ranks)),
                'unique_candidate_ids': len(set(candidate_ids)),
                'empty_reasoning_count': empty_count if 'empty_count' in locals() else 0,
                'min_score': min(scores) if scores else 0,
                'max_score': max(scores) if scores else 0,
            }
        }


def write_submission_csv(
    candidates: List[Dict[str, Any]], 
    output_path: str,
    validate_only: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to write submission CSV.
    
    Args:
        candidates: List of candidate dicts
        output_path: Path to output CSV
        validate_only: If True, only validate without writing
    
    Returns:
        Dict with success status and validation results
    """
    writer = SubmissionCSVWriter(output_path)
    
    if validate_only:
        # Validate without writing
        validation = writer._validate_candidates(
            sorted(candidates, key=lambda x: x.get('rank', 999))
        )
        return {
            'valid': validation['valid'],
            'validation': validation
        }
    else:
        # Write and validate
        return writer.write(candidates)
