# cryptography
from cryptography.hazmat.primitives.asymmetric import ec
#from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes

from datetime import datetime, timezone, timedelta
import os, ipaddress

class CreateCACert():
    def __init__(
        self, 
        certFile                = "certificate.pem", 
        privateFile             = "private.key", 
        caCertFile              = "ca_cert.pem", 
        caprivateKeyFile        = "ca_private.key",
        caKey                   = ec.generate_private_key(ec.SECP256R1()),
        key                     = ec.generate_private_key(ec.SECP256R1()),
        overwrite               = False, 
        expire                  = 10,                        # 有効期限(年単位)
        host                    = "127.0.0.1",
        caHost                  = "BX293A_PEN",
        **kwargs
    ):
        self.certFile           = certFile
        self.privateFile        = privateFile
        self.caCertFile         = caCertFile
        self.caprivateKeyFile   = caprivateKeyFile
        self.key                = key
        self.caKey              = caKey
        self.overwrite          = overwrite
        self.expire             = expire
        self.host               = host
        self.caHost             = caHost
        self.kwargs             = kwargs

        if(os.path.isfile(self.caCertFile)):
            try:
                with open(self.caCertFile, "rb") as f:
                    self.caCertKey = f.read()
            except:
                print("CA Certificate is None")
        else:
            self.create_ca_file()
        
        if(
            (self.privateFile is not None) and 
            (os.path.isfile(self.privateFile))
        ):
            try:
                with open(self.privateFile, "rb") as f: 
                    self.privateKey = f.read()
            except:
                print("Private Key is None")
        
        if(
            (not overwrite) and 
            (os.path.isfile(self.certFile))
        ):
            try:
                with open(self.certFile, "rb") as f: 
                    self.certificate = f.read()
            except:
                print("Certificate File Error")
        
        else:
            self.create_server_file()

    def create_server_file(self):
        subject = x509.Name(
            [
                x509.NameAttribute(
                    NameOID.COUNTRY_NAME, 
                    self.kwargs.get("country","JP")
                ),
                x509.NameAttribute(
                    NameOID.STATE_OR_PROVINCE_NAME, 
                    self.kwargs.get("prefecture","Aichi")
                ),
                x509.NameAttribute(
                    NameOID.LOCALITY_NAME, 
                    self.kwargs.get("city", "Nagoya")
                ),
                x509.NameAttribute(
                    NameOID.ORGANIZATION_NAME, 
                    self.kwargs.get("org", "University")
                ),
                x509.NameAttribute(
                    NameOID.COMMON_NAME, 
                    self.host
                ),
            ]
        )
        self.cert = x509.CertificateBuilder(
            subject_name        = subject,
            issuer_name         = x509.load_pem_x509_certificate(self.caCertKey).subject,
            serial_number       = x509.random_serial_number(),
            not_valid_before    = datetime.now(timezone.utc),
            not_valid_after     = datetime.now(timezone.utc) + timedelta(days=int(365 * self.expire)),
            public_key          = self.key.public_key(),
        )
        self.ip = x509.IPAddress(ipaddress.IPv4Address(self.host))
        self.cert = self.cert.add_extension(
            x509.SubjectAlternativeName(
                [self.ip]
            ),
            critical=False,
        )
        self.cert           = self.cert.sign(self.caKey, hashes.SHA256())

        self.certificate    = self.cert.public_bytes(serialization.Encoding.PEM)    # 証明書
        self.privateKey     = self.key.private_bytes(                               # 秘密鍵
            encoding        = serialization.Encoding.PEM,
            format          = serialization.PrivateFormat.PKCS8,
            encryption_algorithm = serialization.NoEncryption()
        )
        self.publicKey      = self.key.public_key().public_bytes(                   # 公開鍵
            encoding        = serialization.Encoding.PEM,
            format          = serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with open(self.certFile, "wb") as f: 
            f.write(self.certificate)

        with open(self.privateFile, "wb") as f: 
            f.write(self.privateKey)


    def create_ca_file(self):
        subject = x509.Name(
            [
                x509.NameAttribute(
                    NameOID.COUNTRY_NAME, 
                    self.kwargs.get("country","JP")
                ),
                x509.NameAttribute(
                    NameOID.STATE_OR_PROVINCE_NAME, 
                    self.kwargs.get("prefecture","Aichi")
                ),
                x509.NameAttribute(
                    NameOID.LOCALITY_NAME, 
                    self.kwargs.get("city", "Nagoya")
                ),
                x509.NameAttribute(
                    NameOID.ORGANIZATION_NAME, 
                    self.kwargs.get("org", "University")
                ),
                x509.NameAttribute(
                    NameOID.COMMON_NAME, 
                    self.caHost
                ),
            ]
        )
        self.cacert = x509.CertificateBuilder(
            subject_name        = subject,
            issuer_name         = subject,
            serial_number       = x509.random_serial_number(),
            not_valid_before    = datetime.now(timezone.utc),
            not_valid_after     = datetime.now(timezone.utc) + timedelta(days=int(365 * self.expire)),
            public_key          = self.caKey.public_key(),
        )
        self.cacert             = self.cacert.add_extension(
            x509.BasicConstraints(
                ca              = True, 
                path_length     = None
            ), 
            critical            = True
        )
        self.cacert = self.cacert.add_extension(
            x509.KeyUsage(
                digital_signature   = True,
                content_commitment  = False,
                key_encipherment    = False,
                data_encipherment   = False,
                key_agreement       = False,
                key_cert_sign       = True,  # 証明書に署名する権限
                crl_sign            = True,       # CRLに署名する権限
                encipher_only       = False,
                decipher_only       = False,
            ), 
            critical                = True
        )

        self.cacert                 = self.cacert.sign(self.caKey, hashes.SHA256())

        self.caCertKey              = self.cacert.public_bytes(serialization.Encoding.PEM)

        self.caCertPrivateKey = self.caKey.private_bytes(
            encoding                = serialization.Encoding.PEM,
            format                  = serialization.PrivateFormat.PKCS8,
            encryption_algorithm    = serialization.NoEncryption()
        )

        with open(self.caCertFile, "wb") as f:
            f.write(self.caCertKey)

        with open(self.caprivateKeyFile, "wb") as f:
            f.write(self.caCertPrivateKey)

    def get_certificate(self):
        return self.certificate
    
    def get_private_key(self):
        return self.privateKey
    
    def get_ca_cert_key(self):
        return self.caCertKey

if __name__ == "__main__":
    CreateCACert(
        certFile                = "certificate.crt", 
        privateFile             = "private.key", 
        caCertFile              = "ca_cert.crt", 
        caprivateKeyFile        = "ca_private.key",
        caKey                   = ec.generate_private_key(ec.SECP256R1()),
        key                     = ec.generate_private_key(ec.SECP256R1()),
    )