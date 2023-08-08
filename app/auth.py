from typing import Optional, Annotated
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
import chalk
from email_validator import validate_email, EmailNotValidError

from app.db_models import User
from app.api_models import Token, TokenData, UserAPIModel
from app.utils import Log as log
from app.config import AppConfig

# to get a string like this run:
# openssl rand -hex 32
# shahbaz: the actual production SECRET_KEY ideally be moved out of source code and stored in an environment variable on target machine
config = AppConfig()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def validate_password(password, hashed_password):
    return pwd_context.verify(password, hashed_password)


def generate_password_hash(password):
    return pwd_context.hash(password)


def create_new_user(user: UserAPIModel):
    print(f"User: {user}")
    try:
        emailinfo = validate_email(user.username, check_deliverability=False)
        hashed_password = generate_password_hash(user.password)
        user = User.create(username=user.username,
                           password=hashed_password,
                           first_name=user.first_name,
                           last_name=user.last_name,
                           is_admin=user.is_admin)

        user.save()
        user.password = None
        return user
    except (EmailNotValidError, Exception) as e:
        print(chalk.red("Exception in creating user: {}".format(e)))
        log.error("Exception in creating user: {}".format(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Error in creating user. {}".format(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def generate_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.api_token_expires_mins)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, config.api_secret_key, algorithm=config.api_crypto_algo)
    return encoded_jwt


def get_auth_token(username, password):
    try:
        user = User.get(User.username == username)
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Incorrect username or password")
        if validate_password(password, user.password):
            access_token_expires = timedelta(
                minutes=config.api_token_expires_mins)
            access_token = generate_access_token(
                data={"sub": user.username}, expires_delta=access_token_expires
            )
            return {
                "username": user.username,
                "token_expiry": access_token_expires,
                "access_token": access_token,
                "token_type": "bearer"
            }
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Incorrect username or password")
    except Exception as e:
        print(chalk.red("Exception in generating token: {}".format(e)))
        log.error("Exception in generating token: {}".format(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    if token[-1] == "}":
        token = token[:-1]
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.api_secret_key,
                             algorithms=[config.api_crypto_algo])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
        user = User.get(User.username == username)
        if user is None:
            raise credentials_exception
        return user
    except JWTError as e:
        log.error("Exception in get_current_user: {}".format(e))
        raise credentials_exception


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
):
    print(f"current_user: {current_user}")
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_user_list(user: UserAPIModel):
    try:
        if user and type(user) == dict and user["id"] > 0:
            db_user = User.get_by_id(user["id"])
            print(db_user)
            if db_user:
                if db_user.is_admin:
                    users = [user for user in User.select(
                        User.id, User.username, User.first_name, User.last_name, User.is_admin)]
                    return users
                else:
                    raise HTTPException(
                        403, detail="You are not an admin user.")
    except Exception as e:
        log.error(
            "Error in fetching user list. You don't seem to be an admin user. {}".format(e))
        raise HTTPException(
            500, detail="Error in fetching user list. You don't seem to be an admin user. {}".format(e))


async def delete_user(user: UserAPIModel, user_id):
    if user and user["id"] == user_id:
        raise HTTPException(
            422, detail="You can't delete your own auth record.")
    if user and type(user) == dict and user["id"] > 0:
        db_user = User.get_by_id(user["id"])
        if db_user.is_admin:
            u = User.get_by_id(user_id)
            result = u.delete_instance()
            if result > 0:
                return {"message": "User with id {} deleted successfully.".format(user_id)}
        else:
            log.error("Only admin users can delete other users.")
            raise HTTPException(
                403, detail="Only admin users can delete other users.")
