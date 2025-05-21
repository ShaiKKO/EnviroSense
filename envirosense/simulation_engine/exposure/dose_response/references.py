"""
Reference and reliability rating classes for dose-response modeling.

This module provides classes for managing scientific literature references
and reliability ratings for dose-response curve models.
"""

import uuid
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import datetime


class ReliabilityRating(str, Enum):
    """
    Enumeration of reliability ratings for dose-response data sources.
    
    This enum provides a standardized scale to assess the reliability
    of dose-response data based on the quality of the study, methodology,
    and evidence strength.
    """
    
    HIGH = "high"                  # High quality, gold standard studies
    MEDIUM_HIGH = "medium_high"    # Good quality with minor limitations
    MEDIUM = "medium"              # Acceptable quality with some limitations
    MEDIUM_LOW = "medium_low"      # Questionable quality with significant limitations
    LOW = "low"                    # Poor quality with major limitations
    UNKNOWN = "unknown"            # Insufficient information to assess
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return self.value
    
    @classmethod
    def from_string(cls, value: str) -> 'ReliabilityRating':
        """
        Convert a string to a ReliabilityRating enum value.
        
        Args:
            value: String representation of reliability rating
            
        Returns:
            ReliabilityRating enum value
            
        Raises:
            ValueError: If the string doesn't match any enum value
        """
        # Convert to lowercase and replace spaces with underscores
        normalized = value.lower().replace(" ", "_")
        
        # Try to match to an enum value
        for member in cls:
            if member.value == normalized:
                return member
                
        # Allow matching by name
        try:
            return cls[normalized.upper()]
        except KeyError:
            pass
            
        raise ValueError(f"Unknown reliability rating: {value}")


class LiteratureReference:
    """
    Class to store scientific literature reference information.
    
    This class manages bibliographic information about scientific publications
    that serve as sources for dose-response data and models.
    
    Attributes:
        id (str): Unique identifier for this reference
        title (str): Publication title
        authors (List[str]): List of author names
        year (Optional[int]): Publication year
        journal (Optional[str]): Journal or publication title
        volume (Optional[str]): Journal volume
        issue (Optional[str]): Journal issue
        pages (Optional[str]): Page range
        doi (Optional[str]): Digital Object Identifier
        pmid (Optional[str]): PubMed ID
        url (Optional[str]): URL to the reference
        abstract (Optional[str]): Abstract of the publication
        keywords (List[str]): List of keywords associated with the publication
        notes (Optional[str]): Additional notes about the reference
        reliability (Optional[ReliabilityRating]): Reliability rating
        metadata (Dict[str, Any]): Additional metadata about this reference
    """
    
    def __init__(
        self,
        title: str,
        authors: List[str],
        year: Optional[int] = None,
        journal: Optional[str] = None,
        volume: Optional[str] = None,
        issue: Optional[str] = None,
        pages: Optional[str] = None,
        doi: Optional[str] = None,
        pmid: Optional[str] = None,
        url: Optional[str] = None,
        abstract: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        notes: Optional[str] = None,
        reliability: Optional[ReliabilityRating] = None,
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None
    ) -> None:
        """
        Initialize the literature reference.
        
        Args:
            title: Publication title
            authors: List of author names
            year: Publication year
            journal: Journal or publication title
            volume: Journal volume
            issue: Journal issue
            pages: Page range
            doi: Digital Object Identifier
            pmid: PubMed ID
            url: URL to the reference
            abstract: Abstract of the publication
            keywords: List of keywords associated with the publication
            notes: Additional notes about the reference
            reliability: Reliability rating
            metadata: Additional metadata about this reference
            id: Unique identifier (generated if not provided)
        """
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.authors = authors
        self.year = year
        self.journal = journal
        self.volume = volume
        self.issue = issue
        self.pages = pages
        self.doi = doi
        self.pmid = pmid
        self.url = url
        self.abstract = abstract
        self.keywords = keywords or []
        self.notes = notes
        self.reliability = reliability
        self.metadata = metadata or {}
    
    @property
    def citation(self) -> str:
        """
        Get a formatted citation string.
        
        Returns:
            Formatted citation string in a common academic format
        """
        # Format authors
        if not self.authors:
            author_text = "Unknown Author"
        elif len(self.authors) == 1:
            author_text = self.authors[0]
        elif len(self.authors) == 2:
            author_text = f"{self.authors[0]} and {self.authors[1]}"
        else:
            author_text = f"{self.authors[0]} et al."
            
        # Format year
        year_text = f" ({self.year})" if self.year else ""
        
        # Format title
        title_text = f" {self.title}"
        
        # Format journal info
        if self.journal:
            journal_text = f" {self.journal}"
            
            if self.volume:
                journal_text += f" {self.volume}"
                
                if self.issue:
                    journal_text += f"({self.issue})"
                    
            if self.pages:
                journal_text += f": {self.pages}"
        else:
            journal_text = ""
            
        # Format DOI
        doi_text = f" DOI: {self.doi}" if self.doi else ""
        
        # Combine all parts
        return f"{author_text}{year_text}.{title_text}.{journal_text}.{doi_text}"
    
    def to_bibtex(self) -> str:
        """
        Generate a BibTeX entry for this reference.
        
        Returns:
            BibTeX entry as a string
        """
        # Generate a BibTeX key from the first author's last name and year
        if self.authors and self.year:
            first_author = self.authors[0].split()[-1]  # Assume last word is last name
            bibtex_key = f"{first_author}{self.year}"
        else:
            bibtex_key = f"ref{self.id[:8]}"  # Use part of the UUID
            
        # Start BibTeX entry
        bibtex = []
        if self.journal:
            bibtex.append(f"@article{{{bibtex_key},")
        else:
            bibtex.append(f"@misc{{{bibtex_key},")
            
        # Add required fields
        bibtex.append(f"  title = {{{self.title}}},")
        
        # Add authors
        if self.authors:
            authors_str = " and ".join(self.authors)
            bibtex.append(f"  author = {{{authors_str}}},")
            
        # Add optional fields
        if self.year:
            bibtex.append(f"  year = {{{self.year}}},")
            
        if self.journal:
            bibtex.append(f"  journal = {{{self.journal}}},")
            
        if self.volume:
            bibtex.append(f"  volume = {{{self.volume}}},")
            
        if self.issue:
            bibtex.append(f"  number = {{{self.issue}}},")
            
        if self.pages:
            bibtex.append(f"  pages = {{{self.pages}}},")
            
        if self.doi:
            bibtex.append(f"  doi = {{{self.doi}}},")
            
        if self.url:
            bibtex.append(f"  url = {{{self.url}}},")
            
        # Close the entry
        bibtex[-1] = bibtex[-1][:-1]  # Remove the trailing comma
        bibtex.append("}")
        
        return "\n".join(bibtex)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the reference to a dictionary representation.
        
        Returns:
            Dictionary containing all reference data
        """
        return {
            'id': self.id,
            'title': self.title,
            'authors': self.authors,
            'year': self.year,
            'journal': self.journal,
            'volume': self.volume,
            'issue': self.issue,
            'pages': self.pages,
            'doi': self.doi,
            'pmid': self.pmid,
            'url': self.url,
            'abstract': self.abstract,
            'keywords': self.keywords,
            'notes': self.notes,
            'reliability': self.reliability.value if self.reliability else None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LiteratureReference':
        """
        Create a literature reference from a dictionary representation.
        
        Args:
            data: Dictionary containing reference data
            
        Returns:
            Instantiated literature reference
            
        Raises:
            ValueError: If data format is invalid or incompatible
        """
        # Extract reliability rating if present
        reliability = None
        if data.get('reliability'):
            try:
                reliability = ReliabilityRating.from_string(data['reliability'])
            except ValueError:
                # Ignore invalid reliability ratings
                pass
                
        # Create the reference
        return cls(
            title=data.get('title', ''),
            authors=data.get('authors', []),
            year=data.get('year'),
            journal=data.get('journal'),
            volume=data.get('volume'),
            issue=data.get('issue'),
            pages=data.get('pages'),
            doi=data.get('doi'),
            pmid=data.get('pmid'),
            url=data.get('url'),
            abstract=data.get('abstract'),
            keywords=data.get('keywords', []),
            notes=data.get('notes'),
            reliability=reliability,
            metadata=data.get('metadata', {}),
            id=data.get('id')
        )
    
    def to_json(self, filepath: Optional[str] = None) -> str:
        """
        Convert the reference to JSON representation.
        
        Args:
            filepath: If provided, write JSON to this file
            
        Returns:
            JSON string representation
        """
        import json
        
        # Convert to JSON
        json_data = json.dumps(self.to_dict(), indent=2)
        
        # Write to file if requested
        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_data)
        
        return json_data
    
    @classmethod
    def from_json(cls, json_data: Union[str, Dict], filepath: Optional[str] = None) -> 'LiteratureReference':
        """
        Create a literature reference from JSON representation.
        
        Args:
            json_data: JSON string or already parsed dictionary
            filepath: If provided, read JSON from this file
            
        Returns:
            Instantiated literature reference
            
        Raises:
            ValueError: If JSON format is invalid or incompatible
        """
        import json
        
        # Read from file if requested
        if filepath:
            with open(filepath, 'r') as f:
                json_data = f.read()
        
        # Parse JSON if it's a string
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data
        
        # Use the from_dict method
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return self.citation
    
    def __repr__(self) -> str:
        """Return a string representation for developers."""
        return f"LiteratureReference(title='{self.title}', authors={self.authors}, year={self.year})"


class ReferenceCollection:
    """
    Collection of literature references with search capabilities.
    
    This class manages a set of literature references and provides
    search and filtering functionality.
    
    Attributes:
        references (List[LiteratureReference]): List of references in the collection
    """
    
    def __init__(self, references: Optional[List[LiteratureReference]] = None) -> None:
        """
        Initialize the reference collection.
        
        Args:
            references: Initial list of references
        """
        self.references = references or []
    
    def add(self, reference: LiteratureReference) -> None:
        """
        Add a reference to the collection.
        
        Args:
            reference: Reference to add
        """
        self.references.append(reference)
    
    def remove(self, reference_id: str) -> bool:
        """
        Remove a reference from the collection by ID.
        
        Args:
            reference_id: ID of the reference to remove
            
        Returns:
            True if the reference was removed, False if not found
        """
        initial_length = len(self.references)
        self.references = [ref for ref in self.references if ref.id != reference_id]
        return len(self.references) < initial_length
    
    def get(self, reference_id: str) -> Optional[LiteratureReference]:
        """
        Get a reference by ID.
        
        Args:
            reference_id: ID of the reference to get
            
        Returns:
            The reference if found, None otherwise
        """
        for ref in self.references:
            if ref.id == reference_id:
                return ref
        return None
    
    def search(self, 
              query: str = "", 
              authors: Optional[List[str]] = None,
              year: Optional[Union[int, List[int]]] = None,
              journal: Optional[str] = None,
              reliability: Optional[ReliabilityRating] = None,
              keywords: Optional[List[str]] = None
             ) -> List[LiteratureReference]:
        """
        Search for references matching given criteria.
        
        Args:
            query: Text to search in title and abstract
            authors: Author names to match
            year: Publication year(s) to match
            journal: Journal to match
            reliability: Reliability rating to match
            keywords: Keywords to match
            
        Returns:
            List of matching references
        """
        results = []
        query = query.lower()
        
        # Convert year to list if it's a single value
        if isinstance(year, int):
            year = [year]
            
        # Process each reference
        for ref in self.references:
            # Skip if query doesn't match title or abstract
            if query and not (
                (ref.title and query in ref.title.lower()) or
                (ref.abstract and query in ref.abstract.lower())
            ):
                continue
                
            # Skip if authors don't match
            if authors and not any(author in ref.authors for author in authors):
                continue
                
            # Skip if year doesn't match
            if year and (not ref.year or ref.year not in year):
                continue
                
            # Skip if journal doesn't match
            if journal and (not ref.journal or journal.lower() not in ref.journal.lower()):
                continue
                
            # Skip if reliability doesn't match
            if reliability and ref.reliability != reliability:
                continue
                
            # Skip if keywords don't match
            if keywords and not any(keyword in ref.keywords for keyword in keywords):
                continue
                
            # If we get here, the reference matches all criteria
            results.append(ref)
            
        return results
    
    def to_list(self) -> List[Dict[str, Any]]:
        """
        Convert the collection to a list of dictionaries.
        
        Returns:
            List of reference dictionaries
        """
        return [ref.to_dict() for ref in self.references]
    
    def to_json(self, filepath: Optional[str] = None) -> str:
        """
        Convert the collection to JSON representation.
        
        Args:
            filepath: If provided, write JSON to this file
            
        Returns:
            JSON string representation
        """
        import json
        
        # Convert to JSON
        json_data = json.dumps(self.to_list(), indent=2)
        
        # Write to file if requested
        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_data)
        
        return json_data
    
    @classmethod
    def from_json(cls, json_data: Union[str, List], filepath: Optional[str] = None) -> 'ReferenceCollection':
        """
        Create a reference collection from JSON representation.
        
        Args:
            json_data: JSON string or already parsed list
            filepath: If provided, read JSON from this file
            
        Returns:
            Instantiated reference collection
            
        Raises:
            ValueError: If JSON format is invalid or incompatible
        """
        import json
        
        # Read from file if requested
        if filepath:
            with open(filepath, 'r') as f:
                json_data = f.read()
        
        # Parse JSON if it's a string
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data
        
        # Create references from the data
        references = [LiteratureReference.from_dict(item) for item in data]
        
        # Return a new collection
        return cls(references)
    
    def __len__(self) -> int:
        """Return the number of references in the collection."""
        return len(self.references)
    
    def __iter__(self):
        """Allow iteration over the references."""
        return iter(self.references)
    
    def __getitem__(self, index: int) -> LiteratureReference:
        """Allow indexing to access references."""
        return self.references[index]
