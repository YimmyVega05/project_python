import jwt
import datetime
from flask import  Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask import current_app
from functools import wraps


app = Flask(__name__)

app.config['SECRET_KEY'] = '123456789'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#Create models user in database
# Definir modelo de usuario
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Crear token JWT
def create_token(user_id):
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    payload = {
        'sub': user_id,
        'exp': expiration
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token

# Ruta para registrar un nuevo usuario
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    # Verificar si el nombre de usuario ya existe
    existing_user = User.query.filter_by(username=data['username']).first()
    if existing_user:
        return jsonify({"message": "User already exists"}), 400

    # Crear un nuevo usuario
    new_user = User(username=data['username'])
    new_user.set_password(data['password'])  # Aquí se cifra la contraseña

    # Guardar en la base de datos
    db.session.add(new_user)
    db.session.commit()

    # Generar token JWT
    token = create_token(new_user.id)  # Crear token JWT

    return jsonify({
        "message": "User registered successfully",
        "user": {
            "id": new_user.id,
            "username": new_user.username
        },
        "token": token  # Agregar el token a la respuesta
    })

if __name__ == '__main__':
    app.run(debug=True)
    

# Decorador para proteger rutas con token
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Verificar si el token está en la cabecera de la solicitud
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]  # Obtener el token de la cabecera
        
        if not token:
            return jsonify({"message": "Token is missing!"}), 403

        try:
            # Decodificar el token usando la clave secreta
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['sub'])  # Obtener el usuario a partir del token
        except:
            return jsonify({"message": "Token is invalid!"}), 403

        return f(current_user, *args, **kwargs)  # Llamar a la función con el usuario actual

    return decorated_function



# Create models database Books

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer)
    genre = db.Column(db.String(50))

   #method to convert object to dictionary
    def serialize(self):
        return  {
            'id' : self.id,
            'title' : self.title,
            'author' : self.author,
            'year' : self.year,
            'genre' : self.genre,
        }

# Create the tables in the database

    
# Crear las tablas si no existen
with app.app_context():
    db.create_all()
    print("Tables created successfully")

        
        

# create routes
@app.route('/books', methods=['GET'])
def get_books():
    books = Book.query.all()
    if not books:
        return jsonify({'message': 'No books available'}), 404
    return jsonify({'books': [book.serialize() for book in books]}), 200




@app.route('/books', methods=['POST'])
@token_required 
def create_books():
    data = request.get_json()

    # Validaciones
    if not data:
        return jsonify({'error': 'Request body is missing'}), 400

    if 'title' not in data or not isinstance(data['title'], str) or not data['title'].strip():
        return jsonify({'error': 'Title is required and must be a non-empty string'}), 400

    if 'author' not in data or not isinstance(data['author'], str) or not data['author'].strip():
        return jsonify({'error': 'Author is required and must be a non-empty string'}), 400

    if 'year' in data and (not isinstance(data['year'], int) or data['year'] <= 0):
        return jsonify({'error': 'Year must be a positive integer'}), 400

    if 'genre' in data and (not isinstance(data['genre'], str) or not data['genre'].strip()):
        return jsonify({'error': 'Genre must be a non-empty string'}), 400

    # Crear libro
    book = Book(
        title=data['title'],
        author=data['author'],
        year=data.get('year'),
        genre=data.get('genre')
    )
    db.session.add(book)
    db.session.commit()
    return jsonify({'message': 'Book created successfully', 'book': book.serialize()}), 201



#filter books  get book specific
@app.route('/books/<int:id>', methods=['GET'])
@token_required 
def get_filter_books(id):
    book = Book.query.get(id)
    if not book:
        return jsonify({'message': 'Book not found'}), 404
    return jsonify({'message': 'Book successfully found', 'book': book.serialize()}), 200



#Edit register
@app.route('/books/<int:id>', methods=['PUT', 'PATCH'])
@token_required 
def update_books(id):
    book = Book.query.get_or_404(id)
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is missing'}), 400

    # Validaciones y actualización
    if 'title' in data and (not isinstance(data['title'], str) or not data['title'].strip()):
        return jsonify({'error': 'Title must be a non-empty string'}), 400
    if 'author' in data and (not isinstance(data['author'], str) or not data['author'].strip()):
        return jsonify({'error': 'Author must be a non-empty string'}), 400
    if 'year' in data and (not isinstance(data['year'], int) or data['year'] <= 0):
        return jsonify({'error': 'Year must be a positive integer'}), 400
    if 'genre' in data and (not isinstance(data['genre'], str) or not data['genre'].strip()):
        return jsonify({'error': 'Genre must be a non-empty string'}), 400

    # Actualización de campos
    if 'title' in data:
        book.title = data['title']
    if 'author' in data:
        book.author = data['author']
    if 'year' in data:
        book.year = data['year']
    if 'genre' in data:
        book.genre = data['genre']

    db.session.commit()
    return jsonify({'message': 'Successfully updated', 'book': book.serialize()})




#Delete register
@app.route('/books/<int:id>', methods=['DELETE'])
@token_required 
def delete_books(id):
    book = Book.query.get(id)
    if not book:
        return jsonify({'message': 'Book not found'}), 404

    db.session.delete(book)
    db.session.commit()
    return jsonify({'message': 'Book successfully deleted'}), 200



