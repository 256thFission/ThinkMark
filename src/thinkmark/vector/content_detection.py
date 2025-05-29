"""
Content type detection for ThinkMark document processing.
Classifies content as code, explanation, or mixed.
"""
import re
from typing import Literal


def detect_content_type(text: str) -> Literal['code', 'explanation', 'mixed']:
    """
    Determine the type of content based on text analysis.
    
    Args:
        text: The text to analyze
        
    Returns:
        Content type: 'code', 'explanation', or 'mixed'
    """
    # Define keyword indicators for code content
    code_indicators = [
        "```", "def ", "class ", "function", "return", "import ", 
        "from ", "var ", "const ", "let ", "if (", "for (", 
        "while (", "{\n", ":\n", "};\n", "=>\n"
    ]
    
    # Calculate the ratio of code indicators
    code_indicator_count = sum(1 for indicator in code_indicators if indicator in text)
    
    # Check for code blocks specifically
    code_blocks = re.findall(r'```(?:\w+)?\n[\s\S]*?```', text, re.MULTILINE)
    
    # Calculate the proportion of the text that is code blocks
    code_block_chars = sum(len(block) for block in code_blocks)
    text_length = len(text) if len(text) > 0 else 1  # Avoid division by zero
    code_ratio = code_block_chars / text_length
    
    # Determine content type based on indicators and code blocks
    if code_ratio > 0.7 or code_indicator_count > 10:
        return 'code'
    elif code_ratio < 0.2 and code_indicator_count < 3:
        return 'explanation'
    else:
        return 'mixed'
