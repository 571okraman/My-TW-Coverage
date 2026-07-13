-- Migration: 002_add_followups_sources
-- Description: Add sources column to followups table for provenance tracking
-- Created: 2026-07-13

ALTER TABLE followups ADD COLUMN sources TEXT;
