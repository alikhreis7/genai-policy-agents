"""
Data loading and indexing utilities.

Handles:
- Loading policy documents from various sources
- Section-based chunking (not arbitrary token splits)
- Index creation and persistence
"""

import hashlib
import re
from pathlib import Path
from typing import Optional

from ..models.schemas import PolicyChunk


class PolicyLoader:
    """
    Loads and chunks policy documents.
    
    Key design decision: Section-based chunking
    
    Unlike typical RAG systems that chunk by token count, we chunk by
    document structure (sections, headings). This preserves semantic
    coherence and makes citations more meaningful.
    """
    
    def __init__(self, policies_dir: Optional[Path] = None):
        """
        Initialize the policy loader.
        
        Args:
            policies_dir: Directory containing policy markdown files
        """
        self.policies_dir = policies_dir or Path(__file__).parent.parent.parent / "data" / "policies"
    
    def load_all_policies(self) -> list[PolicyChunk]:
        """
        Load all policy documents and return chunks.
        
        Returns:
            List of PolicyChunk objects
        """
        chunks = []
        
        if not self.policies_dir.exists():
            # Return sample policies if directory doesn't exist
            return self._get_sample_policies()
        
        for policy_file in self.policies_dir.glob("*.md"):
            file_chunks = self.load_policy_file(policy_file)
            chunks.extend(file_chunks)
        
        return chunks if chunks else self._get_sample_policies()
    
    def load_policy_file(self, file_path: Path) -> list[PolicyChunk]:
        """
        Load a single policy file and chunk by sections.
        
        Args:
            file_path: Path to the markdown policy file
            
        Returns:
            List of PolicyChunk objects
        """
        content = file_path.read_text(encoding="utf-8")
        source = file_path.name
        
        return self.chunk_by_sections(content, source)
    
    def chunk_by_sections(
        self, 
        content: str, 
        source: str,
        section_markers: list[str] = None
    ) -> list[PolicyChunk]:
        """
        Chunk document by section headings.
        
        This is a key differentiator from standard chunking:
        - Preserves document structure
        - Each chunk is a coherent section
        - Better for citation and attribution
        
        Args:
            content: Full document content
            source: Source identifier
            section_markers: Heading markers (default: ##)
            
        Returns:
            List of PolicyChunk objects
        """
        section_markers = section_markers or ["##", "###"]
        
        # Build regex pattern for section detection
        pattern = r"^(" + "|".join(re.escape(m) for m in section_markers) + r")\s+(.+)$"
        
        chunks = []
        current_section = None
        current_content = []
        
        for line in content.split("\n"):
            match = re.match(pattern, line, re.MULTILINE)
            
            if match:
                # Save previous section
                if current_content:
                    chunk_text = "\n".join(current_content).strip()
                    if chunk_text:
                        chunks.append(self._create_chunk(
                            content=chunk_text,
                            source=source,
                            section=current_section
                        ))
                
                # Start new section
                current_section = match.group(2).strip()
                current_content = [line]
            else:
                current_content.append(line)
        
        # Don't forget the last section
        if current_content:
            chunk_text = "\n".join(current_content).strip()
            if chunk_text:
                chunks.append(self._create_chunk(
                    content=chunk_text,
                    source=source,
                    section=current_section
                ))
        
        # If no sections found, treat whole document as one chunk
        if not chunks and content.strip():
            chunks.append(self._create_chunk(
                content=content.strip(),
                source=source,
                section="Document"
            ))
        
        return chunks
    
    def _create_chunk(
        self, 
        content: str, 
        source: str, 
        section: Optional[str]
    ) -> PolicyChunk:
        """Create a PolicyChunk with generated ID."""
        # Generate deterministic chunk ID
        chunk_id = hashlib.md5(
            f"{source}:{section}:{content[:100]}".encode()
        ).hexdigest()[:12]
        
        return PolicyChunk(
            content=content,
            source=source,
            section=section,
            relevance_score=0.0,  # Will be set during retrieval
            chunk_id=chunk_id,
            metadata={
                "char_count": len(content),
                "word_count": len(content.split()),
            }
        )
    
    def _get_sample_policies(self) -> list[PolicyChunk]:
        """
        Return sample policy chunks for demo purposes.
        
        These are based on real-world policy patterns from:
        - Google SRE practices
        - AWS Well-Architected Framework
        - OWASP guidelines
        """
        sample_policies = [
            # Data Security Policy
            {
                "source": "data-security-policy.md",
                "sections": [
                    ("Data Classification", """## Data Classification

All data must be classified according to sensitivity:

1. **PUBLIC**: Information that can be freely shared
2. **INTERNAL**: Business information for internal use only
3. **CONFIDENTIAL**: Sensitive data requiring access controls
4. **RESTRICTED**: Highly sensitive data (PII, financial, health)

Classification determines handling requirements for storage, transmission, and access."""),
                    
                    ("PII Handling", """## PII Handling Requirements

Personal Identifiable Information (PII) requires special handling:

### Storage
- Must use approved encrypted data stores
- Encryption at rest required (AES-256 minimum)
- Data must be stored in approved geographic regions

### Access
- Principle of least privilege
- All access must be logged and auditable
- Regular access reviews required

### Prohibited Practices
- No PII in logs or error messages
- No PII in general-purpose caches
- No PII in analytics without anonymization"""),
                ]
            },
            
            # API Standards
            {
                "source": "api-standards.md",
                "sections": [
                    ("API Gateway Policy", """## API Gateway Requirements

All external-facing APIs must route through the central API Gateway.

### Required for All External APIs
- Rate limiting
- Authentication verification
- Request/response logging
- DDoS protection

### Internal Service Communication
Internal services may use direct communication with:
- Mutual TLS (mTLS) authentication
- Service mesh (Istio/Linkerd)
- Documented service contracts"""),

                    ("API Versioning", """## API Versioning Policy

All APIs must implement versioning:

1. **URL Path Versioning**: `/api/v1/resource` (preferred)
2. **Header Versioning**: Accept-Version header (acceptable)
3. **Query Parameter**: `?version=1` (discouraged)

### Deprecation Policy
- Minimum 6 months notice before deprecation
- Clear migration guides required
- Metrics on version usage before removal"""),
                ]
            },
            
            # Security Policy
            {
                "source": "security-policy.md",
                "sections": [
                    ("Authentication Standards", """## Authentication Standards

### Password Requirements
- Minimum 12 characters
- Complexity: uppercase, lowercase, number, special char
- No reuse of last 12 passwords
- Maximum age: 90 days for privileged accounts

### Multi-Factor Authentication
Required for:
- All production system access
- Admin consoles and dashboards
- VPN and remote access
- Access to PII or financial data

### API Authentication
- OAuth 2.0 for user-context APIs
- API keys for service-to-service (with rotation)
- JWT tokens with appropriate expiration"""),

                    ("Secret Management", """## Secret Management

Secrets (passwords, API keys, certificates) must be managed securely:

### Approved Solutions
- HashiCorp Vault (preferred)
- AWS Secrets Manager
- Azure Key Vault
- GCP Secret Manager

### Prohibited Practices
- No secrets in source code
- No secrets in environment variables for production
- No secrets in configuration files
- No secrets in container images

### Rotation Requirements
- Database passwords: 90 days
- API keys: 180 days
- Certificates: Before expiration"""),
                ]
            },
        ]
        
        chunks = []
        for policy in sample_policies:
            source = policy["source"]
            for section_name, content in policy["sections"]:
                chunks.append(self._create_chunk(
                    content=content,
                    source=source,
                    section=section_name
                ))
        
        return chunks


def load_policies(policies_dir: Optional[Path] = None) -> list[PolicyChunk]:
    """Convenience function to load all policies."""
    loader = PolicyLoader(policies_dir)
    return loader.load_all_policies()


def create_policy_index(chunks: list[PolicyChunk]):
    """
    Create a FAISS index from policy chunks.
    
    Returns the initialized PolicyRAGAgent with the index.
    """
    from ..agents.policy_rag import PolicyRAGAgent
    
    agent = PolicyRAGAgent()
    agent.initialize_index(chunks)
    return agent
