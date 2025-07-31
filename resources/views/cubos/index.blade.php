@extends('layouts.app')

@section('content')
<div class="container mt-4">
    <h3 class="mb-4">Explorador de Cubos SIS</h3>

    <div class="mb-3">
        <label for="cuboSelect" class="form-label">Selecciona un catálogo SIS:</label>
        <select id="cuboSelect" class="form-select">
            <option value="">-- Selecciona un catálogo --</option>
        </select>
    </div>

    <div class="mb-3 d-flex gap-2">
        <button class="btn btn-primary" onclick="cargarMiembros('CLUES')">Mostrar CLUES</button>
        <button class="btn btn-secondary" onclick="cargarMiembros('Variable')">Mostrar Variables</button>
    </div>

    <div id="tablaResultados" class="d-none">
        <div class="mb-3 input-group">
            <input type="text" id="buscador" class="form-control" placeholder="Buscar por nombre..." oninput="filtrarMiembros()">
            <button class="btn btn-outline-secondary" type="button" onclick="limpiarBuscador()">❌</button>
        </div>

        <div class="table-responsive">
            <table class="table table-bordered">
                <thead>
                    <tr><th>#</th><th>Nombre</th></tr>
                </thead>
                <tbody id="tablaCuerpo"></tbody>
            </table>
        </div>

        <nav>
            <ul class="pagination justify-content-center" id="paginacion"></ul>
        </nav>
    </div>
    <div id="spinnerCarga" class="text-center my-4 d-none">
        <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
            <span class="visually-hidden">Cargando...</span>
        </div>
        <p class="mt-2">Cargando información...</p>
    </div>
    
</div>
@endsection

@section('scripts')
<script>
const baseUrl = 'http://127.0.0.1:8070';
let miembrosGlobal = [];
let miembrosFiltrados = [];
let paginaActual = 1;
const porPagina = 8;

document.addEventListener('DOMContentLoaded', () => {
    fetch(`${baseUrl}/cubos_sis`)
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('cuboSelect');
            data.cubos_sis.forEach(catalogo => {
                const option = document.createElement('option');
                option.value = catalogo;
                option.textContent = catalogo;
                select.appendChild(option);
            });
        });
});

function cargarMiembros(jerarquia) {
    const catalogo = document.getElementById('cuboSelect').value;
    if (!catalogo) return alert('Selecciona un catálogo SIS');

    mostrarSpinner();

    fetch(`${baseUrl}/cubos_en_catalogo/${catalogo}`)
        .then(res => res.json())
        .then(data => {
            const cubo = data.cubos[0];
            console.log("📦 Cubo seleccionado:", cubo);

            const url = `${baseUrl}/miembros_jerarquia2?catalogo=${encodeURIComponent(catalogo)}&cubo=${encodeURIComponent(cubo)}&jerarquia=${encodeURIComponent(jerarquia)}`;

            fetch(url)
                .then(res => {
                    if (!res.ok) throw new Error("Error en la API");
                    return res.json();
                })
                .then(respuesta => {
                    miembrosGlobal = respuesta.miembros || [];
                    miembrosFiltrados = [...miembrosGlobal];
                    paginaActual = 1;
                    renderizarTabla();
                    document.getElementById('tablaResultados').classList.remove('d-none');
                })
                .catch(err => {
                    console.error("❌ Error al cargar miembros:", err);
                    alert("Error al cargar datos. Ver consola.");
                })
                .finally(() => {
                    ocultarSpinner();
                });
        });
}

function filtrarMiembros() {
    const texto = document.getElementById('buscador').value.toLowerCase().trim();

    miembrosFiltrados = miembrosGlobal.filter(m =>
        m.nombre && m.nombre.toLowerCase().includes(texto)
    );
    paginaActual = 1;
    renderizarTabla();

    // Coincidencia exacta o por inicio de nombre
    if (texto !== '') {
        const match = miembrosFiltrados.find(m =>
            m.nombre.toLowerCase() === texto || m.nombre.toLowerCase().startsWith(texto)
        );

        if (match) {
            setTimeout(() => {
                const fila = document.querySelector(`tr[data-nombre="${match.nombre}"]`);
                if (fila) {
                    fila.classList.add('table-success');
                    fila.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }, 100);
        }
    }
}


function limpiarBuscador() {
    document.getElementById('buscador').value = '';
    miembrosFiltrados = [...miembrosGlobal];
    paginaActual = 1;
    renderizarTabla();
}

function renderizarTabla() {
    const cuerpo = document.getElementById('tablaCuerpo');
    const paginacion = document.getElementById('paginacion');
    cuerpo.innerHTML = '';
    paginacion.innerHTML = '';

    const inicio = (paginaActual - 1) * porPagina;
    const datosPagina = miembrosFiltrados.slice(inicio, inicio + porPagina);

    if (datosPagina.length === 0) {
        cuerpo.innerHTML = `<tr><td colspan="2" class="text-center text-muted">No hay datos disponibles.</td></tr>`;
        return;
    }

    datosPagina.forEach((m, i) => {
        cuerpo.innerHTML += `
            <tr data-nombre="${m.nombre}">
                <td>${inicio + i + 1}</td>
                <td>${m.nombre}</td>
            </tr>`;
    });

    const totalPaginas = Math.ceil(miembrosFiltrados.length / porPagina);
    const maxPaginasVisibles = 5;
    const desde = Math.max(1, paginaActual - Math.floor(maxPaginasVisibles / 2));
    const hasta = Math.min(totalPaginas, desde + maxPaginasVisibles - 1);

    if (paginaActual > 1) {
        paginacion.innerHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="cambiarPagina(${paginaActual - 1})">«</a>
            </li>`;
    }

    for (let i = desde; i <= hasta; i++) {
        paginacion.innerHTML += `
            <li class="page-item ${i === paginaActual ? 'active' : ''}">
                <a class="page-link" href="#" onclick="cambiarPagina(${i})">${i}</a>
            </li>`;
    }

    if (paginaActual < totalPaginas) {
        paginacion.innerHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="cambiarPagina(${paginaActual + 1})">»</a>
            </li>`;
    }
}

function cambiarPagina(pagina) {
    paginaActual = pagina;
    renderizarTabla();
}

function mostrarSpinner() {
    document.getElementById('spinnerCarga').classList.remove('d-none');
}

function ocultarSpinner() {
    document.getElementById('spinnerCarga').classList.add('d-none');
}

</script>
@endsection


