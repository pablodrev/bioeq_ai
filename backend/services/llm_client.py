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
        """
        
        # Validate credentials
        if not self.api_key or not self.folder_id:
            logger.error(f"Missing credentials: api_key={bool(self.api_key)}, folder_id={bool(self.folder_id)}")
            return {}
        
        system_prompt = f"""Ты — опытный клинический фармаколог-регулятор ЕАЭС.
Твоя задача — извлечь из научного текста фармакокинетические параметры для препарата {inn}.

Нам нужны следующие параметры (если найдены в тексте):
1. Cmax - максимальная концентрация (мг/л или нг/мл)
2. AUC - площадь под кривой (мг*ч/л или нг*ч/мл)
3. Tmax - время достижения Cmax (часы)
4. T1/2 - период полувыведения (часы)
5. CV_intra - ВНУТРИИНДИВИДУАЛЬНАЯ вариабельность в процентах (не межиндивидуальная!)

ВАЖНО:
- Нам нужна именно INTRA-individual variability, а не INTER-individual
- Приоритет - исследования на ЗДОРОВЫХ ДОБРОВОЛЬЦАХ (healthy volunteers)
- Если параметра нет в тексте - верни null

Ответь ТОЛЬКО валидным JSON, без дополнительного текста:
{{
  "Cmax": {{"value": число, "unit": "мг/л", "found": true}},
  "AUC": {{"value": число, "unit": "мг*ч/л", "found": true}},
  "Tmax": {{"value": число, "unit": "ч", "found": true}},
  "T1/2": {{"value": число, "unit": "ч", "found": true}},
  "CV_intra": {{"value": число, "unit": "%", "found": true}}
}}
Если параметра нет - вместо объекта укажи null.
"""
        
        user_message = f"Вот текст из научной статьи:\n\n{abstract_text}\n\nИзвлеки параметры."
        
        payload = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt-lite",
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
