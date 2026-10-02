"""
core/cert_manager.py - Automated self-signed X.509 certificate and RSA key generator for mTLS tunnels.
"""

import datetime
import hashlib
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

class CertValidationResult(tuple):
    """Tuple subclass whose boolean truthiness matches its first item (is_valid)."""

    def __bool__(self) -> bool:
        return bool(self[0]) if len(self) > 0 else False


class SwarmCertManager:
    @staticmethod
    def generate_self_signed_cert(common_name: str, validity_seconds: int = 3600) -> tuple[str, str, datetime.datetime]:
        """
        Generates a new RSA private key (2048-bit) and a self-signed X.509 certificate.
        Returns:
            private_key_pem (str)
            certificate_pem (str)
            expiration_datetime (datetime)
        """
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        # Structure subject and issuer names
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"FindAi Studio"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, u"Swarm Network"),
        ])

        # Expiry details
        now = datetime.datetime.now(datetime.timezone.utc)
        expiry = now + datetime.timedelta(seconds=validity_seconds)

        # Build certificate
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(expiry)
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None), critical=True
            )
            .sign(private_key, hashes.SHA256())
        )

        # Serialize private key to PEM
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ).decode("utf-8")

        # Serialize certificate to PEM
        certificate_pem = cert.public_bytes(
            encoding=serialization.Encoding.PEM
        ).decode("utf-8")

        return private_key_pem, certificate_pem, expiry

    @staticmethod
    def generate_agent_cert(common_name: str, validity_seconds: int = 3600) -> tuple[str, str]:
        """
        Convenience method returning (certificate_pem, private_key_pem).
        """
        priv_pem, cert_pem, _ = SwarmCertManager.generate_self_signed_cert(common_name, validity_seconds)
        return cert_pem, priv_pem

    @staticmethod
    def get_cert_fingerprint(cert_pem: str) -> str:
        """
        Computes the SHA-256 fingerprint (hash) of the PEM certificate.
        """
        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"))
            return cert.fingerprint(hashes.SHA256()).hex()
        except Exception:
            # Fallback to standard string SHA-256 if loading fails for any reason
            return hashlib.sha256(cert_pem.encode("utf-8")).hexdigest()

    @staticmethod
    def sign_payload(private_key_pem: str, payload: str) -> str:
        """
        Signs a string payload using the RSA private key (using PKCS#1 v1.5 padding and SHA-256).
        Returns the signature in hex.
        """
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None
        )
        signature = private_key.sign(
            payload.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return signature.hex()

    @staticmethod
    def verify_signature(cert_pem: str, signature_hex: str, payload: str) -> bool:
        """
        Extracts the public key from the certificate PEM and verifies the signature against the payload.
        """
        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"))
            public_key = cert.public_key()
            public_key.verify(
                bytes.fromhex(signature_hex),
                payload.encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False

    @staticmethod
    def is_cert_valid(cert_pem: str) -> tuple[bool, str]:
        """
        Validates structure and temporal validity of an X.509 certificate PEM.
        Returns (is_valid, message).
        """
        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"))
            now = datetime.datetime.now(datetime.timezone.utc)
            try:
                not_after = cert.not_valid_after_utc
                not_before = cert.not_valid_before_utc
            except AttributeError:
                not_after = cert.not_valid_after.replace(tzinfo=datetime.timezone.utc)
                not_before = cert.not_valid_before.replace(tzinfo=datetime.timezone.utc)

            if now < not_before:
                return CertValidationResult((False, "Certificate is not yet valid"))
            if now > not_after:
                return CertValidationResult((False, f"Certificate expired at {not_after.isoformat()}"))
            return CertValidationResult((True, "Certificate is valid"))
        except Exception as e:
            return CertValidationResult((False, f"Invalid certificate format: {e}"))

    @staticmethod
    def get_cert_expiry(cert_pem: str) -> datetime.datetime | None:
        """Extracts the UTC expiration datetime from an X.509 certificate PEM."""
        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"))
            try:
                return cert.not_valid_after_utc
            except AttributeError:
                return cert.not_valid_after.replace(tzinfo=datetime.timezone.utc)
        except Exception:
            return None

    @staticmethod
    def should_rotate_cert(cert_pem: str, threshold_seconds: int = 300) -> bool:
        """
        Checks if the certificate has expired or is expiring within threshold_seconds.
        """
        expiry = SwarmCertManager.get_cert_expiry(cert_pem)
        if expiry is None:
            return True
        now = datetime.datetime.now(datetime.timezone.utc)
        remaining = (expiry - now).total_seconds()
        return remaining <= threshold_seconds

