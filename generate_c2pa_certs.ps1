# PowerShell script to generate C2PA-compatible certificates
# Requires OpenSSL to be installed and in PATH

Write-Host "Generating C2PA-compatible certificates..." -ForegroundColor Green

# Create certificates directory if it doesn't exist
New-Item -ItemType Directory -Force -Path "certificates_new" | Out-Null
Set-Location "certificates_new"

# 1. Generate Root CA private key (ES256 - P-256 curve)
Write-Host "Step 1: Generating Root CA private key..." -ForegroundColor Cyan
openssl ecparam -name prime256v1 -genkey -noout -out ca-key.pem

# 2. Generate Root CA certificate (self-signed)
Write-Host "Step 2: Generating Root CA certificate..." -ForegroundColor Cyan
openssl req -new -x509 -sha256 -key ca-key.pem -out ca-cert.pem -days 365 -subj "/C=ET/ST=Addis Ababa/L=Addis Ababa/O=Test Organization/OU=Certificate Authority/CN=C2PA Test CA" -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,digitalSignature,keyCertSign,cRLSign"

# 3. Generate signing certificate private key (ES256 - P-256 curve)
Write-Host "Step 3: Generating signing certificate private key..." -ForegroundColor Cyan
openssl ecparam -name prime256v1 -genkey -noout -out sign-key-temp.pem

# Convert to PKCS#8 format (more compatible)
openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in sign-key-temp.pem -out sign-key.pem
Remove-Item sign-key-temp.pem

# 4. Generate Certificate Signing Request (CSR)
Write-Host "Step 4: Generating Certificate Signing Request..." -ForegroundColor Cyan
openssl req -new -key sign-key.pem -out sign.csr -sha256 -subj "/C=ET/ST=Addis Ababa/L=Addis Ababa/O=Test Organization/OU=Video Signing/CN=C2PA Video Signer"

# 5. Create extension file for signing certificate
Write-Host "Step 5: Creating certificate extension file..." -ForegroundColor Cyan
"basicConstraints = CA:FALSE" | Out-File -FilePath "sign-ext.cnf" -Encoding ASCII
"keyUsage = digitalSignature" | Out-File -FilePath "sign-ext.cnf" -Encoding ASCII -Append
"extendedKeyUsage = emailProtection" | Out-File -FilePath "sign-ext.cnf" -Encoding ASCII -Append
"subjectKeyIdentifier = hash" | Out-File -FilePath "sign-ext.cnf" -Encoding ASCII -Append
"authorityKeyIdentifier = keyid:always,issuer" | Out-File -FilePath "sign-ext.cnf" -Encoding ASCII -Append

# 6. Sign the certificate with the CA
Write-Host "Step 6: Signing certificate with CA..." -ForegroundColor Cyan
openssl x509 -req -in sign.csr -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial -out sign-cert-only.pem -days 365 -sha256 -extfile sign-ext.cnf

# 7. Create certificate chain (signing cert + CA cert)
Write-Host "Step 7: Creating certificate chain..." -ForegroundColor Cyan
Get-Content sign-cert-only.pem, ca-cert.pem | Set-Content sign-cert.pem

# 8. Create signer.json configuration
Write-Host "Step 8: Creating signer configuration..." -ForegroundColor Cyan
"{" | Out-File -FilePath "signer.json" -Encoding UTF8
'    "cert": "sign-cert.pem",' | Out-File -FilePath "signer.json" -Encoding UTF8 -Append
'    "key": "sign-key.pem"' | Out-File -FilePath "signer.json" -Encoding UTF8 -Append
"}" | Out-File -FilePath "signer.json" -Encoding UTF8 -Append

# Clean up temporary files
Remove-Item sign.csr, sign-ext.cnf, ca-cert.pem.srl, sign-cert-only.pem -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Certificate generation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Generated files:" -ForegroundColor Yellow
Write-Host "  - ca-key.pem           (Root CA private key - KEEP SECURE!)"
Write-Host "  - ca-cert.pem          (Root CA certificate)"
Write-Host "  - sign-key.pem         (Signing private key in PKCS#8 format)"
Write-Host "  - sign-cert.pem        (Certificate chain: signing cert + CA)"
Write-Host "  - signer.json          (c2patool configuration)"
Write-Host ""
Write-Host "To use these certificates:" -ForegroundColor Yellow
Write-Host "  1. Run: Copy-Item certificates_new\*.pem, certificates_new\signer.json certificates\ -Force"
Write-Host "  2. Make sure .env has:"
Write-Host "     CERT_PATH=./certificates/sign-cert.pem"
Write-Host "     PRIVATE_KEY_PATH=./certificates/sign-key.pem"
Write-Host ""
Write-Host "To verify the certificate chain:" -ForegroundColor Yellow
Write-Host "  openssl verify -CAfile certificates_new/ca-cert.pem certificates_new/sign-cert.pem"
Write-Host ""
Write-Host "Note: These are test certificates. For production, use certificates from a trusted CA." -ForegroundColor Red

Set-Location ..