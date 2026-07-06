from gpiozero import Motor, PWMOutputDevice
from time import sleep

class Robot_Hardware:
    def __init__(self):
        self._left_dir = Motor(forward=27, backward=17)
        self._left_pwm = PWMOutputDevice(18)

        self._right_dir = Motor(forward=22, backward=23) 
        self._right_pwm = PWMOutputDevice(19)

    def _control_motor(self, motor_obj, pwm_obj, speed):
        val = max(-100, min(100, speed)) / 100.0
        if val > 0:
            motor_obj.forward()
            pwm_obj.value = val
        elif val < 0:
            motor_obj.backward()
            pwm_obj.value = abs(val)
        else:
            motor_obj.stop()
            pwm_obj.value = 0

    # L'intervallo di default è 0. Cosi non rompe il Joystick.
    def set_motors(self, dx: int, sx: int, interval: float = 0) -> tuple[int, int, float]:
        """Controlla i motori del robot."""
        self._control_motor(self._right_dir, self._right_pwm, dx)
        self._control_motor(self._left_dir, self._left_pwm, sx)
        
        if interval > 0:
            sleep(interval)
            self.stop()
            
        return (dx, sx, interval)

    def stop(self):
        self._control_motor(self._right_dir, self._right_pwm, 0)
        self._control_motor(self._left_dir, self._left_pwm, 0)

    def close(self):
        self._left_dir.close()
        self._left_pwm.close()
        self._right_dir.close()
        self._right_pwm.close()


# --- CLASSE DI EMULAZIONE ---
class Robot_Hardware_Mock:
    def __init__(self):
        print("[MOCK]: Modalità simulazione ATTIVA (Hardware non trovato)")

    # Deve avere ESATTAMENTE la stessa firma della classe reale
    def set_motors(self, dx: int, sx: int, interval: float = 0) -> tuple[int, int, float]:
        print(f"[MOCK-NAV]: Comando motori ricevuto -> DX: {dx}, SX: {sx}, Tempo: {interval}s")
        if interval > 0:
            sleep(interval)
            print("[MOCK-NAV]: Motori fermati post-intervallo.")
        return (dx, sx, interval)


if __name__ == "__main__":
    rr = Robot_Hardware() # Se lo provi su PC, cambialo in Robot_Hardware_Mock() per testare
    rr.set_motors(60, 60) # Nessun intervallo, gira all'infinito
    sleep(1)
    rr.set_motors(-60, 60)
    sleep(1)
    rr.set_motors(60, -60)
    sleep(1)
    rr.stop()