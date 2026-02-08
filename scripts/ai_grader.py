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


def create_grading_prompt(document_text: str, rubric: Dict[str, Any], custom_instructions: str = None) -> str:
    """Create a structured prompt for AI grading."""
    criteria_text = ""
    for i, criterion in enumerate(rubric['criteria'], 1):
        criteria_text += f"{i}. {criterion['name']} ({criterion['max_points']} points)\n"
        criteria_text += f"   Description: {criterion['description']}\n\n"
    
    # Add custom instructions if provided
    instructions_section = ""
    if custom_instructions and custom_instructions.strip():
        instructions_section = f"""
ADDITIONAL GRADING INSTRUCTIONS:
{custom_instructions.strip()}

"""
    
    prompt = f"""You are an expert teaching assistant grading a student assignment. 

RUBRIC:
{rubric['name']} (Total: {rubric['total_points']} points)

{criteria_text}{instructions_section}STUDENT'S DOCUMENT:
{document_text}

TASK:
1. Evaluate the document against each rubric criterion
2. Identify strengths, key issues, and suggestions for improvement
3. Assign points for each criterion based on performance
4. Return your evaluation in the following JSON format:

{{
  "strengths": "List 2-4 key strengths of the assignment. Be specific and reference what the student did well.",
  "key_issues": "List 2-4 main issues or weaknesses. Be specific about what needs improvement.",
  "suggestions": "Provide 2-4 actionable suggestions for improvement. Be constructive and specific.",
  "criterion_comments": {{
    "Clarity and Organization": "Brief comment about this criterion",
    "Content Quality": "Brief comment about this criterion",
    ...
  }},
  "scores": {{
    "Clarity and Organization": 18,
    "Content Quality": 25,
    ...
  }},
  "total_score": 85
}}

IMPORTANT:
- Be specific and constructive in your feedback
- Strengths should highlight what the student did well
- Key Issues should identify the main problems that need addressing
- Suggestions should be actionable and specific
- For "criterion_comments", provide a brief comment (1-2 sentences) for each criterion explaining the score
- Scores should reflect actual performance, not just be high
- Total score should match sum of individual criterion scores
- Return ONLY valid JSON, no additional text

Return the JSON now:"""
    
    return prompt


def grade_with_ai(document_text: str, rubric: Dict[str, Any], model_name: str = "gemini-1.5-flash", custom_instructions: str = None) -> Dict[str, Any]:
    """
    Grade document using Gemini API.
    
    Args:
        document_text: Text content of the document
        rubric: Rubric dictionary
        model_name: Gemini model to use (will be auto-selected if not available)
        custom_instructions: Optional custom instructions for grading
    
    Returns:
        Dictionary with comments, scores, and feedback
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    # Strip any whitespace that might have been accidentally included
    api_key = api_key.strip()
    
    genai.configure(api_key=api_key)
    
    # Configure model
    generation_config = {
        "temperature": 0.3,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 4000,
    }
    
    # Ensure model name has models/ prefix if not already present
    if not model_name.startswith('models/'):
        model_name = f"models/{model_name}"
    
    # Try to find an available model that supports generateContent
    model = None
    model_name_to_use = None
    
    try:
        # List all available models
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # Try to find a working model
        # Priority order: gemini-2.5-flash (fastest), gemini-pro-latest, gemini-2.5-pro, or any available
        preferred_models = [
            "models/gemini-2.5-flash",  # Latest fast model
            "models/gemini-flash-latest",  # Latest flash
            "models/gemini-pro-latest",  # Latest pro
            "models/gemini-2.5-pro",  # Latest pro version
            "models/gemini-2.0-flash",  # Alternative flash
            model_name,  # Try the requested model
        ]
        
        for preferred in preferred_models:
            # Check if this model is in the available list
            if preferred in available_models:
                model_name_to_use = preferred
                break
        
        # If no preferred model found, use the first available one
        if not model_name_to_use and available_models:
            model_name_to_use = available_models[0]
        
        if not model_name_to_use:
            raise ValueError(f"No models with generateContent support found. Available models: {[m.name for m in genai.list_models()]}")
        
        # Initialize the model
        model = genai.GenerativeModel(model_name=model_name_to_use, generation_config=generation_config)
        
    except Exception as e:
        # If listing models fails, try common model names as fallback
        fallback_models = ["models/gemini-2.5-flash", "models/gemini-pro-latest", "models/gemini-flash-latest", model_name]
        for fallback_name in fallback_models:
            try:
                model = genai.GenerativeModel(model_name=fallback_name, generation_config=generation_config)
                model_name_to_use = fallback_name
                break
            except:
                continue
        else:
            raise ValueError(f"Could not initialize any Gemini model. Tried to list models but got: {str(e)}. Fallback models also failed.")
    
    # Create prompt
    prompt = create_grading_prompt(document_text, rubric, custom_instructions)
    
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
        
        # Find the first { and last } to extract just the JSON object
        first_brace = response_text.find("{")
        last_brace = response_text.rfind("}")
        
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            response_text = response_text[first_brace:last_brace + 1]
        
        # Parse JSON with better error handling
        result = None
        json_errors = []
        
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as e:
            json_errors.append(f"Initial parse failed: {str(e)}")
            
            # Try to fix common JSON issues
            try:
                # Fix single quotes
                fixed_text = response_text.replace("'", '"')
                # Fix trailing commas
                import re
                fixed_text = re.sub(r',\s*}', '}', fixed_text)
                fixed_text = re.sub(r',\s*]', ']', fixed_text)
                # Fix unquoted keys
                fixed_text = re.sub(r'(\w+):', r'"\1":', fixed_text)
                result = json.loads(fixed_text)
            except json.JSONDecodeError as e2:
                json_errors.append(f"Fixed parse failed: {str(e2)}")
                
                # Last resort: try to extract just the essential parts
                try:
                    # Try to find and parse just the scores and comments
                    scores_match = re.search(r'"scores"\s*:\s*\{[^}]+\}', response_text, re.DOTALL)
                    comments_match = re.search(r'"comments"\s*:\s*\[[^\]]+\]', response_text, re.DOTALL)
                    
                    if scores_match or comments_match:
                        # Build a minimal valid JSON
                        minimal_json = '{"comments": [], "scores": {}, "total_score": 0, "summary": ""}'
                        result = json.loads(minimal_json)
                        print(f"Warning: Using fallback JSON due to parsing errors: {json_errors}", file=sys.stderr)
                    else:
                        raise ValueError(f"Could not parse JSON response. Errors: {json_errors}. Response (first 500 chars): {response_text[:500]}")
                except Exception as e3:
                    raise ValueError(f"Could not parse JSON response. Errors: {json_errors}. Response (first 500 chars): {response_text[:500]}")
        
        if result is None:
            raise ValueError(f"Could not parse JSON response. Response (first 500 chars): {response_text[:500]}")
        
        # Validate and normalize result
        validated_result = validate_grading_result(result, rubric)
        
        return validated_result
    
    except Exception as e:
        print(f"Error in AI grading: {e}", file=sys.stderr)
        raise


def validate_grading_result(result: Dict[str, Any], rubric: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize grading result."""
    # Ensure all required fields exist
    if 'strengths' not in result:
        result['strengths'] = ""
    if 'key_issues' not in result:
        result['key_issues'] = ""
    if 'suggestions' not in result:
        result['suggestions'] = ""
    if 'criterion_comments' not in result:
        result['criterion_comments'] = {}
    if 'scores' not in result:
        result['scores'] = {}
    if 'total_score' not in result:
        result['total_score'] = 0
    
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
    
    # Ensure criterion_comments exist for all criteria
    validated_comments = {}
    for criterion in rubric['criteria']:
        name = criterion['name']
        if name in result.get('criterion_comments', {}):
            validated_comments[name] = result['criterion_comments'][name]
        else:
            # Generate a default comment based on score
            score = validated_scores.get(name, 0)
            max_points = criterion['max_points']
            if score == max_points:
                validated_comments[name] = "Full points - meets all requirements"
            elif score == 0:
                validated_comments[name] = "No points - does not meet requirements"
            else:
                validated_comments[name] = f"Partial credit - {score} out of {max_points} points"
    
    result['criterion_comments'] = validated_comments
    
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

