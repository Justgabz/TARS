import React, { useState } from 'react';
import { StyleSheet, View, TextInput, TouchableOpacity, KeyboardAvoidingView, Platform, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

// Librerie per Audio e Joystick
import { Audio } from 'expo-av';
import { ReactNativeJoystick } from '@korsolutions/react-native-joystick';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

export default function HomeScreen() {
    const [message, setMessage] = useState('');

    // Stato per gestire l'audio
    const [recording, setRecording] = useState();
    const [permissionResponse, requestPermission] = Audio.usePermissions();

    // --- LOGICA INVIO TESTO ---
    const handleSend = () => {
        if (!message.trim()) return;
        console.log("Messaggio di testo inviato al robot:", message);
        // Qui metterai la tua fetch o websocket per inviare il testo
        setMessage('');
    };

    // --- LOGICA JOYSTICK ---
    const handleJoystickMove = (data) => {
        // data contiene: position (x, y), force, angle
        // Esempio: invio comandi di movimento continui
        // console.log(`Muovendo X: ${data.position.x.toFixed(2)} Y: ${data.position.y.toFixed(2)}`);
    };

    const handleJoystickStop = () => {
        console.log("Joystick rilasciato - Comando STOP inviato al robot");
        // Qui invii il comando per fermare i motori
    };

    // --- LOGICA INVIO AUDIO AL BACKEND ---
    const sendAudioToBackend = async (fileUri) => {
        try {
            console.log("Preparazione invio file:", fileUri);

            // 1. Creiamo l'oggetto FormData
            const formData = new FormData();

            // 2. Aggiungiamo il file. Dobbiamo specificare uri, name e type per farlo funzionare in React Native
            formData.append('audioFile', {
                uri: Platform.OS === 'ios' ? fileUri.replace('file://', '') : fileUri,
                name: 'comando_vocale.m4a', // Il nome con cui arriverà al server
                type: 'audio/m4a', // Tipo MIME generico per la registrazione di Expo
            });

            // Esempio di aggiunta di altri campi testuali se il tuo backend li richiede
            formData.append('robotId', 'TARS-01');

            // 3. Facciamo la richiesta POST (SOSTITUISCI L'URL CON QUELLO VERO)
            const backendUrl = 'https://il-tuo-server.com/api/upload-audio';

            /* SCOMMENTA QUESTO BLOCCO QUANDO HAI IL SERVER PRONTO
            const response = await fetch(backendUrl, {
                method: 'POST',
                headers: {
                    // Non impostare 'Content-Type' manualmente con FormData,
                    // fetch lo calcolerà in automatico con il boundary corretto!
                    'Accept': 'application/json',
                },
                body: formData,
            });

            const result = await response.json();
            console.log('Risposta dal server:', result);
            Alert.alert("Successo", "Comando vocale inviato!");
            */

            console.log("Simulazione: Audio inviato con successo tramite FormData!");

        } catch (error) {
            console.error("Errore durante l'invio dell'audio:", error);
            Alert.alert("Errore", "Impossibile inviare il comando vocale.");
        }
    };

    // --- LOGICA REGISTRAZIONE VOCALE ---
    async function startRecording() {
        try {
            if (permissionResponse?.status !== 'granted') {
                console.log('Richiesta permessi microfono...');
                await requestPermission();
            }
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
            });

            const { recording } = await Audio.Recording.createAsync(
                Audio.RecordingOptionsPresets.HIGH_QUALITY
            );
            setRecording(recording);
            console.log('Registrazione in corso...');
        } catch (err) {
            console.error('Impossibile avviare la registrazione', err);
        }
    }

    async function stopRecording() {
        if (!recording) return;

        setRecording(undefined);
        await recording.stopAndUnloadAsync();

        await Audio.setAudioModeAsync({
            allowsRecordingIOS: false,
        });

        const uri = recording.getURI();
        console.log('Registrazione salvata in locale URI:', uri);

        // Non appena stoppiamo, chiamiamo la funzione per inviare il file
        if (uri) {
            sendAudioToBackend(uri);
        }
    }

    const handleVoiceCapture = () => {
        if (recording) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    return (
        <KeyboardAvoidingView
            style={{ flex: 1 }}
            behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
            <ThemedView style={styles.container}>

                {/* 1. Contenitore Stream Video */}
                <View style={styles.streamContainer}>
                    <Ionicons name="videocam-outline" size={64} color="#888" />
                    <ThemedText style={styles.streamText}>Stream Video Robot</ThemedText>
                </View>

                {/* 3. Label per il testo in arrivo/stato */}
                <View style={styles.statusContainer}>
                    <ThemedText style={styles.statusLabel}>Stato Robot:</ThemedText>
                    <ThemedText type="defaultSemiBold" style={styles.statusText}>
                        Connesso | In attesa di comandi...
                    </ThemedText>
                </View>

                {/* 2. Joystick Funzionante */}
                <View style={styles.joystickContainer}>
                    <ReactNativeJoystick
                        color="#0a7ea4"
                        radius={80}
                        onMove={handleJoystickMove}
                        onStop={handleJoystickStop}
                    />
                    <ThemedText style={styles.joystickLabel}>Area Joystick</ThemedText>
                </View>

                {/* 4 & 5. Area di Input */}
                <View style={styles.inputArea}>
                    <TextInput
                        style={styles.textInput}
                        placeholder="Invia un comando..."
                        placeholderTextColor="#999"
                        value={message}
                        onChangeText={setMessage}
                        onSubmitEditing={handleSend} // Invia anche premendo "Invio" sulla tastiera
                    />

                    <TouchableOpacity
                        style={[styles.iconButton, recording ? styles.recordingActive : null]}
                        onPress={handleVoiceCapture}
                    >
                        <Ionicons name={recording ? "stop" : "mic"} size={24} color="#fff" />
                    </TouchableOpacity>

                    <TouchableOpacity
                        style={[styles.iconButton, styles.sendButton]}
                        onPress={handleSend}
                    >
                        <Ionicons name="send" size={20} color="#fff" />
                    </TouchableOpacity>
                </View>

            </ThemedView>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        padding: 16,
        paddingTop: 50,
        justifyContent: 'space-between',
    },
    streamContainer: {
        height: 250,
        backgroundColor: '#1e1e1e',
        borderRadius: 16,
        justifyContent: 'center',
        alignItems: 'center',
        borderWidth: 2,
        borderColor: '#333',
        overflow: 'hidden',
    },
    streamText: {
        color: '#888',
        marginTop: 10,
    },
    statusContainer: {
        paddingVertical: 12,
        paddingHorizontal: 16,
        backgroundColor: 'rgba(150, 150, 150, 0.1)',
        borderRadius: 12,
        marginVertical: 10,
    },
    statusLabel: {
        fontSize: 12,
        opacity: 0.7,
    },
    statusText: {
        fontSize: 16,
        color: '#4CAF50',
        marginTop: 4,
    },
    joystickContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    joystickLabel: {
        marginTop: 16,
        opacity: 0.5,
    },
    inputArea: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 10,
        gap: 8,
    },
    textInput: {
        flex: 1,
        height: 50,
        backgroundColor: 'rgba(150, 150, 150, 0.15)',
        borderRadius: 25,
        paddingHorizontal: 20,
        fontSize: 16,
        color: '#fff',
    },
    iconButton: {
        width: 50,
        height: 50,
        borderRadius: 25,
        backgroundColor: '#E53935',
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.2,
        shadowRadius: 3,
        elevation: 4,
    },
    recordingActive: {
        backgroundColor: '#D32F2F',
        borderWidth: 2,
        borderColor: '#fff',
    },
    sendButton: {
        backgroundColor: '#0a7ea4',
        paddingLeft: 4,
    }
});