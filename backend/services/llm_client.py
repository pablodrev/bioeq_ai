"""
YandexGPT API client for extracting drug parameters from text.
"""
import httpx
import json
import logging
from typing import Optional, Dict, Any
import os

logger = logging.getLogger(__name__)

class YandexGPTClient:
    """Client for YandexGPT API."""
    
    BASE_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    def __init__(self, api_key: Optional[str] = None, folder_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("YANDEX_GPT_API_KEY")
        self.folder_id = folder_id or os.getenv("YANDEX_FOLDER_ID")
        
        if not self.api_key:
            raise ValueError("YANDEX_GPT_API_KEY not set")
        if not self.folder_id:
            raise ValueError("YANDEX_FOLDER_ID not set")
        
        self.client = httpx.Client(timeout=60.0)
    
    def extract_parameters(self, abstract_text: str, inn: str) -> Dict[str, Any]:
        """
        Extract pharmacokinetic parameters from abstract text using LLM.
        Returns dict with parameters: {parameter: value, ...}
        Enforces strict standard units of measurement.
        """
        
        # Validate credentials
        if not self.api_key or not self.folder_id:
            logger.error(f"Missing credentials: api_key={bool(self.api_key)}, folder_id={bool(self.folder_id)}")
            return {}
        
        system_prompt = f"""You are an expert clinical pharmacologist and regulatory affairs specialist.
Your task is to extract pharmacokinetic parameters for the drug {inn} from scientific research papers.

STANDARD UNITS (STRICT - always use these units):
- Cmax: ng/mL (nanograms per milliliter) - CONVERT all values to this unit
- AUC: ng·h/mL (nanogram-hours per milliliter) - CONVERT all values to this unit
- Tmax: h (hours) - CONVERT all values to this unit
- T1/2: h (hours) - CONVERT all values to this unit
- CV_intra: % (percent) - ALWAYS use percent, NOT decimal (e.g., 15.5 not 0.155)

EXTRACTION RULES:
1. Extract INTRA-individual variability (CV_intra) ONLY - NOT inter-individual variability
2. Prioritize data from studies in HEALTHY VOLUNTEERS
3. When multiple units are reported in the paper, CONVERT to standard units using standard conversion factors:
   - mg/L = ng/mL × 1 (1 mg/L = 1000 ng/mL)
   - μg/mL = ng/mL × 1000
   - If the original unit cannot be converted to standard units, DO NOT report that parameter
4. Include a "converted" flag if unit conversion was performed
5. If a parameter is not found in the text, return null for that parameter

RESPONSE FORMAT (strict JSON only):
{{
  "Cmax": {{"value": <number>, "unit": "ng/mL", "found": true, "converted": false}},
  "AUC": {{"value": <number>, "unit": "ng·h/mL", "found": true, "converted": false}},
  "Tmax": {{"value": <number>, "unit": "h", "found": true, "converted": false}},
  "T1/2": {{"value": <number>, "unit": "h", "found": true, "converted": false}},
  "CV_intra": {{"value": <number>, "unit": "%", "found": true, "converted": false}}
}}

IMPORTANT:
- Return ONLY valid JSON, no additional text
- Use null for parameters not found (not absence from JSON)
- All units in response MUST be the standard units specified above
- Do NOT include any explanation or markdown code blocks
"""
        
        user_message = f"Extract pharmacokinetic parameters from this scientific paper abstract:\n\n{abstract_text}"
        
        payload = {
            "modelUri": f"gpt://{self.folder_id}/aliceai-llm/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.1,  # Low temperature for consistency
                "maxTokens": 500
            },
            "messages": [
                {
                    "role": "system",
                    "text": system_prompt
                },
                {
                    "role": "user",
                    "text": user_message
                }
            ]
        }
        
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id,
            "Content-Type": "application/json"
        }
        
        try:
            response = self.client.post(
                self.BASE_URL,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract text from response
            if result.get("result", {}).get("alternatives"):
                text = result["result"]["alternatives"][0].get("message", {}).get("text", "")
                
                # Try to parse as JSON
                try:
                    # Strip markdown code block if present (```json ... ```)
                    text = text.strip()
                    if text.startswith("```"):
                        # Remove opening ``` (with optional language identifier)
                        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                    if text.endswith("```"):
                        text = text.rsplit("\n", 1)[0] if "\n" in text else text[:-3]
                    text = text.strip()
                    
                    params = json.loads(text)
                    logger.info(f"Successfully extracted parameters: {list(params.keys())}")
                    return params
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse LLM response as JSON: {text[:100]} - Error: {e}")
                    return {}
            else:
                logger.warning("No alternatives in YandexGPT response")
                return {}
        
        except httpx.HTTPStatusError as e:
            logger.error(f"YandexGPT API error {e.response.status_code}: {e.response.text}")
            return {}
        except Exception as e:
            logger.error(f"YandexGPT API error: {e}")
            return {}
    
    def close(self):
        """Close HTTP client."""
        self.client.close()
