import random

from curl_cffi.requests import AsyncSession
from fastapi import Response
from loguru import logger

from server import config
from server.utils.logger_trace import trace

IFRAME_HEADERS = {"Access-Control-Allow-Origin": "*", "X-Frame-Options": "SAMEORIGIN"}


@trace
async def iframe_proxy(iframe_id: str):
    """
    Proxy iframe content from Medium's media endpoint.

    Args:
        iframe_id: The Medium iframe/media ID

    Returns:
        Response with patched HTML content
    """
    logger.debug(f"Fetching iframe content for ID: {iframe_id}")

    proxy = random.choice(config.PROXY_LIST) if config.PROXY_LIST else None

    async with AsyncSession(impersonate=config.CURL_IMPERSONATE) as session:
        response = await session.get(
            f"https://medium.com/media/{iframe_id}",
            timeout=config.REQUEST_TIMEOUT,
            proxies={"http": proxy, "https": proxy} if proxy else None,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )

        if response.status_code != 200:
            logger.error(
                f"Failed to fetch iframe {iframe_id}\n"
                f"Status code: {response.status_code}"
            )
            return Response(content="", media_type="text/html", headers=IFRAME_HEADERS)

        request_content = response.text

    patched_content = patch_iframe_content(request_content)
    return Response(content=patched_content, media_type="text/html", headers=IFRAME_HEADERS)


def patch_iframe_content(content: str) -> str:
    """
    Patch iframe content to work in Freedium context.

    Replaces Medium's domain-based security mechanism with a console log
    to avoid cross-origin issues.

    Args:
        content: Raw HTML content from Medium

    Returns:
        Patched HTML content
    """
    return content.replace(
        "document.domain = document.domain",
        'console.log("[FREEDIUM] iframe workaround started")'
    )
