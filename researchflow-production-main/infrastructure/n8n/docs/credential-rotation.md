# n8n Credential Rotation Guide

## Overview
Credential rotation is critical for security. This guide covers:
- GitHub Personal Access Tokens (90-day rotation)
- Notion API Keys (180-day rotation)
- Slack Webhooks

## GitHub Token Rotation
1. Generate new token at GitHub Settings > Developer settings
2. Update in n8n Credentials
3. Run health check workflow
4. Revoke old token

## Quick Reference
| Credential | Rotation Period | Last Rotated |
|------------|-----------------|--------------|
| GitHub PAT | 90 days | Check n8n |
| Notion API | 180 days | Check n8n |

Created: 2026-01-29 for ROS-71
