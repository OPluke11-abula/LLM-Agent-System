"""
core/cert_manager.py - Automated self-signed X.509 certificate and RSA key generator for mTLS tunnels.
"""

import datetime
import hashlib
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

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
