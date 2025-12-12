"""
AI grading using Google Gemini API.
Takes document text and rubric, returns structured feedback with comments and scores.
"""
import os
import sys
import json
import google.generativeai as genai
from typing import Dict, List, Any


def load_rubric(rubric_path: str) -> Dict[str, Any]:
    """Load rubric from JSON file."""
    with open(rubric_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_grading_prompt(document_text: str, rubric: Dict[str, Any]) -> str:
    """Create a structured prompt for AI grading."""
    criteria_text = ""
    for i, criterion in enumerate(rubric['criteria'], 1):
        criteria_text += f"{i}. {criterion['name']} ({criterion['max_points']} points)\n"
        criteria_text += f"   Description: {criterion['description']}\n\n"
    
    prompt = f"""You are an expert teaching assistant grading a student assignment. 

RUBRIC:
{rubric['name']} (Total: {rubric['total_points']} points)

{criteria_text}

STUDENT'S DOCUMENT:
{document_text}

TASK:
1. Evaluate the document against each rubric criterion
2. Identify specific issues and areas for improvement
3. Provide constructive feedback
4. Assign points for each criterion based on performance
5. Return your evaluation in the following JSON format:

{{
  "comments": [
    {{
      "text": "Comment text here",
      "location": "specific text excerpt or paragraph reference",
      "suggestion": "specific improvement suggestion"
    }}
  ],
  "scores": {{
    "Clarity and Organization": 18,
    "Content Quality": 25,
    ...
  }},
  "total_score": 85,
  "summary": "Brief overall feedback"
}}

IMPORTANT:
- Be specific and constructive in your comments
- Reference exact parts of the text when possible
- Provide actionable suggestions
- Scores should reflect actual performance, not just be high
- Total score should match sum of individual criterion scores
- Return ONLY valid JSON, no additional text

Return the JSON now:"""
    
    return prompt


def grade_with_ai(document_text: str, rubric: Dict[str, Any], model_name: str = "gemini-pro") -> Dict[str, Any]:
    """
    Grade document using Gemini API.
    
    Args:
        document_text: Text content of the document
        rubric: Rubric dictionary
        model_name: Gemini model to use
    
    Returns:
        Dictionary with comments, scores, and feedback
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    genai.configure(api_key=api_key)
    
    # Configure model
    generation_config = {
        "temperature": 0.3,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 4000,
    }
    
    model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)
    
    # Create prompt
    prompt = create_grading_prompt(document_text, rubric)
    
    try:
        # Generate response
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to fix common JSON issues
            response_text = response_text.replace("'", '"')
            result = json.loads(response_text)
        
        # Validate and normalize result
        validated_result = validate_grading_result(result, rubric)
        
        return validated_result
    
    except Exception as e:
        print(f"Error in AI grading: {e}", file=sys.stderr)
        raise


def validate_grading_result(result: Dict[str, Any], rubric: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize grading result."""
    # Ensure all required fields exist
    if 'comments' not in result:
        result['comments'] = []
    if 'scores' not in result:
        result['scores'] = {}
    if 'total_score' not in result:
        result['total_score'] = 0
    if 'summary' not in result:
        result['summary'] = ""
    
    # Validate scores match rubric criteria
    criterion_names = [c['name'] for c in rubric['criteria']]
    validated_scores = {}
    total = 0
    
    for criterion in rubric['criteria']:
        name = criterion['name']
        max_points = criterion['max_points']
        
        if name in result['scores']:
            score = result['scores'][name]
            # Ensure score is within valid range
            score = max(0, min(max_points, float(score)))
        else:
            score = 0
        
        validated_scores[name] = score
        total += score
    
    result['scores'] = validated_scores
    result['total_score'] = total
    
    # Ensure comments have required structure
    validated_comments = []
    for comment in result.get('comments', []):
        if isinstance(comment, dict):
            validated_comments.append({
                'text': comment.get('text', ''),
                'location': comment.get('location', ''),
                'suggestion': comment.get('suggestion', '')
            })
    
    result['comments'] = validated_comments
    
    return result


def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 3:
        print("Usage: python ai_grader.py <document_text_file> <rubric_file>", file=sys.stderr)
        sys.exit(1)
    
    text_file = sys.argv[1]
    rubric_file = sys.argv[2]
    
    try:
        # Read document text
        with open(text_file, 'r', encoding='utf-8') as f:
            document_text = f.read()
        
        # Load rubric
        rubric = load_rubric(rubric_file)
        
        # Grade with AI
        result = grade_with_ai(document_text, rubric)
        
        # Output JSON result
        print(json.dumps(result, indent=2))
        return result
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

