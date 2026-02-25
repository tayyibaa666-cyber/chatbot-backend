"""
INTELLIGENT URL PRIORITIZATION - CRITICAL PAGES FIRST
Ensures critical pages (pricing, contact, FAQ) are crawled first.
"""

from typing import List, Dict, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass
import re


@dataclass
class URLPriority:
    """URL with priority score."""
    url: str
    priority: int  # Higher is more important (0-100)
    category: str  # Type of page
    
    def __lt__(self, other):
        # Sort by priority descending
        return self.priority > other.priority


class IntelligentURLPrioritizer:
    """
    Prioritizes URLs based on importance for chatbot training.
    Critical pages like pricing, contact, FAQ get highest priority.
    """
    
    # Priority weights (higher = more important)
    PRIORITY_RULES = {
        # Critical pages - always crawl these first
        'pricing': 100,
        'contact': 95,
        'support': 90,
        'faq': 90,
        'help': 85,
        
        # Important pages
        'about': 80,
        'features': 75,
        'product': 75,
        'service': 75,
        'services': 75,
        'terms': 70,
        'privacy': 70,
        'documentation': 70,
        'docs': 70,
        
        # Useful pages
        'solutions': 60,
        'resources': 55,
        'blog': 50,
        'case-study': 50,
        'case study': 50,
        'testimonial': 50,
        'portfolio': 50,
        
        # Lower priority
        'news': 40,
        'press': 30,
        'career': 20,
        'job': 20,
        'jobs': 20,
        
        # Usually skip these
        'login': 0,
        'signup': 0,
        'sign-up': 0,
        'register': 0,
        'cart': 0,
        'checkout': 0,
        'logout': 0,
        'account': 0,
        'dashboard': 0,
        'admin': 0,
    }
    
    # Boost for homepage and main sections
    HOMEPAGE_BOOST = 10
    SHORT_PATH_BOOST = 5  # Boost for simple paths (fewer slashes)
    
    def prioritize_urls(self, urls: List[str], seed_url: str) -> List[str]:
        """
        Sort URLs by priority, ensuring important pages are crawled first.
        
        Args:
            urls: List of URLs to prioritize
            seed_url: Original seed URL (gets boost if homepage)
        
        Returns:
            Sorted list of URLs (highest priority first)
        """
        prioritized = []
        
        for url in urls:
            priority = self._calculate_priority(url, seed_url)
            category = self._categorize_url(url)
            
            prioritized.append(URLPriority(
                url=url,
                priority=priority,
                category=category
            ))
        
        # Sort by priority (descending)
        prioritized.sort()
        
        return [item.url for item in prioritized]
    
    def _calculate_priority(self, url: str, seed_url: str) -> int:
        """Calculate priority score for a URL."""
        url_lower = url.lower()
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Base priority
        priority = 50
        
        # Check against priority rules
        matched_rule = None
        max_rule_priority = 0
        
        for keyword, rule_priority in self.PRIORITY_RULES.items():
            # Check both path and full URL
            if keyword in path or keyword in url_lower:
                if rule_priority > max_rule_priority:
                    max_rule_priority = rule_priority
                    matched_rule = keyword
        
        if matched_rule:
            priority = max_rule_priority
        
        # Homepage boost
        if self._is_homepage(url, seed_url):
            priority += self.HOMEPAGE_BOOST
        
        # Short path boost (pages closer to root are often more important)
        path_depth = len([p for p in path.split('/') if p])
        if path_depth <= 1:
            priority += self.SHORT_PATH_BOOST
        elif path_depth == 2:
            priority += self.SHORT_PATH_BOOST // 2
        
        # Penalize very long URLs (often dynamic/junk)
        if len(url) > 200:
            priority -= 20
        
        # Penalize query parameters (often dynamic content)
        if '?' in url and 'page=' not in url_lower:
            priority -= 10
        
        # Boost if URL contains numbers (might be important like pricing-v2)
        if re.search(r'\d+', path) and not re.search(r'page=\d+', url_lower):
            priority += 5
        
        # Ensure priority stays in valid range
        return max(0, min(100, priority))
    
    def _categorize_url(self, url: str) -> str:
        """Categorize the URL type."""
        url_lower = url.lower()
        
        # Check each category
        for keyword in self.PRIORITY_RULES.keys():
            if keyword in url_lower:
                return keyword
        
        if self._is_homepage(url, url):
            return 'homepage'
        
        return 'generic'
    
    def _is_homepage(self, url: str, seed_url: str) -> bool:
        """Check if URL is likely a homepage."""
        parsed = urlparse(url)
        seed_parsed = urlparse(seed_url)
        
        # Same domain and path is root or index
        if parsed.netloc == seed_parsed.netloc:
            path = parsed.path.lower()
            if path in ['/', '', '/index.html', '/index.htm', '/home', '/index.php']:
                return True
        
        return False
    
    def filter_low_priority(self, urls: List[str], min_priority: int = 10) -> List[str]:
        """
        Filter out URLs below a minimum priority threshold.
        
        Args:
            urls: List of URLs to filter
            min_priority: Minimum priority score (0-100)
        
        Returns:
            Filtered list of URLs
        """
        filtered = []
        
        for url in urls:
            priority = self._calculate_priority(url, urls[0] if urls else url)
            if priority >= min_priority:
                filtered.append(url)
        
        return filtered
    
    def get_must_have_patterns(self) -> List[str]:
        """Get regex patterns for URLs that should always be included."""
        return [
            r'.*/pricing.*',
            r'.*/contact.*',
            r'.*/support.*',
            r'.*/faq.*',
            r'.*/help.*',
            r'.*/about.*',
            r'.*/features.*',
        ]
    
    def ensure_critical_pages(self, urls: List[str], all_discovered_urls: List[str]) -> List[str]:
        """
        Ensure critical pages are included even if they weren't in the top N.
        
        Args:
            urls: Current selected URLs
            all_discovered_urls: All discovered URLs
        
        Returns:
            URLs with critical pages ensured
        """
        patterns = self.get_must_have_patterns()
        urls_set = set(urls)
        
        for pattern in patterns:
            regex = re.compile(pattern, re.IGNORECASE)
            for discovered_url in all_discovered_urls:
                if regex.search(discovered_url) and discovered_url not in urls_set:
                    urls.append(discovered_url)
                    urls_set.add(discovered_url)
                    break
        
        return urls


def prioritize_urls(urls: List[str], seed_url: str = None, max_urls: int = None) -> List[str]:
    """
    Convenience function to prioritize URLs.
    
    Args:
        urls: List of URLs to prioritize
        seed_url: Original seed URL (optional)
        max_urls: Maximum number of URLs to return (optional)
    
    Returns:
        Prioritized list of URLs
    """
    if not urls:
        return []
    
    prioritizer = IntelligentURLPrioritizer()
    seed = seed_url or urls[0]
    
    # Prioritize
    prioritized = prioritizer.prioritize_urls(urls, seed)
    
    # Ensure critical pages if we have more URLs available
    if max_urls and len(urls) > max_urls:
        selected = prioritized[:max_urls]
        prioritized = prioritizer.ensure_critical_pages(selected, urls)
        prioritized = prioritized[:max_urls]
    
    return prioritized