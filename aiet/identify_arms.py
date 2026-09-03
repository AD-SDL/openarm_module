from damiao_motor import DaMiaoController
import time

channels = {can0, can1, can2, can3}

for ch in channels:
   try:
      ctrl= DaMiaoController(channel=ch, bustype='socketcan')
      motors={}
      for i in range(1,9):
         motors[i]=ctrl.add_motor(motor_id=i, feedback_id=0x10+1,motor_type='4310')
      for m in motors.values():
         m.enable()
         time.sleep(.15)
      time.sleep(0.3)
      motors[1].send_cmd_mit(0.3,0,8,1,0)
      time.sleep(2)
      motors[1].send_cmd_mit(0,0,8,1,0)
      time.sleep(2)
      ctrl.disable_all()
   except Exception as e:
      print(f'Err: {e}')

   role = input(f'What is {ch}?')
