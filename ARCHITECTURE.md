# System Architecture

                    Merchant Portal
                           │
                           │
                           ▼

                    Express REST API

         ┌──────────────┼───────────────┐

         ▼              ▼               ▼

     QR Service    Coupon Service   Wallet Service

         │              │               │

         └──────────────┼───────────────┘

                        ▼

                    SQLite Database

             merchants

             offers

             codes

             api_logs

                        │

                        ▼

                Google Wallet API

                        │

                        ▼

                 Retail POS System

                        │

                        ▼

                  Redeem API
# Responsibilities
QR Service

Creates QR codes.

Does not issue coupons.

Coupon Service

Loads offers.

Creates coupon records.

Validates availability.

Tracks redemption.

Wallet Service

Creates wallet objects.

Signs Google Wallet JWTs.

Database

Single source of truth.

Retail POS

Scans barcode.

Calls Redeem API.