<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Explorador de Cubos SIS</title>
    @vite(['resources/css/app.css', 'resources/js/app.js'])
</head>
<body>
    <nav class="navbar navbar-dark bg-dark px-3">
        <span class="navbar-brand mb-0 h1">Cubos SIS</span>
    </nav>
    <main class="py-4">
        @yield('content')
    </main>
    @yield('scripts')
</body>
</html>
