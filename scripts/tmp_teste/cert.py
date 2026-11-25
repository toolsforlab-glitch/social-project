import ssl, urllib.request
from cryptography import x509
from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID
host = "psg.pi.senac.br"
c = x509.load_pem_x509_certificate(ssl.get_server_certificate((host, 443), timeout=20).encode())
for n in range(5):
    print(n, "assunto:", c.subject.rfc4514_string(), "| emissor:", c.issuer.rfc4514_string(), "| válido até:", c.not_valid_after_utc)
    try:
        aia = c.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value
        urls = [d.access_location.value for d in aia if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS]
    except Exception as e:
        print("  sem AIA", e); break
    print("  AIA:", urls)
    if not urls: break
    d = urllib.request.urlopen(urls[0], timeout=20).read()
    try: c = x509.load_der_x509_certificate(d)
    except ValueError: c = x509.load_pem_x509_certificate(d)
