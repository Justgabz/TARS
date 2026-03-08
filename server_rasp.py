#pip install pybluez2 (funziona solo su linux)
import bluetooth

def avvia_server_bluetooth():
    # 1. Creazione del Socket RFCOMM
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    
    # 2. Binding della porta (0 significa "assegna la prima disponibile")
    server_sock.bind(("", bluetooth.PORT_ANY))
    server_sock.listen(1)

    port = server_sock.getsockname()[1]

    # 3. Identificatore Univoco (UUID) - Deve corrispondere a quello dell'App
    uuid = "00001101-0000-1000-8000-00805F9B34FB"

    # 4. Pubblicità del servizio (Rende il Raspberry visibile all'App)
    bluetooth.advertise_service(server_sock, "TARS_Server",
                               service_id=uuid,
                               service_classes=[uuid, bluetooth.SERIAL_PORT_CLASS],
                               profiles=[bluetooth.SERIAL_PORT_PROFILE])

    print(f"In attesa di connessione sulla porta RFCOMM {port}...")
    #aspettiamo che l'app si connetta
    
    try:
        # 5. Accettazione della connessione (Bloccante finché l'app non si connette)
        client_sock, client_info = server_sock.accept()
        print(f"Connesso a: {client_info}")

        while True:
            # 6. Ricezione dati (1024 byte di buffer)
            data = client_sock.recv(1024)
            if not data:
                break
            
            messaggio = data.decode('utf-8').strip()
            print(f"Messaggio ricevuto: {messaggio}")

            # Qui metterai la tua logica IA/Motori
            if messaggio == "QUIT":
                break

    except Exception as e:
        print(f"Errore: {e}")

    finally:
        # 7. Pulizia
        client_sock.close()
        server_sock.close()
        print("Connessione chiusa e socket rilasciati.")

if __name__ == "__main__":
    avvia_server_bluetooth()