"""Knowledge Base Query Engine for LAS.

Maintains strict read-only boundary checks to prevent directory traversal
and searches/indexes structured YAML knowledge documents.
"""

from __future__ import annotations

import json
import logging
import os
import math
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Standard English stopwords (to clean up high-frequency noise words)
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's",
    "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
    "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't",
    "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's",
    "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when",
    "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}


class KnowledgeBase:
    """Secure, read-only manager for domain knowledge base documents."""

    @staticmethod
    def query(keyword: str, workspace_path: str = ".") -> list[dict[str, Any]]:
        """Query indexed static knowledge base documents by a keyword.

        Checks for matches in tags, title, description, ID, or raw text.
        Maintains robust read-only boundary check to prevent traversal out of
        the active knowledge_base directory.
        """
        resolved_workspace = Path(os.path.abspath(workspace_path))
        project_root = resolved_workspace.parent
        
        index_file = project_root / ".agent" / "knowledge_base" / "index.json"
        kb_dir = resolved_workspace / "knowledge_base"
        kb_dir_resolved = kb_dir.resolve()

        if not index_file.is_file():
            logger.warning("Knowledge index file not found at %s", index_file)
            return []

        try:
            index_data = json.loads(index_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to parse knowledge base index: %s", e)
            return []

        documents = index_data.get("documents", [])
        all_docs = []
        matched_docs = []

        keyword_lower = keyword.lower().strip()

        for doc in documents:
            doc_id = doc.get("id", "")
            title = doc.get("title", "")
            desc = doc.get("description", "")
            tags = doc.get("tags", [])
            doc_path = doc.get("file_path", "")

            # Boundary resolution & protection check
            # Combine paths and resolve completely to absolute forms
            target_file = (project_root / doc_path).resolve()

            try:
                # relative_to will throw ValueError if target_file is not under kb_dir_resolved
                target_file.relative_to(kb_dir_resolved)
            except ValueError:
                raise PermissionError(
                    f"Directory traversal warning: Access denied to outside boundary path '{target_file}'"
                )

            if not target_file.is_file():
                logger.warning("Indexed file '%s' does not exist at resolved path '%s'", doc_id, target_file)
                continue

            try:
                content = target_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.error("Failed to read knowledge document '%s': %s", doc_id, e)
                continue

            # Parse frontmatter and body
            frontmatter = {}
            body = content
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    try:
                        frontmatter = yaml.safe_load(parts[1]) or {}
                    except yaml.YAMLError:
                        pass
                    body = parts[2].strip()

            doc_entry = {
                "id": doc_id,
                "title": title,
                "description": desc,
                "creator": doc.get("creator", ""),
                "version": doc.get("version", ""),
                "tags": tags,
                "frontmatter": frontmatter,
                "content": body
            }
            all_docs.append(doc_entry)

            # Check if keyword matches title, desc, ID, tags, or raw content
            match_found = (
                keyword_lower in doc_id.lower()
                or keyword_lower in title.lower()
                or keyword_lower in desc.lower()
                or any(keyword_lower in t.lower() for t in tags)
                or keyword_lower in content.lower()
            )

            if match_found:
                matched_docs.append(doc_entry)

        if matched_docs:
            return matched_docs

        # Fallback to local semantic search using TF-IDF & Cosine Similarity
        logger.info("Exact keyword match for '%s' returned empty. Executing local TF-IDF semantic fallback.", keyword)
        semantic_results = KnowledgeBase._local_tfidf_search(keyword, all_docs)
        return [doc for score, doc in semantic_results]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Split text by alphanumeric characters, lowercase, and filter stopwords."""
        words = re.findall(r'[a-zA-Z0-9\u4e00-\u9fa5]+', text.lower())
        return [w for w in words if w not in STOPWORDS]

    @staticmethod
    def _local_tfidf_search(query: str, docs: list[dict[str, Any]]) -> list[tuple[float, dict[str, Any]]]:
        """Perform a zero-dependency TF-IDF and Cosine Similarity query against documents."""
        query_tokens = KnowledgeBase._tokenize(query)
        if not query_tokens or not docs:
            return []

        doc_tokens_list = []
        doc_vocab = []

        for doc in docs:
            doc_text = " ".join([
                doc.get("title", ""),
                doc.get("description", ""),
                " ".join(doc.get("tags", [])),
                doc.get("content", "")
            ])
            tokens = KnowledgeBase._tokenize(doc_text)
            doc_tokens_list.append(tokens)
            doc_vocab.append(set(tokens))

        all_tokens = set()
        for tokens in doc_tokens_list:
            all_tokens.update(tokens)
        all_tokens.update(query_tokens)

        num_docs = len(docs)
        idf = {}
        for term in all_tokens:
            docs_with_term = sum(1 for vocab in doc_vocab if term in vocab)
            idf[term] = math.log(1.0 + (num_docs / (1.0 + docs_with_term)))

        # Vectorize documents
        doc_vectors = []
        for tokens in doc_tokens_list:
            tf = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1
            
            vector = {}
            total_terms = len(tokens)
            if total_terms > 0:
                for term, count in tf.items():
                    vector[term] = (count / total_terms) * idf[term]
            doc_vectors.append(vector)

        # Vectorize query
        query_tf = {}
        for token in query_tokens:
            query_tf[token] = query_tf.get(token, 0) + 1

        query_vector = {}
        total_query = len(query_tokens)
        for term, count in query_tf.items():
            query_vector[term] = (count / total_query) * idf[term]

        # Cosine Similarity
        results = []

        def magnitude(vec: dict[str, float]) -> float:
            return math.sqrt(sum(val ** 2 for val in vec.values()))

        q_norm = magnitude(query_vector)
        if q_norm == 0.0:
            return []

        for idx, doc_vec in enumerate(doc_vectors):
            dot_product = sum(query_vector[term] * doc_vec.get(term, 0.0) for term in query_vector)
            d_norm = magnitude(doc_vec)

            if d_norm > 0.0:
                score = dot_product / (q_norm * d_norm)
            else:
                score = 0.0

            if score > 0.0:
                results.append((score, docs[idx]))

        results.sort(key=lambda x: x[0], reverse=True)
        return results

    @staticmethod
    def external_vector_search(query: str, api_key: str | None = None, provider: str = "google-genai") -> list[dict[str, Any]]:
        """Cloud-based vector database slot.

        Integrates with embedding providers (Google Gemini / OpenAI) to generate
        dense vectors and query an external database.
        """
        # API Slot Signature Placeholder
        logger.info("Executing external vector database search for query: '%s' (Provider: %s)", query, provider)
        return []
