import jwt
import logging
import os
import pickle

logger = logging.getLogger(__name__)

# ruleid: py-hardcoded-jwt-secret
t = jwt.encode({"u": 1}, "supersecreto123", algorithm="HS256")
# ok: py-hardcoded-jwt-secret
t = jwt.encode({"u": 1}, os.environ["JWT_SECRET"], algorithm="HS256")


def q(cursor, user):
    # ruleid: py-sql-fstring-injection
    cursor.execute(f"SELECT * FROM clientes WHERE rut = '{user}'")
    # ok: py-sql-fstring-injection
    cursor.execute("SELECT * FROM clientes WHERE rut = %s", (user,))


# ruleid: py-unsafe-model-deserialization
model = pickle.loads(b"...")


def log(rut, request_id):
    # ruleid: py-sensitive-data-in-logs
    logger.info(f"solicitud de {rut}")
    # ok: py-sensitive-data-in-logs
    logger.info(f"solicitud {request_id}")
