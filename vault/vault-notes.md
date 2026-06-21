# Vault Secret Management for HarborNet

## Purpose

HashiCorp Vault is used to securely store and manage sensitive information used by the HarborNet platform.

## Secrets Stored

* Database Password
* API Keys
* Docker Credentials
* Kubernetes Secrets
* Authentication Tokens

## Why Vault?

* Prevents hardcoding passwords in source code
* Provides secure secret storage
* Controls access to sensitive information
* Supports secret rotation and auditing

## HarborNet Secret Flow

Application
↓
Vault
↓
Secure Secret Retrieval

## Example

Instead of storing:

DB_PASSWORD = "admin123"

inside application code, HarborNet stores it securely in Vault and retrieves it when required.

## Benefits

* Improved Security
* Centralized Secret Management
* Reduced Risk of Credential Exposure
* Compliance with Security Standards

## Viva Answer

Vault helps HarborNet securely manage passwords, API keys, and operational credentials without exposing them inside source code or configuration files.

