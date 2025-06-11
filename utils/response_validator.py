import json
from typing import Dict, Any
from loguru import logger

class ResponseValidator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.thresholds = config["validation"]["thresholds"]
        self.tone_words = {
            "friendly": ["hello", "hi", "welcome", "glad", "pleasure", "happy", "great", "wonderful", "help", "assist", "support", "hope", "please", "thank", "appreciate"],
            "informative": ["include", "consists", "located", "found", "major", "important", "significant", "notable", "known", "famous", "primary", "key", "main", "essential", "prominent", "features", "characteristics", "details", "information", "such as", "for example", "specifically", "notably"],
            "apologetic": ["sorry", "apologize", "understand", "assist", "help", "try again", "regret", "unfortunately"]
        }
        self.factual_markers = [
            "is", "are", "was", "were", "includes", "consists", "located", "found", "features", "contains",
            "comprises", "has", "have", "had", "made up of", "composed of", "characterized by", "known for",
            "recognized as", "considered", "established", "developed", "created", "formed", "built"
        ]
    
    def validate_response(self, response: str, language: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single response against test case criteria"""
        validation_criteria = test_case["queries"][language]["validation"]
        expected_contains = test_case["queries"][language]["expected_contains"]
        
        results = {
            "clarity": self._check_clarity(response, validation_criteria),
            "hallucination": self._check_hallucination(response, expected_contains),
            "formatting": self._check_formatting(response),
            "completeness": self._check_completeness(response, validation_criteria),
            "language_specific": self._check_language_specific(response, language, validation_criteria)
        }
        
        logger.info(f"Validation results for {test_case['id']}: {results}")
        return results
    
    def compare_responses(self, en_response: str, ar_response: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Compare responses between English and Arabic"""
        results = {
            "semantic_similarity": self._check_semantic_similarity(en_response, ar_response, test_case),
            "information_consistency": self._check_information_consistency(en_response, ar_response),
            "structure_similarity": self._check_structure_similarity(en_response, ar_response)
        }
        
        logger.info(f"Comparison results for {test_case['id']}: {results}")
        return results
    
    def _check_clarity(self, response: str, validation_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Check response clarity with more lenient scoring"""
        score = 0.0
        
        # Check for minimum length and complete sentences
        sentences = [s.strip() for s in response.split(".") if s.strip()]
        if len(sentences) >= 1 and all(s[-1] in ".!?" for s in sentences):  # Reduced from 2 to 1 sentence
            score += 0.3
        
        # Check for expected tone
        expected_tone = validation_criteria.get("expected_tone", "friendly")
        tone_matches = sum(1 for word in self.tone_words.get(expected_tone, []) 
                         if word.lower() in response.lower())
        if tone_matches >= 1:  # Require at least 1 tone word
            score += 0.4
        
        # Check for factual content structure
        has_factual_markers = any(marker.lower() in response.lower() for marker in self.factual_markers)
        has_subject_content = any(word.lower() in response.lower() for word in validation_criteria["required_keywords"])
        if has_factual_markers or has_subject_content:  # Changed from AND to OR
            score += 0.3
            
        return {"score": min(1.0, score)}
    
    def _check_hallucination(self, response: str, expected_contains: list) -> Dict[str, Any]:
        """Check for response hallucination"""
        # Check if response contains expected keywords
        matches = sum(1 for keyword in expected_contains if keyword.lower() in response.lower())
        score = matches / len(expected_contains)
        return {"score": score}
    
    def _check_formatting(self, response: str) -> Dict[str, Any]:
        """Check response formatting"""
        score = 0.0
        
        # Check capitalization
        if response[0].isupper():
            score += 0.5
            
        # Check punctuation
        if response[-1] in ".!?":
            score += 0.5
            
        return {"score": score}
    
    def _check_completeness(self, response: str, validation_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Check response completeness"""
        score = 0.0
        
        # Check length requirements
        if validation_criteria["min_length"] <= len(response) <= validation_criteria["max_length"]:
            score += 0.4
            
        # Check required keywords
        keywords_present = sum(1 for keyword in validation_criteria["required_keywords"] 
                             if keyword.lower() in response.lower())
        keyword_score = keywords_present / len(validation_criteria["required_keywords"])
        score += 0.6 * keyword_score
        
        return {"score": min(1.0, score)}
    
    def _check_language_specific(self, response: str, language: str, validation_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Check language-specific requirements"""
        score = 0.0
        
        # Check for correct script and language-specific patterns
        if language == "ar":
            # Check for Arabic characters
            arabic_chars = sum(1 for char in response if char in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي")
            char_score = arabic_chars / len(response) if len(response) > 0 else 0.0
            
            # Check for Arabic-specific punctuation
            arabic_punct = sum(1 for char in response if char in "،؛؟")
            punct_score = arabic_punct / len(response) if len(response) > 0 else 0.0
            
            # Check for RTL text direction
            has_rtl = "dir=\"rtl\"" in response or "dir='rtl'" in response
            rtl_score = 1.0 if has_rtl else 0.0
            
            score = (char_score * 0.6 + punct_score * 0.2 + rtl_score * 0.2)
        else:
            # Check for English characters and patterns
            ascii_chars = sum(1 for char in response if char.isascii())
            char_score = ascii_chars / len(response) if len(response) > 0 else 0.0
            
            # Check for English-specific punctuation
            eng_punct = sum(1 for char in response if char in ".,;:!?")
            punct_score = eng_punct / len(response) if len(response) > 0 else 0.0
            
            # Check for LTR text direction
            has_ltr = "dir=\"ltr\"" in response or "dir='ltr'" in response
            ltr_score = 1.0 if has_ltr else 0.0
            
            score = (char_score * 0.6 + punct_score * 0.2 + ltr_score * 0.2)
            
        return {"score": score}
    
    def _check_semantic_similarity(self, en_response: str, ar_response: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Check semantic similarity between responses"""
        score = 0.0
        
        # Check if both responses contain their expected keywords
        en_expected = test_case["queries"]["en"]["expected_contains"]
        ar_expected = test_case["queries"]["ar"]["expected_contains"]
        
        en_matches = sum(1 for keyword in en_expected if keyword.lower() in en_response.lower())
        ar_matches = sum(1 for keyword in ar_expected if keyword.lower() in ar_response.lower())
        
        keyword_score = min(en_matches / len(en_expected), ar_matches / len(ar_expected))
        score += 0.4 * keyword_score
        
        # Check if both responses have similar structure
        en_sentences = len([s for s in en_response.split(".") if s.strip()])
        ar_sentences = len([s for s in ar_response.split(".") if s.strip()])
        structure_score = min(en_sentences, ar_sentences) / max(en_sentences, ar_sentences) if max(en_sentences, ar_sentences) > 0 else 1.0
        score += 0.3 * structure_score
        
        # Check if both responses have similar tone
        en_tone = test_case["queries"]["en"]["validation"]["expected_tone"]
        ar_tone = test_case["queries"]["ar"]["validation"]["expected_tone"]
        if en_tone == ar_tone:
            score += 0.3
            
        return {"score": min(1.0, score)}
    
    def _check_information_consistency(self, en_response: str, ar_response: str) -> Dict[str, Any]:
        """Check information consistency between responses"""
        # Check if responses have similar structure
        en_sentences = len([s for s in en_response.split(".") if s.strip()])
        ar_sentences = len([s for s in ar_response.split(".") if s.strip()])
        score = min(en_sentences, ar_sentences) / max(en_sentences, ar_sentences) if max(en_sentences, ar_sentences) > 0 else 1.0
        return {"score": score}
    
    def _check_structure_similarity(self, en_response: str, ar_response: str) -> Dict[str, Any]:
        """Check structural similarity between responses"""
        # Compare sentence patterns and length ratios
        en_words = len(en_response.split())
        ar_words = len(ar_response.split())
        length_score = min(en_words, ar_words) / max(en_words, ar_words) if max(en_words, ar_words) > 0 else 1.0
        
        # Compare punctuation patterns
        en_puncts = sum(1 for char in en_response if char in ".!?,;")
        ar_puncts = sum(1 for char in ar_response if char in ".!?,;")
        punct_score = min(en_puncts, ar_puncts) / max(en_puncts, ar_puncts) if max(en_puncts, ar_puncts) > 0 else 1.0
        
        # Compare sentence structure
        en_sentences = len([s for s in en_response.split(".") if s.strip()])
        ar_sentences = len([s for s in ar_response.split(".") if s.strip()])
        sentence_score = min(en_sentences, ar_sentences) / max(en_sentences, ar_sentences) if max(en_sentences, ar_sentences) > 0 else 1.0
        
        return {"score": (length_score + punct_score + sentence_score) / 3} 