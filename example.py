import pykuna
import sys
import time


def main():

    if len(sys.argv) < 3:
        print('Usage: python example.py USERNAME PASSWORD')
        exit(1)

    # create an API object, passing username and password
    kuna = pykuna.KunaAPI(sys.argv[1], sys.argv[2])

    # authenticate() to get/refresh the access token
    kuna.authenticate()

    # update() to populate .cameras with a list of cameras in the account
    kuna.update()

    for camera in kuna.cameras:
        # print the name and serial number of the camera
        print('Camera: {} (Serial No. {})'.format(camera.name, camera.serial_number))

        # download a snapshot from the camera
        image = camera.get_thumbnail()
        open('{}.jpeg'.format(camera.name), 'wb').write(image)

        # toggle the camera's light bulb
        current_state = camera.bulb_on
        if current_state:
            camera.set_property(bulb_on=False)
            time.sleep(2)
            camera.set_property(bulb_on=True)
        else:
            camera.set_property(bulb_on=True)
            time.sleep(2)
            camera.set_property(bulb_on=False)


main()