from passlib.context import CryptContext
import bcrypt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def generate_salt():
    return bcrypt.gensalt().decode()


def get_password_hash(password):
    return pwd_context.hash(password)
