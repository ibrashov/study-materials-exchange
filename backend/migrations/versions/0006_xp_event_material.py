"""Link XP events to materials and credit activity from before gamification existed.

Schema: xp_events.material_id lets download XP be paid once per (student, material) and lets
upload XP be taken back when a material goes to Trash.

Data (idempotent, PostgreSQL):
1. Link existing upload events to their materials (same uploader and "Uploaded \"title\"").
2. Credit +50 XP for every live material that has no upload event (uploaded before 0005).
3. Take back upload XP still held for materials that are currently in Trash.
4. Credit +25 XP to users who enabled 2FA before 0005.
5. Recompute users.xp_points as the sum of their XP events and award earned badges.
"""
from alembic import op
import sqlalchemy as sa

revision = '0006_xp_event_material'
down_revision = '0005_trash_gamification'
branch_labels = None
depends_on = None

UPLOAD_DESCRIPTION = "left('Uploaded \"' || m.title || '\"', 200)"


def upgrade():
    op.add_column('xp_events', sa.Column(
        'material_id', sa.Integer(), sa.ForeignKey('materials.material_id', ondelete='SET NULL'), nullable=True))
    op.create_index('ix_xp_events_user_action_material', 'xp_events', ['user_id', 'action', 'material_id'])

    # 1. Pair the k-th unlinked upload event with the k-th material of the same uploader and title.
    op.execute(f"""
        WITH ev AS (
            SELECT event_id, user_id, description,
                   row_number() OVER (PARTITION BY user_id, description ORDER BY event_id) AS rn
            FROM xp_events
            WHERE action = 'upload_material' AND material_id IS NULL
        ), mat AS (
            SELECT m.material_id, m.uploader_id, {UPLOAD_DESCRIPTION} AS description,
                   row_number() OVER (PARTITION BY m.uploader_id, {UPLOAD_DESCRIPTION} ORDER BY m.material_id) AS rn
            FROM materials m
        )
        UPDATE xp_events x SET material_id = mat.material_id
        FROM ev JOIN mat ON mat.uploader_id = ev.user_id AND mat.description = ev.description AND mat.rn = ev.rn
        WHERE x.event_id = ev.event_id
    """)

    # 2. Live materials uploaded before gamification existed earn their upload XP.
    op.execute(f"""
        INSERT INTO xp_events (user_id, action, points, description, material_id, created_at)
        SELECT m.uploader_id, 'upload_material', 50, {UPLOAD_DESCRIPTION}, m.material_id, m.uploaded_at
        FROM materials m
        WHERE m.deleted_at IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM xp_events e
              WHERE e.material_id = m.material_id AND e.action IN ('upload_material', 'upload_revoked'))
    """)

    # 3. Materials already in Trash do not keep upload XP (the same rule the API now applies).
    op.execute("""
        INSERT INTO xp_events (user_id, action, points, description, material_id)
        SELECT m.uploader_id, 'upload_revoked', -held.points, left('Removed "' || m.title || '"', 200), m.material_id
        FROM materials m
        JOIN (
            SELECT user_id, material_id, SUM(points) AS points
            FROM xp_events
            WHERE action IN ('upload_material', 'upload_revoked') AND material_id IS NOT NULL
            GROUP BY user_id, material_id
        ) held ON held.material_id = m.material_id AND held.user_id = m.uploader_id
        WHERE m.deleted_at IS NOT NULL AND held.points > 0
    """)

    # 4. Two-factor authentication enabled before gamification existed.
    op.execute("""
        INSERT INTO xp_events (user_id, action, points, description)
        SELECT u.user_id, 'enable_2fa', 25, 'Enabled two-factor authentication'
        FROM users u
        WHERE u.totp_enabled
          AND NOT EXISTS (SELECT 1 FROM xp_events e WHERE e.user_id = u.user_id AND e.action = 'enable_2fa')
    """)

    # 5. XP is the sum of the user's XP history.
    op.execute("""
        UPDATE users u SET xp_points = GREATEST(0, COALESCE(
            (SELECT SUM(e.points) FROM xp_events e WHERE e.user_id = u.user_id), 0))
    """)
    op.execute("""
        INSERT INTO user_badges (user_id, badge_code)
        SELECT u.user_id, b.code
        FROM users u
        LEFT JOIN LATERAL (
            SELECT
                (SELECT COUNT(*) FROM materials m WHERE m.uploader_id = u.user_id AND m.deleted_at IS NULL) AS uploads,
                (SELECT COUNT(*) FROM xp_events e WHERE e.user_id = u.user_id AND e.action = 'received_download') AS received,
                (SELECT COUNT(*) FROM xp_events e WHERE e.user_id = u.user_id AND e.action = 'download_material') AS downloads
        ) s ON true
        CROSS JOIN LATERAL (VALUES
            ('first_upload', s.uploads >= 1),
            ('prolific_author', s.uploads >= 5),
            ('popular_notes', s.received >= 10),
            ('curious_learner', s.downloads >= 3),
            ('security_champion', u.totp_enabled),
            ('streak_starter', u.longest_streak >= 3),
            ('rising_star', u.xp_points >= 150)
        ) AS b(code, earned)
        WHERE b.earned
        ON CONFLICT ON CONSTRAINT uq_user_badges_user_code DO NOTHING
    """)


def downgrade():
    op.drop_index('ix_xp_events_user_action_material', table_name='xp_events')
    op.drop_column('xp_events', 'material_id')
