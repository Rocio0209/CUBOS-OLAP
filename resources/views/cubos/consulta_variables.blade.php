@extends('layouts.app')

@section('content')

<link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet" />

<div class="container mt-4">
    <h3 class="mb-4">Consulta de Biológicos por CLUES</h3>

    <div class="mb-3">
        <label for="catalogoSelect" class="form-label">Selecciona un catálogo SIS:</label>
        <select id="catalogoSelect" class="form-select">
            <option value="">-- Selecciona un catálogo --</option>
        </select>
    </div>

    <div class="mb-3">
        <label for="cluesSelect" class="form-label">Selecciona CLUES (solo HG):</label>
        <select id="cluesSelect" class="form-select" multiple disabled>
            <option value="">-- Primero selecciona un catálogo --</option>
        </select>
    </div>

    <div class="mb-3">
        <button class="btn btn-secondary" onclick="cargarClues()" id="btnCargarClues" disabled>🔍 Cargar CLUES disponibles</button>
    </div>

    <div id="mensajeCluesCargadas" class="alert alert-info d-none">
        CLUES cargadas correctamente. Filtradas solo las que comienzan con HG.
    </div>

    <div class="mb-3">
        <button class="btn btn-primary mb-2" onclick="consultarBiologicos()" id="btnConsultar" disabled>Consultar Biológicos</button>
        <button class="btn btn-success mb-2 ms-2" onclick="exportarExcel()" id="btnExportar" disabled>Exportar a Excel</button>
    </div>

    <div id="spinnerCarga" class="text-center my-4 d-none">
        <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;"></div>
        <p class="mt-2">Consultando...</p>
    </div>

    <div id="resultadosContainer" class="d-none">
        <div class="alert alert-info" id="resumenConsulta"></div>
        
        <div class="table-responsive">
            <table class="table table-bordered table-striped" id="tablaResultados">
                <thead class="thead-dark">
                    <tr id="tablaHeader">
                        <!-- Encabezados se generarán dinámicamente -->
                    </tr>
                    <tr id="variablesHeader">
                        <!-- Subencabezados de variables se generarán dinámicamente -->
                    </tr>
                </thead>
                <tbody id="tablaResultadosBody">
                    <!-- Datos se insertarán aquí -->
                </tbody>
                <tfoot id="tablaFooter">
                    <!-- Totales se insertarán aquí -->
                </tfoot>
            </table>
        </div>
    </div>
</div>

<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
<script src="https://cdn.sheetjs.com/xlsx-0.20.0/package/dist/xlsx.full.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

@endsection

@section('scripts')
<script>
const baseUrl = 'http://127.0.0.1:8070';
let cuboActivo = null;
let cluesDisponibles = [];
let resultadosConsulta = [];
let apartadosBiologicos = [];

document.addEventListener('DOMContentLoaded', () => {
    $('#cluesSelect').select2({
        placeholder: "Selecciona una o más CLUES",
        width: '100%',
        allowClear: true
    });

    fetch(`${baseUrl}/cubos_sis`)
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('catalogoSelect');
            data.cubos_sis.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c;
                opt.textContent = c;
                select.appendChild(opt);
            });
        });

    document.getElementById('catalogoSelect').addEventListener('change', () => {
        const catalogo = document.getElementById('catalogoSelect').value;
        if (!catalogo) {
            resetearFormulario();
            return;
        }

        $('#btnCargarClues').prop('disabled', false);
        
        fetch(`${baseUrl}/cubos_en_catalogo/${catalogo}`)
            .then(res => res.json())
            .then(data => {
                cuboActivo = data.cubos[0];
            });
    });

    $('#cluesSelect').on('change', function() {
        const cluesSeleccionadas = $(this).val();
        if (cluesSeleccionadas && cluesSeleccionadas.length > 0) {
            $('#btnConsultar').prop('disabled', false);
        } else {
            $('#btnConsultar').prop('disabled', true);
        }
    });
});

function exportarExcel() {
    if (!resultadosConsulta || resultadosConsulta.length === 0) {
        alert("No hay datos para exportar.");
        return;
    }

    const workbook = XLSX.utils.book_new();
    const rows = [];

    // Encabezado
    const headers = ["CLUES", "Unidad Médica", "Entidad", "Jurisdicción", "Municipio"];
    const apartados = {};
    const variables = [];

    resultadosConsulta.forEach(res => {
        res.biologicos?.forEach(apartado => {
            apartado.variables.forEach(v => {
                const key = `${apartado.apartado} - ${v.variable}`;
                if (!variables.includes(key)) {
                    variables.push(key);
                    apartados[key] = apartado.apartado;
                }
            });
        });
    });

    headers.push(...variables);

    rows.push(headers);

    // Filas de datos
    resultadosConsulta.forEach(res => {
        const row = [
            res.clues,
            res.unidad?.nombre || "",
            res.unidad?.entidad || "",
            res.unidad?.jurisdiccion || "",
            res.unidad?.municipio || ""
        ];

        const valores = {};
        res.biologicos?.forEach(apartado => {
            apartado.variables.forEach(v => {
                const key = `${apartado.apartado} - ${v.variable}`;
                valores[key] = v.total;
            });
        });

        variables.forEach(v => {
        const valor = valores[v];
        row.push(typeof valor === "number" ? valor : 0);
    });

        rows.push(row);
    });

    const worksheet = XLSX.utils.aoa_to_sheet(rows);
    XLSX.utils.book_append_sheet(workbook, worksheet, "Biológicos");

    // Descargar archivo
    const fecha = new Date().toISOString().split("T")[0];
    XLSX.writeFile(workbook, `biologicos_${fecha}.xlsx`);
}

function resetearFormulario() {
    $('#cluesSelect').val(null).trigger('change').prop('disabled', true);
    $('#btnCargarClues').prop('disabled', true);
    $('#btnConsultar').prop('disabled', true);
    $('#btnExportar').prop('disabled', true);
    document.getElementById('mensajeCluesCargadas').classList.add('d-none');
    document.getElementById('resultadosContainer').classList.add('d-none');
}

function cargarClues() {
    const catalogo = document.getElementById('catalogoSelect').value;

    if (!catalogo || !cuboActivo) {
        alert("Selecciona un catálogo primero.");
        return;
    }

    mostrarSpinner();
    resetearFormulario();
    document.getElementById('mensajeCluesCargadas').classList.add('d-none');

    fetch(`${baseUrl}/miembros_jerarquia2?catalogo=${encodeURIComponent(catalogo)}&cubo=${encodeURIComponent(cuboActivo)}&jerarquia=CLUES`)
        .then(res => res.json())
        .then(data => {
            const select = $('#cluesSelect');
            select.empty();
            
            if (data.miembros && data.miembros.length > 0) {
                // Filtrar solo CLUES que comienzan con HG
                cluesDisponibles = data.miembros
                    .map(m => m.nombre)
                    .filter(clues => clues.startsWith('HG'));
                
                if (cluesDisponibles.length === 0) {
                    alert("No se encontraron CLUES que comiencen con HG en este cubo.");
                    select.prop('disabled', true);
                    return;
                }
                
                cluesDisponibles.forEach(clues => {
                    select.append(new Option(clues, clues));
                });
                
                select.prop('disabled', false);
                select.trigger('change');
                
                document.getElementById('mensajeCluesCargadas').classList.remove('d-none');
            } else {
                alert("No se encontraron CLUES en este cubo.");
                select.prop('disabled', true);
            }
        })
        .catch(err => {
            console.error("Error al cargar CLUES:", err);
            alert("Ocurrió un error al cargar las CLUES.");
        })
        .finally(() => ocultarSpinner());
}

async function consultarBiologicos() {
    const cluesSeleccionadas = $('#cluesSelect').val();
    const catalogo = document.getElementById('catalogoSelect').value;
    
    if (!cluesSeleccionadas || cluesSeleccionadas.length === 0) {
        alert("Por favor selecciona al menos una CLUES primero.");
        return;
    }

    mostrarSpinner();
    document.getElementById('resultadosContainer').classList.add('d-none');

    try {
        const response = await fetch(`${baseUrl}/biologicos_normalizados_con_migrantes2`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                catalogo: catalogo,
                cubo: cuboActivo,
                clues_list: cluesSeleccionadas
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `Error HTTP ${response.status}`);
        }

        resultadosConsulta = data.resultados;
        mostrarResultadosBiologicos(data);
        document.getElementById('btnExportar').disabled = false;

    } catch (error) {
        console.error("Error completo:", error);
        document.getElementById('resultadosContainer').classList.remove('d-none');
        document.getElementById('resumenConsulta').innerHTML = `<strong>Error:</strong> ${error.message}`;
    } finally {
        ocultarSpinner();
    }
}

function mostrarResultadosBiologicos(data) {
    const container = document.getElementById('resultadosContainer');
    const resumen = document.getElementById('resumenConsulta');
    const tablaHeader = document.getElementById('tablaHeader');
    const variablesHeader = document.getElementById('variablesHeader');
    const tablaBody = document.getElementById('tablaResultadosBody');
    const tablaFooter = document.getElementById('tablaFooter');

    // Limpiar tablas anteriores
    tablaHeader.innerHTML = '';
    variablesHeader.innerHTML = '';
    tablaBody.innerHTML = '';
    tablaFooter.innerHTML = '';
    
    // Generar resumen
    resumen.innerHTML = `
        <strong>Consulta realizada:</strong> 
        Catálogo: ${data.catalogo} |
        Cubo: ${data.cubo} |
        CLUES consultadas: ${data.total_clues_procesadas} |
        CLUES no encontradas: ${data.total_clues_no_encontradas || 0}
    `;

    // Procesar datos para la tabla
    const todasVariables = {};
    const totalesVariables = {};
    const datosPorClues = {};

    // Recopilar todas las variables y sus apartados
    data.resultados.forEach(resultado => {
        if (resultado.biologicos) {
            resultado.biologicos.forEach(apartado => {
                apartado.variables.forEach(variable => {
                    const nombreVariable = variable.variable;
                    if (!todasVariables[nombreVariable]) {
                        todasVariables[nombreVariable] = {
                            apartado: apartado.apartado,
                            total: 0
                        };
                        totalesVariables[nombreVariable] = 0;
                    }
                });
            });
        }
    });

    // Procesar datos por CLUES
    data.resultados.forEach(resultado => {
        const clues = resultado.clues;
        datosPorClues[clues] = {
            nombre: resultado.unidad?.nombre || '',
            entidad: resultado.unidad?.entidad || '',
            jurisdiccion: resultado.unidad?.jurisdiccion || '',
            municipio: resultado.unidad?.municipio || '',
            variables: {}
        };

        // Inicializar todas las variables como vacías para esta CLUES
        Object.keys(todasVariables).forEach(variable => {
            datosPorClues[clues].variables[variable] = '';
        });

        // Llenar los valores reales
        if (resultado.biologicos) {
            resultado.biologicos.forEach(apartado => {
                apartado.variables.forEach(variable => {
                    datosPorClues[clues].variables[variable.variable] = variable.total;
                    totalesVariables[variable.variable] += variable.total;
                });
            });
        }
    });

    // Generar encabezados de tabla
    tablaHeader.innerHTML = `
        <th rowspan="2">CLUES</th>
        <th rowspan="2">Unidad Médica</th>
        <th rowspan="2">Entidad</th>
        <th rowspan="2">Jurisdicción</th>
        <th rowspan="2">Municipio</th>
    `;

    // Agrupar variables por apartado
    const apartados = {};
    Object.entries(todasVariables).forEach(([variable, info]) => {
        if (!apartados[info.apartado]) {
            apartados[info.apartado] = [];
        }
        apartados[info.apartado].push(variable);
    });

    // Agregar columnas por apartado
    Object.entries(apartados).forEach(([apartado, variables]) => {
        tablaHeader.innerHTML += `<th colspan="${variables.length}">${apartado}</th>`;
        
        // Agregar subencabezados de variables
        variables.forEach(variable => {
            variablesHeader.innerHTML += `<th>${variable}</th>`;
        });
    });

    // Llenar datos de la tabla
    Object.entries(datosPorClues).forEach(([clues, datos]) => {
        const fila = document.createElement('tr');
        fila.innerHTML = `
            <td>${clues}</td>
            <td>${datos.nombre}</td>
            <td>${datos.entidad}</td>
            <td>${datos.jurisdiccion}</td>
            <td>${datos.municipio}</td>
        `;

        // Agregar valores de variables agrupadas por apartado
        Object.values(apartados).forEach(variables => {
            variables.forEach(variable => {
                fila.innerHTML += `<td>${datos.variables[variable] || '0'}</td>`;
            });
        });

        tablaBody.appendChild(fila);
    });

    // Agregar fila de totales
    const filaTotales = document.createElement('tr');
    filaTotales.innerHTML = `
        <td colspan="5"><strong>Total de pacientes</strong></td>
    `;

    // Agregar totales por variable, agrupados por apartado
    Object.values(apartados).forEach(variables => {
        variables.forEach(variable => {
            filaTotales.innerHTML += `<td><strong>${totalesVariables[variable] || 0}</strong></td>`;
        });
    });

    tablaFooter.appendChild(filaTotales);

    // Mostrar resultados y habilitar exportación
    container.classList.remove('d-none');
    $('#btnExportar').prop('disabled', false);
}



function mostrarSpinner() {
    document.getElementById('spinnerCarga').classList.remove('d-none');
}

function ocultarSpinner() {
    document.getElementById('spinnerCarga').classList.add('d-none');
}
</script>
@endsection