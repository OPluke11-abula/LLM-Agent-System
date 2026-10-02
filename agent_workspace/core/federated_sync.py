"""
agent_workspace/core/federated_sync.py - Federated Lessons Learned Sync Engine.
"""

from __future__ import annotations

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime


class FederatedSyncEngine:
    """Scans decentralized memory storage or runs logs, aggregating error records to lessons_learned.md."""

    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.project_root = Path(self.workspace_path).parent if os.path.basename(self.workspace_path) == "workspace" else Path(self.workspace_path)
        
        # Defense in depth: locate proper .agent folder location
        if not (self.project_root / ".agent").exists() and (Path(self.workspace_path) / ".agent").exists():
            self.project_root = Path(self.workspace_path)

        self.lessons_file = self.project_root / ".agent" / "knowledge_base" / "lessons_learned.md"
        self.lessons_file.parent.mkdir(parents=True, exist_ok=True)

    def _get_existing_lesson_ids(self) -> set[str]:
        """Parse lessons_learned.md and extract all existing Lesson IDs."""
        if not self.lessons_file.is_file():
            return set()
        
        try:
            content = self.lessons_file.read_text(encoding="utf-8")
            # Pattern matches Lesson ID: L-[ID] or Lesson ID: L-[ID] (Title)
            matches = re.findall(r"Lesson ID:\s*(L-[A-Za-z0-9_-]+)", content)
            return {m.strip() for m in matches}
        except Exception:
            return set()

    def _generate_lesson_id(self, mistake: str) -> str:
        """Generate a Lesson ID based on mistake hash signature."""
        hasher = hashlib.sha256(mistake.encode("utf-8"))
        hash_sig = hasher.hexdigest()[:8].upper()
        # Standard format: L-YYYYMMDD-[hash]
        date_str = datetime.now().strftime("%Y%m%d")
        return f"L-{date_str}-{hash_sig}"

    def sync(self) -> dict:
        """Scan decentralized memory storage and aggregate episodic error records, merging into lessons_learned.md."""
        existing_ids = self._get_existing_lesson_ids()
        new_lessons = []
        
        # Scan directories
        scan_dirs = [
            self.project_root / "workspace",
            self.project_root / "agent_workspace" / "memory",
            self.project_root / ".agent" / "workflows" / "runs",
            self.project_root / "memory"
        ]
        
        for s_dir in scan_dirs:
            if not s_dir.is_dir():
                continue
            
            for file_path in s_dir.glob("*.json"):
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    
                    # 1. Standard Topology JSON format
                    if isinstance(data, dict):
                        # check nodes list
                        nodes = data.get("nodes", [])
                        if isinstance(nodes, list):
                            for node in nodes:
                                if not isinstance(node, dict):
                                    continue
                                status = str(node.get("status", "")).lower()
                                title = node.get("title", "")
                                desc = node.get("description", "")
                                result = str(node.get("result_summary", ""))
                                
                                if status in {"error", "failed"} or "error" in result.lower() or "failed" in result.lower():
                                    mistake = result or f"Task '{title}' failed with status '{status}'"
                                    self._add_discovered_lesson(mistake, f"Task details: {title} - {desc}", new_lessons, existing_ids)
                        
                        # 2. Workflow runs JSON format
                        steps = data.get("steps", {})
                        if isinstance(steps, dict):
                            for step_id, step in steps.items():
                                if not isinstance(step, dict):
                                    continue
                                status = str(step.get("status", "")).lower()
                                if status in {"error", "failed"}:
                                    mistake = str(step.get("error", "")) or f"Workflow step '{step_id}' failed"
                                    self._add_discovered_lesson(mistake, f"Workflow step '{step_id}' failed with error", new_lessons, existing_ids)
                                    
                except Exception:
                    # Ignore unparseable or irrelevant JSONs
                    continue
        
        if new_lessons:
            self._write_lessons_to_md(new_lessons)
            
        return {
            "scanned_directories": [str(d) for d in scan_dirs if d.is_dir()],
            "new_lessons_added": len(new_lessons),
            "total_existing_lessons": len(existing_ids) + len(new_lessons)
        }

    def _add_discovered_lesson(self, mistake: str, context: str, new_lessons: list, existing_ids: set):
        mistake = mistake.strip()
        if not mistake:
            return
        
        lesson_id = self._generate_lesson_id(mistake)
        # Avoid duplicate signature conflict
        if lesson_id in existing_ids or any(l["id"] == lesson_id for l in new_lessons):
            return
            
        lesson_entry = {
            "id": lesson_id,
            "mistake": mistake,
            "root_cause": f"System encountered dynamic operational failure during task execution. Context: {context}",
            "resolution": "Implement explicit validations, proper error trapping and recovery loops.",
            "policy": f"Prevent failures related to: {mistake[:60]}"
        }
        new_lessons.append(lesson_entry)

    def _write_lessons_to_md(self, new_lessons: list):
        if not self.lessons_file.is_file():
            # Create standard header
            content = "# 🎓 FindAi Studio LAS Self-Learning Experience & Lessons Learned Registry\n\n"
            content += "This database catalogs engineering resolutions, compile-time errors, and dynamic swarms refactoring choices.\n\n"
            content += "---\n\n## ⚡ 1. Active Resolution Directory (Lessons Database)\n"
        else:
            content = self.lessons_file.read_text(encoding="utf-8")
            
        # Append each new lesson at the bottom under standard format
        for lesson in new_lessons:
            entry = f"\n---\n\n### Lesson ID: {lesson['id']}\n"
            entry += f"- **Mistake Encountered**: {lesson['mistake']}\n"
            entry += f"- **Root Cause**: {lesson['root_cause']}\n"
            entry += f"- **Resolution Code**:\n```python\n# Resolution implemented at runtime\n```\n"
            entry += f"- **Best Practice Policy**: {lesson['policy']}\n"
            content += entry
            
        self.lessons_file.write_text(content, encoding="utf-8")


class FederatedKnowledgeExchange:
    """Secure multi-tenant knowledge exchange implementing asymmetric signing and hybrid encryption."""

    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.project_root = Path(self.workspace_path).parent if os.path.basename(self.workspace_path) == "workspace" else Path(self.workspace_path)
        
        # Defense in depth: locate proper .agent folder location
        if not (self.project_root / ".agent").exists() and (Path(self.workspace_path) / ".agent").exists():
            self.project_root = Path(self.workspace_path)

        self.keys_dir = self.project_root / ".agent" / "keys"
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self.lessons_file = self.project_root / ".agent" / "knowledge_base" / "lessons_learned.md"

    def generate_key_pair(self) -> tuple[str, str]:
        """Generate a new RSA 2048 private/public keypair in PEM format."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode("utf-8")

        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

        return private_pem, public_pem

    def save_local_keys(self, private_pem: str, public_pem: str) -> None:
        """Save local PEM private/public keys to keys directory."""
        (self.keys_dir / "private_key.pem").write_text(private_pem, encoding="utf-8")
        (self.keys_dir / "public_key.pem").write_text(public_pem, encoding="utf-8")

    def load_local_keys(self) -> tuple[str | None, str | None]:
        """Load private and public keys if they exist."""
        priv_path = self.keys_dir / "private_key.pem"
        pub_path = self.keys_dir / "public_key.pem"
        if priv_path.is_file() and pub_path.is_file():
            return priv_path.read_text(encoding="utf-8"), pub_path.read_text(encoding="utf-8")
        return None, None

    def sign_payload(self, payload: dict, private_key_pem: str) -> str:
        """Sign a dictionary payload using RSA-PSS signature scheme."""
        import base64
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import serialization, hashes

        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None
        )
        # Canonical JSON serialization
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = private_key.sign(
            payload_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode("utf-8")

    def verify_signature(self, payload: dict, signature_str: str, public_key_pem: str) -> bool:
        """Verify the signature against a payload using sender's RSA public key."""
        import base64
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import serialization, hashes

        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            signature = base64.b64decode(signature_str.encode("utf-8"))
            payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
            public_key.verify(
                signature,
                payload_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False

    def encrypt_payload(self, payload: dict, receiver_public_key_pem: str) -> dict:
        """Encrypt a payload dictionary using hybrid Fernet/RSA-OAEP encryption."""
        import base64
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import serialization, hashes

        # Generate standard symmetric key
        fernet_key = Fernet.generate_key()
        fernet = Fernet(fernet_key)
        payload_bytes = json.dumps(payload).encode("utf-8")
        ciphertext = fernet.encrypt(payload_bytes).decode("utf-8")

        # Encrypt the Fernet key with receiver's public key
        receiver_public_key = serialization.load_pem_public_key(
            receiver_public_key_pem.encode("utf-8")
        )
        encrypted_key = receiver_public_key.encrypt(
            fernet_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        encrypted_key_b64 = base64.b64encode(encrypted_key).decode("utf-8")

        return {
            "encrypted_key": encrypted_key_b64,
            "ciphertext": ciphertext
        }

    def decrypt_payload(self, encrypted_payload: dict, receiver_private_key_pem: str) -> dict:
        """Decrypt a hybrid-encrypted payload dictionary using receiver's private key."""
        import base64
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import serialization, hashes

        receiver_private_key = serialization.load_pem_private_key(
            receiver_private_key_pem.encode("utf-8"),
            password=None
        )

        encrypted_key = base64.b64decode(encrypted_payload["encrypted_key"].encode("utf-8"))
        ciphertext = encrypted_payload["ciphertext"].encode("utf-8")

        # Decrypt symmetric Fernet key
        fernet_key = receiver_private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        fernet = Fernet(fernet_key)
        decrypted_bytes = fernet.decrypt(ciphertext)
        return json.loads(decrypted_bytes.decode("utf-8"))

    def sign_and_encrypt_lesson(self, lesson: dict, receiver_public_key_pem: str, sender_private_key_pem: str, sender_id: str) -> dict:
        """Sign a lesson learned payload and encrypt it securely for a receiver."""
        signature = self.sign_payload(lesson, sender_private_key_pem)
        inner = {
            "lesson": lesson,
            "sender_id": sender_id,
            "signature": signature
        }
        outer = self.encrypt_payload(inner, receiver_public_key_pem)
        outer["sender_id"] = sender_id
        return outer

    def decrypt_and_verify_lesson(self, encrypted_payload: dict, receiver_private_key_pem: str, trusted_tenants_keys: dict[str, str]) -> dict | None:
        """Decrypt payload, fetch trusted public key, verify signature, and return validated lesson."""
        sender_id = encrypted_payload.get("sender_id")
        if not sender_id or sender_id not in trusted_tenants_keys:
            raise ValueError("Untrusted or missing sender_id")

        decrypted = self.decrypt_payload(encrypted_payload, receiver_private_key_pem)
        lesson = decrypted.get("lesson")
        signature = decrypted.get("signature")

        if not lesson or not signature:
            raise ValueError("Malformed decrypted payload")

        sender_public_key = trusted_tenants_keys[sender_id]
        if self.verify_signature(lesson, signature, sender_public_key):
            return lesson
        raise ValueError("Invalid cryptographic signature")

    def merge_lesson(self, lesson: dict) -> bool:
        """Safely merge a verified lesson into lessons_learned.md with duplicate prevention."""
        lesson_id = lesson.get("lesson_id") or lesson.get("id")
        if not lesson_id:
            return False

        if not self.lessons_file.is_file():
            content = (
                "# 🎓 FindAi Studio LAS Self-Learning Experience & Lessons Learned Registry\n\n"
                "This database catalogs engineering resolutions, compile-time errors, and dynamic swarms refactoring choices.\n\n"
                "---\n\n## ⚡ 1. Active Resolution Directory (Lessons Database)\n"
            )
            self.lessons_file.parent.mkdir(parents=True, exist_ok=True)
            self.lessons_file.write_text(content, encoding="utf-8")
        else:
            content = self.lessons_file.read_text(encoding="utf-8")

        if lesson_id in content:
            return False

        block = (
            f"\n---\n\n"
            f"### Lesson ID: {lesson_id}\n"
            f"- **Mistake Encountered**: {lesson.get('mistake', 'Unknown mistake.')}\n"
            f"- **Root Cause**: {lesson.get('root_cause', 'Unknown cause.')}\n"
            f"- **Resolution Code**:\n"
            f"```python\n"
            f"{lesson.get('resolution_code', lesson.get('resolution', '# None provided'))}\n"
            f"```\n"
            f"- **Best Practice Policy**: {lesson.get('best_practice', lesson.get('policy', 'None.'))}\n"
        )
        self.lessons_file.write_text(content.rstrip() + "\n" + block, encoding="utf-8")
        return True

