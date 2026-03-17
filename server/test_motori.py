from gpiozero import Motor, PWMOutputDevice
from time import sleep

'''
COLLEGAMENTI driver motori
(giu)
'''
# Motore A
motorA = Motor(forward=27, backward=17) #FORWARD:AIN2 #BACKWARDS:AIN1
pwmA = PWMOutputDevice(18) #PWMA

# Motore B
motorB = Motor(forward=22, backward=23) #FORWARD:BIN1 #BACKWARDS:BIN2
#i GPOI del motore B sono specchiati perchÃ¨ il motore Ã¨ specchiato rispetto
#all'altro
pwmB = PWMOutputDevice(19) #PWMB
#STBY = HIGH sempre perchÃ¨ Ã¨ collegato direttamente a 3.3v
#VM

try:
    print("Avanti")
    pwmA.value = 0.6
    pwmB.value = 0.6
    motorA.forward()
    motorB.forward()
    sleep(3)

    print("Stop")
    pwmA.value = 0
    pwmB.value = 0
    sleep(2)

    print("Indietro")
    pwmA.value = 0.6
    pwmB.value = 0.6
    motorA.backward()
    motorB.backward()
    sleep(3)

    print("Stop finale")
    pwmA.value = 0
    pwmB.value = 0

finally:
    motorA.close()
    motorB.close()
    pwmA.close()
    pwmB.close()
