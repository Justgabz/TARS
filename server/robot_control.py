from gpiozero import Motor, PWMOutputDevice
from time import sleep

class Robot_Hardware:
    def __init__(self):
        # Motore Sinistro (Ex Motore A)
        self._left_dir = Motor(forward=27, backward=17)
        self._left_pwm = PWMOutputDevice(18)

        # Motore Destro (Ex Motore B)
        # Nota: I pin sono invertiti nel costruttore per gestire la specchiatura hardware
        self._right_dir = Motor(forward=23, backward=22) 
        self._right_pwm = PWMOutputDevice(19)

    def _control_motor(self, motor_obj, pwm_obj, speed):
        """Metodo interno per gestire direzione e PWM di un singolo motore."""
        # Normalizzazione del valore da [-100, 100] a [-1.0, 1.0]
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

    def set_motors(self, right: int, left: int) -> tuple[int, int]:
        """
        Controlla i motori del robot.
        Args:
            right: potenza motore destro [-100, 100]
            left: potenza motore sinistro [-100, 100]
        """
        self._control_motor(self._right_dir, self._right_pwm, right)
        self._control_motor(self._left_dir, self._left_pwm, left)
        
        return (right, left)

    def stop(self):
        """Ferma immediatamente entrambi i motori."""
        self.set_motors(0, 0)

    def close(self):
        """Rilascia i pin GPIO."""
        self._left_dir.close()
        self._left_pwm.close()
        self._right_dir.close()
        self._right_pwm.close()






#se avvio questo file come main,fai questo
if __name__ == "__main__":
    rr = Robot_Hardware()
    rr.set_motors(60,60)
    sleep(1)
    rr.set_motors(-60,60)
    sleep(1)
    rr.set_motors(60,-60)
    sleep(1)
    rr.stop()
   