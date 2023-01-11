from flask_restful import Resource
from flask import request
from hmac import compare_digest
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
    get_jwt,
)
from marshmallow import ValidationError
from models.user import UserModel
from schemas.user import UserSchema
from blocklist import BLOCKLIST

USER_ALREADY_EXISTS = "A user with name {} already exists."
USER_NOT_FOUND = "User not found."
USER_DELETED = "User deleted."
USER_LOGGED_OUT = "User <id={}> successfully logged out."
CREATED_SUCCESSFULLY = "User created successfully."
INVALID_CREDENTIALS = "Invalid credentials."

user_schema = UserSchema()

class UserRegister(Resource):
    def post(cls):
        try:
            user_data = user_schema.load(request.get_json())
        except ValidationError as err:
            return err.messages, 400

        if UserModel.find_by_username(user_data["username"]):
            return {"message": USER_ALREADY_EXISTS.format(user_data["username"])}, 400

        user = UserModel(**user_data)
        user.save_to_db()

        return {"message": CREATED_SUCCESSFULLY}, 201


class User(Resource):
    """
    This resource can be useful when testing our Flask app. We may not want to expose it to public users, but for the
    sake of demonstration in this course, it can be useful when we are manipulating data regarding the users.
    """

    @classmethod
    def get(cls, user_id: int):
        user = UserModel.find_by_id(user_id)
        if not user:
            return {"message": USER_NOT_FOUND}, 404
        return user_schema.dump(user), 200

    @classmethod
    def delete(cls, user_id: int):
        user = UserModel.find_by_id(user_id)
        if not user:
            return {"message": USER_NOT_FOUND}, 404
        user.delete_from_db()
        return {"message": USER_DELETED}, 200


class UserLogin(Resource):
    @classmethod
    def post(cls):
        try:
            user_data = user_schema.load(request.get_json())
        except ValidationError as err:
            return err.messages, 400
        user = UserModel.find_by_username(user_data["username"])

        # this is what the `authenticate()` function did in security.py
        if user and compare_digest(user.password, user_data["password"]):
            # identity= is what the identity() function did in security.py—now stored in the JWT
            access_token = create_access_token(identity=user.id, fresh=True)
            refresh_token = create_refresh_token(user.id)
            return {"access_token": access_token, "refresh_token": refresh_token}, 200

        return {"message": INVALID_CREDENTIALS}, 401


class UserLogout(Resource):
    @classmethod
    @jwt_required()
    def post(cls):
        jti = get_jwt()["jti"]  # jti is "JWT ID", a unique identifier for a JWT.
        user_id = get_jwt_identity()
        BLOCKLIST.add(jti)
        return {"message": USER_LOGGED_OUT.format(user_id)}, 200


class TokenRefresh(Resource):
    @classmethod
    @jwt_required(refresh=True)
    def post(cls):
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user, fresh=False)
        return {"access_token": new_token}, 200
