<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\CubosController;

Route::get('/cubos', [CubosController::class, 'index'])->name('cubos.index');

// NUEVA RUTA para la vista de múltiples CLUES
Route::get('/consulta-variables', [CubosController::class, 'consultaVariables'])->name('cubos.consultaVariables');

// routes/web.php
Route::get('/plantillas/plantilla_biologicos.xlsx', function () {
    return response()->file(public_path('storage/app/templates/plantilla_biologicos.xlsx'));
});



