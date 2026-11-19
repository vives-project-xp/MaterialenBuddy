"""Rol- en API-tests zonder echte Authentik-server of MySQL-data."""

import os
import time
import unittest
from unittest.mock import AsyncMock, patch

os.environ.update({
    "DATABASE_URL": "sqlite://", "SESSION_SECRET": "test-only-secret-" * 4,
    "SESSION_COOKIE_SECURE": "false",
    "AUTHENTIK_DISCOVERY_URL": "https://identity.example/application/o/test/.well-known/openid-configuration",
    "AUTHENTIK_CLIENT_ID": "test", "AUTHENTIK_CLIENT_SECRET": "test",
    "AUTHENTIK_REDIRECT_URI": "http://testserver/auth/callback",
    "AUTHENTIK_ADMIN_GROUP": "materialenbuddy-admins",
    "AUTHENTIK_USER_GROUP": "materialenbuddy-users",
})

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import StaticPool

import auth
import server


class PermissionsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                                    poolclass=StaticPool)

        # SQLite-testdatabase: alleen de MySQL-locksyntax wordt weggelaten.
        @event.listens_for(self.engine, "before_cursor_execute", retval=True)
        def sqlite_lock(connection, cursor, statement, parameters, context, executemany):
            return statement.replace("FOR UPDATE", ""), parameters

        with self.engine.begin() as connection:
            for statement in [
                "CREATE TABLE medicijnen (id INTEGER PRIMARY KEY, naam TEXT UNIQUE, minimum_voorraad INTEGER)",
                "CREATE TABLE voorraad (id INTEGER PRIMARY KEY, medicijn_id INTEGER UNIQUE, aantal INTEGER)",
                "CREATE TABLE voorraad_mutaties (id INTEGER PRIMARY KEY, medicijn_id INTEGER, levering_id INTEGER, verschil INTEGER, reden TEXT)",
                "CREATE TABLE leveringen (id INTEGER PRIMARY KEY, startlocatie TEXT, bestemming TEXT, status TEXT)",
                "CREATE TABLE levering_medicijnen (id INTEGER PRIMARY KEY, levering_id INTEGER, medicijn_id INTEGER, aantal INTEGER)",
                "INSERT INTO medicijnen VALUES (1, 'Testmateriaal', 2)",
                "INSERT INTO voorraad VALUES (1, 1, 10)",
            ]:
                connection.execute(text(statement))
        self.engine_patch = patch.object(server, "engine", self.engine)
        self.engine_patch.start()
        self.client = TestClient(server.app)

    def tearDown(self):
        self.client.close()
        self.engine_patch.stop()
        self.engine.dispose()

    def login(self, group):
        claims = {"sub": "test-account", "name": "Test", "groups": [group],
                  "exp": time.time() + 3600}
        with patch.object(auth.oauth.authentik, "authorize_access_token",
                          AsyncMock(return_value={"userinfo": claims})):
            response = self.client.get("/auth/callback", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        me = self.client.get("/auth/me")
        self.assertEqual(me.status_code, 200)
        return {"X-CSRF-Token": me.json()["csrf_token"]}

    def test_anonymous_cannot_read_or_write(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        for url in ["/auth/me", "/voorraad", "/medicijnen", "/leveringen/1"]:
            self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.post("/voorraad/1", json={"aantal": 1}).status_code, 401)

    def test_user_can_order_but_cannot_manage_materials_or_stock(self):
        headers = self.login("materialenbuddy-users")
        self.assertEqual(self.client.get("/voorraad").status_code, 200)
        order = {"startlocatie": "B303", "bestemming": "B301",
                 "medicijnen": [{"naam": "Testmateriaal", "aantal": 3}]}
        response = self.client.post("/leveringen", headers=headers, json=order)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(self.client.get("/voorraad").json()[0]["aantal"], 7)
        for method, url, body in [
            ("POST", "/voorraad/1", {"aantal": 1}),
            ("POST", "/medicijnen", {"naam": "Verboden"}),
            ("PUT", "/medicijnen/1", {"naam": "Verboden", "minimum_voorraad": 0}),
            ("DELETE", "/medicijnen/1", None),
        ]:
            self.assertEqual(self.client.request(method, url, headers=headers, json=body).status_code, 403)

    def test_admin_can_manage(self):
        headers = self.login("materialenbuddy-admins")
        self.assertEqual(self.client.post("/voorraad/1", headers=headers, json={"aantal": 4}).status_code, 200)
        self.assertEqual(self.client.get("/voorraad").json()[0]["aantal"], 14)
        response = self.client.post("/medicijnen", headers=headers, json={"naam": "Nieuw"})
        self.assertEqual(response.status_code, 201, response.text)
        item_id = response.json()["id"]
        self.assertEqual(self.client.put(f"/medicijnen/{item_id}", headers=headers,
                                        json={"naam": "Gewijzigd", "minimum_voorraad": 3}).status_code, 200)
        self.assertEqual(self.client.delete(f"/medicijnen/{item_id}", headers=headers).status_code, 200)

    def test_csrf_and_logout(self):
        headers = self.login("materialenbuddy-admins")
        self.assertEqual(self.client.post("/voorraad/1", json={"aantal": 1}).status_code, 403)
        self.assertEqual(self.client.post("/auth/logout", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/voorraad").status_code, 401)

    def test_unknown_group_is_denied(self):
        with patch.object(auth.oauth.authentik, "authorize_access_token", AsyncMock(return_value={
            "userinfo": {"sub": "outsider", "groups": ["unrelated"], "exp": time.time() + 100}
        })):
            self.assertEqual(self.client.get("/auth/callback").status_code, 403)
        self.assertEqual(self.client.get("/auth/me").status_code, 401)

    def test_expired_session_is_denied(self):
        with patch.object(auth.oauth.authentik, "authorize_access_token", AsyncMock(return_value={
            "userinfo": {"sub": "expired", "groups": ["materialenbuddy-admins"], "exp": time.time() - 1}
        })):
            self.client.get("/auth/callback")
        self.assertEqual(self.client.get("/auth/me").status_code, 401)

    def test_insufficient_stock_rolls_back_order(self):
        headers = self.login("materialenbuddy-users")
        response = self.client.post("/leveringen", headers=headers, json={
            "startlocatie": "B303", "bestemming": "B301",
            "medicijnen": [{"naam": "Testmateriaal", "aantal": 11}]
        })
        self.assertEqual(response.status_code, 409)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM leveringen")).scalar(), 0)
            self.assertEqual(connection.execute(text("SELECT aantal FROM voorraad")).scalar(), 10)


if __name__ == "__main__":
    unittest.main()
