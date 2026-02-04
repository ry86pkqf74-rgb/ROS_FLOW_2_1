# Manuscript Comments Prototype

## Purpose

Prototype collaborative commenting for manuscript editor:
- Inline comments on text selections
- Threaded discussions
- Comment resolution workflow
- Notification indicators
- @mentions

## Status

🔲 **Not Started**

## Key Interactions to Prototype

### 1. Adding Comments
- Select text → Comment popover appears
- Write comment with rich text
- Optional @mention collaborators
- Submit and see inline indicator

### 2. Viewing Comments
- Comment markers in text margin
- Click to expand thread
- See reply count and resolved status
- Filter by section, author, resolved

### 3. Comment Threads
- Reply to comments
- Quote previous replies
- Edit own comments
- Delete (with audit trail)

### 4. Resolution Workflow
- Mark as resolved (author or commenter)
- Re-open if needed
- Track resolution in audit log

## Mock Data States

Test with query params:
- `?comments=many` - Document with many comments
- `?comments=none` - No comments
- `?comments=unresolved` - Only unresolved comments
- `?_status=in_review` - Document in review state

## Integration Points

- Manuscript API for comment CRUD
- Real-time updates (consider WebSocket for later)
- Notification system

## Graduation Criteria

- [ ] Add comment flow works
- [ ] Thread replies working
- [ ] Resolution toggle working
- [ ] @mentions functioning
- [ ] Accessible via keyboard
- [ ] Components extracted to packages/ui

## Notes

<!-- Add findings and learnings here -->
