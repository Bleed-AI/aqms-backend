
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def validate_password(password, hashed_password):
    return pwd_context.verify(password, hashed_password)


def generate_password_hash(password):
    return pwd_context.hash(password)

print(generate_password_hash("Gfv63gfHk$$tWty"))
