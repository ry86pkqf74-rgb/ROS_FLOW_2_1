/**
 * Notification Service for Collaboration Events
 * Integrations: Slack, Email, Linear, In-App
 */

import { Pool } from 'pg';

export interface CollabEvent {
  type: 'join' | 'leave' | 'edit' | 'comment' | 'mention' | 'handoff';
  userId: string;
  manuscriptId: string;
  sectionId?: string;
  details: Record<string, any>;
}

export interface InAppNotificationInput {
  type: string;
  title: string;
  body?: string;
  link?: string;
  metadata?: Record<string, any>;
}

interface NotificationRow {
  id: string;
  user_id: string;
  type: string;
  title: string;
  body: string | null;
  link: string | null;
  metadata: any;
  read_at: string | null;
  created_at: string;
}

interface PreferencesRow {
  user_id: string;
  email_digest: boolean;
  slack_mentions: boolean;
  in_app: boolean;
  digest_frequency: string;
}

type Logger = {
  info: (...args: any[]) => void;
  warn: (...args: any[]) => void;
  error: (...args: any[]) => void;
};

/**
 * NOTE:
 * This service is intentionally "pluggable". Slack/Email/Linear integrations are
 * implemented as safe stubs (logging-only) unless corresponding environment
 * variables are provided.
 *
 * The In-App integration persists notifications into Postgres.
 */
export class NotificationService {
  private pool: Pool;
  private logger: Logger;

  constructor(opts: { pool: Pool; logger?: Logger }) {
    this.pool = opts.pool;
    this.logger = opts.logger ?? console;
  }

  /**
   * Post a collaboration event to Slack.
   *
   * If SLACK_WEBHOOK_URL is not set, this method will no-op (log only).
   */
  async notifySlack(channel: string, event: CollabEvent): Promise<void> {
    const webhookUrl = process.env.SLACK_WEBHOOK_URL;
    const enabled = Boolean(webhookUrl);

    const text = this.formatSlackMessage(channel, event);

    if (!enabled) {
      this.logger.info('[NotificationService] Slack disabled; would send:', {
        channel,
        text,
        event,
      });
      return;
    }

    try {
      // Webhook payload supports "channel" only for legacy incoming webhooks.
      // For modern apps, channel is fixed. We still include it for compatibility.
      await fetch(webhookUrl!, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text, channel }),
      });
    } catch (err) {
      this.logger.warn('[NotificationService] Slack notify failed', err);
    }
  }

  /**
   * Send a periodic email digest for collaboration events.
   *
   * Implementation is a stub by design (no email provider configured in this repo).
   * If EMAIL_DIGEST_ENABLED is true, this method logs a formatted digest.
   */
  async sendEmailDigest(userId: string, events: CollabEvent[]): Promise<void> {
    const enabled = (process.env.EMAIL_DIGEST_ENABLED ?? '').toLowerCase() === 'true';

    if (!enabled) {
      this.logger.info('[NotificationService] Email digest disabled; skipping', {
        userId,
        events: events.length,
      });
      return;
    }

    const subject = `Your collaboration digest (${events.length} updates)`;
    const body = this.formatEmailDigest(events);

    // TODO: integrate real mail provider (SES/Sendgrid/etc)
    this.logger.info('[NotificationService] Email digest (stub)', { userId, subject, body });
  }

  /**
   * Create a Linear task for certain collaboration events.
   *
   * If LINEAR_API_KEY is not set, returns a synthetic id and logs intent.
   */
  async createLinearTask(event: CollabEvent): Promise<string> {
    const apiKey = process.env.LINEAR_API_KEY;
    if (!apiKey) {
      const syntheticId = `linear_stub_${Date.now()}`;
      this.logger.info('[NotificationService] Linear disabled; would create task', {
        syntheticId,
        event,
      });
      return syntheticId;
    }

    try {
      const title = this.formatLinearTitle(event);
      const description = this.formatLinearDescription(event);

      const res = await fetch('https://api.linear.app/graphql', {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          authorization: apiKey,
        },
        body: JSON.stringify({
          query:
            'mutation IssueCreate($input: IssueCreateInput!) { issueCreate(input: $input) { success issue { id identifier url } } }',
          variables: {
            input: {
              title,
              description,
            },
          },
        }),
      });

      const json: any = await res.json();
      const issue = json?.data?.issueCreate?.issue;
      const id = issue?.id ?? `linear_unknown_${Date.now()}`;

      if (!json?.data?.issueCreate?.success) {
        this.logger.warn('[NotificationService] Linear create task not successful', json);
      }

      return id;
    } catch (err) {
      this.logger.warn('[NotificationService] Linear create task failed', err);
      return `linear_error_${Date.now()}`;
    }
  }

  /**
   * Persist an in-app notification for a user.
   */
  async queueInAppNotification(userId: string, notification: InAppNotificationInput): Promise<void> {
    const metadata = notification.metadata ?? {};

    await this.pool.query(
      `INSERT INTO notifications (user_id, type, title, body, link, metadata)
       VALUES ($1, $2, $3, $4, $5, $6::jsonb)`,
      [
        userId,
        notification.type,
        notification.title,
        notification.body ?? null,
        notification.link ?? null,
        JSON.stringify(metadata),
      ],
    );
  }

  async getUnreadCount(userId: string): Promise<number> {
    const res = await this.pool.query(
      `SELECT COUNT(*)::int AS count
       FROM notifications
       WHERE user_id = $1 AND read_at IS NULL`,
      [userId],
    );
    return res.rows?.[0]?.count ?? 0;
  }

  async listNotifications(userId: string, opts: { limit: number; offset: number }) {
    const limit = Math.max(1, Math.min(100, opts.limit));
    const offset = Math.max(0, opts.offset);

    const res = await this.pool.query<NotificationRow>(
      `SELECT id, user_id, type, title, body, link, metadata, read_at, created_at
       FROM notifications
       WHERE user_id = $1
       ORDER BY created_at DESC
       LIMIT $2 OFFSET $3`,
      [userId, limit, offset],
    );

    return res.rows;
  }

  async markRead(userId: string, notificationId: string): Promise<boolean> {
    const res = await this.pool.query(
      `UPDATE notifications
       SET read_at = NOW()
       WHERE id = $1 AND user_id = $2 AND read_at IS NULL`,
      [notificationId, userId],
    );

    return (res.rowCount ?? 0) > 0;
  }

  async markAllRead(userId: string): Promise<number> {
    const res = await this.pool.query(
      `UPDATE notifications
       SET read_at = NOW()
       WHERE user_id = $1 AND read_at IS NULL`,
      [userId],
    );

    return res.rowCount ?? 0;
  }

  async getPreferences(userId: string): Promise<PreferencesRow> {
    const res = await this.pool.query<PreferencesRow>(
      `SELECT user_id, email_digest, slack_mentions, in_app, digest_frequency
       FROM notification_preferences
       WHERE user_id = $1`,
      [userId],
    );

    if (res.rows.length > 0) return res.rows[0];

    // Default preferences (and create row for future updates)
    const created = await this.pool.query<PreferencesRow>(
      `INSERT INTO notification_preferences (user_id)
       VALUES ($1)
       ON CONFLICT (user_id) DO UPDATE SET user_id = EXCLUDED.user_id
       RETURNING user_id, email_digest, slack_mentions, in_app, digest_frequency`,
      [userId],
    );

    return created.rows[0];
  }

  async updatePreferences(
    userId: string,
    patch: Partial<Pick<PreferencesRow, 'email_digest' | 'slack_mentions' | 'in_app' | 'digest_frequency'>>,
  ): Promise<PreferencesRow> {
    const current = await this.getPreferences(userId);

    const next: PreferencesRow = {
      user_id: userId,
      email_digest: patch.email_digest ?? current.email_digest,
      slack_mentions: patch.slack_mentions ?? current.slack_mentions,
      in_app: patch.in_app ?? current.in_app,
      digest_frequency: patch.digest_frequency ?? current.digest_frequency,
    };

    const res = await this.pool.query<PreferencesRow>(
      `INSERT INTO notification_preferences (user_id, email_digest, slack_mentions, in_app, digest_frequency)
       VALUES ($1, $2, $3, $4, $5)
       ON CONFLICT (user_id) DO UPDATE
       SET email_digest = EXCLUDED.email_digest,
           slack_mentions = EXCLUDED.slack_mentions,
           in_app = EXCLUDED.in_app,
           digest_frequency = EXCLUDED.digest_frequency
       RETURNING user_id, email_digest, slack_mentions, in_app, digest_frequency`,
      [userId, next.email_digest, next.slack_mentions, next.in_app, next.digest_frequency],
    );

    return res.rows[0];
  }

  /**
   * Convenience helper: translate collaboration events into in-app notifications.
   */
  async queueFromEvent(event: CollabEvent): Promise<void> {
    const title = this.formatInAppTitle(event);
    const body = this.formatInAppBody(event);

    await this.queueInAppNotification(event.userId, {
      type: `collab:${event.type}`,
      title,
      body,
      link: event.manuscriptId ? `/manuscripts/${event.manuscriptId}` : undefined,
      metadata: {
        manuscriptId: event.manuscriptId,
        sectionId: event.sectionId,
        details: event.details,
      },
    });
  }

  private formatSlackMessage(channel: string, event: CollabEvent): string {
    const base = `[#${channel}] Collaboration event: ${event.type}`;
    const parts = [
      base,
      `user: ${event.userId}`,
      `manuscript: ${event.manuscriptId}`,
      event.sectionId ? `section: ${event.sectionId}` : null,
    ].filter(Boolean);

    return parts.join(' | ');
  }

  private formatEmailDigest(events: CollabEvent[]): string {
    const lines: string[] = [];
    lines.push('Collaboration updates:');
    lines.push('');

    for (const e of events) {
      lines.push(
        `- ${e.type} | user=${e.userId} | manuscript=${e.manuscriptId}${e.sectionId ? ` | section=${e.sectionId}` : ''}`,
      );
    }

    lines.push('');
    lines.push('— ResearchFlow');

    return lines.join('\n');
  }

  private formatLinearTitle(event: CollabEvent): string {
    switch (event.type) {
      case 'handoff':
        return `Handoff requested for manuscript ${event.manuscriptId}`;
      case 'mention':
        return `Mention in manuscript ${event.manuscriptId}`;
      default:
        return `Collaboration event (${event.type}) for manuscript ${event.manuscriptId}`;
    }
  }

  private formatLinearDescription(event: CollabEvent): string {
    return [
      `Type: ${event.type}`,
      `User: ${event.userId}`,
      `Manuscript: ${event.manuscriptId}`,
      event.sectionId ? `Section: ${event.sectionId}` : null,
      '',
      `Details: ${JSON.stringify(event.details, null, 2)}`,
    ]
      .filter(Boolean)
      .join('\n');
  }

  private formatInAppTitle(event: CollabEvent): string {
    switch (event.type) {
      case 'join':
        return 'Someone joined your manuscript';
      case 'leave':
        return 'Someone left your manuscript';
      case 'edit':
        return 'Edits were made';
      case 'comment':
        return 'New comment';
      case 'mention':
        return 'You were mentioned';
      case 'handoff':
        return 'Handoff requested';
      default:
        return 'New update';
    }
  }

  private formatInAppBody(event: CollabEvent): string {
    const who = event.details?.displayName ?? event.userId;

    switch (event.type) {
      case 'join':
        return `${who} joined manuscript ${event.manuscriptId}.`;
      case 'leave':
        return `${who} left manuscript ${event.manuscriptId}.`;
      case 'edit':
        return `${who} edited manuscript ${event.manuscriptId}.`;
      case 'comment':
        return `${who} commented on manuscript ${event.manuscriptId}.`;
      case 'mention':
        return `${who} mentioned you in manuscript ${event.manuscriptId}.`;
      case 'handoff':
        return `${who} requested a handoff in manuscript ${event.manuscriptId}.`;
      default:
        return `${who} triggered ${event.type} in manuscript ${event.manuscriptId}.`;
    }
  }
}
