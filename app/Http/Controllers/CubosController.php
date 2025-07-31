<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

class CubosController extends Controller
{
    public function index()
    {
        return view('cubos.index');
    }

    public function consultaVariables()
{
    return view('cubos.consulta_variables');
}

}


