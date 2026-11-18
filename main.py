import random
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Picas y Fijas")
jugadores = set()   # nombres registrados
juegos = {}         # id -> juego (lo que se muestra a todos)
secretos = {}       # (id, nombre) -> número secreto (nunca se muestra)
contador = 0


# Datos que llegan en el JSON
class LoginIn(BaseModel):
    nombre: str

class NumeroIn(BaseModel):
    nombre: str
    numero: str


# Reglas del juego
def validar_numero(n: str):
    if not n.isdigit():
        raise HTTPException(400, "El número debe contener solo dígitos")
    if len(n) != 4:
        raise HTTPException(400, "El número debe tener exactamente 4 dígitos")
    if len(set(n)) != 4:
        raise HTTPException(400, "El número no puede tener dígitos repetidos")

def calcular(secreto: str, intento: str):
    fijas = sum(1 for a, b in zip(secreto, intento) if a == b)
    picas = len(set(secreto) & set(intento)) - fijas
    return fijas, picas

def exigir_registrado(nombre: str):
    if nombre not in jugadores:
        raise HTTPException(401, "Jugador no registrado. Haz login primero")

def obtener_juego(id: int):
    if id not in juegos:
        raise HTTPException(404, "El juego no existe")
    return juegos[id]


# Endpoints
@app.post("/login")
def login(datos: LoginIn):
    if not datos.nombre:
        raise HTTPException(400, "El nombre no puede estar vacío")
    jugadores.add(datos.nombre)
    return {"nombre": datos.nombre}


@app.post("/juego")
def crear_juego(datos: NumeroIn):
    global contador
    exigir_registrado(datos.nombre)
    validar_numero(datos.numero)
    contador += 1
    juegos[contador] = {
        "id": contador,
        "estado": "por_iniciar",
        "creador": datos.nombre,
        "jugador2": None,
        "turno": None,
        "ganador": None,
        "historial": [],
    }
    secretos[(contador, datos.nombre)] = datos.numero
    return juegos[contador]


@app.get("/juego")
def listar_juegos():
    return list(juegos.values())


@app.get("/juego/{id}")
def ver_juego(id: int):
    return obtener_juego(id)


@app.put("/juego/{id}")
def unirse(id: int, datos: NumeroIn):
    exigir_registrado(datos.nombre)
    j = obtener_juego(id)
    if j["estado"] != "por_iniciar":
        raise HTTPException(409, "El juego ya está lleno o terminado")
    if datos.nombre == j["creador"]:
        raise HTTPException(409, "No puedes unirte a tu propio juego")
    validar_numero(datos.numero)
    j["jugador2"] = datos.nombre
    secretos[(id, datos.nombre)] = datos.numero
    j["estado"] = "en_juego"
    j["turno"] = random.choice([j["creador"], datos.nombre])  # el primero se sortea
    return j


@app.post("/juego/{id}/jugar")
def jugar(id: int, datos: NumeroIn):
    exigir_registrado(datos.nombre)
    j = obtener_juego(id)
    if j["estado"] != "en_juego":
        raise HTTPException(409, "El juego no está en curso")
    if j["turno"] != datos.nombre:
        raise HTTPException(403, "No es tu turno")
    validar_numero(datos.numero)

    rival = j["jugador2"] if datos.nombre == j["creador"] else j["creador"]
    fijas, picas = calcular(secretos[(id, rival)], datos.numero)
    j["historial"].append({"jugador": datos.nombre, "intento": datos.numero,
                           "fijas": fijas, "picas": picas})
    if fijas == 4:
        j["estado"] = "terminado"
        j["ganador"] = datos.nombre
        j["turno"] = None
    else:
        j["turno"] = rival
    return {"fijas": fijas, "picas": picas,
            "estado": j["estado"], "turno": j["turno"], "ganador": j["ganador"]}


@app.get("/")
def inicio():
    return FileResponse("index.html")
