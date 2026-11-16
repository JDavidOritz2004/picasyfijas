import random
import threading
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(title="Picas y Fijas")
lock = threading.Lock()          # evita jugadas simultáneas 
jugadores = set()                # nombres registrados
juegos = {}                      # id -> juego
contador = 0


#las entradas
class LoginIn(BaseModel):
    nombre: str

class NumeroIn(BaseModel):
    nombre: str
    numero: str

#esto es para los errores del json
@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400,
                        content={"error": "JSON inválido o campos faltantes (nombre, numero)"})


#las reglas
def validar_numero(n: str):
    if not (n.isascii() and n.isdigit()):
        raise HTTPException(400, "El número debe contener solo dígitos")
    if len(n) != 4:
        raise HTTPException(400, "El número debe tener exactamente 4 dígitos")
    if len(set(n)) != 4:
        raise HTTPException(400, "El número no puede tener dígitos repetidos")

def calcular(secreto: str, intento: str):
    fijas = sum(1 for a, b in zip(secreto, intento) if a == b)
    picas = len(set(secreto) & set(intento)) - fijas
    return fijas, picas

def exigir_registrado(nombre: str) -> str:
    nombre = nombre.strip()
    if nombre not in jugadores:
        raise HTTPException(401, "Jugador no registrado. Haz login primero")
    return nombre

def obtener_juego(id: int):
    if id not in juegos:
        raise HTTPException(404, "El juego no existe")
    return juegos[id]

def vista(j: dict) -> dict:
    """Versión pública: NUNCA incluye los números secretos."""
    return {
        "id": j["id"],
        "estado": j["estado"],
        "creador": j["creador"],
        "jugador2": j["jugador2"],
        "turno": j["turno"],
        "ganador": j["ganador"],
        "historial": j["historial"],
    }


# ---------- Endpoints ----------
@app.post("/login", status_code=201)
def login(datos: LoginIn):
    nombre = datos.nombre.strip()
    if not nombre:
        raise HTTPException(400, "El nombre no puede estar vacío")
    jugadores.add(nombre)        
    return {"nombre": nombre}


@app.post("/juego", status_code=201)
def crear_juego(datos: NumeroIn):
    global contador
    with lock:
        nombre = exigir_registrado(datos.nombre)
        validar_numero(datos.numero)
        contador += 1
        juegos[contador] = {
            "id": contador,
            "estado": "por_iniciar",
            "creador": nombre,
            "jugador2": None,
            "numeros": {nombre: datos.numero},   #esto es para que no se vean los numeros del otro
            "turno": None,
            "ganador": None,
            "historial": [],
        }
        return vista(juegos[contador])


@app.get("/juego")
def listar_juegos(estado: str | None = None):
    lista = [vista(j) for j in juegos.values()]
    if estado:
        lista = [j for j in lista if j["estado"] == estado]
    return lista


@app.get("/juego/{id}")
def ver_juego(id: int):
    return vista(obtener_juego(id))


@app.put("/juego/{id}")
def unirse(id: int, datos: NumeroIn):
    with lock:
        nombre = exigir_registrado(datos.nombre)
        j = obtener_juego(id)
        if j["estado"] != "por_iniciar":
            raise HTTPException(409, "El juego ya está lleno o terminado")
        if nombre == j["creador"]:
            raise HTTPException(409, "No puedes unirte a tu propio juego")
        validar_numero(datos.numero)
        j["jugador2"] = nombre
        j["numeros"][nombre] = datos.numero
        j["estado"] = "en_juego"
        j["turno"] = random.choice([j["creador"], nombre])  
        return vista(j)


@app.post("/juego/{id}/jugar")
def jugar(id: int, datos: NumeroIn):
    with lock:
        nombre = exigir_registrado(datos.nombre)
        j = obtener_juego(id)
        if nombre not in (j["creador"], j["jugador2"]):
            raise HTTPException(403, "No participas en este juego")
        if j["estado"] == "por_iniciar":
            raise HTTPException(409, "Aún falta el segundo jugador")
        if j["estado"] == "terminado":
            raise HTTPException(409, "El juego ya terminó")
        if j["turno"] != nombre:
            raise HTTPException(403, "No es tu turno")
        validar_numero(datos.numero)

        rival = j["jugador2"] if nombre == j["creador"] else j["creador"]
        fijas, picas = calcular(j["numeros"][rival], datos.numero)
        j["historial"].append({"jugador": nombre, "intento": datos.numero,
                               "fijas": fijas, "picas": picas})
        if fijas == 4:
            j["estado"] = "terminado"
            j["ganador"] = nombre
            j["turno"] = None
        else:
            j["turno"] = rival
        return {"fijas": fijas, "picas": picas,
                "estado": j["estado"], "turno": j["turno"], "ganador": j["ganador"]}



@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse("index.html")