"""Email templates domain module."""


def __getattr__(name: str):
    """Lazy re-export to avoid circular imports.

    email_templates.router -> infrastructure.email.service -> email_templates.service
    forms a cycle; lazy imports break it.
    """
    if name == "router":
        from app.modules.email_templates.router import router
        return router
    if name == "EmailTemplateService":
        from app.modules.email_templates.service import EmailTemplateService
        return EmailTemplateService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["router", "EmailTemplateService"]
