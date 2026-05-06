import datetime
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import load_pem_x509_certificate, load_pem_x509_csr
from cryptography.x509.oid import NameOID

from app.config import get_settings

_ca: "CertificateAuthority | None" = None


class CertificateAuthority:
    def __init__(self, cert_path: Path, key_path: Path, key_password: bytes | None = None):
        self.cert_path = cert_path
        self.key_path = key_path
        self.key_password = key_password
        self._ca_cert: x509.Certificate | None = None
        self._ca_key = None

    def load_or_create(self, common_name: str, org: str) -> None:
        if self.cert_path.exists() and self.key_path.exists():
            self._load()
        else:
            self._create(common_name, org)

    def _load(self) -> None:
        with open(self.key_path, "rb") as f:
            self._ca_key = serialization.load_pem_private_key(f.read(), password=self.key_password)
        with open(self.cert_path, "rb") as f:
            self._ca_cert = load_pem_x509_certificate(f.read())

    def _create(self, common_name: str, org: str) -> None:
        self.cert_path.parent.mkdir(parents=True, exist_ok=True)

        self._ca_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)

        now = datetime.datetime.now(datetime.timezone.utc)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "PL"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        self._ca_cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(self._ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True, key_cert_sign=True, crl_sign=True,
                    content_commitment=False, key_encipherment=False,
                    data_encipherment=False, key_agreement=False,
                    encipher_only=False, decipher_only=False,
                ),
                critical=True,
            )
            .sign(self._ca_key, hashes.SHA256())
        )

        key_encryption = (
            serialization.BestAvailableEncryption(self.key_password)
            if self.key_password
            else serialization.NoEncryption()
        )
        with open(self.key_path, "wb") as f:
            f.write(self._ca_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                key_encryption,
            ))
        os.chmod(self.key_path, 0o600)

        with open(self.cert_path, "wb") as f:
            f.write(self._ca_cert.public_bytes(serialization.Encoding.PEM))

    def sign_csr(
        self,
        csr_pem: str,
        validity_days: int = 365,
    ) -> tuple[str, int, datetime.datetime, datetime.datetime]:
        csr = load_pem_x509_csr(csr_pem.encode())
        if not csr.is_signature_valid:
            raise ValueError("CSR signature is invalid")

        now = datetime.datetime.now(datetime.timezone.utc)
        expires_at = now + datetime.timedelta(days=validity_days)
        serial = x509.random_serial_number()

        builder = (
            x509.CertificateBuilder()
            .subject_name(csr.subject)
            .issuer_name(self._ca_cert.subject)
            .public_key(csr.public_key())
            .serial_number(serial)
            .not_valid_before(now)
            .not_valid_after(expires_at)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True, key_encipherment=True,
                    content_commitment=False, key_cert_sign=False, crl_sign=False,
                    data_encipherment=False, key_agreement=False,
                    encipher_only=False, decipher_only=False,
                ),
                critical=True,
            )
        )

        cn_attrs = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if cn_attrs:
            builder = builder.add_extension(
                x509.SubjectAlternativeName([x509.DNSName(cn_attrs[0].value)]),
                critical=False,
            )

        cert = builder.sign(self._ca_key, hashes.SHA256())
        return cert.public_bytes(serialization.Encoding.PEM).decode(), serial, now, expires_at

    @property
    def ca_cert_pem(self) -> str:
        return self._ca_cert.public_bytes(serialization.Encoding.PEM).decode()


def initialize_ca() -> None:
    global _ca
    settings = get_settings()
    ca = CertificateAuthority(
        cert_path=settings.ca_cert_path,
        key_path=settings.ca_key_path,
        key_password=settings.ca_key_password.encode() if settings.ca_key_password else None,
    )
    ca.load_or_create(common_name=settings.ca_common_name, org=settings.ca_org)
    _ca = ca


def get_ca() -> CertificateAuthority:
    if _ca is None:
        raise RuntimeError("Certificate Authority not initialized — call initialize_ca() first")
    return _ca
