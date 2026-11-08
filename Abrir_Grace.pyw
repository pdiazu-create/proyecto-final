"""Ventana privada de inicio. Ejecutar con pythonw en Windows."""
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from gestor_grace import iniciar, detener, salud, URL


def main():
    ventana = tk.Tk()
    ventana.title('Grace')
    ventana.geometry('460x275')
    ventana.resizable(False, False)
    ventana.configure(background='#f4f8fb')
    if '--detener' in sys.argv:
        ventana.withdraw()
        if messagebox.askyesno('Detener Grace', '¿Quieres detener Grace en esta computadora?'):
            try:
                messagebox.showinfo('Grace', detener())
            except ValueError as error:
                messagebox.showinfo('Grace', str(error))
        ventana.destroy()
        return
    if salud():
        ventana.withdraw()
        webbrowser.open(URL)
        ventana.destroy()
        return
    panel = ttk.Frame(ventana, padding=24)
    panel.pack(fill='both', expand=True)
    ttk.Label(panel, text='Abrir Grace', font=('Segoe UI', 21, 'bold')).pack(anchor='w')
    ttk.Label(panel, text='Introduce tu clave de Gemini. No se guarda.',
              font=('Segoe UI', 11)).pack(anchor='w', pady=(12, 8))
    entrada = ttk.Entry(panel, show='*', font=('Segoe UI', 12))
    entrada.pack(fill='x', ipady=5)
    estado = ttk.Label(panel, text='La ventana se cerrará al abrir el navegador.',
                       wraplength=400, font=('Segoe UI', 10))
    estado.pack(anchor='w', pady=12)
    eventos = queue.Queue()
    ocupado = False

    def tarea(clave):
        try:
            iniciar(clave)
            eventos.put(True)
        except ValueError as error:
            eventos.put(str(error))
        except Exception:
            eventos.put('No se pudo iniciar Grace. Revisa Python y la carpeta del proyecto.')

    def abrir():
        nonlocal ocupado
        if ocupado:
            return
        clave = entrada.get().strip()
        if not clave:
            estado.configure(text='Introduce la clave en el campo privado.')
            return
        ocupado = True
        entrada.delete(0, 'end')
        entrada.configure(state='disabled')
        boton.configure(state='disabled')
        estado.configure(text='Iniciando Grace…')
        threading.Thread(target=tarea, args=(clave,), daemon=True).start()

    def revisar():
        nonlocal ocupado
        try:
            resultado = eventos.get_nowait()
        except queue.Empty:
            ventana.after(150, revisar)
            return
        if resultado is True:
            webbrowser.open(URL)
            ventana.destroy()
            return
        ocupado = False
        estado.configure(text=resultado)
        entrada.configure(state='normal')
        boton.configure(state='normal')
        ventana.after(150, revisar)

    boton = ttk.Button(panel, text='Abrir Grace', command=abrir)
    boton.pack(fill='x', ipady=5)
    entrada.bind('<Return>', lambda _e: abrir())
    ventana.protocol('WM_DELETE_WINDOW', lambda: None if ocupado else ventana.destroy())
    entrada.focus_set()
    ventana.after(150, revisar)
    ventana.mainloop()


if __name__ == '__main__':
    main()
