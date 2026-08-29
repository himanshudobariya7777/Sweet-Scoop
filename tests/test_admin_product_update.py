import io
import os
import unittest

from app import app, db, seed_database, Product, User, Order, cache_bust_url


class AdminProductCrudTest(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.testing = True
        self.client = self.app.test_client()
        self.created_upload_files = []

        with self.app.app_context():
            seed_database()
            # Ensure default admin exists
            admin = User.query.filter_by(email='admin@sweetscoop.com').first()
            if not admin:
                admin = User(username='Admin', email='admin@sweetscoop.com', role='admin')
                db.session.add(admin)
            admin.set_password('admin123')

            product = Product(
                name='Temp Flavour',
                description='Old description',
                category_slug='chocolate',
                price_small=199.0,
                price_medium=299.0,
                price_large=399.0,
                image_url='/static/images/chocolate.jpg',
                ingredients='Cream, Milk',
                is_popular=False,
                is_special_offer=False,
                discount_percent=0,
            )
            db.session.add(product)
            db.session.commit()
            self.product_id = product.id

    def tearDown(self):
        # Clean up any files uploaded during testing
        upload_folder = self.app.config.get('UPLOAD_FOLDER')
        for filename in self.created_upload_files:
            file_path = os.path.join(upload_folder, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def test_seed_database_keeps_only_four_items_per_category(self):
        with self.app.app_context():
            seed_database()
            for category in ['chocolate', 'vanilla', 'strawberry', 'butterscotch', 'mango', 'black-currant', 'sundaes']:
                self.assertLessEqual(
                    Product.query.filter_by(category_slug=category).count(),
                    4,
                    f'{category} should have at most 4 products after seeding.'
                )

    def test_admin_can_update_product(self):
        login_response = self.client.post(
            '/login',
            data={'email': 'admin@sweetscoop.com', 'password': 'admin123'},
            follow_redirects=True,
        )
        self.assertIn(login_response.status_code, (200, 302))

        response = self.client.post(
            f'/admin/products/update/{self.product_id}',
            data={
                'name': 'Updated Flavour',
                'description': 'Freshly updated flavour description',
                'category_slug': 'vanilla',
                'price_small': '450.00',
                'price_medium': '560.00',
                'price_large': '700.00',
                'image_url': '/static/images/vanilla.jpg',
                'ingredients': 'Cream, Vanilla Bean, Sugar',
                'is_popular': 'on',
                'is_special_offer': 'on',
                'discount_percent': '15',
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            product = db.session.get(Product, self.product_id)
            self.assertEqual(product.name, 'Updated Flavour')
            self.assertEqual(product.category_slug, 'vanilla')
            self.assertEqual(product.price_small, 450.00)
            self.assertTrue(product.is_popular)
            self.assertTrue(product.is_special_offer)
            self.assertEqual(product.discount_percent, 15)

    def test_admin_can_upload_new_flavour_image(self):
        login_response = self.client.post(
            '/login',
            data={'email': 'admin@sweetscoop.com', 'password': 'admin123'},
            follow_redirects=True,
        )
        self.assertIn(login_response.status_code, (200, 302))

        image = io.BytesIO(b'fake-image-data')
        image.name = 'flavour.jpg'

        response = self.client.post(
            f'/admin/products/update/{self.product_id}',
            data={
                'name': 'Image Updated Flavour',
                'description': 'Updated with new image',
                'category_slug': 'strawberry',
                'price_small': '410.00',
                'price_medium': '520.00',
                'price_large': '650.00',
                'ingredients': 'Cream, Strawberry',
                'discount_percent': '12',
                'image': (image, 'flavour.jpg'),
            },
            content_type='multipart/form-data',
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            product = db.session.get(Product, self.product_id)
            self.assertEqual(product.name, 'Image Updated Flavour')
            self.assertIn('/static/images/uploads/', product.image_url)
            self.assertEqual(product.discount_percent, 12)
            # Track for cleanup
            uploaded_filename = os.path.basename(product.image_url.split('?')[0])
            self.created_upload_files.append(uploaded_filename)

    def test_image_url_is_cache_busted(self):
        cached_url = cache_bust_url('/static/images/chocolate.jpg', 42)
        self.assertIn('/static/images/chocolate.jpg', cached_url)
        self.assertIn('v=42', cached_url)

    def test_place_order_stores_product_image_for_receipt(self):
        with self.app.app_context():
            product = Product(
                name='Receipt Image Flavour',
                description='Decorated for receipts',
                category_slug='chocolate',
                price_small=250.0,
                price_medium=350.0,
                price_large=450.0,
                image_url='/static/images/vanilla.jpg',
                ingredients='Cream, Vanilla',
            )
            db.session.add(product)
            db.session.commit()
            product_id = product.id

        response = self.client.post(
            '/place-order',
            json={
                'customer_name': 'Receipt Tester',
                'mobile_number': '9876543210',
                'address': 'Test Street 123',
                'payment_option': 'COD',
                'coupon_code': '',
                'cart_items': [{
                    'id': product_id,
                    'name': 'Receipt Image Flavour',
                    'size': 'Regular',
                    'quantity': 2,
                    'price': 250.0,
                    'image': '/static/images/vanilla.jpg',
                }],
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])

        with self.app.app_context():
            created_order = db.session.query(Order).filter_by(customer_name='Receipt Tester').order_by(Order.id.desc()).first()
            self.assertIsNotNone(created_order)
            self.assertTrue(created_order.items)
            self.assertEqual(created_order.items[0].image_url, '/static/images/vanilla.jpg')


if __name__ == '__main__':
    unittest.main()
