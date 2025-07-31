<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\CubosController;

Route::get('/cubos', [CubosController::class, 'index'])->name('cubos.index');

// NUEVA RUTA para la vista de múltiples CLUES
Route::get('/consulta-variables', [CubosController::class, 'consultaVariables'])->name('cubos.consultaVariables');
