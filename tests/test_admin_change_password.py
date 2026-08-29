import unittest

from app import app, db, seed_database, User


class AdminChangePasswordTest(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.testing = True
        self.client = self.app.test_client()

        with self.app.app_context():
            seed_database()
            # Reset admin password to default admin123 before each test
            self.admin = User.query.filter_by(email='admin@sweetscoop.com').first()
            if not self.admin:
                self.admin = User(username='Admin User', email='admin@sweetscoop.com', role='admin')
                db.session.add(self.admin)
            self.admin.set_password('admin123')

            # Ensure customer user exists
            self.customer = User.query.filter_by(email='customer@example.com').first()
            if not self.customer:
                self.customer = User(username='John Customer', email='customer@example.com', role='customer')
                self.customer.set_password('customer123')
                db.session.add(self.customer)

            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            admin = User.query.filter_by(email='admin@sweetscoop.com').first()
            if admin:
                admin.set_password('admin123')
                db.session.commit()

    def login_admin(self, password='admin123'):
        return self.client.post(
            '/login',
            data={'email': 'admin@sweetscoop.com', 'password': password},
            follow_redirects=True,
        )

    def login_customer(self):
        return self.client.post(
            '/login',
            data={'email': 'customer@example.com', 'password': 'customer123'},
            follow_redirects=True,
        )

    def test_unauthorized_access_redirects(self):
        response = self.client.get('/admin/change-password', follow_redirects=True)
        self.assertIn(b'Access restricted', response.data)

        post_response = self.client.post('/admin/change-password', data={
            'current_password': 'admin123',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        }, follow_redirects=True)
        self.assertIn(b'Access restricted', post_response.data)

    def test_customer_cannot_access_admin_change_password(self):
        self.login_customer()
        response = self.client.get('/admin/change-password', follow_redirects=True)
        self.assertIn(b'Access restricted to store administrators', response.data)

    def test_admin_get_change_password_page(self):
        self.login_admin()
        response = self.client.get('/admin/change-password')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Change Admin Password', response.data)
        self.assertIn(b'Current Password', response.data)

    def test_incorrect_current_password(self):
        self.login_admin()
        response = self.client.post('/admin/change-password', data={
            'current_password': 'wrongpassword',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Current password is incorrect', response.data)

    def test_mismatched_new_passwords(self):
        self.login_admin()
        response = self.client.post('/admin/change-password', data={
            'current_password': 'admin123',
            'new_password': 'newpassword123',
            'confirm_password': 'differentpassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'do not match', response.data)

    def test_short_new_password(self):
        self.login_admin()
        response = self.client.post('/admin/change-password', data={
            'current_password': 'admin123',
            'new_password': '12345',
            'confirm_password': '12345'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'at least 6 characters long', response.data)

    def test_same_new_password_warning(self):
        self.login_admin()
        response = self.client.post('/admin/change-password', data={
            'current_password': 'admin123',
            'new_password': 'admin123',
            'confirm_password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'New password must be different', response.data)

    def test_successful_password_change_and_login(self):
        self.login_admin('admin123')
        response = self.client.post('/admin/change-password', data={
            'current_password': 'admin123',
            'new_password': 'NewAdminPass2026!',
            'confirm_password': 'NewAdminPass2026!'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Password changed successfully', response.data)

        # Logout
        self.client.get('/logout', follow_redirects=True)

        # Old password should fail
        fail_login = self.login_admin('admin123')
        self.assertIn(b'Invalid email or password', fail_login.data)

        # New password should succeed
        success_login = self.login_admin('NewAdminPass2026!')
        self.assertIn(b'Admin Control Dashboard', success_login.data)


if __name__ == '__main__':
    unittest.main()
