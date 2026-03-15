from __future__ import annotations

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    import ultima_scraper_api.apis.fansly.classes as fansly_classes
    import ultima_scraper_api.apis.loyalfans.classes as loyalfans_classes
    import ultima_scraper_api.apis.onlyfans.classes as onlyfans_classes

    SiteModel = Union[
        "onlyfans_classes.user_model.UserModel",
        "fansly_classes.user_model.UserModel",
        "loyalfans_classes.user_model.UserModel",
    ]


class UnifiedUserModel:
    """Unified user model that wraps site-specific user models"""

    def __init__(
        self,
        site_model: SiteModel,
        site_name: str,
    ) -> None:
        """Initialize a unified user model.

        Args:
            site_model: Site-specific user model (OnlyFans, Fansly, or LoyalFans)
            site_name: Name of the site ("OnlyFans", "Fansly", "LoyalFans")
        """
        self.id = site_model.id
        self.username = site_model.username
        self.name = site_model.name
        self.subscription_price = site_model.subscription_price
        self.aliases: list[str] = []
        self.join_date = site_model.join_date
        self.site_name = site_name
        self.site_model = site_model

    def get_usernames(self, ignore_id: bool = True) -> list[str]:
        """Get all usernames including aliases.

        Args:
            ignore_id: If True, exclude ID-based usernames like "u123"

        Returns:
            List of all usernames and aliases
        """
        final_usernames: list[str] = [self.username]
        for alias in self.aliases:
            if alias not in final_usernames:
                final_usernames.append(alias)

        if ignore_id and len(final_usernames) > 1:
            invalid_usernames = [f"u{self.id}"]
            for invalid_username in invalid_usernames:
                if invalid_username in final_usernames:
                    final_usernames.remove(invalid_username)

        assert final_usernames
        return final_usernames

    def get_aliases(self, ignore_id: bool = True) -> list[str]:
        """Get all aliases.

        Args:
            ignore_id: If True, exclude ID-based aliases like "u123"

        Returns:
            List of all aliases
        """
        final_aliases = self.aliases.copy()
        if ignore_id:
            invalid_aliases = [f"u{self.id}"]
            for invalid_alias in invalid_aliases:
                if invalid_alias in final_aliases:
                    final_aliases.remove(invalid_alias)
        return final_aliases

    def add_aliases(self, aliases: list[str]) -> None:
        """Add aliases for this user.

        Args:
            aliases: List of aliases to add
        """
        for alias in aliases:
            if alias == self.username:
                continue
            if alias not in self.aliases:
                self.aliases.append(alias)

    def __repr__(self) -> str:
        return f"UnifiedUserModel(username={self.username}, site={self.site_name})"
