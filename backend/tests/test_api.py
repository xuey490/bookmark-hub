from __future__ import annotations

import httpx
import respx


async def _create_bookmark(client, **overrides):
    payload = {
        "url": "https://example.test/article",
        "title": "示例文章",
        "tags": ["python", "教程"],
    }
    payload.update(overrides)
    response = await client.post("/api/bookmarks", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


async def test_requires_token(client):
    response = await client.get(
        "/api/bookmarks", headers={"Authorization": "Bearer wrong"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == 401

    response = await client.get(
        "/api/bookmarks", headers={"Authorization": ""}
    )
    assert response.status_code == 401


async def test_category_and_bookmark_crud(client):
    category = (
        await client.post("/api/categories", json={"name": "技术"})
    ).json()["data"]
    assert category["name"] == "技术"

    duplicate = await client.post("/api/categories", json={"name": "技术"})
    assert duplicate.status_code == 409

    bookmark = await _create_bookmark(client, category_id=category["id"])
    assert bookmark["category"]["name"] == "技术"
    assert bookmark["tags"] == ["python", "教程"]
    assert bookmark["status"] == "unknown"

    listing = (await client.get("/api/bookmarks")).json()["data"]
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == bookmark["id"]

    filtered = (
        await client.get("/api/bookmarks", params={"tag": "python"})
    ).json()["data"]
    assert filtered["total"] == 1

    searched = (
        await client.get("/api/bookmarks", params={"q": "示例"})
    ).json()["data"]
    assert searched["total"] == 1

    status_filtered = (
        await client.get("/api/bookmarks", params={"status": "ok"})
    ).json()["data"]
    assert status_filtered["total"] == 0

    updated = (
        await client.put(
            f"/api/bookmarks/{bookmark['id']}",
            json={"title": "新标题", "tags": ["fastapi"]},
        )
    ).json()["data"]
    assert updated["title"] == "新标题"
    assert updated["tags"] == ["fastapi"]

    detail = (
        await client.get(f"/api/bookmarks/{bookmark['id']}")
    ).json()["data"]
    assert detail["id"] == bookmark["id"]

    duplicate_url = await client.post(
        "/api/bookmarks",
        json={"url": bookmark["url"], "title": "重复"},
    )
    assert duplicate_url.status_code == 409
    assert duplicate_url.json()["data"]["id"] == bookmark["id"]

    stats = (await client.get("/api/stats")).json()["data"]
    assert stats["total"] == 1
    assert stats["unknown"] == 1

    tags = (await client.get("/api/tags")).json()["data"]
    assert tags == [{"name": "fastapi", "count": 1}]

    await client.delete(f"/api/categories/{category['id']}")
    detail = (
        await client.get(f"/api/bookmarks/{bookmark['id']}")
    ).json()["data"]
    assert detail["category"] is None

    deleted = await client.delete(f"/api/bookmarks/{bookmark['id']}")
    assert deleted.status_code == 200
    listing = (await client.get("/api/bookmarks")).json()["data"]
    assert listing["total"] == 0


async def test_batch_delete_bookmarks(client):
    first = await _create_bookmark(
        client, url="https://batch.test/a", title="批量 A"
    )
    second = await _create_bookmark(
        client, url="https://batch.test/b", title="批量 B"
    )
    third = await _create_bookmark(
        client, url="https://batch.test/c", title="批量 C"
    )

    response = await client.post(
        "/api/bookmarks/batch-delete",
        json={"ids": [first["id"], third["id"], third["id"]]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["deleted"] == 2

    listing = (await client.get("/api/bookmarks")).json()["data"]
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == second["id"]

    empty = await client.post(
        "/api/bookmarks/batch-delete", json={"ids": []}
    )
    assert empty.status_code == 422


async def test_bookmark_visit_tracking(client):
    bookmark = await _create_bookmark(
        client, url="https://visit.test/page", title="访问统计"
    )
    assert bookmark["visit_count"] == 0
    assert bookmark["last_visited_at"] is None

    first = await client.post(f"/api/bookmarks/{bookmark['id']}/visit")
    assert first.status_code == 200, first.text
    first_data = first.json()["data"]
    assert first_data["visit_count"] == 1
    assert first_data["last_visited_at"]

    second = await client.post(f"/api/bookmarks/{bookmark['id']}/visit")
    second_data = second.json()["data"]
    assert second_data["visit_count"] == 2
    assert second_data["last_visited_at"]

    listing = (await client.get("/api/bookmarks")).json()["data"]
    assert listing["items"][0]["visit_count"] == 2

    missing = await client.post("/api/bookmarks/999999/visit")
    assert missing.status_code == 404


async def test_update_and_reset_server_token(client):
    new_token = "custom-token-1234567890"
    response = await client.put("/api/token", json={"token": new_token})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["token"] == new_token

    old = await client.get(
        "/api/bookmarks",
        headers={"Authorization": "Bearer test-token"},
    )
    assert old.status_code == 401

    new = await client.get(
        "/api/bookmarks",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert new.status_code == 200

    reset = await client.post(
        "/api/token/reset",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert reset.status_code == 200, reset.text
    reset_token = reset.json()["data"]["token"]
    assert reset_token != new_token

    old_new = await client.get(
        "/api/bookmarks",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert old_new.status_code == 401

    reset_ok = await client.get(
        "/api/bookmarks",
        headers={"Authorization": f"Bearer {reset_token}"},
    )
    assert reset_ok.status_code == 200

    weak = await client.put(
        "/api/token",
        json={"token": "too-short"},
        headers={"Authorization": f"Bearer {reset_token}"},
    )
    assert weak.status_code == 422


async def test_create_bookmark_validation(client):
    response = await client.post(
        "/api/bookmarks", json={"url": "ftp://example.test/file"}
    )
    assert response.status_code == 422

    response = await client.post(
        "/api/bookmarks",
        json={"url": "https://example.test", "tags": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"]},
    )
    assert response.status_code == 422


async def test_title_falls_back_to_hostname(client):
    bookmark = await _create_bookmark(
        client, url="https://fallback.test/page", title=""
    )
    assert bookmark["title"] == "fallback.test"


async def test_import_export_roundtrip(client):
    payload = {
        "version": 1,
        "bookmarks": [
            {
                "url": "https://import.test/a",
                "title": "导入 A",
                "category": "技术",
                "tags": ["x", "y"],
            },
            {
                "url": "https://import.test/b",
                "title": "导入 B",
                "tags": "z,w",
            },
        ],
    }
    imported = (
        await client.post("/api/bookmarks/import", json=payload)
    ).json()["data"]
    assert imported["imported"] == 2

    again = (
        await client.post("/api/bookmarks/import", json=payload)
    ).json()["data"]
    assert again["skipped"] == 2

    exported = await client.get(
        "/api/bookmarks/export", params={"format": "json"}
    )
    assert exported.status_code == 200
    body = exported.json()
    assert body["version"] == 1
    assert len(body["bookmarks"]) == 2
    assert body["bookmarks"][0]["category"] in (None, "技术")

    html_export = await client.get(
        "/api/bookmarks/export", params={"format": "html"}
    )
    assert html_export.status_code == 200
    assert html_export.text.startswith("<!DOCTYPE NETSCAPE-Bookmark-file-1>")
    assert "import.test" in html_export.text

    html_import = (
        "<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><p>"
        '<DT><A HREF="https://html.test/page" TAGS="html,test">HTML 页面</A>'
        "</DL><p>"
    )
    uploaded = await client.post(
        "/api/bookmarks/import",
        files={
            "file": ("bookmarks.html", html_import, "text/html"),
        },
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["data"]["imported"] == 1


async def test_import_invalid_url_is_reported(client):
    response = await client.post(
        "/api/bookmarks/import",
        json={"items": [{"url": "javascript:alert(1)"}]},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["imported"] == 0
    assert data["failed"] >= 1


async def test_manual_check_ok_and_timeout(client):
    bookmark = await _create_bookmark(
        client, url="https://check-ok.test/page"
    )

    with respx.mock(assert_all_called=False) as mock:
        mock.head("https://check-ok.test/page").mock(
            return_value=httpx.Response(200)
        )
        response = await client.post(
            f"/api/bookmarks/{bookmark['id']}/check"
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "ok"
    assert data["http_status"] == 200
    assert data["last_checked_at"]

    timeout_bookmark = await _create_bookmark(
        client, url="https://check-timeout.test/page"
    )
    with respx.mock(assert_all_called=False) as mock:
        mock.head("https://check-timeout.test/page").mock(
            side_effect=httpx.ReadTimeout("slow")
        )
        response = await client.post(
            f"/api/bookmarks/{timeout_bookmark['id']}/check"
        )

    assert response.json()["data"]["status"] == "timeout"

    with respx.mock(assert_all_called=False) as mock:
        mock.head("https://check-ok.test/page").mock(
            return_value=httpx.Response(404)
        )
        response = await client.post("/api/check/urls", json={})
    summary = response.json()["data"]
    assert summary["checked"] == 2
    assert summary["error"] >= 1


async def test_password_like_token_not_needed_for_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
