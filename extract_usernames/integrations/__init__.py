"""HTTP-bound integrations: instagram_validator (GET ig profile), notion_manager
(notion-client wrapper), notion_sync (orchestrator), notion_deduplicator (URL-group merge).
All require network; none are safe to call from import-time module code."""
