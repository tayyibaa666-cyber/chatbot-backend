"""
Enhanced content extractor for comprehensive chatbot training.
Extracts structured data, contact info, pricing, FAQs, and important sections.
"""

import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse


@dataclass
class ContactInfo:
    """Structured contact information."""
    emails: List[str]
    phones: List[str]
    addresses: List[str]
    social_links: Dict[str, str]  # platform -> url
    
    def to_text(self) -> str:
        """Convert to readable text for chatbot training."""
        parts = []
        if self.emails:
            parts.append(f"Contact Emails: {', '.join(self.emails)}")
        if self.phones:
            parts.append(f"Phone Numbers: {', '.join(self.phones)}")
        if self.addresses:
            parts.append(f"Addresses: {' | '.join(self.addresses)}")
        if self.social_links:
            social = ', '.join([f"{k}: {v}" for k, v in self.social_links.items()])
            parts.append(f"Social Media: {social}")
        return "\n".join(parts)


@dataclass
class PricingPlan:
    """Structured pricing information."""
    name: str
    price: str
    billing_cycle: str  # monthly, yearly, one-time
    features: List[str]
    is_featured: bool = False
    
    def to_text(self) -> str:
        """Convert to readable text for chatbot training."""
        text = f"Plan: {self.name}\n"
        text += f"Price: {self.price} ({self.billing_cycle})\n"
        if self.features:
            text += f"Features: {', '.join(self.features)}\n"
        return text


@dataclass
class FAQItem:
    """FAQ question and answer pair."""
    question: str
    answer: str
    
    def to_text(self) -> str:
        return f"Q: {self.question}\nA: {self.answer}"


@dataclass
class PageSection:
    """A labeled section of content."""
    type: str  # hero, features, pricing, faq, about, contact, etc.
    title: str
    content: str
    metadata: Dict[str, Any]  # Additional structured data


@dataclass
class ExtractedContent:
    """Complete extracted content from a page."""
    url: str
    page_type: str  # homepage, pricing, contact, faq, product, blog, generic
    title: str
    meta_description: str
    main_content: str
    
    # Structured data
    contact_info: Optional[ContactInfo]
    pricing_plans: List[PricingPlan]
    faqs: List[FAQItem]
    sections: List[PageSection]
    
    # Schema.org and JSON-LD data
    structured_data: Dict[str, Any]
    
    def to_training_text(self) -> str:
        """Convert all extracted data into comprehensive training text."""
        parts = []
        
        # Page header
        parts.append(f"=== {self.title} ===")
        parts.append(f"Page Type: {self.page_type}")
        parts.append(f"URL: {self.url}")
        
        if self.meta_description:
            parts.append(f"Description: {self.meta_description}")
        
        parts.append("")  # blank line
        
        # Contact information (high priority)
        if self.contact_info:
            contact_text = self.contact_info.to_text()
            if contact_text:
                parts.append("=== CONTACT INFORMATION ===")
                parts.append(contact_text)
                parts.append("")
        
        # Pricing (high priority)
        if self.pricing_plans:
            parts.append("=== PRICING & PLANS ===")
            for plan in self.pricing_plans:
                parts.append(plan.to_text())
                parts.append("")
        
        # FAQs (high priority)
        if self.faqs:
            parts.append("=== FREQUENTLY ASKED QUESTIONS ===")
            for faq in self.faqs:
                parts.append(faq.to_text())
                parts.append("")
        
        # Sections
        if self.sections:
            for section in self.sections:
                parts.append(f"=== {section.title.upper()} ===")
                parts.append(section.content)
                parts.append("")
        
        # Main content
        if self.main_content:
            parts.append("=== MAIN CONTENT ===")
            parts.append(self.main_content)
        
        return "\n".join(parts)


class EnhancedContentExtractor:
    """
    Extracts comprehensive, structured content from web pages.
    Designed to maximize chatbot training quality for SaaS websites.
    """
    
    # Page type indicators
    PAGE_INDICATORS = {
        'pricing': ['pricing', 'plans', 'subscription', 'packages', 'buy'],
        'contact': ['contact', 'support', 'help', 'reach-us'],
        'faq': ['faq', 'questions', 'help-center', 'knowledge'],
        'about': ['about', 'company', 'team', 'story'],
        'product': ['product', 'service', 'features', 'solutions'],
        'blog': ['blog', 'news', 'article', 'post'],
    }
    
    # Regex patterns
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})')
    PRICE_PATTERN = re.compile(r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)|(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:USD|dollars?)')
    
    # Social media platforms
    SOCIAL_PLATFORMS = {
        'facebook.com': 'Facebook',
        'twitter.com': 'Twitter',
        'x.com': 'X (Twitter)',
        'linkedin.com': 'LinkedIn',
        'instagram.com': 'Instagram',
        'youtube.com': 'YouTube',
        'github.com': 'GitHub',
        'tiktok.com': 'TikTok',
    }
    
    def extract(self, html: str, url: str) -> ExtractedContent:
        """Main extraction method."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove noise
        self._remove_noise(soup)
        
        # Determine page type
        page_type = self._detect_page_type(url, soup)
        
        # Extract basic metadata
        title = self._extract_title(soup)
        meta_desc = self._extract_meta_description(soup)
        
        # Extract structured data
        contact_info = self._extract_contact_info(soup, html)
        pricing_plans = self._extract_pricing(soup)
        faqs = self._extract_faqs(soup)
        sections = self._extract_sections(soup, page_type)
        structured_data = self._extract_structured_data(soup)
        
        # Extract main content
        main_content = self._extract_main_content(soup)
        
        return ExtractedContent(
            url=url,
            page_type=page_type,
            title=title,
            meta_description=meta_desc,
            main_content=main_content,
            contact_info=contact_info,
            pricing_plans=pricing_plans,
            faqs=faqs,
            sections=sections,
            structured_data=structured_data,
        )
    
    def _remove_noise(self, soup: BeautifulSoup) -> None:
        """Remove non-content elements."""
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 
                        'noscript', 'aside', 'iframe', 'svg']):
            tag.decompose()
    
    def _detect_page_type(self, url: str, soup: BeautifulSoup) -> str:
        """Detect the type of page based on URL and content."""
        url_lower = url.lower()
        
        # Check URL patterns
        for page_type, indicators in self.PAGE_INDICATORS.items():
            if any(indicator in url_lower for indicator in indicators):
                return page_type
        
        # Check page title and h1
        title_text = self._extract_title(soup).lower()
        h1_text = soup.find('h1')
        h1_text = h1_text.get_text(strip=True).lower() if h1_text else ""
        
        combined = f"{title_text} {h1_text}"
        
        for page_type, indicators in self.PAGE_INDICATORS.items():
            if any(indicator in combined for indicator in indicators):
                return page_type
        
        # Check if homepage
        parsed = urlparse(url)
        if parsed.path in ['/', '', '/index.html', '/index.htm']:
            return 'homepage'
        
        return 'generic'
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        # Try title tag
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        # Try og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content']
        
        # Try h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        return "Untitled Page"
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description."""
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta and meta.get('content'):
            return meta['content']
        
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            return og_desc['content']
        
        return ""
    
    def _extract_contact_info(self, soup: BeautifulSoup, html: str) -> Optional[ContactInfo]:
        """Extract all contact information."""
        text = soup.get_text()
        
        # Extract emails
        emails = list(set(self.EMAIL_PATTERN.findall(text)))
        # Filter out common false positives
        emails = [e for e in emails if not any(x in e.lower() for x in ['example', 'test', 'placeholder', '@2x'])]
        
        # Extract phone numbers
        phones = []
        phone_matches = self.PHONE_PATTERN.findall(text)
        for match in phone_matches:
            if isinstance(match, tuple):
                phone = f"({match[0]}) {match[1]}-{match[2]}"
                phones.append(phone)
        phones = list(set(phones))
        
        # Extract addresses (look for common patterns)
        addresses = self._extract_addresses(soup)
        
        # Extract social media links
        social_links = {}
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            for domain, platform in self.SOCIAL_PLATFORMS.items():
                if domain in href:
                    social_links[platform] = a['href']
                    break
        
        if emails or phones or addresses or social_links:
            return ContactInfo(
                emails=emails,
                phones=phones,
                addresses=addresses,
                social_links=social_links
            )
        
        return None
    
    def _extract_addresses(self, soup: BeautifulSoup) -> List[str]:
        """Extract physical addresses."""
        addresses = []
        
        # Look for schema.org address markup
        address_tags = soup.find_all(attrs={'itemprop': 'address'})
        for tag in address_tags:
            addr_text = tag.get_text(strip=True)
            if addr_text:
                addresses.append(addr_text)
        
        # Look for common address patterns in text
        text = soup.get_text()
        # Simple pattern: digits followed by street keywords
        street_pattern = re.compile(r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way)[,\s]+[\w\s]+,\s+[A-Z]{2}\s+\d{5}')
        addr_matches = street_pattern.findall(text)
        addresses.extend(addr_matches)
        
        return list(set(addresses))
    
    def _extract_pricing(self, soup: BeautifulSoup) -> List[PricingPlan]:
        """Extract pricing plans from the page."""
        plans = []
        
        # Strategy 1: Look for pricing tables/cards with common class names
        pricing_containers = soup.find_all(
            ['div', 'section'],
            class_=re.compile(r'pric(e|ing)|plan|package|tier', re.I)
        )
        
        for container in pricing_containers:
            # Look for individual plan cards
            plan_cards = container.find_all(
                ['div', 'article'],
                class_=re.compile(r'plan|package|tier|card|pricing-card', re.I),
                recursive=False
            )
            
            if not plan_cards:
                plan_cards = [container]
            
            for card in plan_cards:
                plan = self._extract_single_plan(card)
                if plan:
                    plans.append(plan)
        
        # Strategy 2: Look for structured data (JSON-LD)
        json_ld_plans = self._extract_pricing_from_jsonld(soup)
        plans.extend(json_ld_plans)
        
        return plans
    
    def _extract_single_plan(self, element: Tag) -> Optional[PricingPlan]:
        """Extract a single pricing plan from an element."""
        try:
            # Extract plan name
            name_tag = element.find(['h1', 'h2', 'h3', 'h4'], class_=re.compile(r'name|title|plan', re.I))
            if not name_tag:
                name_tag = element.find(['h1', 'h2', 'h3', 'h4'])
            name = name_tag.get_text(strip=True) if name_tag else "Unknown Plan"
            
            # Extract price
            price_tag = element.find(class_=re.compile(r'price|cost|amount', re.I))
            if not price_tag:
                # Look for price patterns in text
                text = element.get_text()
                price_match = self.PRICE_PATTERN.search(text)
                price = price_match.group(0) if price_match else "Contact for pricing"
            else:
                price = price_tag.get_text(strip=True)
            
            # Extract billing cycle
            billing_cycle = "monthly"  # default
            text_lower = element.get_text().lower()
            if '/year' in text_lower or 'annually' in text_lower or 'per year' in text_lower:
                billing_cycle = "yearly"
            elif 'one-time' in text_lower or 'lifetime' in text_lower:
                billing_cycle = "one-time"
            
            # Extract features
            features = []
            feature_lists = element.find_all(['ul', 'ol'])
            for ul in feature_lists:
                for li in ul.find_all('li'):
                    feature_text = li.get_text(strip=True)
                    if feature_text and len(feature_text) > 3:
                        features.append(feature_text)
            
            # Check if featured/popular
            is_featured = bool(element.find(class_=re.compile(r'featured|popular|recommended|best', re.I)))
            
            # Only return if we have meaningful data
            if name and price:
                return PricingPlan(
                    name=name,
                    price=price,
                    billing_cycle=billing_cycle,
                    features=features[:10],  # Limit to 10 features
                    is_featured=is_featured
                )
        except Exception:
            pass
        
        return None
    
    def _extract_pricing_from_jsonld(self, soup: BeautifulSoup) -> List[PricingPlan]:
        """Extract pricing from JSON-LD structured data."""
        plans = []
        
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    offers = data.get('offers', [])
                    if not isinstance(offers, list):
                        offers = [offers]
                    
                    for offer in offers:
                        if isinstance(offer, dict):
                            name = data.get('name', 'Product')
                            price = offer.get('price', '')
                            currency = offer.get('priceCurrency', 'USD')
                            
                            if price:
                                plans.append(PricingPlan(
                                    name=name,
                                    price=f"{currency} {price}",
                                    billing_cycle="one-time",
                                    features=[],
                                    is_featured=False
                                ))
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return plans
    
    def _extract_faqs(self, soup: BeautifulSoup) -> List[FAQItem]:
        """Extract FAQ questions and answers."""
        faqs = []
        
        # Strategy 1: Look for FAQ sections
        faq_sections = soup.find_all(['div', 'section'], class_=re.compile(r'faq|question|accordion', re.I))
        
        for section in faq_sections:
            # Look for Q&A pairs
            questions = section.find_all(['h3', 'h4', 'h5', 'dt', 'div'], class_=re.compile(r'question|q[^a-z]', re.I))
            
            for q_tag in questions:
                question = q_tag.get_text(strip=True)
                
                # Find associated answer
                answer_tag = q_tag.find_next_sibling(['p', 'div', 'dd'])
                if not answer_tag:
                    # Try finding next element with answer class
                    answer_tag = q_tag.find_next(class_=re.compile(r'answer|a[^a-z]', re.I))
                
                if answer_tag and question:
                    answer = answer_tag.get_text(strip=True)
                    if answer and len(answer) > 10:
                        faqs.append(FAQItem(question=question, answer=answer))
        
        # Strategy 2: Look for JSON-LD FAQPage
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'FAQPage':
                    main_entity = data.get('mainEntity', [])
                    for item in main_entity:
                        if item.get('@type') == 'Question':
                            question = item.get('name', '')
                            accepted_answer = item.get('acceptedAnswer', {})
                            answer = accepted_answer.get('text', '')
                            
                            if question and answer:
                                faqs.append(FAQItem(question=question, answer=answer))
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return faqs[:20]  # Limit to 20 FAQs
    
    def _extract_sections(self, soup: BeautifulSoup, page_type: str) -> List[PageSection]:
        """Extract major content sections."""
        sections = []
        
        # Find all major headings
        headings = soup.find_all(['h1', 'h2'])
        
        for heading in headings:
            title = heading.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            
            # Determine section type
            title_lower = title.lower()
            section_type = 'generic'
            
            if any(word in title_lower for word in ['feature', 'benefit', 'capability']):
                section_type = 'features'
            elif any(word in title_lower for word in ['about', 'story', 'mission']):
                section_type = 'about'
            elif any(word in title_lower for word in ['testimonial', 'review', 'customer']):
                section_type = 'testimonials'
            elif any(word in title_lower for word in ['how it works', 'getting started']):
                section_type = 'how_it_works'
            
            # Extract content until next heading
            content_parts = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ['h1', 'h2']:
                    break
                text = sibling.get_text(separator=' ', strip=True)
                if text:
                    content_parts.append(text)
            
            content = ' '.join(content_parts)
            
            if content and len(content) > 50:
                sections.append(PageSection(
                    type=section_type,
                    title=title,
                    content=content,
                    metadata={}
                ))
        
        return sections
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract all JSON-LD and schema.org data."""
        structured = {}
        
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    schema_type = data.get('@type', 'Unknown')
                    if schema_type not in structured:
                        structured[schema_type] = []
                    structured[schema_type].append(data)
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return structured
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main body content."""
        # Try to find main content area
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|body', re.I))
        
        if not main_content:
            main_content = soup.find('body')
        
        if main_content:
            # Remove navigation, forms, and other non-content
            for tag in main_content.find_all(['nav', 'form', 'button']):
                tag.decompose()
            
            text = main_content.get_text(separator=' ', strip=True)
            # Clean up whitespace
            text = ' '.join(text.split())
            return text
        
        return ""