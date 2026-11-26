# SmartConnect

**Control de acceso residencial · TI3041 · Unidad 3 · Segundo avance**

Una persona puede administrar una casa en Parque Norte, arrendar un departamento en Mirador Sur y tener permiso para entrar por un único portón. SmartConnect conserva cada relación por separado para poder responder tres preguntas: quién puede asignar residentes, por dónde puede ingresar una persona y qué ocurrió en cada intento.

[![Verificar API](https://github.com/KevinInacap/smartconnect-ti3041/actions/workflows/verificar.yml/badge.svg)](https://github.com/KevinInacap/smartconnect-ti3041/actions/workflows/verificar.yml)

[Guía para la clase](#guía-para-la-clase) · [Modelo de datos](#modelo-de-datos) · [Referencia de la API](#referencia-de-la-api) · [Evidencia de las pruebas](#pruebas-reproducibles)

## Empezar en el PC de clase

Si ya tienes la copia preparada en Windows, abre **Iniciar SmartConnect.cmd** con doble clic. El archivo prepara el entorno con Python 3.13, aplica las migraciones, carga los usuarios ficticios e inicia Django en el puerto 8000. Mantén abierta la ventana si acaba de arrancar el servidor. [Archivo de inicio](<Iniciar SmartConnect.cmd>)

- **Apidog** envía las peticiones al servidor de este PC. Abre el proyecto **SmartConnect · Acceso residencial** y selecciona el entorno que apunta a `http://127.0.0.1:8000`. [Proyecto de la clase](https://app.apidog.com/project/1420338)
- **Historial** muestra los últimos 50 intentos visibles para la cuenta. Abre la página en otra pestaña, inicia sesión como Scarlett y déjala abierta para la demostración. [Historial en este PC](http://127.0.0.1:8000/historial/)
- **Swagger** sirve para explorar todas las rutas. **Django Admin** permite a Kevin consultar los registros de los cuatro maestros, las participaciones y los intentos. [Swagger](http://127.0.0.1:8000/api/docs/) · [Django Admin](http://127.0.0.1:8000/admin/)

### Cuentas de clase

| Usuario | Clave de práctica | Qué puedes mostrar |
|---|---|---|
| `aula_scarlett` | `Scarlett-Aula-TI3041!` | Arrendataria de A-01. Puede entrar por N-01, recibe una denegación en N-02 y puede consultar sus propios intentos. |
| `aula_kevin` | `Kevin-Aula-TI3041!` | Operador de los cuatro maestros en la API, con lectura del historial global. También es propietario administrador de A-01 y puede asignar residentes allí. |

Estas identidades son datos ficticios elegidos para el ejercicio. Las claves de esta tabla son públicas y se habilitan expresamente con `seed_demo --aula` para una instancia local con datos de ejemplo. En la colección actual el login ya incluye la cuenta y la clave de práctica. Puedes comenzar sin crear `demoPassword`. Repetir la semilla conserva las contraseñas que ya existan.

## Guía para la clase

Abre al mismo tiempo **Apidog** y el **Historial**. Las peticiones de la carpeta **Acceso de una residente** están ordenadas. Pulsa **Enviar** en cada una, desde la primera. El login y las consultas guardan en el entorno los tokens y los identificadores que utilizan los pasos siguientes.

| En Apidog | Qué mostrar y cómo explicarlo |
|---|---|
| 1. **Viviendas sin sesión** | `401`. La API exige que la persona se identifique. |
| 2–3. **Iniciar sesión** y **Renovar sesión** | `200`. El login de Scarlett entrega `access` y `refresh`. El siguiente paso obtiene un nuevo `access`. Apidog lo envía en el encabezado `Authorization: Bearer …`. |
| 4–6. **Mis viviendas**, **Mi rol en A-01** y **Puntos de mi terreno** | Se ve A-01, su rol de arrendataria y los dos puntos de Parque Norte. Conocer un punto y tener permiso para utilizarlo son dos comprobaciones distintas. |
| 7. **Entrar por el portón** | `201`, `permitido: true`, `motivo: autorizado`. Lee el `id` de la respuesta. Cambia a la pestaña Historial y busca la fila con ese mismo ID, Scarlett y N-01. Se actualiza cada tres segundos mientras está visible. |
| 8. **Intentar la puerta de servicio** | `201`, `permitido: false`, `motivo: sin_permiso_punto`. El segundo ID aparece como **Denegado** junto a N-02. El 201 indica que se guardó el intento. |
| 9–10. **Asignar como residente** y **Mi historial** | `403` al intentar asignar a otra persona. Con **Mi historial** se recuperan ambos intentos en JSON. |

**Para explicar la persistencia:** “Apidog envió un POST. Django identificó la cuenta por su JWT, comprobó el permiso del punto y guardó la decisión en SQLite. El GET del historial y el panel consultan esa misma fila. Aquí se ve el mismo ID”. El login y las consultas GET no crean intentos. La proximidad se simula con `cerca`. La confirmación de una apertura física corresponde a la integración del dispositivo.

**Para mostrar la rúbrica completa**, usa la colección **Rúbrica**. La cuenta de Kevin crea, lista, consulta, actualiza y elimina un registro de cada maestro. Primero enseña un PUT seguido de un GET con el mismo ID. Luego muestra la asignación de una persona a A-01 (201), el segundo intento de asignarla (409) y la operación sin autoridad de Scarlett (403). Las relecturas verifican que los rechazos conservaron las relaciones. El recorrido utiliza códigos nuevos por ejecución y conserva la asignación de ejemplo. [Colección con los cuatro CRUD y la operación de negocio](apidog/Rubrica.json)

### Preparación en otro equipo

Con Python 3.13, Git y, para ejecutar las colecciones por consola, Node.js con npm, clona la versión del pull request:

```powershell
git clone --branch fix/demo-clase https://github.com/KevinInacap/smartconnect-ti3041.git
cd smartconnect-ti3041
& '.\Iniciar SmartConnect.cmd'
```

La instalación manual equivalente empieza con `python -m venv .venv`. Activa ese entorno y ejecuta `python -m pip install -r requirements.txt`, `python manage.py migrate`, `python manage.py seed_demo --aula` y `python manage.py runserver 127.0.0.1:8000 --insecure`. Django usa el argumento `--insecure` para servir los archivos estáticos locales de Swagger y Admin durante la práctica.

En un proyecto nuevo de Apidog, importa [SmartConnect.json](apidog/SmartConnect.json) como colección Postman. Para el recorrido largo importa [Rubrica.json](apidog/Rubrica.json) en un módulo o proyecto aparte a fin de conservar los nombres de peticiones que comparten método y URL. Puedes importar también [el contrato OpenAPI](esquema.yaml). Usa `http://127.0.0.1:8000` como URL base del servicio y valor de `baseUrl` si el importador mantiene la variable. [Guía de importación](https://docs.apidog.com/en/manual-import-633884m0)

**Si hay un error en Apidog**

| Qué ves | Qué revisar |
|---|---|
| Error de conexión | Abre el historial local. Si tampoco carga, inicia SmartConnect en ese mismo PC. En Apidog web selecciona un agente local que pueda llegar a localhost, o abre el proyecto en Apidog de escritorio. |
| `401` en **Iniciar sesión** | Revisa el cuerpo JSON de **POST /api/token/**. Usa el usuario y la clave de Scarlett de la tabla. Si el cuerpo todavía contiene `{{demoPassword}}`, estás usando una copia anterior. |
| `401` después de un login correcto | Selecciona el mismo entorno y vuelve a ejecutar login y renovación. En las rutas protegidas revisa el encabezado Bearer y que los postprocesadores estén habilitados. |
| `400` o una URL con `{{casa}}` o `{{principal}}` sin resolver | Ejecuta las consultas 4 a 6 en orden. Son las que obtienen los ID de **tu** base de datos. |
| Apidog marca en rojo «se esperaba 200» | Mira el **estado real**, el **Body** y el paso de la guía. Algunas definiciones importadas tienen validación genérica de éxito 200. Para las aperturas el resultado esperado es 201, y en las pruebas de rechazo se esperan 401, 403 o 409 según el caso. Las aserciones de la colección comprueban esos códigos. |

## Modelo de datos

El ER de la implementación se divide en dos vistas que comparten **Persona** y **Terreno**. Las etiquetas indican las cardinalidades. **PK** identifica la clave primaria, **FK** una referencia y **UQ** una restricción de unicidad.

### Residencia y administración

![Diagrama ER de cuentas, personas, terrenos, viviendas, empleos y participaciones](docs/diagramas/residencia.svg)

Cada vivienda pertenece a un solo terreno. Una persona puede administrar varios terrenos y cada terreno tiene una administradora o administrador responsable. La relación muchos a muchos entre persona y vivienda se materializa en **Participación**. El par persona–vivienda es único y su rol puede ser propietario administrador, propietario, arrendatario o conviviente. **Conviviente** representa a quien vive allí sin ser titular ni arrendatario. **Empleo** conserva el vínculo laboral aunque la persona carezca de vivienda.

### Cómo reconoce el sistema a quien llama

| Pregunta | Dato que lee el servidor | Alcance |
|---|---|---|
| ¿Quién inició sesión? | Django valida el usuario y la clave. El access JWT identifica la cuenta y `Persona.cuenta_id` la vincula con su ficha. | Identidad para esta petición. El cliente envía el token. |
| ¿Puede operar el catálogo global? | `User.is_staff` | El operador gestiona los cuatro maestros. |
| ¿Administra este terreno? | `Terreno.administrador_id` coincide con la persona. | Mantener viviendas y puntos de ese terreno. |
| ¿Puede asignar personas a esta vivienda? | Existe la participación de esa persona en **esa vivienda** con `rol = propietario_administrador`. | Incorporar arrendatarios o convivientes. |
| ¿Puede entrar por este portón? | Para app: persona vinculada a la cuenta, cercanía simulada, vínculo vigente con el terreno del punto y fila en `PermisoPunto` para la persona y el punto exactos. | Autorizar ese intento y registrar la decisión. |

**Ejemplo.** Scarlett usa su propia cuenta. Su ficha registra que arrienda A-01 y que tiene permiso para el portón N-01. El servidor consulta esas relaciones cuando recibe la petición. Si su cuenta aún carece de ficha, la app registra `sin_persona`. Si falta la relación territorial o el permiso específico, registra el motivo correspondiente. Un encargado con los permisos adecuados debe registrar la relación y habilitar el punto durante el alta. Los puntos del modelo actual pertenecen al terreno: el ejemplo representa el portón del conjunto donde está su casa.

```mermaid
flowchart TD
    JWT["Solicitud desde la app"] --> T{"¿Token válido?"}
    T -->|No| R["401 · requiere sesión"]
    T -->|Sí| P{"¿Cuenta vinculada a una persona?"}
    P -->|No| D["Guardar intento denegado con su motivo"]
    P -->|Sí| C{"¿Está cerca del punto?"}
    C -->|No| D
    C -->|Sí| V{"¿Vivienda, empleo o administración en ese terreno?"}
    V -->|No| D
    V -->|Sí| G{"¿Permiso para esa persona y ese punto?"}
    G -->|No| D
    G -->|Sí| A["Guardar intento autorizado"]
    classDef ok fill:#e0f4ee,stroke:#186556,color:#143c33
    classDef stop fill:#fff0eb,stroke:#9a402a,color:#632d20
    class A ok
    class R,D stop
```

### Autorización y trazabilidad

![Diagrama ER de credenciales RFID, permisos por punto e intentos de acceso](docs/diagramas/accesos.svg)

Cada punto pertenece a un terreno. **Permiso por punto** vincula una persona con un acceso concreto. La autorización requiere un vínculo territorial vigente y un permiso explícito para ese punto. Para la app también se comprueba el booleano de proximidad simulada. En un intento RFID desconocido queda registrada una huella HMAC del identificador, el punto, la hora y el motivo. La persona queda vacía. La clave de firma local debe conservarse para poder volver a identificar las tarjetas registradas.

| Restricción física | Finalidad |
|---|---|
| Unicidad de `(terreno, codigo)` en vivienda y punto | Los códigos pueden repetirse en terrenos distintos. |
| Unicidad de `(persona, vivienda)`, `(persona, terreno)` en empleo y `(persona, punto)` en permiso | Cada relación tiene una sola fila. |
| Claves foráneas protegidas e índice sobre `intento.fecha` | Las bajas preservan relaciones e historial. La fecha permite acotar consultas. |
| Cuenta opcional y única por persona | Una persona puede recibir una tarjeta antes de tener cuenta en la app. |

Fuentes editables de los diagramas y esquema ejecutable: [residencia](docs/diagramas/residencia.dot), [accesos](docs/diagramas/accesos.dot) y [migración inicial](residencial/migrations/0001_initial.py).

## Operación de negocio

```mermaid
sequenceDiagram
    actor A as Alba
    participant API as API SmartConnect
    participant BD as Base de datos
    A->>API: POST asignaciones con access, persona y rol
    API->>API: Validar token e identificar la cuenta
    alt Token ausente o inválido
        API-->>A: 401
    else Cuenta autenticada
        API->>BD: Consultar rol de Alba en esta vivienda
        alt Alba administra la vivienda
            API->>BD: Crear vínculo único en una transacción
            alt Primera asignación
                BD-->>API: Vínculo persistido
                API-->>A: 201 y registro creado
            else La persona ya está vinculada
                API-->>A: 409 y rol original conservado
            end
        else Falta autoridad sobre la vivienda
            API-->>A: 403
        end
    end
```

El operador da de alta a la persona en el catálogo. El propietario administrador utiliza su ID para asignarla como arrendataria o conviviente. La designación inicial de propietarios se gestiona en Django Admin por personal autorizado. La regla de la API se comprueba incluso si el solicitante tiene acceso administrativo al catálogo.

Para habilitar a un nuevo residente, vincula su cuenta con su ficha de persona en Django Admin, asígnale su rol en la vivienda y registra un **Permiso por punto** con su persona y el portón autorizado. A partir de ese momento puede entrar con sus propias credenciales cada vez que se cumplan las condiciones de acceso.

## Referencia de la API

Todas las rutas de negocio requieren `Authorization: Bearer <access>`. Las cuatro colecciones maestras aceptan GET y POST. Cada ruta con `{id}/` acepta GET, PUT, PATCH y DELETE.

| Ruta bajo `/api/` | Alcance |
|---|---|
| `personas/` | El operador gestiona el catálogo. Cada persona puede consultar su propia ficha. |
| `terrenos/` | El operador mantiene los terrenos. Administradores, residentes y trabajadores consultan los vinculados. |
| `viviendas/` | El operador y el administrador del terreno mantienen viviendas. Los residentes consultan las que les corresponden. |
| `puntos-acceso/` | El operador y el administrador del terreno mantienen los puntos. Las personas vinculadas pueden ver el catálogo de ese terreno. |
| `viviendas/{id}/asignaciones/` | POST asigna un rol. GET devuelve los vínculos visibles. El residente ordinario ve su propio registro. |
| `accesos/solicitudes/` | POST con `punto`, `medio: "app"` y `cerca`, o con `punto`, `medio: "rfid"` y `uid` desde la cuenta operadora. Tarjeta ficticia conocida: `DEMO-RFID-LUZ`. |
| `historial/` | GET filtra por `persona`, `terreno`, `punto` y `fecha=AAAA-MM-DD` en hora de Chile continental. El operador ve todo, el administrador sus terrenos y cada persona sus propios intentos. |

**Cómo leer las respuestas.** Un 201 en solicitudes de acceso confirma que se guardó el intento. Revisa `permitido` y `motivo` para saber la decisión. Un 403 en una operación administrativa indica que la cuenta carece de autoridad. Las consultas de detalle fuera del listado visible devuelven 404. Los datos inválidos devuelven 400.

## Pruebas reproducibles

Con el servidor local encendido y los datos de clase cargados, abre una segunda terminal en el repositorio:

```powershell
npx --yes --package=apidog-cli@2.2.12 apidog run apidog/SmartConnect.json --lang en
npx --yes --package=apidog-cli@2.2.12 apidog run apidog/Rubrica.json --lang en
.\.venv\Scripts\python manage.py test
```

| Prueba | Resultado verificado |
|---|---|
| Acceso de Scarlett · Apidog CLI | 10 peticiones y 18 aserciones aprobadas. [Registro](docs/evidencia-apidog.txt) |
| Cuatro CRUD, JWT y asignaciones · Apidog CLI | 48 peticiones y 78 aserciones aprobadas. [Registro](docs/evidencia-rubrica.txt) |
| Backend · Django | 15 pruebas aprobadas, con autenticación, permisos, semilla, altas/rechazos e igualdad de los ID en la API y el panel. |

**Decisión para el siguiente avance.** Las autorizaciones se conceden por persona y punto. La app usa proximidad simulada y el operador representa al lector RFID. La integración física tendrá que registrar una confirmación del dispositivo después de la autorización.
