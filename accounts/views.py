from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('menu')  # redirige al menú principal del analyzer
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    return render(request, 'accounts/login.html')


def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El usuario ya existe.')
        else:
            user = User.objects.create_user(username=username, password=password)
            messages.success(request, 'Usuario creado con éxito. Ahora puedes iniciar sesión.')
            return redirect('login')
    return render(request, 'accounts/register.html')


def logout_view(request):
    logout(request)
    return redirect('login')