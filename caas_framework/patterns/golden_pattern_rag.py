"""
Golden Pattern RAG (Retrieval-Augmented Generation)

Stores successful code generation results and retrieves similar patterns
for reuse in future requests, improving quality and consistency.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from caas_framework.models.specifications import ConcretizedRequirement, FeatureSpec
from caas_framework.utils.logger import get_logger

try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

logger = get_logger()


@dataclass
class PatternMatch:
    """Represents a matched pattern from the library."""

    request: str
    features: List[Dict[str, Any]]
    num_agents: int
    num_tasks: int
    satisfaction: float
    timestamp: str
    similarity: float = 0.0


class Feedback(BaseModel):
    """User feedback for a code generation result."""

    satisfaction: int = Field(ge=1, le=5, description="Satisfaction rating (1-5)")
    comments: Optional[str] = None


class GoldenPatternLibrary:
    """
    Stores and retrieves successful code generation patterns using RAG.

    Uses vector embeddings to find similar past successful projects and
    suggests missing features based on those patterns.
    """

    def __init__(
        self,
        collection_name: str = "golden_patterns",
        persist_directory: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize the Golden Pattern Library.

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist the database
            embedding_model: Sentence transformer model name
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory or "./data/patterns"
        self.embedding_model_name = embedding_model

        # In-memory fallback when dependencies unavailable
        self.use_fallback = not (CHROMADB_AVAILABLE and SENTENCE_TRANSFORMERS_AVAILABLE)
        self.fallback_storage: List[Dict[str, Any]] = []

        if not self.use_fallback:
            self._init_chromadb()
            self._init_encoder()

    def _init_chromadb(self):
        """Initialize ChromaDB client and collection."""
        try:
            settings = Settings(
                persist_directory=self.persist_directory, anonymized_telemetry=False
            )
            self.chroma_client = chromadb.Client(settings)

            # Get or create collection
            try:
                self.collection = self.chroma_client.get_collection(name=self.collection_name)
            except Exception:
                self.collection = self.chroma_client.create_collection(name=self.collection_name)
        except Exception as e:
            logger.warning(f"ChromaDB initialization failed: {e}")
            logger.info("Falling back to in-memory storage")
            self.use_fallback = True

    def _init_encoder(self):
        """Initialize sentence transformer model."""
        try:
            self.encoder = SentenceTransformer(self.embedding_model_name)
        except Exception as e:
            logger.warning(f"Sentence transformer initialization failed: {e}")
            logger.info("Falling back to simple text matching")
            self.use_fallback = True

    def store_successful_generation(
        self,
        user_request: str,
        concretized: ConcretizedRequirement,
        design: Optional[Dict[str, Any]] = None,
        user_feedback: Optional[Feedback] = None,
    ) -> bool:
        """
        Store a successful code generation result.

        Args:
            user_request: Original user request text
            concretized: Concretized requirement specification
            design: Optional design output (agents, tasks)
            user_feedback: Optional user feedback

        Returns:
            True if stored successfully, False otherwise
        """
        # Default feedback if not provided
        if user_feedback is None:
            user_feedback = Feedback(satisfaction=5)

        # Only store high-satisfaction results
        if user_feedback.satisfaction < 4:
            return False

        # Extract features
        features_dict = [
            {
                "id": f.id if hasattr(f, "id") else f"feat_{i}",
                "name": f.name,
                "description": f.description,
                "priority": f.priority if hasattr(f, "priority") else "medium",
                "acceptance_criteria": (
                    f.acceptance_criteria if hasattr(f, "acceptance_criteria") else []
                ),
            }
            for i, f in enumerate(concretized.features)
        ]

        # Extract design info
        num_agents = len(design.get("agents", [])) if design else 0
        num_tasks = len(design.get("tasks", [])) if design else 0

        # Create metadata
        metadata = {
            "features": json.dumps(features_dict),
            "num_agents": num_agents,
            "num_tasks": num_tasks,
            "satisfaction": user_feedback.satisfaction,
            "timestamp": datetime.now().isoformat(),
            "domain": concretized.domain if hasattr(concretized, "domain") else "general",
        }

        # Generate unique ID
        pattern_id = self._generate_id(user_request)

        if self.use_fallback:
            return self._store_fallback(user_request, metadata, pattern_id)
        else:
            return self._store_chromadb(user_request, metadata, pattern_id)

    def _store_chromadb(self, user_request: str, metadata: Dict[str, Any], pattern_id: str) -> bool:
        """Store pattern in ChromaDB."""
        try:
            # Generate embedding
            embedding = self.encoder.encode(user_request)

            # Store in ChromaDB
            self.collection.add(
                documents=[user_request],
                embeddings=[embedding.tolist()],
                metadatas=[metadata],
                ids=[pattern_id],
            )

            return True
        except Exception as e:
            logger.error(f"Error storing pattern: {e}")
            return False

    def _store_fallback(self, user_request: str, metadata: Dict[str, Any], pattern_id: str) -> bool:
        """Store pattern in fallback in-memory storage."""
        try:
            self.fallback_storage.append(
                {"id": pattern_id, "document": user_request, "metadata": metadata}
            )
            return True
        except Exception as e:
            logger.error(f"Error storing pattern: {e}")
            return False

    def _generate_id(self, text: str) -> str:
        """Generate unique ID from text."""
        return f"pattern_{hashlib.md5(text.encode()).hexdigest()[:16]}"

    def retrieve_similar_patterns(
        self, user_request: str, top_k: int = 3, min_similarity: float = 0.5
    ) -> List[PatternMatch]:
        """
        Retrieve similar successful patterns.

        Args:
            user_request: The new user request
            top_k: Number of top results to return
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of pattern matches
        """
        if self.use_fallback:
            return self._retrieve_fallback(user_request, top_k)
        else:
            return self._retrieve_chromadb(user_request, top_k, min_similarity)

    def _retrieve_chromadb(
        self, user_request: str, top_k: int, min_similarity: float
    ) -> List[PatternMatch]:
        """Retrieve patterns from ChromaDB."""
        try:
            # Generate query embedding
            query_embedding = self.encoder.encode(user_request)

            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=min(top_k, self.collection.count()),
            )

            # Convert to PatternMatch objects
            matches = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i]

                    # Calculate similarity from distance
                    # ChromaDB returns distances, convert to similarity
                    distance = results["distances"][0][i] if "distances" in results else 0
                    similarity = 1.0 / (1.0 + distance)

                    if similarity >= min_similarity:
                        matches.append(
                            PatternMatch(
                                request=doc,
                                features=json.loads(metadata["features"]),
                                num_agents=metadata["num_agents"],
                                num_tasks=metadata["num_tasks"],
                                satisfaction=metadata["satisfaction"],
                                timestamp=metadata["timestamp"],
                                similarity=similarity,
                            )
                        )

            return matches
        except Exception as e:
            logger.error(f"Error retrieving patterns: {e}")
            return []

    def _retrieve_fallback(self, user_request: str, top_k: int) -> List[PatternMatch]:
        """Retrieve patterns from fallback storage using simple text matching."""
        matches = []

        request_lower = user_request.lower()
        words = set(request_lower.split())

        for pattern in self.fallback_storage:
            doc = pattern["document"]
            doc_words = set(doc.lower().split())

            # Simple Jaccard similarity
            intersection = words & doc_words
            union = words | doc_words
            similarity = len(intersection) / len(union) if union else 0.0

            if similarity > 0.1:  # Very low threshold for fallback
                metadata = pattern["metadata"]
                matches.append(
                    PatternMatch(
                        request=doc,
                        features=json.loads(metadata["features"]),
                        num_agents=metadata["num_agents"],
                        num_tasks=metadata["num_tasks"],
                        satisfaction=metadata["satisfaction"],
                        timestamp=metadata["timestamp"],
                        similarity=similarity,
                    )
                )

        # Sort by similarity and return top_k
        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:top_k]

    def enhance_with_patterns(
        self,
        user_request: str,
        concretized: ConcretizedRequirement,
        auto_add: bool = False,
        verbose: bool = True,
    ) -> ConcretizedRequirement:
        """
        Enhance concretized requirements with features from similar patterns.

        Args:
            user_request: The user request
            concretized: Current concretized requirements
            auto_add: Automatically add suggested features without prompting
            verbose: Print suggestions

        Returns:
            Enhanced concretized requirements
        """
        # Retrieve similar patterns
        similar_patterns = self.retrieve_similar_patterns(user_request, top_k=3)

        if not similar_patterns:
            if verbose:
                logger.info("✓ No similar patterns found in library")
            return concretized

        # Get current feature names
        current_feature_names = {f.name.lower() for f in concretized.features}

        # Collect suggested features from best match
        best_match = similar_patterns[0]
        suggested_features = []

        for feature in best_match.features:
            if feature["name"].lower() not in current_feature_names:
                suggested_features.append(feature)

        if not suggested_features:
            if verbose:
                logger.info(f"✓ Found similar pattern (similarity: {best_match.similarity:.2%})")
                logger.info("  All features already included")
            return concretized

        # Display suggestions
        if verbose:
            self._print_suggestions(best_match, suggested_features)

        # Ask user or auto-add
        should_add = auto_add
        if not auto_add and verbose:
            response = input("\nAdd these features? (y/n): ").strip().lower()
            should_add = response == "y"

        if should_add:
            for feature_data in suggested_features:
                # Create FeatureSpec from the stored data
                new_feature = FeatureSpec(
                    id=feature_data.get("id", f"feat_{len(concretized.features)}"),
                    name=feature_data["name"],
                    description=feature_data["description"],
                    priority=feature_data.get("priority", "medium"),
                    acceptance_criteria=feature_data.get("acceptance_criteria", []),
                )
                concretized.features.append(new_feature)

            if verbose:
                logger.info(f"✓ Added {len(suggested_features)} features from pattern library")

        return concretized

    def _print_suggestions(self, pattern: PatternMatch, suggested_features: List[Dict[str, Any]]):
        """Print pattern suggestions to user."""
        logger.info("\n" + "=" * 70)
        logger.info("💡 PATTERN SUGGESTION")
        logger.info("=" * 70)
        logger.info(f"Found similar project (similarity: {pattern.similarity:.1%})")
        logger.info(f'Original request: "{pattern.request}"')
        logger.info(f"User satisfaction: {pattern.satisfaction}/5 ⭐")
        logger.info("\nSuggested features from this pattern:")

        for feature in suggested_features:
            logger.info(f"  • {feature['name']}")
            logger.info(f"    └─ {feature['description']}")

        logger.info("=" * 70)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get library statistics.

        Returns:
            Dictionary with pattern library stats
        """
        if self.use_fallback:
            total = len(self.fallback_storage)
            if total == 0:
                return {"total_patterns": 0, "avg_satisfaction": 0, "domains": []}

            satisfactions = [float(p["metadata"]["satisfaction"]) for p in self.fallback_storage]
            domains = [p["metadata"].get("domain", "general") for p in self.fallback_storage]
        else:
            try:
                total = self.collection.count()
                if total == 0:
                    return {"total_patterns": 0, "avg_satisfaction": 0, "domains": []}

                # Get all patterns
                results = self.collection.get()
                satisfactions = [m["satisfaction"] for m in results["metadatas"]]
                domains = [m.get("domain", "general") for m in results["metadatas"]]
            except Exception:
                return {"total_patterns": 0, "avg_satisfaction": 0, "domains": []}

        return {
            "total_patterns": total,
            "avg_satisfaction": sum(satisfactions) / len(satisfactions) if satisfactions else 0,
            "domains": list(set(domains)),
            "domain_counts": {d: domains.count(d) for d in set(domains)},
        }


def store_successful_pattern(
    library: GoldenPatternLibrary,
    user_request: str,
    concretized: ConcretizedRequirement,
    design: Optional[Dict[str, Any]] = None,
    satisfaction: int = 5,
) -> bool:
    """
    Convenience function to store a successful pattern.

    Args:
        library: The pattern library
        user_request: Original user request
        concretized: Concretized requirements
        design: Optional design output
        satisfaction: User satisfaction rating (1-5)

    Returns:
        True if stored successfully
    """
    feedback = Feedback(satisfaction=satisfaction)
    return library.store_successful_generation(
        user_request=user_request, concretized=concretized, design=design, user_feedback=feedback
    )


def retrieve_patterns(
    library: GoldenPatternLibrary, user_request: str, top_k: int = 3
) -> List[PatternMatch]:
    """
    Convenience function to retrieve similar patterns.

    Args:
        library: The pattern library
        user_request: The user request to match
        top_k: Number of results to return

    Returns:
        List of pattern matches
    """
    return library.retrieve_similar_patterns(user_request, top_k=top_k)
