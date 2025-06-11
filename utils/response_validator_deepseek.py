import json
from typing import Dict, Any
from loguru import logger
import requests
import time
import re
from functools import lru_cache
import random

class ResponseValidatorDeepseek:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.thresholds = config["validation"]["thresholds"]
        self.api_keys = config["api"]["api_keys"]
        self.current_key_index = 0
        self.api_url = config["api"]["url"]
        self.model = config["api"]["model"]
        self.headers = {
            "Content-Type": "application/json"
        }
        self.system_prompt = config["api"]["system_message"]
        
        # Define regex patterns for key matching
        self.key_patterns = {
            re.compile(r'^[Cc]larity$'): 'clarity',
            re.compile(r'^[Hh]allucination$'): 'hallucination',
            re.compile(r'^[Ff]ormatting$'): 'formatting',
            re.compile(r'^[Cc]ompleteness$'): 'completeness',
            re.compile(r'^[Ll]anguage[-\s]?[Ss]pecific[-\s]?[Rr]equirements?$'): 'language_specific'
        }
        
        # Initialize response cache
        self.response_cache = {}
        self.cache_ttl = 1800  # 30 minutes cache TTL

    def _get_next_api_key(self) -> str:
        """Get the next API key in rotation"""
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key

    @lru_cache(maxsize=100)
    def _get_cached_analysis(self, response_hash: str) -> Dict[str, Any]:
        """Get cached analysis if available and not expired"""
        if response_hash in self.response_cache:
            cache_entry = self.response_cache[response_hash]
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                return cache_entry['results']
        return None

    def validate_response(self, response: str, language: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single response using Deepseek"""
        validation_criteria = test_case["queries"][language]["validation"]
        expected_contains = test_case["queries"][language]["expected_contains"]
        
        # Store the current test case for API logging
        self.current_test_case = test_case
        
        # Prepare prompt for Deepseek
        prompt = self._create_validation_prompt(response, validation_criteria, expected_contains, language)
        
        # Get Deepseek's analysis
        analysis = self._get_deepseek_analysis(response, validation_criteria)
        
        # Process and structure the results
        results = {
            "clarity": self._extract_clarity_score(analysis),
            "hallucination": self._extract_hallucination_score(analysis, expected_contains),
            "formatting": self._extract_formatting_score(analysis),
            "completeness": self._extract_completeness_score(analysis, validation_criteria),
            "language_specific": self._extract_language_specific_score(analysis, language)
        }
        
        # Add API log to results if available
        if 'api_log' in analysis:
            results['api_log'] = analysis['api_log']
        
        logger.info(f"Deepseek validation results for {test_case['id']}: {results}")
        return results

    def compare_responses(self, en_response: str, ar_response: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Compare responses between English and Arabic using Deepseek"""
        # Prepare prompt for comparison
        prompt = self._create_comparison_prompt(en_response, ar_response, test_case)
        
        # Get Deepseek's analysis
        analysis = self._get_deepseek_analysis(prompt)
        
        # Process and structure the results
        results = {
            "semantic_similarity": self._extract_semantic_similarity_score(analysis),
            "information_consistency": self._extract_information_consistency_score(analysis),
            "structure_similarity": self._extract_structure_similarity_score(analysis)
        }
        
        logger.info(f"Deepseek comparison results for {test_case['id']}: {results}")
        return results

    def _create_validation_prompt(self, response: str, validation_criteria: Dict[str, Any], 
                                expected_contains: list, language: str) -> str:
        """Create a prompt for Deepseek to validate a single response"""
        return f"""Please analyze the following response in {language} and provide scores for different aspects:

Response: {response}

Validation Criteria:
- Expected tone: {validation_criteria.get('expected_tone', 'friendly')}
- Required keywords: {validation_criteria.get('required_keywords', [])}
- Expected content: {expected_contains}
- Min length: {validation_criteria.get('min_length', 0)}
- Max length: {validation_criteria.get('max_length', 1000)}

Please provide scores (0-1) and brief explanations for:
1. Clarity: How clear and well-structured is the response?
2. Hallucination: Does the response contain the expected content without adding false information?
3. Formatting: Is the response properly formatted with correct capitalization and punctuation?
4. Completeness: Does the response meet length requirements and include required keywords?
5. Language-specific requirements: Does the response follow language-specific patterns and requirements?

Format your response as a JSON object with these exact keys:
{{
    "clarity": {{
        "score": <score>,
        "explanation": "<brief explanation>"
    }},
    "hallucination": {{
        "score": <score>,
        "explanation": "<brief explanation>"
    }},
    "formatting": {{
        "score": <score>,
        "explanation": "<brief explanation>"
    }},
    "completeness": {{
        "score": <score>,
        "explanation": "<brief explanation>"
    }},
    "language_specific": {{
        "score": <score>,
        "explanation": "<brief explanation>"
    }}
}}"""

    def _create_comparison_prompt(self, en_response: str, ar_response: str, test_case: Dict[str, Any]) -> str:
        """Create a prompt for Deepseek to compare responses between languages"""
        return f"""Please compare the following English and Arabic responses and analyze their cross-language consistency:

English Response: {en_response}
Arabic Response: {ar_response}

Test Case ID: {test_case['id']}

Please analyze and provide scores (0-1) for:
1. Semantic similarity: How well do the responses convey the same meaning and intent across languages?
2. Information consistency: Are the key points, facts, and details consistent between both language versions?
3. Structure similarity: How similar is the organization, flow, and presentation of information?

For each aspect, consider:
- Semantic similarity: Meaning preservation, intent matching, and cultural appropriateness
- Information consistency: Factual accuracy, detail matching, and completeness
- Structure similarity: Organization, formatting, and presentation style

Format your response as a JSON object with these exact keys:
{{
    "semantic_similarity": {{
        "score": <score>,
        "explanation": "<brief explanation>"
    }},
    "information_consistency": {{
        "score": <score>,
        "explanation": "<brief explanation>"
    }},
    "structure_similarity": {{
        "score": <score>,
        "explanation": "<brief explanation>"
    }}
}}"""

    def _get_deepseek_analysis(self, response: str, validation_criteria: dict = None) -> dict:
        """Get analysis from Deepseek API with improved rate limit handling."""
        try:
            # Generate cache key
            response_hash = hash(response + str(validation_criteria))
            
            # Check cache first
            cached_results = self._get_cached_analysis(response_hash)
            if cached_results:
                logger.info("Using cached analysis results")
                return cached_results

            # Prepare the API request
            url = "https://openrouter.ai/api/v1/chat/completions"
            
            # Prepare the validation prompt
            validation_prompt = self._prepare_validation_prompt(response, validation_criteria or {})
            
            # Prepare the request payload
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": validation_prompt
                    }
                ],
                "temperature": 0.3
            }
            
            # Create a detailed log of the API interaction
            api_log = {
                "request": {
                    "url": url,
                    "headers": {k: v for k, v in self.headers.items() if k != "Authorization"},
                    "payload": payload
                }
            }
            
            # Make the API request with improved retry logic
            max_retries = 3
            base_delay = 5
            max_delay = 30
            
            for attempt in range(max_retries):
                try:
                    # Get next API key in rotation
                    current_key = self._get_next_api_key()
                    headers = {**self.headers, "Authorization": f"Bearer {current_key}"}
                    
                    response = requests.post(url, headers=headers, json=payload)
                    
                    if response.status_code == 200:
                        # Cache successful response
                        self.response_cache[response_hash] = {
                            'timestamp': time.time(),
                            'results': self._parse_api_response(response, api_log)
                        }
                        return self.response_cache[response_hash]['results']
                    
                    elif response.status_code == 429:  # Rate limit hit
                        delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                        logger.warning(f"Rate limit hit, attempt {attempt + 1}/{max_retries}. Waiting {delay:.1f} seconds...")
                        time.sleep(delay)
                        continue
                    
                    else:
                        logger.error(f"API request failed with status code {response.status_code}")
                        return self._get_default_scores()
                        
                except Exception as e:
                    logger.error(f"Error during API request: {str(e)}")
                    if attempt == max_retries - 1:
                        return self._get_default_scores()
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                    time.sleep(delay)
            
            logger.error("All retry attempts failed")
            return self._get_default_scores()
            
        except Exception as e:
            logger.error(f"Error in _get_deepseek_analysis: {str(e)}")
            return self._get_default_scores()

    def _parse_api_response(self, response: requests.Response, api_log: dict) -> dict:
        """Parse the API response and extract scores."""
        response_data = response.json()
        
        if 'choices' not in response_data or not response_data['choices']:
            logger.error("No choices found in API response")
            return self._get_default_scores()
            
        content = response_data['choices'][0]['message']['content']
        
        # Log the raw API response for debugging
        logger.debug(f"Raw API response content: {content}")
        
        # Remove markdown code block if present
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]
        
        # Parse the inner JSON content
        try:
            validation_results = json.loads(content.strip())
            logger.debug(f"Parsed validation results: {validation_results}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return self._get_default_scores()
        
        # Initialize default scores
        results = {
            'clarity': {'score': 0.0},
            'hallucination': {'score': 0.0},
            'formatting': {'score': 0.0},
            'completeness': {'score': 0.0},
            'language_specific': {'score': 0.0},
            'semantic_similarity': {'score': 0.0},
            'information_consistency': {'score': 0.0},
            'structure_similarity': {'score': 0.0}
        }
        
        # Extract scores from validation results
        if isinstance(validation_results, dict):
            # Handle scores object format
            if 'scores' in validation_results:
                scores = validation_results.get('scores', {})
                logger.debug(f"Found scores object: {scores}")
                for api_key, score_data in scores.items():
                    # Find matching pattern for the key
                    for pattern, our_key in self.key_patterns.items():
                        if pattern.match(api_key):
                            logger.debug(f"Matched pattern {pattern.pattern} for key {api_key}")
                            if isinstance(score_data, dict):
                                results[our_key]['score'] = float(score_data.get('score', 0.0))
                            else:
                                results[our_key]['score'] = float(score_data)
                            break
            # Handle direct scores format
            else:
                logger.debug(f"Processing direct scores from: {validation_results}")
                for api_key, score_data in validation_results.items():
                    # Find matching pattern for the key
                    for pattern, our_key in self.key_patterns.items():
                        if pattern.match(api_key):
                            logger.debug(f"Matched pattern {pattern.pattern} for key {api_key}")
                            if isinstance(score_data, dict):
                                results[our_key]['score'] = float(score_data.get('score', 0.0))
                            else:
                                results[our_key]['score'] = float(score_data)
                            break
                    
                    # Handle comparison scores directly
                    if api_key in ['semantic_similarity', 'information_consistency', 'structure_similarity']:
                        if isinstance(score_data, dict):
                            results[api_key]['score'] = float(score_data.get('score', 0.0))
                        else:
                            results[api_key]['score'] = float(score_data)
        
        # Add API log to results
        results['api_log'] = api_log
        
        # Log the extracted scores for debugging
        logger.debug(f"Extracted scores: {results}")
        
        return results

    def _extract_clarity_score(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract clarity score from Deepseek analysis"""
        return {"score": analysis.get("clarity", {}).get("score", 0.0)}

    def _extract_hallucination_score(self, analysis: Dict[str, Any], expected_contains: list) -> Dict[str, Any]:
        """Extract hallucination score from Deepseek analysis"""
        return {"score": analysis.get("hallucination", {}).get("score", 0.0)}

    def _extract_formatting_score(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract formatting score from Deepseek analysis"""
        return {"score": analysis.get("formatting", {}).get("score", 0.0)}

    def _extract_completeness_score(self, analysis: Dict[str, Any], validation_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Extract completeness score from Deepseek analysis"""
        return {"score": analysis.get("completeness", {}).get("score", 0.0)}

    def _extract_language_specific_score(self, analysis: Dict[str, Any], language: str) -> Dict[str, Any]:
        """Extract language-specific score from Deepseek analysis"""
        return {"score": analysis.get("language_specific", {}).get("score", 0.0)}

    def _extract_semantic_similarity_score(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract semantic similarity score from Deepseek analysis"""
        return {"score": analysis.get("semantic_similarity", {}).get("score", 0.0)}

    def _extract_information_consistency_score(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract information consistency score from Deepseek analysis"""
        return {"score": analysis.get("information_consistency", {}).get("score", 0.0)}

    def _extract_structure_similarity_score(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structure similarity score from Deepseek analysis"""
        return {"score": analysis.get("structure_similarity", {}).get("score", 0.0)}

    def _prepare_validation_prompt(self, response: str, validation_criteria: dict) -> str:
        """Prepare the validation prompt for the API."""
        prompt = f"""Please analyze the following response in en and provide scores for different aspects:

Response: {response}

Validation Criteria:
- Expected tone: {validation_criteria.get('expected_tone', 'informative')}
- Required keywords: {validation_criteria.get('required_keywords', [])}
- Expected content: {validation_criteria.get('expected_content', [])}
- Min length: {validation_criteria.get('min_length', 20)}
- Max length: {validation_criteria.get('max_length', 500)}

Please provide scores (0-1) and brief explanations for:
1. Clarity (sentence structure, tone, factual content)
2. Hallucination (presence of expected content)
3. Formatting (capitalization, punctuation)
4. Completeness (length, required keywords)
5. Language-specific requirements (script, patterns)

Format your response as a JSON object with scores and explanations."""
        return prompt

    def _get_default_scores(self) -> dict:
        """Return default scores when validation fails."""
        return {
            'clarity': {'score': 0.4},
            'hallucination': {'score': 0.5},
            'formatting': {'score': 0.5},
            'completeness': {'score': 0.7},
            'language_specific': {'score': 0.3},
            'semantic_similarity': {'score': 0.4},
            'information_consistency': {'score': 0.5},
            'structure_similarity': {'score': 0.5}
        } 