import os
import random
import datetime
from urllib.parse import parse_qsl, urlencode
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sweet_scoop_super_secret_key_2026_ice_cream'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sweet_scoop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==============================================================================
# DATABASE MODELS
# ==============================================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='customer')  # 'customer' or 'admin'
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(10), default='🍨')
    slug = db.Column(db.String(50), nullable=False, unique=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category_slug = db.Column(db.String(50), nullable=False)
    price_small = db.Column(db.Float, nullable=False)   # Regular 1-scoop
    price_medium = db.Column(db.Float, nullable=False)  # Double scoop
    price_large = db.Column(db.Float, nullable=False)   # Waffle bowl extra
    image_url = db.Column(db.String(255), nullable=False)
    is_popular = db.Column(db.Boolean, default=False)
    is_special_offer = db.Column(db.Boolean, default=False)
    discount_percent = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=4.8)
    review_count = db.Column(db.Integer, default=12)
    ingredients = db.Column(db.String(255), default='Pure Cream, Organic Milk, Natural Extracts')
    is_available = db.Column(db.Boolean, default=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_code = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    customer_name = db.Column(db.String(100), nullable=False)
    mobile_number = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    payment_option = db.Column(db.String(50), nullable=False)  # 'COD', 'Card', 'UPI'
    subtotal = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, default=0.0)
    total_price = db.Column(db.Float, nullable=False)
    coupon_code = db.Column(db.String(30), nullable=True)
    status = db.Column(db.String(30), default='Pending')  # 'Pending', 'Preparing', 'Out for Delivery', 'Delivered', 'Cancelled'
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    size = db.Column(db.String(20), nullable=False)  # 'Regular', 'Medium', 'Large'
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_name = db.Column(db.String(80), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    discount_percent = db.Column(db.Integer, nullable=False)
    min_amount = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Unread')  # 'Unread', 'Read'
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)




# ==============================================================================
# DECORATORS & HELPERS
# ==============================================================================

def get_current_user():
    if 'user_id' in session:
        return db.session.get(User, session['user_id'])
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user.role != 'admin':
            flash('Access restricted to store administrators.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_global_vars():
    return dict(current_user=get_current_user(), cache_bust_url=cache_bust_url)

# ==============================================================================
# FILE UPLOAD HELPERS
# ==============================================================================

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'images', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


def cache_bust_url(url, version=None):
    if not url:
        return url

    if version is None:
        version = int(datetime.datetime.now(datetime.UTC).timestamp() * 1000)

    base_url, _, query_string = url.partition('?')
    params = parse_qsl(query_string, keep_blank_values=True)
    filtered_params = [(key, value) for key, value in params if key != 'v']
    filtered_params.append(('v', str(version)))
    return f"{base_url}?{urlencode(filtered_params)}"


def save_uploaded_image(file_storage):
    if not file_storage or file_storage.filename == '':
        return None

    filename = secure_filename(file_storage.filename)
    if not filename:
        return None

    extension = os.path.splitext(filename)[1].lower()
    allowed = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    if extension not in allowed:
        return None

    unique_name = f"{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d%H%M%S%f')}_{filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file_storage.save(file_path)
    uploaded_url = f"/static/images/uploads/{unique_name}"
    return cache_bust_url(uploaded_url, int(datetime.datetime.now(datetime.UTC).timestamp() * 1000))


def trim_products_to_four_per_category(max_per_category=4, keep_ids=None):
    keep_ids = set(keep_ids or [])

    for category in Category.query.filter(Category.slug != 'all').all():
        products = Product.query.filter_by(category_slug=category.slug).order_by(Product.id.asc()).all()
        extra_products = [p for p in products if p.id not in keep_ids]

        if len(extra_products) > max_per_category:
            for product in extra_products[max_per_category:]:
                db.session.delete(product)

    db.session.commit()


def ensure_db_schema():
    inspector = db.inspect(db.engine)
    if 'order_item' not in inspector.get_table_names():
        return

    columns = [column['name'] for column in inspector.get_columns('order_item')]
    if 'image_url' not in columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE order_item ADD COLUMN image_url VARCHAR(255)"))


# ==============================================================================
# DATABASE SEEDING
# ==============================================================================

def seed_database():
    db.create_all()
    ensure_db_schema()
    
    # 1. Categories
    if Category.query.count() == 0:
        categories = [
            Category(name='All Flavours', icon='✨', slug='all'),
            Category(name='Chocolate', icon='🍫', slug='chocolate'),
            Category(name='Vanilla', icon='🍨', slug='vanilla'),
            Category(name='Strawberry', icon='🍓', slug='strawberry'),
            Category(name='Butterscotch', icon='🍯', slug='butterscotch'),
            Category(name='Mango', icon='🥭', slug='mango'),
            Category(name='Black Currant', icon='🍇', slug='black-currant'),
            Category(name='Special Sundaes', icon='🍧', slug='sundaes')
        ]
        db.session.bulk_save_objects(categories)
        db.session.commit()

    # 2. Products (8 items per category x 7 categories = 56 total items with UNIQUE images)
    if Product.query.count() == 0 or Product.query.first().image_url.startswith('http'):
        Product.query.delete()
        db.session.commit()

        products = [
            # ================= CHOCOLATE (8 Items) =================
            Product(
                name='Belgian Dark Chocolate Fudge',
                description='Rich 70% dark Belgian cocoa blended into velvety cream, topped with roasted hazelnuts and thick hot fudge drizzle.',
                category_slug='chocolate',
                price_small=399.00, price_medium=559.00, price_large=719.00,
                image_url='/static/images/chocolate.jpg',
                is_popular=True, is_special_offer=True, discount_percent=15,
                rating=4.9, review_count=48,
                ingredients='Dark Cocoa, Milk, Cream, Roasted Hazelnuts, Cane Sugar'
            ),
            Product(
                name='Double Choco Chip Cookie Dough',
                description='Rich milk chocolate churned with soft cookie dough chunks and bittersweet chocolate drops.',
                category_slug='chocolate',
                price_small=349.00, price_medium=499.00, price_large=649.00,
                image_url='/static/images/chocolate.jpg',
                is_popular=True, is_special_offer=False, discount_percent=0,
                rating=4.8, review_count=36,
                ingredients='Milk Chocolate, Cookie Dough, Dark Choco Chips, Whole Milk'
            ),
            Product(
                name='Triple Chocolate Lava Overload',
                description='Dark, milk & white chocolate swirls with liquid lava fudge center and cocoa nibs.',
                category_slug='chocolate',
                price_small=429.00, price_medium=589.00, price_large=749.00,
                image_url='/static/images/chocolate.jpg',
                is_popular=False, is_special_offer=True, discount_percent=20,
                rating=4.9, review_count=55,
                ingredients='Dark Cocoa, White Chocolate Swirl, Lava Fudge, Cream'
            ),
            Product(
                name='Nutella Ferrero Rocher Crunch',
                description='Creamy Nutella scoop with crushed Ferrero Rocher & toasted hazelnut praline.',
                category_slug='chocolate',
                price_small=459.00, price_medium=629.00, price_large=799.00,
                image_url='/static/images/chocolate.jpg',
                is_popular=True, is_special_offer=False, discount_percent=0,
                rating=5.0, review_count=72,
                ingredients='Hazelnut Spread, Crushed Ferrero, Cocoa, Cream, Sugar'
            ),
            Product(
                name='Dark Chocolate Garden Mint Crisp',
                description='Refreshing organic garden mint gelato churned with 70% dark Belgian chocolate shards and crispy cocoa nibs.',
                category_slug='chocolate',
                price_small=379.00, price_medium=529.00, price_large=679.00,
                image_url='/static/images/chocolate.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.7, review_count=28,
                ingredients='Fresh Organic Mint, 70% Dark Chocolate Shards, Cocoa Butter, Double Cream, Peppermint Extract'
            ),
            Product(
                name='Chocolate Silk Brownie Fudge',
                description='Silky chocolate ice cream with soft fudge brownie bites & chocolate syrup stream.',
                category_slug='chocolate',
                price_small=389.00, price_medium=549.00, price_large=699.00,
                image_url='/static/images/chocolate.jpg',
                is_popular=True, is_special_offer=True, discount_percent=10,
                rating=4.8, review_count=44,
                ingredients='Fudge Brownie Bites, Chocolate Syrup, Double Cream'
            ),
            Product(
                name='Swiss White Chocolate Raspberry',
                description='Creamy Swiss white chocolate scoop folded with sweet red raspberry swirls.',
                category_slug='chocolate',
                price_small=419.00, price_medium=579.00, price_large=739.00,
                image_url='/static/images/chocolate.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.8, review_count=31,
                ingredients='Swiss White Cocoa, Red Raspberry Coulis, Milk, Sugar'
            ),
            Product(
                name='Choco Peanut Butter Cup Crunch',
                description='Roasted peanut butter swirl folded into dark cocoa cream with mini peanut cups.',
                category_slug='chocolate',
                price_small=369.00, price_medium=519.00, price_large=669.00,
                image_url='/static/images/chocolate.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.6, review_count=23,
                ingredients='Peanut Butter Swirl, Mini Choco Cups, Cream, Cocoa'
            ),

            # ================= VANILLA (8 Items) =================
            Product(
                name='Madagascar Bourbon Vanilla Bean',
                description='Classic French-style vanilla ice cream infused with real Madagascar vanilla pod speckles and warm caramel swirl.',
                category_slug='vanilla',
                price_small=319.00, price_medium=479.00, price_large=599.00,
                image_url='/static/images/vanilla.jpg',
                is_popular=True, is_special_offer=False, discount_percent=0,
                rating=4.8, review_count=35,
                ingredients='Madagascar Vanilla Beans, Fresh Cream, Egg Yolk, Sugar'
            ),
            Product(
                name='French Vanilla Bean Salted Caramel',
                description='Rich custard-style French vanilla with golden salted caramel ribbon stream.',
                category_slug='vanilla',
                price_small=329.00, price_medium=489.00, price_large=619.00,
                image_url='/static/images/vanilla.jpg',
                is_popular=True, is_special_offer=True, discount_percent=10,
                rating=4.9, review_count=42,
                ingredients='French Custard Vanilla, Salted Caramel Ribbon, Cream'
            ),
            Product(
                name='Vanilla Bean Cinnamon Roll Swirl',
                description='Sweet vanilla scoop infused with cinnamon sugar swirl and pastry dough bites.',
                category_slug='vanilla',
                price_small=349.00, price_medium=499.00, price_large=639.00,
                image_url='/static/images/vanilla.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.7, review_count=19,
                ingredients='Vanilla Custard, Cinnamon Sugar, Pastry Bites, Cream'
            ),
            Product(
                name='Classic Vanilla Waffle Cone Crunch',
                description='Pure cream vanilla paired with crushed golden waffle cone crisp.',
                category_slug='vanilla',
                price_small=299.00, price_medium=439.00, price_large=569.00,
                image_url='/static/images/vanilla.jpg',
                is_popular=False, is_special_offer=True, discount_percent=15,
                rating=4.6, review_count=27,
                ingredients='Sweet Cream Vanilla, Waffle Cone Crisps, Caramel Drizzle'
            ),
            Product(
                name='Vanilla Salted Pretzel Toffee',
                description='Vanilla bean scoop with crunchy salted pretzel clusters & butter caramel.',
                category_slug='vanilla',
                price_small=369.00, price_medium=519.00, price_large=659.00,
                image_url='/static/images/vanilla.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.8, review_count=33,
                ingredients='Vanilla Cream, Salted Pretzel Clusters, Butter Toffee'
            ),
            Product(
                name='Vanilla Almond Honeycomb Brittle',
                description='Churned vanilla cream studded with crunchy honey-almond brittle.',
                category_slug='vanilla',
                price_small=379.00, price_medium=539.00, price_large=679.00,
                image_url='/static/images/vanilla.jpg',
                is_popular=True, is_special_offer=False, discount_percent=0,
                rating=4.9, review_count=46,
                ingredients='Vanilla Pods, Honey Almond Brittle, Whole Milk, Cream'
            ),
            Product(
                name='Vanilla Bean Macadamia Supreme',
                description='Smooth vanilla with roasted buttery macadamia nuts & white choc swirl.',
                category_slug='vanilla',
                price_small=419.00, price_medium=579.00, price_large=729.00,
                image_url='/static/images/vanilla.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.8, review_count=25,
                ingredients='Vanilla Cream, Roasted Macadamia Nuts, White Chocolate'
            ),
            Product(
                name='Tahitian Vanilla Blackberry Compote',
                description='Aromatic Tahitian vanilla infused with wild blackberry compote.',
                category_slug='vanilla',
                price_small=359.00, price_medium=509.00, price_large=649.00,
                image_url='/static/images/vanilla.jpg',
                is_popular=False, is_special_offer=True, discount_percent=12,
                rating=4.7, review_count=30,
                ingredients='Tahitian Vanilla Beans, Wild Blackberry Swirl, Cream'
            ),

            # ================= STRAWBERRY (8 Items) =================
            Product(
                name='Fresh Garden Strawberry Bliss',
                description='Real farm-picked strawberries churned into luscious pink ice cream with actual fruit chunks and sweet berry drizzle.',
                category_slug='strawberry',
                price_small=359.00, price_medium=519.00, price_large=639.00,
                image_url='/static/images/strawberry.jpg',
                is_popular=True, is_special_offer=True, discount_percent=10,
                rating=4.7, review_count=29,
                ingredients='Fresh Strawberries, Strawberry Puree, Cream, Whole Milk'
            ),
            Product(
                name='Strawberry Shortcake Cookie Crunch',
                description='Creamy strawberry scoop mixed with yellow sponge cake bites and sweet crumb.',
                category_slug='strawberry',
                price_small=379.00, price_medium=539.00, price_large=679.00,
                image_url='/static/images/strawberry.jpg',
                is_popular=True, is_special_offer=False, discount_percent=0,
                rating=4.8, review_count=41,
                ingredients='Strawberry Ice Cream, Sponge Cake Chunks, Cookie Crumb'
            ),
            Product(
                name='Wild Strawberry Cheesecake Swirl',
                description='Cream cheese gelato layered with sweet strawberry jam & graham crust.',
                category_slug='strawberry',
                price_small=399.00, price_medium=569.00, price_large=719.00,
                image_url='/static/images/strawberry.jpg',
                is_popular=True, is_special_offer=True, discount_percent=15,
                rating=4.9, review_count=58,
                ingredients='Cream Cheese Gelato, Strawberry Jam, Graham Crust'
            ),
            Product(
                name='Strawberry Dark Chocolate Flake',
                description='Ripe strawberry ice cream folded with bittersweet dark chocolate flakes.',
                category_slug='strawberry',
                price_small=389.00, price_medium=549.00, price_large=699.00,
                image_url='/static/images/strawberry.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.7, review_count=22,
                ingredients='Ripe Strawberry Cream, Bittersweet Chocolate Flakes'
            ),
            Product(
                name='Organic Strawberry Lemonade Sorbet',
                description='Zesty lemonade sorbet swirled with fresh organic strawberry puree.',
                category_slug='strawberry',
                price_small=329.00, price_medium=469.00, price_large=599.00,
                image_url='/static/images/strawberry.jpg',
                is_popular=False, is_special_offer=True, discount_percent=20,
                rating=4.6, review_count=18,
                ingredients='Strawberry Puree, Fresh Lemon Juice, Cane Sugar, Mint'
            ),
            Product(
                name='Strawberry Banana Smoothie Twist',
                description='Fresh banana cream blended with sweet strawberry swirl stream.',
                category_slug='strawberry',
                price_small=349.00, price_medium=499.00, price_large=629.00,
                image_url='/static/images/strawberry.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.8, review_count=37,
                ingredients='Fresh Banana Cream, Sweet Strawberry Coulis, Milk'
            ),
            Product(
                name='Strawberry Coconut Milk Delight',
                description='Tropical coconut milk ice cream folded with sun-ripened strawberry compote.',
                category_slug='strawberry',
                price_small=369.00, price_medium=519.00, price_large=659.00,
                image_url='/static/images/strawberry.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.7, review_count=26,
                ingredients='Organic Coconut Milk, Sun-Ripened Strawberry Puree'
            ),
            Product(
                name='Romanoff Strawberry & White Choco',
                description='Vanilla-strawberry scoop tossed with white chocolate shavings & berry syrup.',
                category_slug='strawberry',
                price_small=409.00, price_medium=579.00, price_large=729.00,
                image_url='/static/images/strawberry.jpg',
                is_popular=True, is_special_offer=False, discount_percent=0,
                rating=4.9, review_count=50,
                ingredients='Strawberry Ice Cream, White Chocolate Shavings, Syrup'
            ),

            # ================= BUTTERSCOTCH (8 Items) =================
            Product(
                name='Golden Butterscotch Caramel Crunch',
                description='Rich butter-caramel scoop filled with crispy praline nut crunch and warm butterscotch syrup stream.',
                category_slug='butterscotch',
                price_small=379.00, price_medium=539.00, price_large=679.00,
                image_url='/static/images/butterscotch.jpg',
                is_popular=True, is_special_offer=False, discount_percent=0,
                rating=4.9, review_count=52,
                ingredients='Brown Butter, Caramel, Cashew Praline, Double Cream'
            ),
            Product(
                name='Smokey Salted Butterscotch Praline',
                description='Deep brown sugar butterscotch churned with sea salt caramel and almond praline.',
                category_slug='butterscotch',
                price_small=399.00, price_medium=559.00, price_large=709.00,
                image_url='/static/images/butterscotch.jpg',
                is_popular=True, is_special_offer=True, discount_percent=10,
                rating=4.9, review_count=47,
                ingredients='Brown Sugar Butterscotch, Sea Salt Caramel, Almond Praline'
            ),
            Product(
                name='Butterscotch Roasted Cashew Crunch',
                description='Smooth butterscotch ice cream packed with slow-roasted salted cashews.',
                category_slug='butterscotch',
                price_small=369.00, price_medium=519.00, price_large=669.00,
                image_url='/static/images/butterscotch.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.8, review_count=39,
                ingredients='Butterscotch Cream, Roasted Salted Cashews, Caramel'
            ),
            Product(
                name='Butterscotch Pecan Pie Deluxe',
                description='Creamy butterscotch infused with toasted pecan nuts and brown sugar crumble.',
                category_slug='butterscotch',
                price_small=429.00, price_medium=589.00, price_large=749.00,
                image_url='/static/images/butterscotch.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.8, review_count=24,
                ingredients='Butterscotch Gelato, Toasted Pecans, Brown Sugar Crust'
            ),
            Product(
                name='Butterscotch Brownie Fudge Ripple',
                description='Rich butterscotch base with dark chocolate fudge brownie cubes.',
                category_slug='butterscotch',
                price_small=389.00, price_medium=549.00, price_large=699.00,
                image_url='/static/images/butterscotch.jpg',
                is_popular=True, is_special_offer=True, discount_percent=15,
                rating=4.9, review_count=43,
                ingredients='Butterscotch Base, Dark Choco Brownie, Hot Fudge'
            ),
            Product(
                name='Golden Honeycomb Butterscotch',
                description='Old-fashioned butterscotch ice cream filled with crunchy honey honeycomb sponge.',
                category_slug='butterscotch',
                price_small=359.00, price_medium=509.00, price_large=649.00,
                image_url='/static/images/butterscotch.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.7, review_count=21,
                ingredients='Old-fashioned Butterscotch, Honeycomb Crunch, Cream'
            ),
            Product(
                name='Canadian Maple Butterscotch Walnut',
                description='Canadian maple syrup infused butterscotch with roasted English walnuts.',
                category_slug='butterscotch',
                price_small=419.00, price_medium=579.00, price_large=729.00,
                image_url='/static/images/butterscotch.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.8, review_count=30,
                ingredients='Maple Syrup, Butterscotch, Roasted English Walnuts'
            ),
            Product(
                name='Royal English Toffee Butterscotch',
                description='English butter toffee bits folded into velvet butterscotch cream.',
                category_slug='butterscotch',
                price_small=349.00, price_medium=499.00, price_large=639.00,
                image_url='/static/images/butterscotch.jpg',
                is_popular=False, is_special_offer=True, discount_percent=12,
                rating=4.7, review_count=28,
                ingredients='English Butter Toffee Bits, Velvet Butterscotch Cream'
            ),

            # ================= MANGO (8 Items) =================
            Product(
                name='Alphonso Mango Sorbet Delight',
                description='Refreshing tropical sorbet made from 100% natural Alphonso mango pulp, garnished with juicy mango cubes and mint.',
                category_slug='mango',
                price_small=359.00, price_medium=519.00, price_large=639.00,
                image_url='/static/images/mango.jpg',
                is_popular=False, is_special_offer=True, discount_percent=20,
                rating=4.8, review_count=41,
                ingredients='Alphonso Mango Pulp, Fresh Lime Juice, Organic Honey'
            ),
            Product(
                name='Mango Passion Fruit Swirl',
                description='Tropical Alphonso mango gelato swirled with tangy passion fruit ribbon.',
                category_slug='mango',
                price_small=379.00, price_medium=539.00, price_large=679.00,
                image_url='/static/images/mango.jpg',
                is_popular=True, is_special_offer=False, discount_percent=0,
                rating=4.9, review_count=45,
                ingredients='Alphonso Mango Gelato, Tangy Passion Fruit Ribbon'
            ),
            Product(
                name='Royal Mango Kulfi Pistachio',
                description='Traditional Indian kulfi style mango ice cream with cardamom & pistachio bits.',
                category_slug='mango',
                price_small=399.00, price_medium=559.00, price_large=709.00,
                image_url='/static/images/mango.jpg',
                is_popular=True, is_special_offer=True, discount_percent=10,
                rating=4.9, review_count=62,
                ingredients='Indian Mango Kulfi, Cardamom, Roasted Pistachio'
            ),
            Product(
                name='Dairy-Free Mango Coconut Cream',
                description='Dairy-free coconut milk ice cream blended with sweet ripe mango compote.',
                category_slug='mango',
                price_small=349.00, price_medium=499.00, price_large=629.00,
                image_url='/static/images/mango.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.7, review_count=29,
                ingredients='Coconut Milk Cream, Fresh Alphonso Mango Pulp'
            ),
            Product(
                name='Mango Cheesecake Cookie Crumble',
                description='Creamy cheese ice cream swirled with thick Alphonso mango reduction & cookie crumble.',
                category_slug='mango',
                price_small=419.00, price_medium=579.00, price_large=729.00,
                image_url='/static/images/mango.jpg',
                is_popular=True, is_special_offer=False, discount_percent=0,
                rating=4.9, review_count=51,
                ingredients='Cream Cheese Gelato, Alphonso Mango Coulis, Cookies'
            ),
            Product(
                name='Mango Raspberry White Choco',
                description='Sweet mango scoop with tart red raspberry drizzle and white chocolate chips.',
                category_slug='mango',
                price_small=389.00, price_medium=549.00, price_large=699.00,
                image_url='/static/images/mango.jpg',
                is_popular=False, is_special_offer=True, discount_percent=15,
                rating=4.8, review_count=34,
                ingredients='Ripe Mango Scoop, Red Raspberry Jam, White Choco Chips'
            ),
            Product(
                name='Spiced Mango Chili Lime Sorbet',
                description='Zesty Alphonso mango sorbet infused with a hint of red chili and fresh lime.',
                category_slug='mango',
                price_small=329.00, price_medium=469.00, price_large=599.00,
                image_url='/static/images/mango.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.6, review_count=20,
                ingredients='Mango Pulp, Fresh Lime Juice, Red Chili Flakes'
            ),
            Product(
                name='Mango Pineapple Sunshine Gelato',
                description='Sun-drenched mango and pineapple fruit chunks churned in sweet cream.',
                category_slug='mango',
                price_small=369.00, price_medium=519.00, price_large=659.00,
                image_url='/static/images/mango.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.7, review_count=27,
                ingredients='Sun Mango Pulp, Crushed Pineapple Chunks, Sweet Cream'
            ),

            # ================= BLACK CURRANT (8 Items) =================
            Product(
                name='Royal Velvet Black Currant Berry',
                description='Deep violet berries blended into tangy-sweet velvety cream, packed with dark currant chunks and forest blueberries.',
                category_slug='black-currant',
                price_small=399.00, price_medium=559.00, price_large=719.00,
                image_url='/static/images/blackcurrant.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.9, review_count=38,
                ingredients='Black Currants, Blueberries, Cream, Pure Cane Sugar'
            ),
            Product(
                name='Black Currant Cheesecake Swirl',
                description='Tangy black currant ice cream with rich cheesecake swirls and graham dust.',
                category_slug='black-currant',
                price_small=419.00, price_medium=579.00, price_large=739.00,
                image_url='/static/images/blackcurrant.jpg',
                is_popular=True, is_special_offer=True, discount_percent=10,
                rating=4.9, review_count=49,
                ingredients='Tangy Black Currant Jam, Cream Cheese, Graham Crumb'
            ),
            Product(
                name='Black Currant Dark Choco Truffle',
                description='Black currant berry cream studded with dark chocolate truffle chunks.',
                category_slug='black-currant',
                price_small=429.00, price_medium=589.00, price_large=749.00,
                image_url='/static/images/blackcurrant.jpg',
                is_popular=True, is_special_offer=False, discount_percent=0,
                rating=4.9, review_count=53,
                ingredients='Black Currant Cream, Bittersweet Choco Truffles'
            ),
            Product(
                name='Chilled Black Currant Garden Mint Sorbet',
                description='Chilled black currant fruit sorbet infused with crushed garden mint leaves.',
                category_slug='black-currant',
                price_small=339.00, price_medium=479.00, price_large=609.00,
                image_url='/static/images/blackcurrant.jpg',
                is_popular=False, is_special_offer=True, discount_percent=15,
                rating=4.6, review_count=19,
                ingredients='Black Currant Fruit Puree, Crushed Mint, Lime'
            ),
            Product(
                name='Black Currant Almond Crunch',
                description='Dark purple berry scoop filled with roasted slivered almonds & berry jam.',
                category_slug='black-currant',
                price_small=389.00, price_medium=549.00, price_large=699.00,
                image_url='/static/images/blackcurrant.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.8, review_count=32,
                ingredients='Dark Purple Berry Base, Roasted Slivered Almonds'
            ),
            Product(
                name='Black Currant Vanilla Bean Ripple',
                description='Creamy Madagascar vanilla swirled with concentrated black currant reduction.',
                category_slug='black-currant',
                price_small=359.00, price_medium=509.00, price_large=649.00,
                image_url='/static/images/blackcurrant.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.7, review_count=25,
                ingredients='Madagascar Vanilla Cream, Black Currant Reduction'
            ),
            Product(
                name='Black Currant Sweet Plum Sorbet',
                description='Tart black currant berries blended with sweet red plum puree.',
                category_slug='black-currant',
                price_small=349.00, price_medium=489.00, price_large=629.00,
                image_url='/static/images/blackcurrant.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.7, review_count=21,
                ingredients='Black Currant Puree, Sweet Red Plum Reduction'
            ),
            Product(
                name='Black Currant White Chocolate Chip',
                description='Smooth berry scoop loaded with sweet white chocolate chips.',
                category_slug='black-currant',
                price_small=379.00, price_medium=529.00, price_large=679.00,
                image_url='/static/images/blackcurrant.jpg',
                is_popular=False, is_special_offer=True, discount_percent=12,
                rating=4.8, review_count=36,
                ingredients='Velvet Currant Cream, Sweet White Chocolate Chips'
            ),

            # ================= SPECIAL SUNDAES (8 Items) =================
            Product(
                name='Sweet Scoop Supreme Sundae',
                description='Triple scoop spectacular featuring Chocolate, Vanilla & Strawberry scoops with waffle sticks, nuts, cherry and whipped cream.',
                category_slug='sundaes',
                price_small=559.00, price_medium=719.00, price_large=879.00,
                image_url='/static/images/sundaes.jpg',
                is_popular=True, is_special_offer=True, discount_percent=15,
                rating=5.0, review_count=64,
                ingredients='Assorted Scoops, Chocolate Sauce, Whipped Cream, Cherry'
            ),
            Product(
                name='Chocolate Fudge Brownie Explosion Sundae',
                description='Double chocolate scoops topped with warm brownies, hot fudge & choco chips.',
                category_slug='sundaes',
                price_small=529.00, price_medium=689.00, price_large=849.00,
                image_url='/static/images/sundaes.jpg',
                is_popular=True, is_special_offer=False, discount_percent=0,
                rating=4.9, review_count=57,
                ingredients='Double Choco Scoops, Fudgy Brownies, Hot Fudge'
            ),
            Product(
                name='Royal Nutty Caramel Delight Sundae',
                description='Butterscotch & vanilla scoops layered with caramel, roasted almonds, cashews & pecans.',
                category_slug='sundaes',
                price_small=499.00, price_medium=659.00, price_large=819.00,
                image_url='/static/images/sundaes.jpg',
                is_popular=True, is_special_offer=False, discount_percent=0,
                rating=4.9, review_count=50,
                ingredients='Butterscotch & Vanilla Scoops, Roasted Cashews, Pecans'
            ),
            Product(
                name='Berry Blast Waffle Bowl Sundae',
                description='Strawberry & black currant scoops in a fresh waffle bowl with berry coulis & cream.',
                category_slug='sundaes',
                price_small=479.00, price_medium=639.00, price_large=799.00,
                image_url='/static/images/sundaes.jpg',
                is_popular=False, is_special_offer=True, discount_percent=10,
                rating=4.8, review_count=43,
                ingredients='Strawberry & Black Currant Scoops, Waffle Bowl, Cream'
            ),
            Product(
                name='Tropical Mango Passion Fruit Sundae',
                description='Mango sorbet & vanilla scoops with fresh fruit slices, passion fruit & toasted coconut.',
                category_slug='sundaes',
                price_small=469.00, price_medium=629.00, price_large=789.00,
                image_url='/static/images/sundaes.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.8, review_count=39,
                ingredients='Mango Sorbet, Fresh Mango Chunks, Passion Coulis'
            ),
            Product(
                name='Classic Banana Split Royale Sundae',
                description='Classic fresh banana split with chocolate, vanilla & strawberry scoops, cherries & syrup.',
                category_slug='sundaes',
                price_small=519.00, price_medium=679.00, price_large=839.00,
                image_url='/static/images/sundaes.jpg',
                is_popular=True, is_special_offer=True, discount_percent=12,
                rating=4.9, review_count=61,
                ingredients='Fresh Banana Split, Choco Vanilla Strawberry Scoops'
            ),
            Product(
                name='Ferrero Rocher Hazelnut Tower Sundae',
                description='Nutella scoop with Ferrero Rocher, roasted hazelnut crunch, chocolate sauce & wafer.',
                category_slug='sundaes',
                price_small=549.00, price_medium=709.00, price_large=869.00,
                image_url='/static/images/sundaes.jpg',
                is_popular=True, is_special_offer=False, discount_percent=0,
                rating=5.0, review_count=78,
                ingredients='Nutella Scoop, Ferrero Rocher, Wafer Stick, Choco Sauce'
            ),
            Product(
                name='Oreo Cookies & Cream Overload Sundae',
                description='Cookies & cream scoops topped with crushed Oreos, chocolate sauce & whipped cream.',
                category_slug='sundaes',
                price_small=489.00, price_medium=649.00, price_large=809.00,
                image_url='/static/images/sundaes.jpg',
                is_popular=False, is_special_offer=False, discount_percent=0,
                rating=4.8, review_count=46,
                ingredients='Cookies Cream Scoops, Crushed Oreos, Chocolate Drizzle'
            )
        ]
        db.session.bulk_save_objects(products)
        db.session.commit()

        # Keep only 4 featured items per category for a cleaner storefront.
        trim_products_to_four_per_category()

    else:
        trim_products_to_four_per_category()

    # 3. Default Users (Admin & Customer)
    if User.query.filter_by(role='admin').count() == 0:
        admin = User(username='Admin', email='admin@sweetscoop.com', role='admin')
        admin.set_password('admin123')
        
        customer = User(username='Sarah Jenkins', email='customer@example.com', role='customer')
        customer.set_password('customer123')
        
        db.session.add(admin)
        db.session.add(customer)
        db.session.commit()

    # 4. Coupons
    if Coupon.query.count() == 0:
        coupons = [
            Coupon(code='SCOOP10', discount_percent=10, min_amount=400.0),
            Coupon(code='FIRST20', discount_percent=20, min_amount=600.0),
            Coupon(code='SUMMER15', discount_percent=15, min_amount=500.0),
            Coupon(code='FRIEND25', discount_percent=25, min_amount=800.0),
            Coupon(code='TREAT30', discount_percent=30, min_amount=1000.0),
        ]
        db.session.bulk_save_objects(coupons)
        db.session.commit()

    # 5. Reviews
    if Review.query.count() == 0:
        sample_reviews = [
            Review(product_id=1, user_name='Emily R.', rating=5, comment='Absolute chocolate heaven! The dark fudge and hazelnut crunch combination is unmatched.'),
            Review(product_id=2, user_name='David K.', rating=5, comment='Super authentic vanilla taste with real vanilla bean seeds. My kid loved it!'),
            Review(product_id=4, user_name='Priya M.', rating=5, comment='The butterscotch praline crunch is so addictive. Packaging was crisp & fresh.')
        ]
        db.session.bulk_save_objects(sample_reviews)
        db.session.commit()


# ==============================================================================
# FRONTEND ROUTES
# ==============================================================================

@app.route('/')
def index():
    popular_products = Product.query.filter_by(is_popular=True, is_available=True).all()
    special_offers = Product.query.filter_by(is_special_offer=True, is_available=True).all()
    categories = Category.query.all()
    featured_reviews = Review.query.order_by(Review.id.desc()).limit(3).all()
    return render_template('index.html', 
                           popular_products=popular_products, 
                           special_offers=special_offers,
                           categories=categories,
                           reviews=featured_reviews)


@app.route('/menu')
def menu():
    category_slug = request.args.get('category', 'all')
    search_query = request.args.get('search', '').strip()
    
    # Retrieve all active products for the client-side filter
    products = Product.query.filter_by(is_available=True).all()
    categories = Category.query.all()
    
    return render_template('menu.html', 
                           products=products, 
                           categories=categories, 
                           selected_category=category_slug, 
                           search_query=search_query)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)
        
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.id.desc()).all()
    related_products = Product.query.filter(Product.id != product_id, Product.category_slug == product.category_slug).limit(3).all()
    if not related_products:
        related_products = Product.query.filter(Product.id != product_id).limit(3).all()
    return render_template('product_detail.html', product=product, reviews=reviews, related_products=related_products)


@app.route('/cart')
def cart():
    return render_template('cart.html')


@app.route('/checkout')
def checkout():
    return render_template('checkout.html')


@app.route('/place-order', methods=['POST'])
def place_order():
    data = request.get_json()
    if not data or not data.get('cart_items'):
        return jsonify({'success': False, 'message': 'Your cart is empty!'}), 400

    customer_name = data.get('customer_name')
    mobile_number = data.get('mobile_number')
    address = data.get('address')
    payment_option = data.get('payment_option', 'COD')
    coupon_code = data.get('coupon_code', '')
    cart_items = data.get('cart_items', [])

    if not customer_name or not mobile_number or not address:
        return jsonify({'success': False, 'message': 'Please fill in all customer details!'}), 400

    subtotal = 0.0
    order_items_objs = []

    for item in cart_items:
        p_id = item.get('id')
        size = item.get('size', 'Regular')
        qty = max(1, int(item.get('quantity', 1)))
        
        product = db.session.get(Product, p_id)
        if not product:
            continue
            
        unit_price = product.price_small
        if size == 'Medium':
            unit_price = product.price_medium
        elif size == 'Large':
            unit_price = product.price_large
        elif item.get('price'):
            unit_price = float(item.get('price'))

        item_subtotal = round(unit_price * qty, 2)
        subtotal += item_subtotal

        order_items_objs.append(OrderItem(
            product_id=product.id,
            product_name=product.name,
            image_url=product.image_url,
            size=size,
            unit_price=unit_price,
            quantity=qty,
            subtotal=item_subtotal
        ))

    subtotal = round(subtotal, 2)
    discount_amount = 0.0

    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code.upper(), is_active=True).first()
        if coupon and subtotal >= coupon.min_amount:
            discount_amount = round(subtotal * (coupon.discount_percent / 100.0), 2)

    total_price = round(max(0.0, subtotal - discount_amount), 2)

    # Generate unique order code e.g. SCOOP-8492
    order_code = f"SCOOP-{random.randint(1000, 9999)}"
    while Order.query.filter_by(order_code=order_code).first():
        order_code = f"SCOOP-{random.randint(1000, 9999)}"

    user = get_current_user()
    user_id = user.id if user else None

    new_order = Order(
        order_code=order_code,
        user_id=user_id,
        customer_name=customer_name,
        mobile_number=mobile_number,
        address=address,
        payment_option=payment_option,
        subtotal=subtotal,
        discount_amount=discount_amount,
        total_price=total_price,
        coupon_code=coupon_code.upper() if coupon_code else None,
        status='Pending',
        items=order_items_objs
    )

    db.session.add(new_order)
    db.session.commit()

    return jsonify({
        'success': True, 
        'order_code': order_code, 
        'message': 'Order placed successfully!'
    })


@app.route('/order-success/<order_code>')
def order_success(order_code):
    order = Order.query.filter_by(order_code=order_code).first()
    if not order:
        abort(404)
    return render_template('order_success.html', order=order)


@app.route('/track', methods=['GET', 'POST'])
def track():
    order = None
    searched_code = ''
    if request.method == 'POST':
        searched_code = request.form.get('order_code', '').strip().upper()
        if searched_code:
            order = Order.query.filter_by(order_code=searched_code).first()
            if not order:
                flash(f'No order found with code "{searched_code}". Please check your order ID.', 'warning')
    elif request.args.get('code'):
        searched_code = request.args.get('code').strip().upper()
        order = Order.query.filter_by(order_code=searched_code).first()

    return render_template('track.html', order=order, searched_code=searched_code)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        if not name or not email or not message:
            flash('Please complete all required form fields.', 'danger')
        else:
            new_msg = ContactMessage(name=name, email=email, subject=subject or 'General Inquiry', message=message)
            db.session.add(new_msg)
            db.session.commit()
            flash('Thank you for contacting Sweet Scoop! We will get back to you shortly.', 'success')
            return redirect(url_for('contact'))

    return render_template('contact.html')


# ==============================================================================
# AUTHENTICATION ROUTES
# ==============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Welcome back, {user.username}!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address is already registered.', 'warning')
            return render_template('register.html')

        new_user = User(username=username, email=email, role='customer')
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        session['username'] = new_user.username
        session['role'] = new_user.role

        flash('Registration successful! Welcome to Sweet Scoop family.', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/profile')
def profile():
    user = get_current_user()
    if not user:
        flash('Please login to view your order history & saved items.', 'info')
        return redirect(url_for('login'))

    user_orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    return render_template('profile.html', user=user, orders=user_orders)


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@app.route('/api/coupon/validate', methods=['POST'])
def validate_coupon():
    data = request.get_json()
    code = data.get('code', '').strip().upper()
    subtotal = float(data.get('subtotal', 0.0))

    coupon = Coupon.query.filter_by(code=code, is_active=True).first()
    if not coupon:
        return jsonify({'valid': False, 'message': 'Invalid or expired coupon code.'})

    if subtotal < coupon.min_amount:
        return jsonify({'valid': False, 'message': f'Coupon code {code} requires a minimum subtotal of ₹{coupon.min_amount:.2f}.'})

    discount_amount = round(subtotal * (coupon.discount_percent / 100.0), 2)
    final_total = round(max(0.0, subtotal - discount_amount), 2)

    return jsonify({
        'valid': True,
        'code': coupon.code,
        'discount_percent': coupon.discount_percent,
        'discount_amount': discount_amount,
        'final_total': final_total,
        'message': f'Coupon {coupon.code} applied! ({coupon.discount_percent}% off)'
    })


@app.route('/api/product/<int:product_id>/review', methods=['POST'])
def add_product_review(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404
        
    data = request.get_json()
    user_name = data.get('user_name', 'Ice Cream Lover')
    rating = int(data.get('rating', 5))
    comment = data.get('comment', '').strip()

    if not comment:
        return jsonify({'success': False, 'message': 'Please enter a review comment.'}), 400

    new_rev = Review(product_id=product_id, user_name=user_name, rating=rating, comment=comment)
    db.session.add(new_rev)
    db.session.commit()
    
    # Recalculate average rating accurately from database
    all_reviews = Review.query.filter_by(product_id=product_id).all()
    if all_reviews:
        total_ratings = sum([r.rating for r in all_reviews])
        new_count = len(all_reviews)
        product.rating = round(total_ratings / new_count, 1)
        product.review_count = new_count
        db.session.commit()

    return jsonify({
        'success': True, 
        'message': 'Review added successfully!', 
        'new_rating': product.rating, 
        'new_count': product.review_count
    })


# ==============================================================================
# ADMIN PORTAL ROUTES
# ==============================================================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='Pending').count()
    preparing_orders = Order.query.filter_by(status='Preparing').count()
    delivered_orders = Order.query.filter_by(status='Delivered').count()
    
    total_revenue = db.session.query(db.func.sum(Order.total_price)).filter(Order.status != 'Cancelled').scalar() or 0.0
    total_products = Product.query.count()
    unread_messages = ContactMessage.query.filter_by(status='Unread').count()
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_orders=total_orders,
                           pending_orders=pending_orders,
                           preparing_orders=preparing_orders,
                           delivered_orders=delivered_orders,
                           total_revenue=total_revenue,
                           total_products=total_products,
                           unread_messages=unread_messages,
                           recent_orders=recent_orders)


@app.route('/admin/orders')
@admin_required
def admin_orders():
    status_filter = request.args.get('status', 'all')
    if status_filter != 'all':
        orders = Order.query.filter_by(status=status_filter).order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.order_by(Order.created_at.desc()).all()
        
    return render_template('admin/orders.html', orders=orders, current_status=status_filter)


@app.route('/admin/order/update-status', methods=['POST'])
@admin_required
def admin_update_order_status():
    data = request.get_json()
    if not data or not data.get('order_id'):
        return jsonify({'success': False, 'message': 'Missing order_id'}), 400

    order_id = int(data.get('order_id'))
    new_status = data.get('status', 'Pending')

    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404

    order.status = new_status
    db.session.commit()
    return jsonify({'success': True, 'message': f'Order {order.order_code} updated to {new_status}'})


@app.route('/admin/products', methods=['GET', 'POST'])
@admin_required
def admin_products():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category_slug = request.form.get('category_slug')
        price_small = float(request.form.get('price_small') or 319.0)
        price_medium = float(request.form.get('price_medium') or 479.0)
        price_large = float(request.form.get('price_large') or 639.0)
        ingredients = request.form.get('ingredients', 'Cream, Milk, Sugar')
        is_popular = True if request.form.get('is_popular') == 'on' else False
        is_special_offer = True if request.form.get('is_special_offer') == 'on' else False
        discount_percent = int(request.form.get('discount_percent') or 0)

        uploaded_image_url = request.form.get('image_url')
        if 'image' in request.files and request.files['image'].filename:
            uploaded_image_url = save_uploaded_image(request.files['image']) or uploaded_image_url
        if not uploaded_image_url:
            uploaded_image_url = '/static/images/hero.jpg'

        new_prod = Product(
            name=name,
            description=description,
            category_slug=category_slug,
            price_small=price_small,
            price_medium=price_medium,
            price_large=price_large,
            image_url=uploaded_image_url,
            ingredients=ingredients,
            is_popular=is_popular,
            is_special_offer=is_special_offer,
            discount_percent=discount_percent
        )
        db.session.add(new_prod)
        db.session.commit()
        trim_products_to_four_per_category(keep_ids={new_prod.id})
        flash(f'New flavor "{name}" added to inventory!', 'success')
        return redirect(url_for('admin_products'))

    products = Product.query.order_by(Product.id.desc()).all()
    categories = Category.query.all()
    return render_template('admin/products.html', products=products, categories=categories)


@app.route('/admin/products/update/<int:product_id>', methods=['POST'])
@admin_required
def admin_update_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('admin_products'))

    product.name = request.form.get('name') or product.name
    product.description = request.form.get('description') or product.description
    product.category_slug = request.form.get('category_slug') or product.category_slug
    product.price_small = float(request.form.get('price_small') or product.price_small)
    product.price_medium = float(request.form.get('price_medium') or product.price_medium)
    product.price_large = float(request.form.get('price_large') or product.price_large)
    product.ingredients = request.form.get('ingredients') or product.ingredients
    product.is_popular = request.form.get('is_popular') == 'on'
    product.is_special_offer = request.form.get('is_special_offer') == 'on'
    product.discount_percent = int(request.form.get('discount_percent') or 0)

    uploaded_image = request.files.get('image')
    if uploaded_image and uploaded_image.filename:
        saved_image = save_uploaded_image(uploaded_image)
        if saved_image:
            product.image_url = saved_image
    elif request.form.get('image_url'):
        product.image_url = request.form.get('image_url')

    db.session.commit()
    trim_products_to_four_per_category(keep_ids={product.id})
    flash(f'Flavor "{product.name}" updated successfully.', 'success')
    return redirect(url_for('admin_products'))


@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('admin_products'))

    name = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f'Flavor "{name}" removed from inventory.', 'info')
    return redirect(url_for('admin_products'))


@app.route('/admin/messages')
@admin_required
def admin_messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/messages.html', messages=messages)


@app.route('/admin/messages/toggle-read/<int:msg_id>', methods=['POST'])
@admin_required
def admin_toggle_message_read(msg_id):
    msg = db.session.get(ContactMessage, msg_id)
    if not msg:
        return jsonify({'success': False, 'message': 'Message not found'}), 404

    msg.status = 'Read' if msg.status == 'Unread' else 'Unread'
    db.session.commit()
    return jsonify({'success': True, 'new_status': msg.status})


@app.route('/admin/change-password', methods=['GET', 'POST'])
@admin_required
def admin_change_password():
    user = get_current_user()
    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not current_password or not new_password or not confirm_password:
            flash('All password fields are required.', 'danger')
            return render_template('admin/change_password.html')

        if not user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
            return render_template('admin/change_password.html')

        if len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'danger')
            return render_template('admin/change_password.html')

        if new_password != confirm_password:
            flash('New password and confirmation password do not match.', 'danger')
            return render_template('admin/change_password.html')

        if user.check_password(new_password):
            flash('New password must be different from your current password.', 'warning')
            return render_template('admin/change_password.html')

        user.set_password(new_password)
        db.session.commit()
        flash('Password changed successfully! Please keep your new password safe.', 'success')
        return redirect(url_for('admin_change_password'))

    return render_template('admin/change_password.html')



# ==============================================================================
# MAIN EXECUTION & SEED INITIALIZATION
# ==============================================================================

if __name__ == '__main__':
    with app.app_context():
        seed_database()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)

