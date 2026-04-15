#!/bin/bash

# Create SSL directory
mkdir -p /etc/ssl/certs /etc/ssl/private

# Generate self-signed certificate (for development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/nginx-selfsigned.key \
    -out /etc/ssl/certs/nginx-selfsigned.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Set proper permissions
chmod 600 /etc/ssl/private/nginx-selfsigned.key
chmod 644 /etc/ssl/certs/nginx-selfsigned.crt

echo "SSL certificate generated successfully!"