from flask import Flask, render_template, jsonify
from flask_mysqldb import MySQL
from config import config
import random
from datetime import datetime
import requests
import time
from threading import Thread

app = Flask(__name__)
mysql = MySQL(app)

# Endpoint para obtener el ingrediente con menor inventario y acceder a la API
@app.route('/obtener_ingrediente_menor_inventario')
def obtener_ingrediente_menor_inventario():
    try:
        with app.app_context():
            with mysql.connection.cursor() as cursor:
                cursor.execute("SELECT ingrediente FROM ingredientes ORDER BY inventario ASC LIMIT 1")
                ingrediente_menor_inventario = cursor.fetchone()[0]

        cantidad_ingredientes = consumir_api(ingrediente_menor_inventario)

        if cantidad_ingredientes is not None:
            return jsonify({ingrediente_menor_inventario: cantidad_ingredientes}), 200
        else:
            return jsonify({'message': 'Error al obtener la cantidad de ingredientes.'}), 500

    except Exception as e:
        print(f"Error al obtener el ingrediente con menor inventario: {e}")
        return jsonify({'message': 'Error al obtener el ingrediente con menor inventario.'}), 500

# Función para consumir la API y obtener la cantidad de ingredientes
def consumir_api(ingrediente):
    url = "https://microservices-utadeo-arq-fea471e6a9d4.herokuapp.com/api/v1/software-architecture/market-place"
    params = {"ingredient": ingrediente}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if "data" in data and ingrediente in data["data"]:
            cantidad = data["data"][ingrediente]
            return cantidad
        else:
            return 0
    else:
        print("Error:", response.text)
        return None

# Función para manejar la consulta de ingredientes cada 5 segundos
def manejar_consulta_ingredientes():
    while True:
        try:
            with app.app_context():
                with mysql.connection.cursor() as cursor:
                    # Obtener el ingrediente con el menor inventario
                    cursor.execute("SELECT id, ingrediente, inventario FROM ingredientes ORDER BY inventario ASC LIMIT 1")
                    ingrediente_id, ingrediente_menor_inventario, inventario = cursor.fetchone()

                    # Verificar si el inventario es 10 o más
                    if inventario >= 10:
                        print(f"Inventario de {ingrediente_menor_inventario} alcanzó o superó 10. Deteniendo el proceso.")
                        break

                    # Consumir la API para obtener la cantidad de inventario que se sumará
                    cantidad_sumar = consumir_api(ingrediente_menor_inventario)

                    # Calcular el nuevo inventario sumando la cantidad obtenida de la API al inventario actual
                    nuevo_inventario = inventario + cantidad_sumar

                    # Actualizar el inventario en la base de datos
                    cursor.execute("UPDATE ingredientes SET inventario = inventario + %s WHERE id = %s",
                                   (cantidad_sumar, ingrediente_id))
                    mysql.connection.commit()

                    print(f"Inventario actualizado de {ingrediente_menor_inventario}: {nuevo_inventario}")

            time.sleep(5)
        except Exception as e:
            print(f"Error al manejar la consulta de ingredientes: {e}")
            time.sleep(5)



if __name__ == '__main__':
    app.config.from_object(config['development'])
    consulta_ingredientes_thread = Thread(target=manejar_consulta_ingredientes)
    consulta_ingredientes_thread.start()
    app.run(port=5001)