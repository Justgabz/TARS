class robot:
    def __init__(self):
        pass

    def set_motors(self,right : int,left : int) -> tuple[int,int]:
        '''
        description:
            a function that starts 2 motors at a certain speed ( range:[-100;100] for each motor) controlled by an arduino
        Args:
            right : the power of the right motor range:[-100;100]
            left : the power of the left motor range: [-100;100]
            the robot goes back for set_motors(-100,-100)
            the tobot goes left for set_motors(100,-100)
            the robot goes right for set_motors(-100,100)
            the robot goes forwars for set_motors(100,100)
        Returns:
            the exact params passed as inputs
        '''
        
        #test code
        print(right,left)
        return (right,left)