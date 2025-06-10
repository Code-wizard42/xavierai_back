import re
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

class ResponseFormatter:
    """
    Formats chatbot responses dynamically based on question type and content structure
    """
    
    def __init__(self):
        self.question_patterns = {
            'list': [
                r'\b(?:list|show|tell me|what are|give me)\b.*\b(?:all|options|types|kinds|examples|items|features|capabilities)\b',
                r'\bhow many\b.*\b(?:types|kinds|options|ways|features)\b',
                r'\b(?:enumerate|itemize)\b',
                r'\b(?:can you list|please list)\b',
                r'\b(?:features|capabilities|functionalities)\b.*\b(?:platform|system|tool|service)\b',
                r'\bwhat.*\b(?:platform|system)\b.*\b(?:has|offers|provides|includes)\b'
            ],
            'use_case': [
                r'\bwhat.*\b(?:can|could)\b.*\b(?:use|used|using)\b.*\b(?:platform|system|tool|service|for)\b',
                r'\b(?:use cases|usage|applications|purposes)\b',
                r'\bwhat.*\b(?:good for|suitable for|designed for)\b',
                r'\bhow.*\b(?:use|utilize|apply)\b.*\b(?:platform|system|tool|service)\b'
            ],
            'comparison': [
                r'\b(?:difference|compare|versus|vs|which is better)\b',
                r'\b(?:pros and cons|advantages and disadvantages)\b',
                r'\b(?:similarities|differences)\b'
            ],
            'pricing': [
                r'\b(?:price|cost|pricing|fees|charges|subscription|payment|plan)\b',
                r'\b(?:how much|what does it cost|what is the price)\b',
                r'\b(?:affordable|expensive|cheap|budget)\b'
            ],
            'tutorial': [
                r'\b(?:how to|how do I|how can I|step by step|guide|tutorial|instructions)\b',
                r'\b(?:setup|install|configure|create|make)\b'
            ],
            'technical': [
                r'\b(?:error|bug|issue|problem|not working|failed|crash)\b',
                r'\b(?:troubleshoot|debug|fix|solve)\b',
                r'\b(?:API|integration|webhook|database|server)\b'
            ],
            'feature': [
                r'\b(?:feature|functionality|capability|can it|does it support)\b',
                r'\b(?:available|support|include|offer)\b'
            ],
            'contact': [
                r'\b(?:contact|support|help|phone|email|address)\b',
                r'\b(?:talk to|speak with|human|agent|representative)\b'
            ],
            'account': [
                r'\b(?:account|profile|settings|password|login|logout)\b',
                r'\b(?:change|update|modify|reset)\b'
            ]
        }
    
    def detect_question_type(self, question: str) -> str:
        """
        Detect the type of question to determine appropriate formatting
        """
        question_lower = question.lower()
        
        for question_type, patterns in self.question_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    return question_type
        
        return 'general'
    
    def extract_structured_data(self, answer: str) -> Dict[str, Any]:
        """
        Extract structured information from the answer text
        """
        structured_data = {
            'lists': [],
            'numbers': [],
            'code_blocks': [],
            'links': [],
            'emphasis': [],
            'sections': []
        }
        
        # Extract numbered lists
        numbered_lists = re.findall(r'(?:^\d+\..*(?:\n|$))+', answer, re.MULTILINE)
        for match in numbered_lists:
            items = re.findall(r'^\d+\.\s*(.+)', match, re.MULTILINE)
            if items:
                structured_data['lists'].append({
                    'type': 'numbered',
                    'items': items
                })
        
        # Extract bullet lists
        bullet_lists = re.findall(r'(?:^[-•*]\s.*(?:\n|$))+', answer, re.MULTILINE)
        for match in bullet_lists:
            items = re.findall(r'^[-•*]\s*(.+)', match, re.MULTILINE)
            if items:
                structured_data['lists'].append({
                    'type': 'bulleted',
                    'items': items
                })
        
        # Extract code blocks
        code_blocks = re.findall(r'```(?:(\w+)\n)?(.*?)```', answer, re.DOTALL)
        for language, code in code_blocks:
            structured_data['code_blocks'].append({
                'language': language or 'text',
                'code': code.strip()
            })
        
        # Extract URLs
        urls = re.findall(r'https?://[^\s]+', answer)
        structured_data['links'] = urls
        
        # Extract emphasis (bold/italic)
        bold_text = re.findall(r'\*\*(.*?)\*\*', answer)
        italic_text = re.findall(r'\*(.*?)\*', answer)
        structured_data['emphasis'] = {
            'bold': bold_text,
            'italic': italic_text
        }
        
        return structured_data
    
    def format_use_case_response(self, answer: str, structured_data: Dict[str, Any]) -> str:
        """
        Format response for use case questions
        """
        formatted_answer = "## Platform Use Cases\n\n"
        
        # Look for bullet points with bold headers (the format we expect)
        use_case_pattern = r'•\s*\*\*(.*?)\*\*:\s*(.*?)(?=•|\*\*|$)'
        use_cases = re.findall(use_case_pattern, answer, re.DOTALL)
        
        if use_cases:
            formatted_answer += "### Key Applications:\n\n"
            for i, (title, description) in enumerate(use_cases, 1):
                # Clean up the description
                clean_description = description.strip().replace('\n', ' ')
                # Remove multiple spaces
                clean_description = re.sub(r'\s+', ' ', clean_description)
                formatted_answer += f"**{i}. {title}:** {clean_description}\n\n"
        else:
            # Fallback: look for any bold text patterns
            bold_patterns = re.findall(r'\*\*(.*?)\*\*:\s*([^•*]+)', answer)
            if bold_patterns:
                formatted_answer += "### Key Applications:\n\n"
                for i, (title, description) in enumerate(bold_patterns, 1):
                    clean_description = description.strip().replace('\n', ' ')
                    clean_description = re.sub(r'\s+', ' ', clean_description)
                    formatted_answer += f"**{i}. {title}:** {clean_description}\n\n"
            else:
                # Extract sentences as individual use cases
                sentences = [s.strip() for s in answer.split('.') if s.strip() and len(s.strip()) > 20]
                if len(sentences) > 2:
                    formatted_answer += "### Key Applications:\n\n"
                    for i, sentence in enumerate(sentences[:6], 1):  # Limit to 6 items
                        if not sentence.lower().startswith(('our', 'these', 'if you')):
                            formatted_answer += f"**{i}.** {sentence}\n\n"
                else:
                    # Complete fallback
                    formatted_answer = self.format_general_response(answer, structured_data)
        
        return formatted_answer
    
    def format_list_response(self, answer: str, structured_data: Dict[str, Any]) -> str:
        """
        Format response for list-type questions
        """
        # First, try to extract ALL numbered items from the entire response
        all_numbered_items = []
        lines = answer.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for numbered patterns (1., 2., etc.)
            number_match = re.match(r'^\d+\.\s*(.+)', line)
            if number_match:
                item_text = number_match.group(1).strip()
                # Only add substantial content
                if len(item_text) > 10:
                    all_numbered_items.append(item_text)
        
        if all_numbered_items and len(all_numbered_items) > 1:
            formatted_answer = "## Key Features\n\n"
            for i, item in enumerate(all_numbered_items, 1):
                # Clean up the item text
                clean_item = item.strip()
                if clean_item:
                    formatted_answer += f"**{i}.** {clean_item}\n\n"
        elif structured_data['lists']:
            # Fallback to structured data if available
            formatted_answer = "## Key Features\n\n"
            all_items = []
            
            # Combine all list items from different sections
            for list_data in structured_data['lists']:
                all_items.extend(list_data['items'])
            
            # Renumber continuously
            for i, item in enumerate(all_items, 1):
                formatted_answer += f"**{i}.** {item}\n\n"
        else:
            # Final fallback to sentence-based splitting
            sentences = [s.strip() for s in answer.split('.') if s.strip() and len(s.strip()) > 15]
            if len(sentences) > 2:
                formatted_answer = "## Key Points\n\n"
                for i, sentence in enumerate(sentences[:8], 1):  # Limit to 8 items for readability
                    formatted_answer += f"**{i}.** {sentence}\n\n"
            else:
                formatted_answer = answer
        
        return formatted_answer
    
    def format_comparison_response(self, answer: str, structured_data: Dict[str, Any]) -> str:
        """
        Format response for comparison questions
        """
        formatted_answer = "## Comparison Overview\n\n"
        
        # Try to identify comparison elements
        comparison_keywords = ['difference', 'versus', 'compared to', 'while', 'however', 'on the other hand']
        
        paragraphs = [p.strip() for p in answer.split('\n\n') if p.strip()]
        
        if len(paragraphs) >= 2:
            formatted_answer += "### Key Differences:\n\n"
            for i, paragraph in enumerate(paragraphs[:3], 1):
                formatted_answer += f"**Point {i}:** {paragraph}\n\n"
        else:
            formatted_answer = answer
        
        return formatted_answer
    
    def format_pricing_response(self, answer: str, structured_data: Dict[str, Any]) -> str:
        """
        Format response for pricing questions
        """
        formatted_answer = "## Pricing Information\n\n"
        
        # Extract price mentions
        price_patterns = [
            r'\$\d+(?:\.\d{2})?(?:/\w+)?',
            r'\d+\s*(?:dollars?|USD|EUR|\$)',
            r'free|no cost|complimentary'
        ]
        
        prices_found = []
        for pattern in price_patterns:
            matches = re.findall(pattern, answer, re.IGNORECASE)
            prices_found.extend(matches)
        
        if prices_found:
            formatted_answer += "### Pricing Details:\n\n"
            # Remove duplicates while preserving order
            unique_prices = list(dict.fromkeys(prices_found))
            for price in unique_prices:
                formatted_answer += f"• **{price}**\n"
            formatted_answer += f"\n{answer}\n"
        else:
            formatted_answer = answer
        
        return formatted_answer
    
    def format_tutorial_response(self, answer: str, structured_data: Dict[str, Any]) -> str:
        """
        Format response for tutorial/how-to questions
        """
        formatted_answer = "## Step-by-Step Guide\n\n"
        
        if structured_data['lists']:
            for list_data in structured_data['lists']:
                if list_data['type'] == 'numbered':
                    formatted_answer += "### Steps:\n\n"
                    for i, step in enumerate(list_data['items'], 1):
                        formatted_answer += f"**Step {i}:** {step}\n\n"
                else:
                    formatted_answer += "### Requirements:\n\n"
                    for item in list_data['items']:
                        formatted_answer += f"✓ {item}\n"
                    formatted_answer += "\n"
        else:
            # Create steps from sentences
            sentences = [s.strip() for s in answer.split('.') if s.strip() and len(s.strip()) > 10]
            if len(sentences) > 1:
                formatted_answer += "### Steps:\n\n"
                for i, sentence in enumerate(sentences, 1):
                    formatted_answer += f"**Step {i}:** {sentence}\n\n"
            else:
                formatted_answer = answer
        
        # Add code blocks if present
        if structured_data['code_blocks']:
            formatted_answer += "\n### Code Examples:\n\n"
            for code_block in structured_data['code_blocks']:
                formatted_answer += f"```{code_block['language']}\n{code_block['code']}\n```\n\n"
        
        return formatted_answer
    
    def format_technical_response(self, answer: str, structured_data: Dict[str, Any]) -> str:
        """
        Format response for technical questions
        """
        formatted_answer = "## Technical Solution\n\n"
        
        # Add diagnostic section if error-related
        if any(keyword in answer.lower() for keyword in ['error', 'issue', 'problem', 'bug']):
            formatted_answer += "### Issue Analysis:\n"
            formatted_answer += f"{answer.split('.')[0]}.\n\n"
            
            formatted_answer += "### Solution:\n"
            remaining_text = '.'.join(answer.split('.')[1:]).strip()
            if remaining_text:
                formatted_answer += f"{remaining_text}\n\n"
        else:
            formatted_answer = answer + "\n\n"
        
        # Add code blocks if present
        if structured_data['code_blocks']:
            formatted_answer += "### Code Example:\n\n"
            for code_block in structured_data['code_blocks']:
                formatted_answer += f"```{code_block['language']}\n{code_block['code']}\n```\n\n"
        
        # Add links if present
        if structured_data['links']:
            formatted_answer += "### Additional Resources:\n\n"
            for link in structured_data['links']:
                formatted_answer += f"• [{link}]({link})\n"
            formatted_answer += "\n"
        
        return formatted_answer
    
    def format_contact_response(self, answer: str, structured_data: Dict[str, Any]) -> str:
        """
        Format response for contact/support questions
        """
        formatted_answer = "## Contact Information\n\n"
        
        # Extract contact details
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}'
        
        emails = re.findall(email_pattern, answer)
        phones = re.findall(phone_pattern, answer)
        
        if emails or phones:
            formatted_answer += "### Contact Details:\n\n"
            for email in emails:
                formatted_answer += f"📧 **Email:** {email}\n"
            for phone in phones:
                formatted_answer += f"📞 **Phone:** {phone}\n"
            formatted_answer += "\n"
        
        formatted_answer += answer + "\n"
        
        return formatted_answer
    
    def format_response(self, question: str, answer: str, confidence: float = None) -> Dict[str, Any]:
        """
        Main method to format responses based on question type
        """
        try:
            question_type = self.detect_question_type(question)
            structured_data = self.extract_structured_data(answer)
            
            # Format based on question type
            if question_type == 'list':
                formatted_answer = self.format_list_response(answer, structured_data)
            elif question_type == 'use_case':
                formatted_answer = self.format_use_case_response(answer, structured_data)
            elif question_type == 'comparison':
                formatted_answer = self.format_comparison_response(answer, structured_data)
            elif question_type == 'pricing':
                formatted_answer = self.format_pricing_response(answer, structured_data)
            elif question_type == 'tutorial':
                formatted_answer = self.format_tutorial_response(answer, structured_data)
            elif question_type == 'technical':
                formatted_answer = self.format_technical_response(answer, structured_data)
            elif question_type == 'contact':
                formatted_answer = self.format_contact_response(answer, structured_data)
            else:
                # General formatting - just clean up the text
                formatted_answer = self.format_general_response(answer, structured_data)
            
            return {
                'answer': formatted_answer,
                'question_type': question_type,
                'structured_data': structured_data,
                'confidence': confidence,
                'formatted_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error formatting response: {str(e)}")
            return {
                'answer': answer,
                'question_type': 'general',
                'structured_data': {},
                'confidence': confidence,
                'error': str(e)
            }
    
    def format_general_response(self, answer: str, structured_data: Dict[str, Any]) -> str:
        """
        Format general responses with basic improvements
        """
        # Clean up formatting
        formatted_answer = answer.strip()
        
        # Add emphasis if structured data contains emphasis
        if structured_data.get('emphasis', {}).get('bold'):
            for bold_text in structured_data['emphasis']['bold']:
                formatted_answer = formatted_answer.replace(f"**{bold_text}**", f"**{bold_text}**")
        
        # Add proper line breaks for readability
        if len(formatted_answer) > 200:
            # Break long paragraphs
            sentences = formatted_answer.split('. ')
            if len(sentences) > 3:
                mid_point = len(sentences) // 2
                formatted_answer = '. '.join(sentences[:mid_point]) + '.\n\n' + '. '.join(sentences[mid_point:])
        
        return formatted_answer

# Global instance
response_formatter = ResponseFormatter() 