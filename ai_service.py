import os
import json
import re
import boto3

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

def extract_json(text: str):
    text = text.strip()

    # Remove markdown JSON fences if present
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except Exception:
        return {
            "intent": "resolve",
            "reply": text,
            "category": "General",
            "severity": "Medium"
        }

def ai_support_decision(user_message: str, kb_answer: str = ""):
    system_prompt = """
You are a customer support AI assistant.

Your job:
1. Decide whether to help resolve the issue or create an incident.
2. If a KB answer is available, use it to provide a concise support response.
3. If the message clearly asks to raise a ticket/incident, set intent=create_incident.
4. Infer category and severity.

Return ONLY valid JSON in this format:
{
  "intent": "resolve" | "create_incident",
  "reply": "response to user",
  "category": "General | Access | Performance | Installation | Billing | Login",
  "severity": "Low | Medium | High | Critical"
}
"""

    user_prompt = f"""
Customer message:
{user_message}

Knowledge base answer:
{kb_answer if kb_answer else "No KB answer found"}
"""

    response = bedrock.converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": system_prompt}],
        messages=[
            {
                "role": "user",
                "content": [{"text": user_prompt}]
            }
        ],
        inferenceConfig={
            "maxTokens": 300,
            "temperature": 0.2
        }
    )

    output_text = response["output"]["message"]["content"][0]["text"]
    return extract_json(output_text)
