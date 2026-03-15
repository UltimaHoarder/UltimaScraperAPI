"""URL diagnostics for CDN signed URLs.

This module provides utilities to decode and analyze signed CDN URLs,
particularly AWS CloudFront URLs used by OnlyFans and similar platforms.

URL Structure (OnlyFans CloudFront):
    https://cdn2.onlyfans.com/files/.../image.jpg?Tag=X&u=USER_ID&Policy=BASE64&Signature=SIG&Key-Pair-Id=KEY

The Policy parameter is base64-encoded JSON containing:
    - Resource: The URL pattern this signature is valid for
    - Condition.DateLessThan.AWS:EpochTime: Expiration timestamp
    - Condition.IpAddress.AWS:SourceIp: IP address restriction (if any)
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse


@dataclass
class CloudFrontPolicy:
    """Decoded CloudFront policy information."""

    resource: str | None = None
    expires_at: datetime | None = None
    ip_address: str | None = None
    raw_policy: dict[str, Any] | None = None

    @property
    def is_expired(self) -> bool:
        """Check if the URL has expired."""
        if self.expires_at is None:
            return False  # Unknown = assume valid
        return self.expires_at < datetime.now(timezone.utc)

    @property
    def time_until_expiry(self) -> float | None:
        """Seconds until expiration (negative if expired)."""
        if self.expires_at is None:
            return None
        return (self.expires_at - datetime.now(timezone.utc)).total_seconds()

    @property
    def is_ip_locked(self) -> bool:
        """Check if URL is restricted to a specific IP."""
        return self.ip_address is not None


@dataclass
class UrlDiagnostics:
    """Complete diagnostics for a CDN URL."""

    url: str
    cdn_host: str | None = None
    user_id: int | None = None
    policy: CloudFrontPolicy | None = None
    error: str | None = None

    def get_diagnosis(self) -> str:
        """Get human-readable diagnosis of potential issues."""
        issues: list[str] = []

        if self.error:
            return f"Parse error: {self.error}"

        if self.policy is None:
            return "No CloudFront policy found in URL"

        if self.policy.is_expired:
            expiry = self.policy.expires_at
            if expiry:
                ago = datetime.now(timezone.utc) - expiry
                if ago.days > 0:
                    issues.append(
                        f"URL expired {ago.days} day(s) ago at {expiry.isoformat()}"
                    )
                else:
                    hours = int(ago.total_seconds() / 3600)
                    issues.append(
                        f"URL expired {hours} hour(s) ago at {expiry.isoformat()}"
                    )
            else:
                issues.append("URL is expired")

        if self.policy.is_ip_locked:
            issues.append(f"URL is IP-locked to {self.policy.ip_address}")

        if not issues:
            remaining = self.policy.time_until_expiry
            if remaining is not None:
                hours = remaining / 3600
                if hours < 1:
                    issues.append(f"URL expires in {int(remaining / 60)} minutes")
                else:
                    issues.append(f"URL valid for ~{hours:.1f} hours")

        return "; ".join(issues) if issues else "URL appears valid"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "url": self.url[:100] + "..." if len(self.url) > 100 else self.url,
            "cdn_host": self.cdn_host,
            "user_id": self.user_id,
            "diagnosis": self.get_diagnosis(),
        }
        if self.policy:
            result["policy"] = {
                "expires_at": (
                    self.policy.expires_at.isoformat()
                    if self.policy.expires_at
                    else None
                ),
                "is_expired": self.policy.is_expired,
                "ip_address": self.policy.ip_address,
                "is_ip_locked": self.policy.is_ip_locked,
            }
        if self.error:
            result["error"] = self.error
        return result


def decode_cloudfront_policy(policy_b64: str) -> CloudFrontPolicy:
    """Decode a CloudFront Policy parameter.

    CloudFront/OnlyFans uses a modified URL-safe base64 encoding where:
    - '~' is used instead of '+' (URL-safe character substitution)
    - '-' is kept as-is (standard URL-safe base64)
    - '_' at the end is used instead of '=' for padding

    Args:
        policy_b64: Base64-encoded policy string from URL

    Returns:
        Decoded CloudFrontPolicy object
    """
    # CloudFront uses ~ as URL-safe replacement for + (NOT for padding)
    fixed = policy_b64.replace("~", "+")

    # Strip trailing underscores (used as padding replacement)
    fixed = fixed.rstrip("_")

    # Add standard base64 padding if needed
    padding = 4 - len(fixed) % 4
    if padding != 4:
        fixed += "=" * padding

    policy_json = base64.b64decode(fixed).decode("utf-8")
    policy_data = json.loads(policy_json)

    result = CloudFrontPolicy(raw_policy=policy_data)

    # Extract from Statement[0]
    statements = policy_data.get("Statement", [])
    if statements:
        statement = statements[0]
        result.resource = statement.get("Resource")

        condition = statement.get("Condition", {})

        # Expiration
        date_less_than = condition.get("DateLessThan", {})
        epoch_time = date_less_than.get("AWS:EpochTime")
        if epoch_time:
            result.expires_at = datetime.fromtimestamp(epoch_time, tz=timezone.utc)

        # IP restriction
        ip_address = condition.get("IpAddress", {})
        source_ip = ip_address.get("AWS:SourceIp")
        if source_ip:
            result.ip_address = source_ip

    return result


def diagnose_url(url: str) -> UrlDiagnostics:
    """Analyze a CDN URL and return diagnostics.

    Supports:
    - OnlyFans CDN URLs (cdn*.onlyfans.com)
    - Fansly CDN URLs (if similar structure)

    Args:
        url: The CDN URL to analyze

    Returns:
        UrlDiagnostics with decoded information and diagnosis
    """
    result = UrlDiagnostics(url=url)

    try:
        parsed = urlparse(url)
        result.cdn_host = parsed.netloc

        query_params = parse_qs(parsed.query)

        # Extract user ID (OnlyFans specific)
        if "u" in query_params:
            try:
                result.user_id = int(query_params["u"][0])
            except (ValueError, IndexError):
                pass

        # Decode Policy
        if "Policy" in query_params:
            policy_b64 = query_params["Policy"][0]
            result.policy = decode_cloudfront_policy(policy_b64)

    except Exception as e:
        result.error = str(e)

    return result


def diagnose_download_failure(
    url: str,
    filepath: str,
    post_id: int | None = None,
    media_id: int | None = None,
    http_status: int | None = None,
    error_message: str | None = None,
) -> str:
    """Generate a detailed diagnosis for a download failure.

    Args:
        url: The URL that failed to download
        filepath: Target file path
        post_id: Content/Post ID
        media_id: Media ID
        http_status: HTTP status code if available
        error_message: Error message from the download attempt

    Returns:
        Detailed diagnosis string for logging/display
    """
    lines = ["=" * 60, "DOWNLOAD FAILURE DIAGNOSIS", "=" * 60]

    # IDs
    if post_id or media_id:
        lines.append(f"Post ID: {post_id} - Media ID: {media_id}")

    # File path
    lines.append(f"Target: {filepath}")

    # HTTP status
    if http_status:
        lines.append(f"HTTP Status: {http_status}")
        if http_status == 403:
            lines.append("  → 403 typically means URL signature expired or IP mismatch")
        elif http_status == 404:
            lines.append("  → 404 means content was deleted from CDN")
        elif http_status == 410:
            lines.append("  → 410 means content permanently removed")

    # Error message
    if error_message:
        lines.append(f"Error: {error_message}")

    # URL diagnostics
    lines.append("")
    lines.append("URL Analysis:")
    diag = diagnose_url(url)
    lines.append(f"  CDN Host: {diag.cdn_host}")
    lines.append(f"  User ID: {diag.user_id}")
    lines.append(f"  Diagnosis: {diag.get_diagnosis()}")

    if diag.policy:
        lines.append("")
        lines.append("Policy Details:")
        if diag.policy.expires_at:
            lines.append(f"  Expires: {diag.policy.expires_at.isoformat()}")
            lines.append(f"  Expired: {diag.policy.is_expired}")
            remaining = diag.policy.time_until_expiry
            if remaining is not None:
                if remaining < 0:
                    lines.append(f"  Expired: {abs(remaining / 3600):.1f} hours ago")
                else:
                    lines.append(f"  Remaining: {remaining / 3600:.1f} hours")
        if diag.policy.ip_address:
            lines.append(f"  IP Lock: {diag.policy.ip_address}")

    # Recommendations
    lines.append("")
    lines.append("Recommendations:")
    if diag.policy and diag.policy.is_expired:
        lines.append("  → Re-scrape the content to get fresh URLs")
    elif diag.policy and diag.policy.is_ip_locked:
        lines.append("  → Use a proxy matching the IP in the policy")
        lines.append(f"     Required IP: {diag.policy.ip_address}")
    elif http_status == 404:
        lines.append("  → Content has been deleted, cannot be recovered")
    else:
        lines.append("  → Check network connectivity and proxy configuration")

    lines.append("=" * 60)
    return "\n".join(lines)


def is_onlyfans_cdn_url(url: str) -> bool:
    """Check if URL is an OnlyFans CDN URL."""
    return bool(re.match(r"https?://cdn\d*\.onlyfans\.com/", url))


def is_fansly_cdn_url(url: str) -> bool:
    """Check if URL is a Fansly CDN URL."""
    return "fansly" in url.lower() and "cdn" in url.lower()
