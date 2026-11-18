# Picas y Fijas — Versión distribuida

Proyecto del curso de **Sistemas Distribuidos**. Es el juego clásico de *Picas y Fijas* convertido en un servicio web REST (JSON) que se puede desplegar en **Kubernetes**.

---

## ¿Qué hace el programa?

Dos jugadores se enfrentan a través de un servidor:

1. Cada jugador se registra con su nombre.
2. Un jugador **crea un juego** y escribe su número secreto.
3. Otro jugador **se une** a ese juego con su propio número secreto. En ese momento el juego empieza y el servidor **sortea quién juega primero**.
4. Por turnos, cada jugador intenta adivinar el número del rival. El servidor responde cuántas **fijas** y cuántas **picas** obtuvo.
5. El primero que adivina el número del otro (4 fijas) **gana**.

En cualquier momento se puede ver la lista de juegos y el estado de cada uno.

### Reglas del número secreto

- Exactamente **4 dígitos**.
- **Solo números** (sin letras, espacios ni signos).
- **Sin dígitos repetidos**.

El servidor valida estas reglas y responde con un error si no se cumplen.

### ¿Qué son picas y fijas?

- **Fija**: el dígito está en el número secreto y **en la misma posición**.
- **Pica**: el dígito está en el número secreto pero **en otra posición**.

Ejemplo: número secreto `4271`, intento `1234` → **1 fija** (el 2) y **2 picas** (el 4 y el 1).

---

## Tecnologías

| Parte | Herramienta |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Servidor | Uvicorn |
| Front | HTML + JavaScript (archivo `index.html`) |
| Contenedor | Docker |
| Orquestación | Kubernetes (probado en Killercoda) |

No usa base de datos: los jugadores y los juegos se guardan **en memoria**.

---

## Estructura del proyecto

```
picasyfijas/
├── main.py              # Backend: endpoints y lógica del juego
├── index.html           # Front básico para jugar desde el navegador
├── requirements.txt     # Dependencias de Python
├── Dockerfile           # Instrucciones para construir la imagen
├── .dockerignore
├── .gitignore
└── k8s/
    ├── deployment.yaml  # Despliegue del contenedor en Kubernetes
    └── service.yaml     # Expone la app en el puerto 30080 del nodo
```

---

## Endpoints

Todas las peticiones y respuestas usan **JSON**.

| Método | Ruta | Para qué sirve | Cuerpo (JSON) |
|---|---|---|---|
| POST | `/login` | Registrar el nombre del jugador | `{"nombre": "ana"}` |
| POST | `/juego` | Crear un juego con tu número secreto | `{"nombre": "ana", "numero": "4271"}` |
| PUT | `/juego/{id}` | Unirse a un juego (aquí empieza la partida) | `{"nombre": "luis", "numero": "5678"}` |
| POST | `/juego/{id}/jugar` | Enviar un intento (solo si es tu turno) | `{"nombre": "luis", "numero": "1234"}` |
| GET | `/juego/{id}` | Ver el estado de un juego, el turno, el historial y el ganador | — |
| GET | `/juego` | Listar todos los juegos | — |
| GET | `/` | Abre el front para jugar | — |

**Estados de un juego:** `por_iniciar` (esperando rival), `en_juego` y `terminado` (indica quién ganó).

Los números secretos **nunca** aparecen en las respuestas.

**Códigos de error:** `400` dato inválido · `401` jugador no registrado · `403` no es tu turno · `404` el juego no existe · `409` el juego ya está lleno, terminado o aún no empieza. Los errores llegan como `{"detail": "mensaje"}`.

> FastAPI genera documentación automática: abre `/docs` para probar todos los endpoints desde el navegador.

---

## Cómo ejecutarlo

Hay tres formas. Para la entrega, la importante es la **opción 3 (Kubernetes)**.

### Opción 1: En tu computador (sin Docker)

Requisito: tener **Python 3.12** o superior.

1. Abre una terminal en la carpeta del proyecto.
2. Crea un entorno virtual:
   ```bash
   python -m venv venv
   ```
3. Actívalo:
   - Windows: `venv\Scripts\activate`
   - Linux / Mac: `source venv/bin/activate`
4. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
5. Arranca el servidor:
   ```bash
   uvicorn main:app --reload
   ```
6. Abre en el navegador: **http://localhost:8000**

### Opción 2: Con Docker

Requisito: tener **Docker Desktop** instalado y abierto.

1. Construye la imagen:
   ```bash
   docker build -t picasyfijas .
   ```
2. Ejecuta el contenedor:
   ```bash
   docker run -p 8000:8000 picasyfijas
   ```
3. Abre en el navegador: **http://localhost:8000**

### Opción 3: En Kubernetes (Killercoda)

#### Paso 1. Subir la imagen a Docker Hub (desde tu computador)

Kubernetes descarga la imagen desde Docker Hub, así que primero hay que subirla. El archivo `k8s/deployment.yaml` usa la imagen `julian0411/picasyfijas:1.0`. Si vas a usar tu propia cuenta, cambia ese nombre en el archivo.

```bash
docker login
docker build -t julian0411/picasyfijas:1.0 .
docker push julian0411/picasyfijas:1.0
```

En Docker Hub, verifica que el repositorio sea **público**.

#### Paso 2. Abrir Killercoda

1. Entra a **https://killercoda.com/playgrounds** e inicia sesión.
2. Abre el escenario **Kubernetes** (el que trae un clúster listo).

#### Paso 3. Descargar el proyecto

En la terminal de Killercoda:

```bash
git clone https://github.com/JDavidOritz2004/picasyfijas.git
cd picasyfijas
```

#### Paso 4. Desplegar

```bash
kubectl apply -f k8s/
```

#### Paso 5. Verificar que esté corriendo

```bash
kubectl get pods
kubectl get svc
```

Espera a que el pod aparezca con estado **Running** y **READY 1/1**. Si tarda, vuelve a ejecutar `kubectl get pods` después de unos segundos.

#### Paso 6. Abrir el juego

- **Desde el navegador:** en Killercoda abre el menú (arriba a la derecha) → **Traffic / Ports** → escribe el puerto **30080** → **Access**. Se abrirá el front del juego.
- **Desde la terminal:**
  ```bash
  curl http://localhost:30080/juego
  ```

#### Si algo falla

| Problema | Qué revisar |
|---|---|
| El pod queda en `ErrImagePull` o `ImagePullBackOff` | La imagen no existe en Docker Hub o es privada. Repite el Paso 1. |
| El pod queda en `CrashLoopBackOff` | Mira el error con `kubectl logs deployment/picasyfijas`. |
| No abre en el puerto 30080 | Revisa con `kubectl get svc` que el servicio diga `8000:30080/TCP`. |

Para borrar todo: `kubectl delete -f k8s/`

---

## Probar una partida completa con `curl`

Estos comandos simulan a dos jugadores (`ana` y `luis`). Usa el puerto `30080` en Kubernetes o `8000` en tu computador.

```bash
URL=http://localhost:30080

# 1. Registrar a los dos jugadores
curl -X POST $URL/login -H "Content-Type: application/json" -d '{"nombre":"ana"}'
curl -X POST $URL/login -H "Content-Type: application/json" -d '{"nombre":"luis"}'

# 2. Ana crea un juego con su número secreto
curl -X POST $URL/juego -H "Content-Type: application/json" -d '{"nombre":"ana","numero":"4271"}'

# 3. Luis se une al juego 1 (el juego empieza y se sortea el turno)
curl -X PUT $URL/juego/1 -H "Content-Type: application/json" -d '{"nombre":"luis","numero":"5678"}'

# 4. Ver de quién es el turno
curl $URL/juego/1

# 5. El jugador que tenga el turno envía un intento (ejemplo: luis)
curl -X POST $URL/juego/1/jugar -H "Content-Type: application/json" -d '{"nombre":"luis","numero":"1234"}'

# 6. Listar todos los juegos
curl $URL/juego
```

Para ver la validación funcionando, prueba con un número inválido:

```bash
curl -X POST $URL/juego -H "Content-Type: application/json" -d '{"nombre":"ana","numero":"1123"}'
# {"detail":"El número no puede tener dígitos repetidos"}
```

---

## Cómo jugar desde el front

1. Abre la página del juego en **dos pestañas o navegadores distintos** (un jugador en cada una).
2. En cada una escribe un nombre y pulsa **Entrar**.
3. **Jugador 1:** escribe su número secreto y pulsa **Crear juego**.
4. **Jugador 2:** escribe su número secreto y pulsa **Unirme** en el juego de la lista.
5. Quien tenga el turno escribe su intento y pulsa **Probar**. La página se actualiza sola cada 3 segundos.

---

## Limitación importante

Como no hay base de datos, los datos viven en la memoria del pod. Por eso:

- El deployment usa **`replicas: 1`**. Con más réplicas, cada pod tendría su propia lista de juegos y los jugadores no se encontrarían.
- Si el pod se reinicia, **se pierden los juegos**.

Para escalar a varias réplicas, el estado tendría que guardarse en un almacenamiento compartido, por ejemplo **Redis** o una base de datos.
