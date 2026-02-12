-- Migration: Add app_settings table
-- Run this if your database was created before the settings feature was added.
-- Usage: psql -U plg_user -d plg_lead_sourcer -f database/migrations/001_add_app_settings.sql

CREATE TABLE IF NOT EXISTS app_settings (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    description TEXT,
    is_secret BOOLEAN DEFAULT false,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
