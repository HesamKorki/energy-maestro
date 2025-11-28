"""
Chat module for AI assistant using AWS Bedrock.
"""

import os
import json
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_bedrock_client():
    """
    Get AWS Bedrock runtime client.
    
    Uses the default boto3 credential chain:
    - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    - ~/.aws/credentials file
    - IAM role (if running on AWS)
    
    Returns:
        Tuple of (client, error_message) - client is None if error
    """
    try:
        import boto3
        
        region = os.getenv("AWS_REGION", "us-west-2")
        
        # Use boto3's default credential chain
        # This will automatically pick up credentials from env vars, 
        # ~/.aws/credentials, or IAM roles
        client = boto3.client(
            "bedrock-runtime",
            region_name=region,
        )
        return client, None
            
    except Exception as e:
        error_msg = str(e)
        print(f"[Bedrock] Failed to create client: {error_msg}")
        return None, error_msg


def build_context_prompt(page_context: Dict[str, Any]) -> str:
    """
    Build a context string from the current page state.
    
    Args:
        page_context: Dictionary with current page information
        
    Returns:
        Formatted context string
    """
    context_parts = [
        "You are an energy advisor assistant for Energy Maestro, helping users understand their electricity costs and renewable energy options.",
        "",
        "## Current Page Context:",
    ]
    
    if page_context.get("customer_id"):
        context_parts.append(f"- Selected Customer: {page_context.get('customer_name', page_context['customer_id'])}")
    
    if page_context.get("consumption_summary"):
        summary = page_context["consumption_summary"]
        context_parts.append(f"- Annual Consumption: {summary.get('total_annual_kwh', 0):,.0f} kWh")
        context_parts.append(f"- Average Daily: {summary.get('avg_daily_kwh', 0):.1f} kWh")
        context_parts.append(f"- Peak Power: {summary.get('peak_power_kw', 0):.1f} kW")
    
    if page_context.get("pv_enabled"):
        context_parts.append(f"- PV System: {page_context.get('pv_capacity', 0)} kWp enabled")
    else:
        context_parts.append("- PV System: Not enabled")
    
    if page_context.get("battery_enabled"):
        context_parts.append(f"- Battery: {page_context.get('battery_capacity', 0)} kWh enabled")
    else:
        context_parts.append("- Battery: Not enabled")
    
    if page_context.get("ev_enabled"):
        context_parts.append(f"- EV: {page_context.get('ev_km', 0)} km/year enabled")
    else:
        context_parts.append("- EV: Not enabled")
    
    if page_context.get("best_tariff"):
        context_parts.append(f"- Best Tariff: {page_context['best_tariff']}")
    
    if page_context.get("metrics"):
        metrics = page_context["metrics"]
        if metrics.get("self_sufficiency_pct"):
            context_parts.append(f"- Self-Sufficiency: {metrics['self_sufficiency_pct']}%")
        if metrics.get("total_pv_generation_kwh"):
            context_parts.append(f"- PV Generation: {metrics['total_pv_generation_kwh']:,.0f} kWh/year")
    
    if page_context.get("savings"):
        context_parts.append(f"- Potential Savings: €{page_context['savings']:,.0f}/year")
    
    context_parts.extend([
        "",
        "## Your Role:",
        "- Help users understand their energy data and options",
        "- Explain tariff differences and recommendations",
        "- Provide advice on PV sizing, battery storage, and EV charging",
        "- Answer questions about renewable energy and cost savings",
        "- Be concise but helpful",
        "",
    ])
    
    return "\n".join(context_parts)


def chat_with_bedrock(
    messages: List[Dict[str, str]],
    page_context: Dict[str, Any],
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
) -> Optional[str]:
    """
    Send a chat message to AWS Bedrock.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        page_context: Current page context for the system prompt
        model_id: Bedrock model ID to use
        
    Returns:
        Assistant response or None on error
    """
    client, error = get_bedrock_client()
    if not client:
        if error:
            return f"Failed to connect to AI: {error}"
        return "I'm sorry, the AI assistant is not configured. Please check your AWS credentials."
    
    try:
        # Build system prompt with context
        system_prompt = build_context_prompt(page_context)
        
        # Format messages for Claude
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Prepare request body for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": formatted_messages,
        }
        
        # Call Bedrock
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )
        
        # Parse response
        response_body = json.loads(response["body"].read())
        
        if "content" in response_body and len(response_body["content"]) > 0:
            return response_body["content"][0]["text"]
        else:
            return "I received an empty response. Please try again."
            
    except Exception as e:
        error_msg = str(e)
        if "AccessDeniedException" in error_msg:
            return "Access denied. Please check your AWS Bedrock permissions and ensure the model is enabled in your region."
        elif "ResourceNotFoundException" in error_msg:
            return "The AI model is not available. Please check your AWS region and model access."
        elif "ExpiredTokenException" in error_msg:
            return "AWS session expired. Please refresh your credentials."
        elif "UnrecognizedClientException" in error_msg or "InvalidSignatureException" in error_msg:
            return "Invalid AWS credentials. Please check your access key and secret key."
        elif "could not be assumed" in error_msg.lower() or "accessdenied" in error_msg.lower():
            return "Could not assume the specified IAM role. Please check that your credentials have permission to assume the role."
        else:
            return f"I encountered an error: {error_msg}"


def get_chat_css() -> str:
    """
    Get CSS for the floating chat widget.
    
    Returns:
        CSS string
    """
    return """
    <style>
    /* Floating chat button container - fixed position */
    .floating-chat-btn {
        position: fixed !important;
        bottom: 30px !important;
        right: 30px !important;
        z-index: 999999 !important;
    }
    
    /* Style the popover button to look like a round floating action button */
    .floating-chat-btn button[data-testid="stBaseButton-secondary"] {
        background: linear-gradient(135deg, #0f3460 0%, #16213e 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 50% !important;
        width: 64px !important;
        height: 64px !important;
        padding: 0 !important;
        font-size: 28px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4) !important;
        transition: transform 0.2s, box-shadow 0.2s !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    .floating-chat-btn button[data-testid="stBaseButton-secondary"]:hover {
        transform: scale(1.1) !important;
        box-shadow: 0 6px 25px rgba(0,0,0,0.5) !important;
    }
    
    /* Style the popover content */
    div[data-testid="stPopover"] {
        width: 420px !important;
        max-width: 95vw !important;
    }
    
    /* Chat message styling */
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: linear-gradient(135deg, #0f3460 0%, #16213e 100%) !important;
        border-radius: 12px !important;
        margin-left: 15% !important;
    }
    
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) p {
        color: white !important;
    }
    
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background: #f0f4f8 !important;
        border-radius: 12px !important;
        margin-right: 10% !important;
        border: 1px solid #d4e8f5 !important;
    }
    </style>
    
    <script>
    // Function to move chat button to fixed position
    function fixChatButton() {
        // Find the chat marker
        const marker = document.getElementById('floating-chat-marker');
        if (!marker) return;
        
        // Find the next sibling which should be the popover container
        let popoverContainer = marker.nextElementSibling;
        
        // If the container exists and hasn't been moved yet
        if (popoverContainer && !popoverContainer.classList.contains('floating-chat-btn')) {
            popoverContainer.classList.add('floating-chat-btn');
        }
    }
    
    // Run on load and periodically (Streamlit re-renders)
    if (document.readyState === 'complete') {
        fixChatButton();
    } else {
        window.addEventListener('load', fixChatButton);
    }
    
    // Also run periodically to catch Streamlit re-renders
    setInterval(fixChatButton, 500);
    </script>
    """

