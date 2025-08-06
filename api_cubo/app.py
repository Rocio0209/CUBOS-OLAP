from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi import Body
import win32com.client
import pythoncom
import pandas as pd
import math
from typing import List
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import unquote  # Importación necesaria para decodificar URLs
from typing import List, Optional
from pydantic import BaseModel
from fastapi import Body

from fastapi import HTTPException
from openpyxl import load_workbook
import io
import os
import json



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def obtener_valor_dim(cadena_conexion, cubo_mdx, dim, clues):
    mdx = f"""
    SELECT
    NON EMPTY {{ [{dim}].[{dim}].Members }} ON ROWS,
    {{ [Measures].DefaultMember }} ON COLUMNS
    FROM {cubo_mdx}
    WHERE ([CLUES].[CLUES].&[{clues}])
    """
    df = query_olap(cadena_conexion, mdx)
    if not df.empty:
        valor = str(df.iloc[0, 0]) if pd.notna(df.iloc[0, 0]) else None
        if valor:
            return valor.split("].[")[-1].replace("]", "").strip()
    return None


def crear_conexion(catalogo: str = None):
    pythoncom.CoInitialize()
    conn = win32com.client.Dispatch("ADODB.Connection")

    cadena = (
        "Provider=MSOLAP.8;"
        "Data Source=pwidgis03.salud.gob.mx;"
        "User ID=SALUD\\DGIS15;"
        "Password=Temp123!;"
        "Persist Security Info=True;"
        "Connect Timeout=60;"
    )

    if catalogo:
        cadena += f"Initial Catalog={catalogo};"

    conn.Open(cadena)
    return conn



def ejecutar_query_lista(conn, query, campo):
    rs = win32com.client.Dispatch("ADODB.Recordset")
    rs.Open(query, conn)
    resultados = []
    while not rs.EOF:
        resultados.append(rs.Fields(campo).Value)
        rs.MoveNext()
    rs.Close()
    return resultados



def query_olap(connection_string: str, query: str) -> pd.DataFrame:
    pythoncom.CoInitialize()
    conn = win32com.client.Dispatch("ADODB.Connection")
    rs = win32com.client.Dispatch("ADODB.Recordset")
    conn.Open(connection_string)
    rs.Open(query, conn)

    fields = [rs.Fields.Item(i).Name for i in range(rs.Fields.Count)]
    data = []
    while not rs.EOF:
        row = [rs.Fields.Item(i).Value for i in range(rs.Fields.Count)]
        data.append(row)
        rs.MoveNext()
    rs.Close()
    conn.Close()
    pythoncom.CoUninitialize()
    return pd.DataFrame(data, columns=fields)



def sanitize_result(data):
    if isinstance(data, float) and (math.isnan(data) or data == float("inf") or data == float("-inf")):
        return None
    elif isinstance(data, list):
        return [sanitize_result(x) for x in data]
    elif isinstance(data, dict):
        return {k: sanitize_result(v) for k, v in data.items()}
    return data


@app.get("/cubos_disponibles")
def cubos_disponibles():
    try:
        conn = crear_conexion()
        cubos = ejecutar_query_lista(conn, "SELECT [catalog_name] FROM $system.DBSCHEMA_CATALOGS", "CATALOG_NAME")
        conn.Close()
        pythoncom.CoUninitialize()
        return {"cubos": list(set(cubos))}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/cubos_en_catalogo/{catalogo}")
def cubos_en_catalogo(catalogo: str):
    try:
        conn = crear_conexion(catalogo)
        cubos = ejecutar_query_lista(conn, "SELECT CUBE_NAME FROM $system.mdschema_cubes WHERE CUBE_SOURCE = 1", "CUBE_NAME")
        conn.Close()
        pythoncom.CoUninitialize()
        return {"catalogo": catalogo, "cubos": cubos}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/explorar_catalogo/{catalogo}")
def explorar_catalogo(catalogo: str):
    try:
        conn = crear_conexion(catalogo)
        resultado = {"catalogo": catalogo, "cubos": []}

        cubos = ejecutar_query_lista(conn, "SELECT CUBE_NAME FROM $system.mdschema_cubes WHERE CUBE_SOURCE = 1", "CUBE_NAME")

        for cubo in cubos:
            cubo_info = {
                "cubo": cubo,
                "jerarquias": ejecutar_query_lista(conn, f"SELECT HIERARCHY_NAME FROM $system.mdschema_hierarchies WHERE CUBE_NAME = '{cubo}'", "HIERARCHY_NAME"),
                "niveles": ejecutar_query_lista(conn, f"SELECT LEVEL_NAME FROM $system.mdschema_levels WHERE CUBE_NAME = '{cubo}'", "LEVEL_NAME"),
                "medidas": ejecutar_query_lista(conn, f"SELECT MEASURE_NAME FROM $system.mdschema_measures WHERE CUBE_NAME = '{cubo}'", "MEASURE_NAME")
            }
            resultado["cubos"].append(cubo_info)

        conn.Close()
        pythoncom.CoUninitialize()
        return resultado
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
@app.get("/cubos_sis")
def cubos_sis():
    try:
        conn = crear_conexion()
        cubos = ejecutar_query_lista(conn, "SELECT [catalog_name] FROM $system.DBSCHEMA_CATALOGS", "CATALOG_NAME")
        conn.Close()
        pythoncom.CoUninitialize()

   
        cubos_filtrados = [c for c in cubos if 'sis' in c.lower() and 'sectorial' not in c.lower()]
        return {"cubos_sis": cubos_filtrados}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/explorar_sis")
def explorar_sis():
    try:
        conn = crear_conexion()
        catalogos = ejecutar_query_lista(conn, "SELECT [catalog_name] FROM $system.DBSCHEMA_CATALOGS", "CATALOG_NAME")
        conn.Close()

       
        catalogos_sis = [c for c in catalogos if "sis" in c.lower() and "sectorial" not in c.lower()]
        resultado = []

        for catalogo in catalogos_sis:
            conn = crear_conexion(catalogo)
            cubos = ejecutar_query_lista(conn, "SELECT CUBE_NAME FROM $system.mdschema_cubes WHERE CUBE_SOURCE = 1", "CUBE_NAME")
            catalogo_info = {
                "catalogo": catalogo,
                "cubos": []
            }

            for cubo in cubos:
                cubo_info = {
                    "cubo": cubo,
                    "jerarquias": ejecutar_query_lista(conn, f"SELECT HIERARCHY_NAME FROM $system.mdschema_hierarchies WHERE CUBE_NAME = '{cubo}'", "HIERARCHY_NAME"),
                    "niveles": ejecutar_query_lista(conn, f"SELECT LEVEL_NAME FROM $system.mdschema_levels WHERE CUBE_NAME = '{cubo}'", "LEVEL_NAME"),
                    "medidas": ejecutar_query_lista(conn, f"SELECT MEASURE_NAME FROM $system.mdschema_measures WHERE CUBE_NAME = '{cubo}'", "MEASURE_NAME")
                }
                catalogo_info["cubos"].append(cubo_info)

            resultado.append(catalogo_info)
            conn.Close()

        pythoncom.CoUninitialize()
        return resultado

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/inspeccionar_columnas_miembros/{catalogo}/{cubo}")
def inspeccionar_columnas_miembros(catalogo: str, cubo: str):
    try:
        conn = crear_conexion(catalogo)
        rs = win32com.client.Dispatch("ADODB.Recordset")
        query = f"SELECT * FROM $system.mdschema_members WHERE CUBE_NAME = '{cubo}'"
        rs.Open(query, conn)

        columnas = [rs.Fields.Item(i).Name for i in range(rs.Fields.Count)]

        rs.Close()
        conn.Close()
        pythoncom.CoUninitialize()
        return {"columnas_disponibles": columnas}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/miembros_jerarquia2")
def miembros_jerarquia(
    catalogo: str,
    cubo: str,
    jerarquia: str
):
    try:
     
        cubo_mdx = f'"{cubo}"' if " " in cubo else f"[{cubo}]"

      
        if "." not in jerarquia:
            jerarquia_completa = f"[{jerarquia}].[{jerarquia}]"
        else:
            jerarquia_completa = f"[{jerarquia}]"

        mdx = f"""
        SELECT 
            {{ [Measures].DefaultMember }} ON COLUMNS,
            {{ {jerarquia_completa}.MEMBERS }} ON ROWS
        FROM {cubo_mdx}
        """

        cadena_conexion = (
            "Provider=MSOLAP.8;"
            "Data Source=pwidgis03.salud.gob.mx;"
            "User ID=SALUD\\DGIS15;"
            "Password=Temp123!;"
            f"Initial Catalog={catalogo};"
        )

        df = query_olap(cadena_conexion, mdx)
        df = df.rename(columns=lambda x: x.strip())

        miembros = [{"nombre": row[0]} for _, row in df.iterrows()]
        return {"jerarquia": jerarquia_completa, "miembros": miembros}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# GET PARA OBTENER DATOS DE BIOLÓGICOS POR CLUES, DIVIDE LAS VARIABLES EN DOS GRUPOS

@app.get("/biologicos_por_clues")
def biologicos_por_clues(catalogo: str, cubo: str, clues: str):
    
    try:
        # Configuración inicial
        cubo_mdx = f'[{cubo}]'
        cadena_conexion = (
            "Provider=MSOLAP.8;"
            "Data Source=pwidgis03.salud.gob.mx;"
            "User ID=SALUD\\DGIS15;"
            "Password=Temp123!;"
            f"Initial Catalog={catalogo};"
        )

        # 1. Verificar que la CLUES existe
        mdx_check = f"""
        SELECT {{[Measures].DefaultMember}} ON COLUMNS
        FROM {cubo_mdx}
        WHERE ([CLUES].[CLUES].&[{clues}])
        """
        try:
            check_df = query_olap(cadena_conexion, mdx_check)
            if check_df.empty:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"La CLUES '{clues}' no existe en el cubo especificado."}
                )
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"error": f"Error al verificar CLUES: {str(e)}"}
            )

        # 2. Obtener datos geográficos de la unidad médica (versión mejorada)
        def obtener_datos_geograficos(clues: str) -> dict:
            """Obtiene los datos geográficos de la unidad médica"""
            geo_data = {
                "entidad": None,
                "jurisdiccion": None,
                "municipio": None,
                "unidad_medica": None
            }

            # Primero intentamos con la consulta combinada
            try:
                mdx_geo = f"""
                SELECT
                NON EMPTY {{
                    [Entidad].[Entidad].CurrentMember,
                    [Jurisdicción].[Jurisdicción].CurrentMember,
                    [Municipio].[Municipio].CurrentMember,
                    [Unidad Médica].[Nombre de la Unidad Médica].CurrentMember
                }} ON ROWS,
                {{ [Measures].DefaultMember }} ON COLUMNS
                FROM {cubo_mdx}
                WHERE ([CLUES].[CLUES].&[{clues}])
                """
                
                df_geo = query_olap(cadena_conexion, mdx_geo)
                if not df_geo.empty:
                    for i, row in df_geo.iterrows():
                        cell_value = str(row[0]) if pd.notna(row[0]) else None
                        if cell_value:
                            if "[Entidad].[Entidad]" in cell_value:
                                geo_data["entidad"] = cell_value.split("].[")[-1].replace("]", "").strip()
                            elif "[Jurisdicción].[Jurisdicción]" in cell_value:
                                geo_data["jurisdiccion"] = cell_value.split("].[")[-1].replace("]", "").strip()
                            elif "[Municipio].[Municipio]" in cell_value:
                                geo_data["municipio"] = cell_value.split("].[")[-1].replace("]", "").strip()
                            elif "[Unidad Médica].[Nombre de la Unidad Médica]" in cell_value:
                                geo_data["unidad_medica"] = cell_value.split("].[")[-1].replace("]", "").strip()
                    return geo_data
            except Exception as geo_error:
                print(f"Error en consulta geográfica combinada: {str(geo_error)}")

            # Si falla, intentamos con consultas individuales
            try:
                # Intentamos diferentes nombres para la unidad médica
                um_names = [
                    "[Unidad Médica].[Nombre de la Unidad Médica]",
                    "[Unidad Médica].[Unidad Médica]",
                    "[Unidad Médica].[Nombre Unidad]",
                    "[Unidad Médica].[Nombre]"
                ]
                
                for um_name in um_names:
                    try:
                        mdx_um = f"""
                        SELECT
                        NON EMPTY {{ {um_name}.Members }} ON ROWS,
                        {{ [Measures].DefaultMember }} ON COLUMNS
                        FROM {cubo_mdx}
                        WHERE ([CLUES].[CLUES].&[{clues}])
                        """
                        df_um = query_olap(cadena_conexion, mdx_um)
                        if not df_um.empty:
                            cell_value = str(df_um.iloc[0, 0]) if pd.notna(df_um.iloc[0, 0]) else None
                            if cell_value:
                                geo_data["unidad_medica"] = cell_value.split("].[")[-1].replace("]", "").strip()
                                break
                    except Exception:
                        continue

                # Consultamos las otras dimensiones por separado
                for dim in ["Entidad", "Jurisdicción", "Municipio"]:
                    try:
                        mdx_dim = f"""
                        SELECT
                        NON EMPTY {{ [{dim}].[{dim}].Members }} ON ROWS,
                        {{ [Measures].DefaultMember }} ON COLUMNS
                        FROM {cubo_mdx}
                        WHERE ([CLUES].[CLUES].&[{clues}])
                        """
                        df_dim = query_olap(cadena_conexion, mdx_dim)
                        if not df_dim.empty:
                            cell_value = str(df_dim.iloc[0, 0]) if pd.notna(df_dim.iloc[0, 0]) else None
                            if cell_value:
                                key = dim.lower().replace("ó", "o")
                                geo_data[key] = cell_value.split("].[")[-1].replace("]", "").strip()
                    except Exception:
                        continue
            except Exception as e:
                print(f"Error en consultas individuales: {str(e)}")

            return geo_data

        geo_data = obtener_datos_geograficos(clues)

        # 3. Obtener datos de biológicos
        def obtener_datos_biologicos(clues: str) -> list:
            """Obtiene los datos de aplicación de biológicos"""
            biologicos_data = []
            
            try:
                # Obtener todos los apartados que contienen 'BIOLÓGICOS'
                mdx_apartados = f"""
                SELECT
                NON EMPTY {{ [Apartado].[Apartado].MEMBERS }} ON ROWS,
                {{ [Measures].DefaultMember }} ON COLUMNS
                FROM {cubo_mdx}
                WHERE ([CLUES].[CLUES].&[{clues}])
                """
                
                df_apartados = query_olap(cadena_conexion, mdx_apartados)
                
                apartados_biologicos = []
                for _, row in df_apartados.iterrows():
                    if row[0] and 'BIOLÓGICOS' in row[0].upper():
                        apartado = row[0].split('.')[-1].replace('[', '').replace(']', '')
                        apartados_biologicos.append(apartado)
                
                # Para cada apartado de biológicos, obtener sus variables
                for apartado in apartados_biologicos:
                    mdx_variables = f"""
                    SELECT
                    NON EMPTY {{ [Variable].[Variable].MEMBERS }} ON ROWS,
                    {{ [Measures].[Total] }} ON COLUMNS
                    FROM {cubo_mdx}
                    WHERE ([Apartado].[Apartado].&[{apartado}], [CLUES].[CLUES].&[{clues}])
                    """
                    
                    df_variables = query_olap(cadena_conexion, mdx_variables)
                    
                    variables_con_valores = []
                    for _, row in df_variables.iterrows():
                        if len(row) >= 2 and row[0] and pd.notna(row[1]):
                            nombre_variable = row[0].split('.')[-1].replace('[', '').replace(']', '')
                            try:
                                valor = int(float(row[1])) if pd.notna(row[1]) else None
                            except:
                                valor = None
                            
                            if valor is not None:
                                variables_con_valores.append({
                                    "variable": nombre_variable,
                                    "total": valor
                                })

                    if variables_con_valores:
                        biologicos_data.append({
                            "apartado": apartado,
                            "variables": variables_con_valores
                        })
            except Exception as e:
                print(f"Error al obtener datos de biológicos: {str(e)}")
            
            return biologicos_data

        datos_biologicos = obtener_datos_biologicos(clues)

        # Construir respuesta final
        resultado = {
            "catalogo": catalogo,
            "cubo": cubo,
            "clues": clues,
            "unidad": geo_data,
            "biologicos": datos_biologicos,
            "metadata": {
                "fecha_consulta": pd.Timestamp.now().isoformat(),
                "version": "1.2"
            }
        }

        return resultado

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "detalle": "Error interno al procesar la solicitud",
                "catalogo": catalogo,
                "cubo": cubo,
                "clues": clues
            }
        )


# PARA CONSULTA DE BIOLOGICOS POR MULTIPLES CLUES 

#biologicos_por_multiples_clues
# 


@app.post("/biologicos_por_multiples_clues")
def biologicos_por_multiples_clues(
    catalogo: str = Body(...),
    cubo: str = Body(...),
    clues_list: List[str] = Body(...)
):
    try:
        # 1. Cargar el JSON de unidades médicas al inicio
        ruta_archivo = os.path.join(os.path.dirname(__file__), "../database/seeders/json/unidades.json")
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            unidades_medicas = json.load(f)
        unidades_dict = {um["clues"]: um for um in unidades_medicas}

        # 2. Configuración inicial del cubo OLAP
        cubo_mdx = f'[{cubo}]'
        cadena_conexion = (
            "Provider=MSOLAP.8;"
            "Data Source=pwidgis03.salud.gob.mx;"
            "User ID=SALUD\\DGIS15;"
            "Password=Temp123!;"
            f"Initial Catalog={catalogo};"
        )

        resultados = []
        clues_no_encontradas = []
        
        for clues in clues_list:
            try:
                # 3. Verificar que la CLUES existe en OLAP
                mdx_check = f"""
                SELECT {{[Measures].DefaultMember}} ON COLUMNS
                FROM {cubo_mdx}
                WHERE ([CLUES].[CLUES].&[{clues}])
                """
                check_df = query_olap(cadena_conexion, mdx_check)
                if check_df.empty:
                    clues_no_encontradas.append(clues)
                    continue

                # 4. Obtener datos geográficos
                def obtener_datos_geograficos(clues: str) -> dict:
                    """Obtiene los datos geográficos combinando OLAP y JSON local"""
                    geo_data = {
                        "entidad": None,
                        "jurisdiccion": None,
                        "municipio": None,
                        "nombre": None
                    }

                    unidad_info = unidades_dict.get(clues)
                    if unidad_info:
                        geo_data["nombre"] = unidad_info.get("nombre", None)

                    geo_data["entidad"] = obtener_valor_dim(cadena_conexion, cubo_mdx, "Entidad", clues)
                    geo_data["jurisdiccion"] = obtener_valor_dim(cadena_conexion, cubo_mdx, "Jurisdicción", clues)
                    geo_data["municipio"] = obtener_valor_dim(cadena_conexion, cubo_mdx, "Municipio", clues)

                    return geo_data

                geo_data = obtener_datos_geograficos(clues)

                # 5. Obtener datos de biológicos con consolidación de migrantes
                def obtener_datos_biologicos(clues: str) -> list:
                    """Obtiene los datos de aplicación de biológicos consolidando migrantes"""
                    biologicos_data = []
                    
                    try:
                        # Obtener todos los apartados que contienen 'BIOLÓGICOS'
                        mdx_apartados = f"""
                        SELECT
                        NON EMPTY {{ [Apartado].[Apartado].MEMBERS }} ON ROWS,
                        {{ [Measures].DefaultMember }} ON COLUMNS
                        FROM {cubo_mdx}
                        WHERE ([CLUES].[CLUES].&[{clues}])
                        """
                        
                        df_apartados = query_olap(cadena_conexion, mdx_apartados)
                        
                        apartados_biologicos = []
                        for _, row in df_apartados.iterrows():
                            if row[0] and 'BIOLÓGICOS' in row[0].upper():
                                apartado = row[0].split('].[')[-1].replace(']', '').strip()
                                apartados_biologicos.append(apartado)
                        
                        # Procesar cada apartado
                        for apartado in apartados_biologicos:
                            mdx_variables = f"""
                            SELECT
                            NON EMPTY {{ [Variable].[Variable].MEMBERS }} ON ROWS,
                            {{ [Measures].[Total] }} ON COLUMNS
                            FROM {cubo_mdx}
                            WHERE ([Apartado].[Apartado].&[{apartado}], [CLUES].[CLUES].&[{clues}])
                            """
                            
                            df_variables = query_olap(cadena_conexion, mdx_variables)
                            
                            variables_normales = []
                            total_migrantes = 0
                            tiene_migrantes = False
                            
                            for _, row in df_variables.iterrows():
                                if len(row) >= 2 and row[0] and pd.notna(row[1]):
                                    # Extraer nombre completo
                                    full_variable_name = row[0]
                                    if '].&[' in full_variable_name:
                                        full_variable_name = full_variable_name.split('].&[')[-1].rstrip(']')
                                    elif '].[' in full_variable_name:
                                        full_variable_name = full_variable_name.split('].[')[-1].rstrip(']')
                                    else:
                                        full_variable_name = full_variable_name.strip('[]')
                                    
                                    try:
                                        valor = int(float(row[1])) if pd.notna(row[1]) else None
                                    except:
                                        valor = None
                                    
                                    if valor is not None:
                                        # Verificar si es variable de migrante
                                        if 'MIGRANTE' in full_variable_name.upper():
                                            total_migrantes += valor
                                            tiene_migrantes = True
                                        else:
                                            variables_normales.append({
                                                "variable": full_variable_name,
                                                "total": valor
                                            })
                            
                            # Construir estructura de resultado para el apartado
                            apartado_data = {
                                "apartado": apartado,
                                "variables": variables_normales
                            }
                            
                            # Agregar total consolidado de migrantes si existe
                            if tiene_migrantes:
                                apartado_data["variables"].append({
                                    "variable": f"TOTAL DE VACUNAS APLICADAS A MIGRANTES - {apartado}",
                                    "total": total_migrantes
                                })
                            
                            biologicos_data.append(apartado_data)
                            
                    except Exception as e:
                        print(f"Error al obtener datos de biológicos para CLUES {clues}: {str(e)}")
                    
                    return biologicos_data

                datos_biologicos = obtener_datos_biologicos(clues)

                # 6. Construir respuesta
                resultado_clues = {
                    "clues": clues,
                    "unidad": geo_data,
                    "biologicos": datos_biologicos
                }

                resultados.append(resultado_clues)

            except Exception as e:
                print(f"Error procesando CLUES {clues}: {str(e)}")
                resultados.append({
                    "clues": clues,
                    "error": str(e),
                    "unidad": {
                        "nombre": None,
                        "entidad": None,
                        "jurisdiccion": None,
                        "municipio": None
                    },
                    "biologicos": []
                })

        # Construir respuesta final
        respuesta = {
            "catalogo": catalogo,
            "cubo": cubo,
            "resultados": resultados,
            "clues_no_encontradas": clues_no_encontradas,
            "metadata": {
                "fecha_consulta": pd.Timestamp.now().isoformat(),
                "version": "1.2",
                "total_clues_solicitadas": len(clues_list),
                "total_clues_procesadas": len(resultados),
                "total_clues_no_encontradas": len(clues_no_encontradas),
                "nota": "Variables con 'MIGRANTE' se consolidan en un total por apartado"
            }
        }

        return respuesta

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "detalle": "Error interno al procesar la solicitud",
                "catalogo": catalogo,
                "cubo": cubo,
                "clues_solicitadas": clues_list
            }
        )



    

#######################################################
# variables con cero
#######################################################
@app.post("/biologicos_normalizados")
def biologicos_normalizados(
    catalogo: str = Body(...),
    cubo: str = Body(...),
    clues_list: List[str] = Body(...)
):
    try:
        # 1. Cargar JSON de unidades médicas
        ruta_archivo = os.path.join(os.path.dirname(__file__), "../database/seeders/json/unidades.json")
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            unidades_medicas = json.load(f)
        unidades_dict = {um["clues"]: um for um in unidades_medicas}

        # 2. Configuración OLAP
        cubo_mdx = f'[{cubo}]'
        cadena_conexion = (
            "Provider=MSOLAP.8;"
            "Data Source=pwidgis03.salud.gob.mx;"
            "User ID=SALUD\\DGIS15;"
            "Password=Temp123!;"
            f"Initial Catalog={catalogo};"
        )

        resultados = []
        clues_no_encontradas = []

        # 3. Obtener TODAS las variables posibles (una sola vez)
        mdx_apartados = f"""
        SELECT
        NON EMPTY {{ [Apartado].[Apartado].MEMBERS }} ON ROWS,
        {{ [Measures].DefaultMember }} ON COLUMNS
        FROM {cubo_mdx}
        """
        df_apartados = query_olap(cadena_conexion, mdx_apartados)

        todas_las_variables = {}
        for _, row in df_apartados.iterrows():
            if row[0] and 'BIOLÓGICOS' in row[0].upper():
                apartado = row[0].split('].[')[-1].replace(']', '').strip()
                mdx_vars = f"""
                SELECT
                NON EMPTY {{ [Variable].[Variable].MEMBERS }} ON ROWS,
                {{ [Measures].[Total] }} ON COLUMNS
                FROM {cubo_mdx}
                WHERE ([Apartado].[Apartado].&[{apartado}])
                """
                df_vars = query_olap(cadena_conexion, mdx_vars)
                variables = []
                for _, vrow in df_vars.iterrows():
                    var_name = vrow[0]
                    if '].&[' in var_name:
                        var_name = var_name.split('].&[')[-1].rstrip(']')
                    elif '].[' in var_name:
                        var_name = var_name.split('].[')[-1].rstrip(']')
                    else:
                        var_name = var_name.strip('[]')
                    variables.append(var_name)
                todas_las_variables[apartado] = variables

        # 4. Procesar cada CLUES
        for clues in clues_list:
            try:
                mdx_check = f"""
                SELECT {{[Measures].DefaultMember}} ON COLUMNS
                FROM {cubo_mdx}
                WHERE ([CLUES].[CLUES].&[{clues}])
                """
                check_df = query_olap(cadena_conexion, mdx_check)
                if check_df.empty:
                    clues_no_encontradas.append(clues)
                    continue

                geo_data = {
                    "nombre": unidades_dict.get(clues, {}).get("nombre"),
                    "entidad": obtener_valor_dim(cadena_conexion, cubo_mdx, "Entidad", clues),
                    "jurisdiccion": obtener_valor_dim(cadena_conexion, cubo_mdx, "Jurisdicción", clues),
                    "municipio": obtener_valor_dim(cadena_conexion, cubo_mdx, "Municipio", clues)
                }

                biologicos_data = []
                for apartado, variables in todas_las_variables.items():
                    valores = {}
                    mdx_clues = f"""
                    SELECT
                    NON EMPTY {{ [Variable].[Variable].MEMBERS }} ON ROWS,
                    {{ [Measures].[Total] }} ON COLUMNS
                    FROM {cubo_mdx}
                    WHERE ([Apartado].[Apartado].&[{apartado}], [CLUES].[CLUES].&[{clues}])
                    """
                    df_vars = query_olap(cadena_conexion, mdx_clues)

                    for _, vrow in df_vars.iterrows():
                        var_name = vrow[0]
                        if '].&[' in var_name:
                            var_name = var_name.split('].&[')[-1].rstrip(']')
                        elif '].[' in var_name:
                            var_name = var_name.split('].[')[-1].rstrip(']')
                        else:
                            var_name = var_name.strip('[]')
                        try:
                            valor = int(float(vrow[1])) if pd.notna(vrow[1]) else 0
                        except:
                            valor = 0
                        valores[var_name] = valor

                    variables_finales = [
                        {"variable": var, "total": valores.get(var, 0)}
                        for var in variables
                    ]

                    biologicos_data.append({
                        "apartado": apartado,
                        "variables": variables_finales
                    })

                resultados.append({
                    "clues": clues,
                    "unidad": geo_data,
                    "biologicos": biologicos_data
                })

            except Exception as e:
                resultados.append({
                    "clues": clues,
                    "error": str(e),
                    "unidad": {
                        "nombre": None,
                        "entidad": None,
                        "jurisdiccion": None,
                        "municipio": None
                    },
                    "biologicos": []
                })

        return {
            "catalogo": catalogo,
            "cubo": cubo,
            "resultados": resultados,
            "clues_no_encontradas": clues_no_encontradas,
            "metadata": {
                "fecha_consulta": pd.Timestamp.now().isoformat(),
                "version": "1.3",
                "total_clues_solicitadas": len(clues_list),
                "total_clues_procesadas": len(resultados),
                "total_clues_no_encontradas": len(clues_no_encontradas),
                "nota": "Todas las variables se normalizan con valor 0 si no están presentes"
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "detalle": "Error interno al procesar la solicitud",
                "catalogo": catalogo,
                "cubo": cubo,
                "clues_solicitadas": clues_list
            }
        )
    
####################################################
@app.post("/biologicos_normalizados_con_migrantes2")
def biologicos_normalizados_con_migrantes(
    catalogo: str = Body(...),
    cubo: str = Body(...),
    clues_list: List[str] = Body(...)
):
    try:
        # 1. Cargar JSON de unidades médicas
        ruta_archivo = os.path.join(os.path.dirname(__file__), "../database/seeders/json/unidades.json")
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            unidades_medicas = json.load(f)
        unidades_dict = {um["clues"]: um for um in unidades_medicas}

        # 2. Configuración OLAP
        cubo_mdx = f'[{cubo}]'
        cadena_conexion = (
            "Provider=MSOLAP.8;"
            "Data Source=pwidgis03.salud.gob.mx;"
            "User ID=SALUD\\DGIS15;"
            "Password=Temp123!;"
            f"Initial Catalog={catalogo};"
        )

        resultados = []
        clues_no_encontradas = []

        # 3. Obtener TODAS las variables posibles por apartado
        mdx_apartados = f"""
        SELECT
        NON EMPTY {{ [Apartado].[Apartado].MEMBERS }} ON ROWS,
        {{ [Measures].DefaultMember }} ON COLUMNS
        FROM {cubo_mdx}
        """
        df_apartados = query_olap(cadena_conexion, mdx_apartados)

        todas_las_variables = {}
        for _, row in df_apartados.iterrows():
            if row[0] and 'BIOLÓGICOS' in row[0].upper():
                apartado = row[0].split('].[')[-1].replace(']', '').strip()
                mdx_vars = f"""
                SELECT
                NON EMPTY {{ [Variable].[Variable].MEMBERS }} ON ROWS,
                {{ [Measures].[Total] }} ON COLUMNS
                FROM {cubo_mdx}
                WHERE ([Apartado].[Apartado].&[{apartado}])
                """
                df_vars = query_olap(cadena_conexion, mdx_vars)
                variables = []
                for _, vrow in df_vars.iterrows():
                    var_name = vrow[0]
                    if '].&[' in var_name:
                        var_name = var_name.split('].&[')[-1].rstrip(']')
                    elif '].[' in var_name:
                        var_name = var_name.split('].[')[-1].rstrip(']')
                    else:
                        var_name = var_name.strip('[]')
                    variables.append(var_name)
                todas_las_variables[apartado] = variables

        # 4. Procesar cada CLUES
        for clues in clues_list:
            try:
                mdx_check = f"""
                SELECT {{[Measures].DefaultMember}} ON COLUMNS
                FROM {cubo_mdx}
                WHERE ([CLUES].[CLUES].&[{clues}])
                """
                check_df = query_olap(cadena_conexion, mdx_check)
                if check_df.empty:
                    clues_no_encontradas.append(clues)
                    continue

                geo_data = {
                    "nombre": unidades_dict.get(clues, {}).get("nombre"),
                    "entidad": obtener_valor_dim(cadena_conexion, cubo_mdx, "Entidad", clues),
                    "jurisdiccion": obtener_valor_dim(cadena_conexion, cubo_mdx, "Jurisdicción", clues),
                    "municipio": obtener_valor_dim(cadena_conexion, cubo_mdx, "Municipio", clues)
                }

                biologicos_data = []

                for apartado, variables in todas_las_variables.items():
                    mdx_clues = f"""
                    SELECT
                    NON EMPTY {{ [Variable].[Variable].MEMBERS }} ON ROWS,
                    {{ [Measures].[Total] }} ON COLUMNS
                    FROM {cubo_mdx}
                    WHERE ([Apartado].[Apartado].&[{apartado}], [CLUES].[CLUES].&[{clues}])
                    """
                    df_vars = query_olap(cadena_conexion, mdx_clues)

                    valores = {}
                    total_migrantes = 0
                    tiene_migrantes = False

                    for _, vrow in df_vars.iterrows():
                        var_name = vrow[0]
                        if '].&[' in var_name:
                            var_name = var_name.split('].&[')[-1].rstrip(']')
                        elif '].[' in var_name:
                            var_name = var_name.split('].[')[-1].rstrip(']')
                        else:
                            var_name = var_name.strip('[]')

                        try:
                            valor = int(float(vrow[1])) if pd.notna(vrow[1]) else 0
                        except:
                            valor = 0

                        if 'MIGRANTE' in var_name.upper():
                            total_migrantes += valor
                            tiene_migrantes = True
                        else:
                            valores[var_name] = valor

                    variables_finales = [
                        {"variable": var, "total": valores.get(var, 0)}
                        for var in variables
                        if 'MIGRANTE' not in var.upper()
                    ]

                    
                    variables_finales.append({
                        "variable": f"TOTAL DE VACUNAS APLICADAS A MIGRANTES - {apartado}",
                        "total": total_migrantes
                    })

                    biologicos_data.append({
                        "apartado": apartado,
                        "variables": variables_finales
                    })

                resultados.append({
                    "clues": clues,
                    "unidad": geo_data,
                    "biologicos": biologicos_data
                })

            except Exception as e:
                resultados.append({
                    "clues": clues,
                    "error": str(e),
                    "unidad": {
                        "nombre": None,
                        "entidad": None,
                        "jurisdiccion": None,
                        "municipio": None
                    },
                    "biologicos": []
                })

        return {
            "catalogo": catalogo,
            "cubo": cubo,
            "resultados": resultados,
            "clues_no_encontradas": clues_no_encontradas,
            "metadata": {
                "fecha_consulta": pd.Timestamp.now().isoformat(),
                "version": "1.4",
                "total_clues_solicitadas": len(clues_list),
                "total_clues_procesadas": len(resultados),
                "total_clues_no_encontradas": len(clues_no_encontradas),
                "nota": "Todas las variables se normalizan con valor 0 si no están presentes, incluyendo consolidación de migrantes"
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "detalle": "Error interno al procesar la solicitud",
                "catalogo": catalogo,
                "cubo": cubo,
                "clues_solicitadas": clues_list
            }
        )