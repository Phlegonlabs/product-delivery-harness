<p align="center">
  <img src="./assets/readme-cover-en.png" alt="Product Delivery Harness — define, diseña, entrega y verifica" width="100%">
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-TW.md">繁體中文</a> | <a href="README.zh-CN.md">简体中文</a> | <strong>Español</strong>
</p>

<p align="center">
  <a href="https://github.com/Phlegonlabs/product-delivery-harness/actions/workflows/harness-ci.yml"><img alt="CI" src="https://github.com/Phlegonlabs/product-delivery-harness/actions/workflows/harness-ci.yml/badge.svg"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-0.75.4-059669?style=flat-square">
</p>

# Product Delivery Harness

Skills para convertir ideas de producto y solicitudes de cambio en software verificado con Codex, Claude Code, Pi u otro host compatible. Definición, diseño, implementación, seguridad y configuración externa conservan sus propias fuentes, pruebas y decisiones del owner.

## Instalación

Necesitas Python 3.10+, Git y un host que descubra `~/.agents/skills/`. En Windows, ejecuta `./install.sh` desde Git Bash.

```bash
git clone https://github.com/Phlegonlabs/product-delivery-harness.git
cd product-delivery-harness
./install.sh
```

El instalador bloquea el destino y prepara solo archivos del bundle registrados en el índice de Git. Guarda los IDs gestionados actuales y heredados bajo `~/.agents/skill-backups/product-delivery-harness/`; después verifica cada ruta y byte instalado.

Rechaza enlaces inseguros y archivos de origen inesperados. Los marcadores de propiedad limitan el rollback a ese intento y preservan rutas ajenas y backups anteriores. El recibo de origen registra el SHA y los cambios sin commit.

El instalador copia scripts, referencias, assets y plantillas. Los tests quedan en el checkout de origen; ejecútalos allí. Instala las dependencias Python fijadas antes de validar:

```bash
python -m pip install -r skills/delivery-harness/requirements-test.txt
```

Actualiza con el mismo instalador, nunca mediante copia directa. Obtén autorización, detén las sesiones relevantes y conserva los backups; abre una sesión nueva tras verificar el éxito. Una instalación fallida se revierte. Si falla la verificación posterior, ejecuta el instalador desde el tag de la versión anterior.

Al actualizar desde 0.23 o anterior, el instalador archiva los directorios heredados bajo sus IDs originales en el mismo backup: `full-harness` → `delivery-harness`, `prd-builder` → `product-definition-builder`, `product-design-builder` → `design-system-compiler`. Desde 0.73.0 el instalador también retira `code-security-review` (ahora `delivery-harness/references/security-review.md`), `product-activation` (ahora el registro de despliegue y `references/external-setup.md`) y `seo-growth-review` (ahora `growth-review`).

El trabajo UI también necesita los árboles externos exactos de `frontend-design` e `impeccable` fijados en el [manifest de dependencias](skills/delivery-harness/assets/external-skill-dependencies.json). Sigue las rutas de instalación registradas y ejecuta `check_external_skill_dependencies.py`. Revisa los cambios antes de actualizar los hashes del árbol completo. Los Skill Bindings conservan las elecciones del owner; nunca sustituyas un skill silenciosamente.

## Empieza aquí

| Punto de partida | Skill | Resultado |
| --- | --- | --- |
| Idea de producto | `product-definition-builder` | PRD, arquitectura, stack y obligaciones TEST aprobados |
| Product Definition aprobada con UI (el diseño puede empezar tras el Product Thesis con una ronda de exploración opcional) | `ui-design-builder` | Direcciones, journey maps, HiFi completo, evidencia de navegador y Visual Approval |
| HiFi aprobado que requiere design system | `design-system-compiler` | Par congelado y HTML derivado vinculado al origen |
| Implementación o mantenimiento acotado | `delivery-harness` | Trabajo Direct o PLAN/RUN gestionado; las missions de UI siguen los journeys aprobados |
| Producto publicado con alguna superficie descubrible | `growth-review` | Revisión de crecimiento por superficie, de solo lectura, con seguimientos asignados |

Los cinco skills centrales y los cuatro independientes requieren una petición explícita que nombre el skill, como `$delivery-harness`. Se permite continuar un flujo ya solicitado. Las tareas ordinarias no inician rutas Harness, sincronización documental, registros Epic ni PLAN/RUN. La instalación y los documentos existentes no activan el flujo. El skill solicitado conserva sus controles y dependencias; una nueva etapa principal requiere una petición explícita. Codex usa `allow_implicit_invocation: false`; los demás hosts respetan el mismo límite.

Usa la [selección de referencias](skills/delivery-harness/references/reference-selection.md) y el [catálogo opcional](skills/delivery-harness/references/option-library/README.md) para decisiones pertinentes sin resolver o contexto de decisiones adoptadas. No son requisitos previos ni conceden autoridad para ejecutar; las decisiones y aprobaciones existentes siguen vigentes.

## Prompts típicos

Usa `$skill-name` en Codex o pide el skill por nombre en tu host. Indica el alcance exacto de escritura y el resultado local o remoto.

```text
Usa $product-definition-builder para definir este producto, incluyendo arquitectura frontend/backend completa, decisiones de data/auth/deployment, stack coherente, comportamiento UI, release targets, tests y Product Definition Approval. Detente antes del diseño de UI.
```

```text
La Product Definition está aprobada. Usa $ui-design-builder con el contrato `ui-design/3` y $frontend-design obligatorio. Ejecuta el preflight del producto, lee directamente el PRD UI Surface Contract y muestra tres direcciones materialmente distintas sobre los mismos casos representativos para que yo elija.
```

```text
Elegí una dirección. Continúa $ui-design-builder con $frontend-design: crea el HiFi conectado completo, ejecuta el preflight de completitud del HiFi y luego critique y audit de $impeccable solo con su autorización más scoring H1-H9. Pide una sola Visual Approval completa de texto, estructura, menús de producto, pestañas, visuales y tokens, después usa $design-system-compiler para el par obligatorio `design-system/4` y su HTML derivado congelado.
```

```text
Usa $delivery-harness para implementar el plan aprobado. Crea una branch y haz commit del cambio verificado, pero no hagas push ni abras un PR.
```

```text
La entrega está completa. Usa $delivery-harness para ejecutar las filas de configuración externa de docs/DEPLOYMENT.md para los targets de producción, configura solo las acciones exactas que apruebo, verifica cada resultado por read-back y registra el estado de Measurement Sources.
```

```text
Usa $growth-review para leer cada superficie de este producto publicado con su propia lente, reconciliar las fuentes de medición verificadas con el Growth Contract, priorizar oportunidades basadas en evidencia por superficie y enrutar cada cambio propuesto sin modificar el producto ni las cuentas externas.
```

## Qué incluye

| Skill | Responsabilidad |
| --- | --- |
| `product-definition-builder` | `PRD.md` con `## Ambition`, la fila `Shape` del At a Glance y `## Growth Contract`, `architecture.md`, `stack-decisions.md`, investigación, deltas de PRD por ronda y Product Definition Approval; el perfil de entrega `program` para productos de muchos módulos (PRD de programa más un [paquete por módulo](skills/product-definition-builder/assets/templates/PROGRAM_PRD.template.md), validado por módulo), el [contrato de funciones de IA](skills/product-definition-builder/references/ai-feature-contract.md) y el patrón de monolito modular para productos de muchos módulos |
| `ui-design-builder` | `docs/design/ui-design.md`, estudios de dirección y paquete HiFi completo aprobado |
| `design-system-compiler` | `design-system.md` / `design-system.json` congelados y `design-system-preview.html` |
| `delivery-harness` | Selección de ruta, autorización, tareas, integración, verificación, la lente de seguridad, configuración externa y fuentes de medición en `docs/DEPLOYMENT.md` (incluidas la [configuración de administración de GA4](skills/delivery-harness/references/ga4-admin-setup.md) y la del proveedor de IA), [presupuestos de rendimiento y coste](skills/delivery-harness/references/performance-and-cost-budget.md), verificación nativa que limpia lo que construyó, PLAN/RUN cuando hace falta, las stage cards del modo gestionado y el launch brief para ejecución autónoma |
| `growth-review` | Una lente por superficie según el Surface Catalog: motores de búsqueda y de respuestas, listados de tiendas, registries y directorios, plataformas de bots y las cuentas que gestiona el equipo; modos `pre_launch`, `baseline`, `growth_review` de Day 7 y Day 30 y `traffic_drop`, salida inline |

## Skills independientes

[Go To Market](standalone-skills/go-to-market/SKILL.md) selecciona canales y experimentos, mantiene un messaging record por proyecto, amplía la Launch Window del PRD en un launch runbook, redacta lifecycle messaging para los mecanismos de re-engagement del Growth Contract y prepara borradores, assets, calendarios y variantes por canal con dos hooks, incluidos canales de desarrolladores y listings de tiendas.

[Customer Discovery](standalone-skills/customer-discovery/SKILL.md) planifica entrevistas con usuarios, sintetiza notas anonimizadas y entrega hallazgos candidatos `RA-*` a la Product Definition. [README Studio](standalone-skills/readme-studio/SKILL.md) redacta READMEs con demostraciones reales. [Release Packager](standalone-skills/release-packager/SKILL.md) verifica artifacts de release y rutas de instalación del consumidor.

Estos cuatro directorios completos requieren registro separado en el host; `install.sh` instala solo los cinco skills centrales. Registro, builds, descargas, firmas, publicación, programación y cambios de cuenta conservan su autorización. Reutiliza los registros de producto y medición; no añadas una ronda de revisión.

## Cómo encaja el sistema

```mermaid
flowchart LR
  Product["Product Definition, Ambition y Growth Contract con aprobación del owner"] --> UI["Direcciones UI, journey maps y HiFi completo"] --> Design["Visual Approval y par de diseño obligatorio"]
  Product -.->|"ronda de exploración R0 opcional tras el Product Thesis"| UI
  Product -->|"sin UI o mejora o mantenimiento acotado"| Harness["Entrega Direct o gestionada"]
  Design -->|"las missions siguen los journeys aprobados"| Harness
  Harness --> Review["Una revisión conjunta sobre el SHA final"] --> Tests["Una validación final amplia"] --> C["Candidato fijo C"]
  C -->|managed| A["Solo Managed: archivo A"] --> Publish["Publicación autorizada y Preview aplicable"]
  C -->|direct| Publish
  Publish --> Main["Landing main exact-SHA autorizado por separado"] --> Setup["Readback de configuración externa por target"] --> Outcome["Resultados medidos y growth review opcional"]
```

La entrega inicial con UI requiere diseño y todas las autorrevisiones aplicables antes de ejecutar Harness. Sigue la [autorrevisión del autor](skills/delivery-harness/references/pre-delivery-self-review.md) en las salidas existentes de Product, dirección y HiFi indicadas abajo.

## Reglas operativas

Las reglas siguientes se aplican dentro de flujos de skills solicitados explícitamente.

El núcleo toma una decisión de tamaño: un escritor y una secuencia coherente de verificación permanecen en Direct. Misiones escribibles independientes, handoff duradero o un grafo acotado de corrección usan PLAN/RUN. Las missions son lotes de funcionalidad; las tasks finas conservan commits atómicos. Con `Delivery profile: mvp` elegido por el owner, un proyecto pequeño o un MVP de una semana usa la ruta comprimida: aprobación de stack y producto en una sola llamada, HiFi solo para las superficies requeridas, una revisión de entrega combinada con Final UI Acceptance integrada y como máximo cuatro gates del owner; la evidencia, la seguridad y la protección de datos no cambian.

- [Entrada y handoff](skills/delivery-harness/references/governance/task-and-handoff.md): inspecciona instrucciones y fuentes actuales; la identidad cargada desconocida sigue siendo desconocida. Una run gestionada se reanuda desde el bloque `Next` del inspector; un RUN `running` estancado necesita antes una decisión del owner, y una run autónoma parte de un launch brief firmado.
- [Delegación](skills/delivery-harness/references/delegation-contract.md): la configuración de agentes y AGENTS eligen executor, modelo, esfuerzo y fallback. Un escritor posee cada checkout; los workers asignados nunca delegan. Los briefs y los paquetes de revisión se dimensionan antes del lanzamiento a los límites de tiempo, turnos y bytes de la ruta. Un plazo vencido sin veredicto queda bloqueado por entorno y se vuelve a despachar como llamadas acotadas más pequeñas.
- [Verificación](skills/delivery-harness/references/verification-gates.md): vincula la evidencia requerida al candidato exacto; capacidad o evidencia ausente sigue bloqueada. La revisión independiente de una matriz de navegador es verificar y luego muestrear: verifica los recibos, inspecciona las filas FAIL y las marcadas por diff, y muestrea las filas PASS. La sonda de capacidad del navegador se reutiliza durante el resto de la sesión.
- [Publicación y promoción](skills/delivery-harness/references/branch-promotion-contract.md): conserva targets, autorizaciones y readback remoto exactos; nunca uses force-push.
- [Mantenimiento del origen](skills/delivery-harness/references/governance/source-maintenance.md): verificaciones atómicas enfocadas y una matriz completa por candidato fijo.

Antes de cada handoff, comprueba hashes de origen (source hashes), el Epic y la coherencia documental, y reescribe el bloque `## Handoff` del Epic (etapa, aprobaciones vigentes, trabajo restante, siguiente acción); cada entrada de skill lee ese bloque primero. `docs/tasks.md` deriva de RUN; no se edita a mano el contenido generado. [Sincronización documental](skills/delivery-harness/references/document-sync-contract.md), [reparaciones acotadas](skills/delivery-harness/references/bounded-enhancement.md) y [aceptación de entrega](skills/delivery-harness/references/delivery-acceptance-contract.md) poseen estas reglas.

| Etapa | Revisión predeterminada y condición de parada |
| --- | --- |
| Product Definition | Una lectura de la Product Thesis antes de las decisiones cerradas. Una autorrevisión del paquete completo después de redactar y reconciliar la investigación; recheck de cambios afectados antes de la aprobación del owner; después una revisión independiente de solo lectura del PRD y un recheck acotado, y el owner decide con una guía de diez preguntas. Discovery pregunta un segmento Ambition, `PRD.md` lleva `## Ambition`, y cada ronda del PRD publica un delta alineado con su Epic. La fila `Shape` del At a Glance declara el track, la superficie acompañante y la consola, y el checker la valida. `## Growth Contract` registra el north star, el re-engagement, las discovery surfaces y la launch window. El presupuesto del paquete es la autorrevisión, una revisión independiente y un recheck acotado; los defectos posteriores se vuelven reparaciones aisladas con revisión acotada. |
| Direcciones | El mismo autor comprueba y repara los estudios renderizados antes de la selección del owner. Tres estudios; modificar añade un estudio revisado de la dirección elegida y una decisión; rechazar inicia otro conjunto. |
| HiFi | Tras el preflight de completitud, el mismo autor revisa y repara antes de la revisión independiente. La autorrevisión se guía con herramientas: ejecuta el driver de matriz, corrige los FAIL de geometría y los errores de consola, y lee los renders de las páginas cambiadas. Una ronda diagnóstica, una reparación consolidada y una revisión del alcance afectado. Cobertura obligatoria de navegador, Impeccable `critique` **y** `audit`, media H1–H9 redondeada **mínima de 85** y cada dimensión **mínima de 80**, después Visual Approval. Los casos intactos se arrastran por render fingerprint (geometría más estilos calculados), no por bytes de página, con su identidad. La etapa conserva el mismo presupuesto de dos revisiones; los defectos posteriores se vuelven reparaciones aisladas con una revisión acotada del diff de reparación, con un máximo de dos revisiones acotadas. Una fila aún abierta pasa entonces a Visual Approval como advisory o block listado. |
| Entrega | `review_policy: final_candidate`: una revisión conjunta de código, visual si hay UI y seguridad en el SHA final fijo (navegador real para UI), con hallazgos triados en blocking y notes, más un recheck acotado. Tras el recheck, cada defecto restante o nuevo se vuelve una reparación acotada con su verifier enfocado y una revisión acotada solo del diff de reparación (hallazgo, diff de reparación, consumidores directos); la lente de seguridad se une cuando el diff toca un límite de confianza, un PASS acotado revincula las rutas reparadas y las revisiones acotadas no gastan intentos. Sin nueva Final UI Acceptance salvo que la reparación toque una superficie UI, y entonces solo esa superficie: recaptura sus entradas, arrastra el resto por render fingerprint y juzga el parity empezando por el diff (`parity_capture.py` clasifica los pares); la validación final amplia corre una vez por candidato al final. Los intentos bloqueados por entorno no gastan presupuesto. |
| Release | Una instrucción del owner puede nombrar varias acciones exactas. El archivo A y el SHA main S con árbol idéntico heredan evidencia verificada según las reglas siguientes. Un árbol distinto es otro candidato. |
| Configuración externa | `docs/DEPLOYMENT.md` guarda una fila External Console Setup por acción y la tabla Measurement Sources. Verifica autorización, readback independiente y comportamiento aplicable por target; preparación y readiness de producción siguen separados. |

Omitir `review_policy` conserva el comportamiento histórico `per_mission`. Preserva pins PLAN/RUN y aprobaciones anteriores; renombrar un nodo nunca reinicia los intentos consumidos. Agotado el presupuesto, los defectos restantes reciben reparaciones aisladas con una revisión acotada de cada diff de reparación; no hay ronda de revisión extra. Los diffs ejecutables exigen seguridad; sin ella informa `UNVALIDATED`, nunca PASS. Un diff de solo docs, copy, Epic, evidencia o bookkeeping registra `security: not_applicable (<reason>)` con la lista de rutas. Un PASS arrastrado con alcance disjunto conserva su SHA de origen y nunca se rotula como fresh. La primera revisión HiFi ejecuta la matriz base. Muestrea los ejes de estrés en casos representativos: texto al 200 %, forced colors, copy largo, anchos intermedios, reflow a 320 px y reduced motion. Una captura por caso superficie × estado × target sirve a todas las observaciones de ese caso. Una superficie UI del PRD puede declarar `derivedStates`: un overlay o subestado con el mismo layout. Cada uno se captura una vez, en el target más pequeño de su superficie. Cada intención de motion deja un frame de trigger, un frame de estado final y una comprobación de duración con reduced motion en un target representativo. El driver de matriz, `hifi_matrix_capture.py`, recorre toda la matriz en un solo contexto de navegador. Añade una sonda de geometría, un render fingerprint, arrastre desde una ejecución anterior y ejes muestreados, y escribe un resultado `ui-output/3`. La revisión posterior repite critique y audit en páginas y estados afectados, y vuelve a observar solo los casos cuyo render fingerprint cambió. Empieza por el diff: las filas idénticas se registran solas y el reviewer juzga las marcadas. El arrastre conserva la matriz completa.

Impeccable sigue siendo obligatorio para HiFi, pero no es el reviewer predeterminado de implementación de solo lectura. Su workflow requiere autorización separada para subagents, navegador/server, snapshots y descargas opcionales. Producto, stack, dirección y Visual Approval siguen con sus owners. El Visual Approval del owner, también con seguimientos, cierra la ronda de diseño; las filas abiertas pasan a seguimientos del Epic. Una ronda termina con el pin de bundle de su entrada; el drift de instalación a mitad de ronda se registra y no bloquea.

## Adaptador general de runtime

Los drivers actuales son `subagents` y `sequential_parent`; el [adaptador runtime](skills/delivery-harness/references/runtime-adapters.md) los relaciona con herramientas nativas observadas. La ejecución del parent no sustituye la revisión independiente. Los verifiers host usan permisos del usuario actual, sin confinamiento del sistema de archivos ni de red. La capacidad no concede acciones.

Conserva los doce [permisos de acción](skills/delivery-harness/references/execution-state-model.md#authorization-action-ledger):

```text
invoke_external_runtime, spawn_subagents, create_user_owned_tasks,
create_local_worktrees, create_app_managed_worktrees, create_local_branches,
create_local_commits, integrate_locally, push, archive_worker_tasks,
remove_worktrees, delete_branches
```

Los RUN actuales cierran en `local_only`, con `push` false y `pushed_head_sha` null. Publicación, landing protegido, despliegue, instalación, archivo y limpieza conservan sus autorizaciones separadas. Una misión que pasa devuelve `WORKER_RESULT`; una misión bloqueada o fallida devuelve el resultado del nodo del grafo con `worker_result: null`, y el parent conserva la autoridad de validación, revisión e integración.

## Estructura del repositorio

| Ruta | Propósito |
| --- | --- |
| `skills/` | Cinco skills canónicos, referencias, assets, plantillas y tests de origen |
| `standalone-skills/` | Skills opcionales registrados por separado |
| `assets/` | Portadas del README |
| `docs/` | Índice vigente y registros de tareas |
| `.github/workflows/harness-ci.yml` | CI del candidato exacto |
| `install.sh` | Instalación y actualización verificadas del bundle |

## Mantén los skills

Edita las fuentes canónicas y actualiza las descripciones de los cuatro READMEs en el mismo cambio. Selecciona pruebas enfocadas y casos negativos según los archivos cambiados. Ejecuta desde el checkout de origen:

```bash
python skills/delivery-harness/scripts/check_skill_spec.py
python -m unittest discover -s skills/delivery-harness/scripts/tests -p "test_skill_contract.py"
python skills/delivery-harness/scripts/docs_weight.py
git diff --check
```

La [matriz requerida](skills/delivery-harness/references/governance/source-maintenance.md#required-verification) corre una vez en CI sobre el candidato fijo. Ejecútala localmente solo si CI no está disponible. Conserva cobertura de navegador y nativa; fallos o entradas cambiadas requieren rechecks afectados. La evidencia reutilizada conserva su origen.

## Releasing

Sigue el [Git flow del origen](skills/delivery-harness/references/governance/source-maintenance.md#git-flow) y la [verificación requerida](skills/delivery-harness/references/governance/source-maintenance.md#required-verification). Lleva el candidato revisado mediante el PR requerido a `main` protegido y etiqueta ese commit con `v<version>`. Actualiza estas superficies juntas:

1. Versión de `package.json` y `skills/delivery-harness/VERSION`.
2. Badges y entradas de la versión actual en los cuatro READMEs.
3. `required_harness_version` en `assets/templates/MISSION_RUNBOOK.template.md` del skill delivery.
4. Los tests siguen derivando la versión de `VERSION`, sin nuevos literales fijos.

A debe ser hijo directo de C. Hereda la evidencia solo tras verificar el archivo exacto vinculado al recibo. Solo pueden cambiar los movimientos de coordinación/evidencia registrados, el `docs/tasks.md` generado opcional, `docs/DOCUMENTS.md` y `ARCHIVE_RECEIPT.json`. Las demás rutas quedan intactas. Retén el SHA revisado de C y los orígenes de los resultados. La evidencia heredada no es una ejecución nueva en A. Un SHA main S creado por el servidor con árbol idéntico hereda la evidencia y su origen original. La igualdad sola no exige repetir suites ni seguridad. Un árbol distinto requiere verificar otro candidato.

Publicar exige el SHA y la rama exactos autorizados por el owner, push sin force y readback remoto. Una instrucción puede vincular esas autorizaciones; detente ante drift o gates fallidos. Tras verificar el release formal, actualiza un bundle instalado distinto con el instalador oficial, en reposo y con backup y verificación. Un badge no demuestra instalación ni despliegue.

## Seguridad y protección de datos

Mantén credenciales y datos de usuario fuera del repositorio. Preserva archivos ajenos, worktrees y backups; borrar o sustituir requiere autorización exacta del owner. La revisión de solo lectura no instala scanners, cambia código ni sondea targets vivos sin otro alcance. Consulta [seguridad](skills/delivery-harness/references/security-review.md) y [protección de datos](skills/delivery-harness/references/governance/development-rules.md#protect-local-data).

## Licencia

[MIT](LICENSE). Conserva licencias y atribución de código y assets de terceros.

## Historial de versiones

- **0.75.4** — Revisión del contenido de seguridad. `security-review.md` ya no permite una revisión de seguridad inline en la ruta directa, toma los trust boundaries de las filas de Security Requirements del PRD y sus trazas `TEST-*`, confirma la prueba de denegación de cada boundary planificado en el head revisado, copia `scope` del packet tal cual y explica cómo se registra un intento bloqueado por el entorno. El índice de la option library dirige la revisión de alcance exacto al security lens de delivery-harness en lugar del retirado `code-security-review`, y `security.md` coloca sus controles antes de la lista de fuentes.

- **0.75.3** — Correcciones de plantillas detectadas en la adopción de 0.75.2. `PROJECT_AGENTS.template.md` apunta ahora las reglas de runs gestionadas a `project-operating-rules.md` en lugar de una sección que la plantilla nunca tuvo; el ejemplo de presence de `DEPLOYMENT.template.md` ya no lo marca `check_deployment.py` como placeholder sin rellenar; la guía de GA4 indica que una fila `MS-*` queda en `available` hasta que Realtime o DebugView muestran el evento.

- **0.75.2** — Lectura más ligera. `docs_reading_budget.py` mide las palabras que un agente debe leer antes de actuar en cada punto de entrada (enlaces obligatorios y condicionales por separado, `--budget N` para CI). Siete referencias se comprimieron sin eliminar ninguna regla: el output contract del PRD, las verification gates, el modelo de estado de ejecución, design input updates, el output contract de UI, el architecture playbook y la guía de entrevista (unas 8.600 palabras menos); `design-input-updates.md` se lee ahora solo para trabajo de UI, lo que quita 3,7k palabras a cada run directa y gestionada. El total contado queda por debajo de v0.74.1 pese a las adiciones de esta semana.

- **0.75.1** — Más ligero por defecto. Las guías que solo necesita un paquete fijado a una versión anterior (`legacy-pins.md`, la guía de wireframes `ui-design/2` retirada) pasan a `references/legacy/`, se leen solo cuando el paquete fija una versión anterior y ya no cuentan en el docs weight (6.481 palabras excluidas; se siguen instalando). `docs_duplicates.py` encuentra frases repetidas entre archivos de skills y puede mantener un límite en CI con `--fail-over`.

- **0.75.0** — El perfil de entrega `program` para productos a escala ERP. Un PRD de programa contiene el mapa de módulos con orden de dependencias, datos compartidos propiedad de un kernel, glosario, roles y segregación de funciones, supuestos de capacidad, registro de integraciones y procesos de negocio entre módulos (`TEST-E2E-*` sobre un fixture fijo `PF-BASE`, incluido el cierre de periodo); cada módulo tiene su propio PRD y arquitectura en `docs/product/modules/<id>/` con IDs con ámbito (`PRD-INV-001`), una tabla de reglas de negocio `BR-*` con estados de documento, una matriz de permisos y un catálogo de informes; la arquitectura del programa añade Migration and Cutover con `TEST-MIG-*`. `check_product_package.py` valida el programa una vez y cada módulo (`--module <id>`), avisa cuando el `Program revision` de un módulo está desactualizado y deja `standard`/`mvp` sin cambios. Los módulos se entregan con un Epic y un PLAN/RUN a la vez en el orden del mapa; la entrevista añade las preguntas de programa; una entrada de cumplimiento por jurisdicción se suma a la option library.

Versiones anteriores: [CHANGELOG.md en inglés](CHANGELOG.md).
