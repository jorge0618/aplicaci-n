import io, base64
import chardet
import pandas as pd
import matplotlib.pyplot as plt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import UploadedFile, Analysis
import tempfile
import seaborn as sns
import numpy as np
from django.http import HttpResponse

@login_required
def menu(request):
    return render(request, 'analyzer/menu.html')

@login_required
def upload(request):
    if request.method == 'POST' and request.FILES.get('file'):
        print("📂 Se recibió un archivo:", request.FILES['file'].name)
        uploaded_file = request.FILES['file']
        name = uploaded_file.name

        try:
            file_instance = UploadedFile.objects.create(
                user=request.user,
                file=uploaded_file,
                name=name
            )

            # Abrir archivo en modo binario para detectar codificación
            file_path = file_instance.file.path
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)
                encoding_detected = chardet.detect(raw_data)['encoding']

            # Ahora abrimos en modo texto con esa codificación
            if name.endswith('.csv'):
                try:
                    df = pd.read_csv(file_path, encoding=encoding_detected, sep=None, engine='python')
                except Exception:
                    df = pd.read_csv(file_path, encoding=encoding_detected, sep=';', engine='python')
            elif name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_path)
            else:
                messages.error(request, 'Formato no soportado.')
                return redirect('upload')

            summary = f"Archivo con {df.shape[0]} filas y {df.shape[1]} columnas."

            Analysis.objects.create(file=file_instance, user=request.user, summary=summary)
            messages.success(request, f'Archivo "{name}" cargado con éxito. Ahora selecciona las variables para analizar.')
            
            return redirect('select_variables', file_id=file_instance.id)


        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {e}')

    return render(request, 'analyzer/upload.html')

@login_required
def dashboard(request):
    analyses = Analysis.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'analyzer/dashboard.html', {'analyses': analyses})

@login_required
def history_files(request):
    files = UploadedFile.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'analyzer/history.html', {'files': files})


@login_required
def select_variables(request, file_id):
    file_instance = get_object_or_404(UploadedFile, id=file_id, user=request.user)

    # 🔹 Guardamos temporalmente el archivo para poder leerlo correctamente
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        for chunk in file_instance.file.chunks():
            temp_file.write(chunk)
        temp_path = temp_file.name  # Ruta temporal del archivo

    name = file_instance.name.lower()

    # 🔹 Detectar codificación si es CSV
    if name.endswith('.csv'):
        with open(temp_path, 'rb') as f:
            raw_data = f.read(10000)
            encoding_detected = chardet.detect(raw_data)['encoding']

        try:
            df = pd.read_csv(temp_path, encoding=encoding_detected, sep=None, engine='python')
        except Exception:
            df = pd.read_csv(temp_path, encoding=encoding_detected, sep=';', engine='python')

    elif name.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(temp_path)
    else:
        messages.error(request, 'Formato no soportado.')
        return redirect('upload')

    columns = df.columns.tolist()

    if request.method == 'POST':
        var_x = request.POST.get('var_x')
        var_y = request.POST.get('var_y')
        chart_type = request.POST.get('chart_type')

        fig, ax = plt.subplots()

        if chart_type == 'scatter':
            df.plot(kind='scatter', x=var_x, y=var_y, ax=ax)
        elif chart_type == 'line':
            df.plot(kind='line', x=var_x, y=var_y, ax=ax)
        elif chart_type == 'bar':
            df.plot(kind='bar', x=var_x, y=var_y, ax=ax)
        elif chart_type == 'hist':
            df[[var_x, var_y]].plot(kind='hist', ax=ax)

        buffer = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buffer, format='png')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()

        return render(request, 'analyzer/plot.html', {
            'image_base64': image_base64,
            'var_x': var_x,
            'var_y': var_y,
            'chart_type': chart_type,
            'file_id': file_id
        })

    return render(request, 'analyzer/select_variables.html', {'columns': columns, 'file_id': file_id})



import seaborn as sns
import matplotlib.pyplot as plt
import io, base64
from django.http import HttpResponse


@login_required
def auto_analysis(request, file_id):
    """Genera análisis automático con gráficos y descripciones"""
    file_instance = get_object_or_404(UploadedFile, id=file_id, user=request.user)
    file_path = file_instance.file.path
    name = file_instance.name.lower()

    # Leer archivo según tipo
    if name.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif name.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file_path)
    else:
        messages.error(request, 'Formato no soportado para análisis automático.')
        return redirect('upload')

    graficos = []

    # --- 1️⃣ Matriz de correlación ---
    plt.figure(figsize=(8, 6))
    corr = df.select_dtypes(include=['float64', 'int64']).corr()
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f")
    plt.title('Matriz de correlación')
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    image_corr = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()
    graficos.append({
        'titulo': 'Matriz de correlación',
        'descripcion': 'Muestra la fuerza de relación entre variables numéricas. Valores cercanos a 1 o -1 indican correlación fuerte.',
        'imagen': image_corr
    })

    # --- 2️⃣ Histogramas ---
    for col in df.select_dtypes(include=['float64', 'int64']).columns[:3]:
        plt.figure()
        sns.histplot(df[col], kde=True, color='blue')
        plt.title(f'Distribución de {col}')
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_hist = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        graficos.append({
            'titulo': f'Distribución de {col}',
            'descripcion': f'El histograma muestra cómo se distribuyen los valores de la variable "{col}". Picos indican concentraciones de valores frecuentes.',
            'imagen': image_hist
        })

    # --- 3️⃣ Gráfico de dispersión entre las dos primeras columnas numéricas ---
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    if len(numeric_cols) >= 2:
        plt.figure()
        sns.scatterplot(x=df[numeric_cols[0]], y=df[numeric_cols[1]])
        plt.title(f'Relación entre {numeric_cols[0]} y {numeric_cols[1]}')
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_scatter = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        graficos.append({
            'titulo': f'Relación entre {numeric_cols[0]} y {numeric_cols[1]}',
            'descripcion': f'Este gráfico de dispersión muestra cómo varía "{numeric_cols[1]}" en función de "{numeric_cols[0]}". Una tendencia ascendente o descendente sugiere correlación.',
            'imagen': image_scatter
        })

    # --- 4️⃣ Diagrama de caja ---
    for col in df.select_dtypes(include=['float64', 'int64']).columns[:2]:
        plt.figure()
        sns.boxplot(x=df[col])
        plt.title(f'Valores atípicos en {col}')
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_box = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        graficos.append({
            'titulo': f'Valores atípicos en {col}',
            'descripcion': f'El diagrama de caja muestra la mediana, los cuartiles y posibles valores atípicos de "{col}".',
            'imagen': image_box
        })

    context = {
        'file_name': name,
        'graficos': graficos
    }

    return render(request, 'analyzer/auto_analysis.html', context)
