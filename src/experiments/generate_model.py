from lxml import etree
import math

#In version 2 added limit to knee joint angles
VERSION = 2

# MODEL PARAMETERS
model_config = {
	'body': {
		'width': 15,
		'height': 3,
		'length': 25
	},
	'legs': {
		'FL': {
			'motor': {
				'width': 3.6,
				'length': 3.6,
				'height': 5.06,
				'leg_attachment_height': 3.3,
			},
			'position': 'front',
			'leg_attachment_height_offset': 0, # height offset of the leg attachment point relative to the middle of height of the body
			'leg_attachment_length_offset': 3, # offset of leg attachment point relative to front of body
			'femur_length': 7,
			'femur_angle': 25, # angle between femur and vertical in degrees
			'tibia_length': 8.5,
			'spring_length': 2.5,
			'femur_spring_tibia_joint_dst': 4.5,
			'tibia_spring_to_joint_dst': 3.5,
			'hip_damping': 0.2,
			'knee_damping': 0.2,
			'spring_stiffness': 400,
			'actuator_kp': 254,
		},
		'FR': {
			'motor': {
				'width': 3.6,
				'length': 3.6,
				'height': 5.06,
				'leg_attachment_height': 3.3,
			},
			'position': 'front',
			'leg_attachment_height_offset': 0, # height offset of the leg attachment point relative to the middle of height of the body
			'leg_attachment_length_offset': 3, # offset of leg attachment point relative to front of body
			'femur_length': 7,
			'femur_angle': 25, # angle between femur and vertical in degrees
			'tibia_length': 8.5,
			'spring_length': 2.5,
			'femur_spring_tibia_joint_dst': 4.5,
			'tibia_spring_to_joint_dst': 3.5,
			'hip_damping': 0.2,
			'knee_damping': 0.2,
			'spring_stiffness': 400,
			'actuator_kp': 254,
		},
		'BL': {
			'motor': {
				'width': 3.6,
				'length': 3.6,
				'height': 5.06,
				'leg_attachment_height': 3.3,
			},
			'position': 'back',
			'leg_attachment_height_offset': 0, # height offset of the leg attachment point relative to the middle of height of the body
			'leg_attachment_length_offset': 3, # offset of leg attachment point relative to front of body
			'femur_length': 7,
			'femur_angle': 0, # angle between femur and vertical in degrees
			'tibia_length': 8.5,
			'spring_length': 2.5,
			'femur_spring_tibia_joint_dst': 4.5,
			'tibia_spring_to_joint_dst': 3.5,
			'hip_damping': 0.2,
			'knee_damping': 0.2,
			'spring_stiffness': 400,
			'actuator_kp': 254,
		},
		'BR': {
			'motor': {
				'width': 3.6,
				'length': 3.6,
				'height': 5.06,
				'leg_attachment_height': 3.3,
			},
			'position': 'back',
			'leg_attachment_height_offset': 0, # height offset of the leg attachment point relative to the middle of height of the body
			'leg_attachment_length_offset': 3, # offset of leg attachment point relative to front of body
			'femur_length': 7,
			'femur_angle': 0, # angle between femur and vertical in degrees
			'tibia_length': 8.5,
			'spring_length': 2.5,
			'femur_spring_tibia_joint_dst': 4.5,
			'tibia_spring_to_joint_dst': 3.5,
			'hip_damping': 0.2,
			'knee_damping': 0.2,
			'spring_stiffness': 400,
			'actuator_kp': 254,
		},
	},
}

model_scale = 10

tendons = []
actuators = []
sensors = []

class Point(object):
	def __init__(self, x, y, z):
		self.x = x
		self.y = y
		self.z = z

	def offset_by(self, x_offset, y_offset, z_offset):
		self.x = self.x + x_offset
		self.y = self.y + y_offset
		self.z = self.z + z_offset

	def rotate_in_yz(self, angle):
		self.z, self.y = self.y*math.cos(angle) - self.z*math.sin(angle), self.y*math.sin(angle) + self.z*math.cos(angle)

	def get_rescaled_text(self):
		return "{0:.5f} {1:.5f} {2:.5f}".format(self.x / model_scale, self.y / model_scale, self.z / model_scale)

class MotorLeg(object):
	def __init__(self, leg_id, config):
		self.leg_id = leg_id
		self.config = config
		self.leg = Leg(self.leg_id, self.config)

	def generate_xml(self, torso_width, y, z):
		# x and y are the center of the top plane of motor

		width, length, height = self.config['motor']['width'], self.config['motor']['length'], self.config['motor']['height'] 
		
		leg_height = self.leg.get_height()
		leg_xml = self.leg.generate_xml_leg((-1)**((self.leg_id-1)%2) * (torso_width + 0.5), y, z - self.config['motor']['leg_attachment_height'])

		motor = etree.Element('body')
		motor_geom = etree.Element('geom', type="box", mass="0.067", size="{0:.5f} {1:.5f} {2:.5f}".format(width/2/model_scale, length/2/model_scale, height/2/model_scale),  pos="{0:.5f} {1:.5f} {2:.5f}".format((-1)**((self.leg_id-1)%2) * (torso_width - width/2) / model_scale, y / model_scale, (z-height/2) / model_scale))
		# motor_geom = etree.Element('geom', type="box", size="{0:.5f} {1:.5f} {2:.5f}".format(width/2/model_scale, length/2/model_scale, height/2/model_scale),  pos="{0:.5f} {1:.5f} {2:.5f}".format((-1)**(self.leg_id%2) * (torso_width - width/2) / model_scale, y / model_scale, leg_height / model_scale))
		
		motor.extend([motor_geom, leg_xml])
		return motor

	def get_height(self):
		return self.leg.get_height() + self.config['motor']['height'] / 2


class Leg(object):
	def __init__(self, leg_id, config):
		self.leg_id = leg_id
		self.config = config
		self.calc_morphology()

	def calc_tibia_spring_attachment(self):
		tibia_y = (self.config['femur_spring_tibia_joint_dst']**2 + self.config['spring_length']**2 - self.config['tibia_spring_to_joint_dst']**2) / (2 * self.config['femur_spring_tibia_joint_dst'])
		tibia_z = -1.0 * math.sqrt(self.config['spring_length']**2 - tibia_y**2)

		tibia_point = Point(0, tibia_y, tibia_z)
		femur_point = Point(0, self.config['femur_length'] - self.config['femur_spring_tibia_joint_dst'], 0)
		tibia_point.offset_by(0, self.config['femur_length'] - self.config['femur_spring_tibia_joint_dst'], 0)

		# Do rotation
		rotation_angle = self.femur_angle
		tibia_point.rotate_in_yz(rotation_angle)
		femur_point.rotate_in_yz(rotation_angle)

		return femur_point, tibia_point

	def calc_morphology(self):
		self.femur_angle = (self.config['femur_angle'] - 180) / 360 * 2 * math.pi

		self.femur_joint = Point(0, 0, 0)
		self.femur_tibia_joint = Point(
			0,
			math.sin(self.femur_angle) * self.config['femur_length'],
			math.cos(self.femur_angle) * self.config['femur_length'])
		self.femur_attachment, self.tibia_attachment = self.calc_tibia_spring_attachment()

		tibia_foot_y = self.femur_tibia_joint.y + ((self.femur_tibia_joint.y - self.tibia_attachment.y) / self.config['tibia_spring_to_joint_dst'] * (self.config['tibia_length']-self.config['tibia_spring_to_joint_dst']))
		tibia_foot_z = self.femur_tibia_joint.z + ((self.femur_tibia_joint.z - self.tibia_attachment.z) / self.config['tibia_spring_to_joint_dst'] * (self.config['tibia_length']-self.config['tibia_spring_to_joint_dst']))

		self.tibia_foot = Point(0, tibia_foot_y, tibia_foot_z)
		self.tibia_foot2 = Point(0, tibia_foot_y-0.2, tibia_foot_z-0.4)

	def offset_by(self, x, y, z):
		self.femur_joint.offset_by(x, y, z)
		self.femur_tibia_joint.offset_by(x, y, z)
		self.femur_attachment.offset_by(x, y, z)
		self.tibia_attachment.offset_by(x, y, z)
		self.tibia_foot.offset_by(x, y, z)
		self.tibia_foot2.offset_by(x, y, z)

	def generate_xml_leg(self, x, y, z):
		self.offset_by(x, y, z)
		
		leg = etree.Element('body')
		femur_geom = etree.Element('geom', type='capsule', fromto=self.femur_joint.get_rescaled_text() + ' ' + self.femur_tibia_joint.get_rescaled_text())
		femur_joint = etree.Element('joint', pos=self.femur_joint.get_rescaled_text(), name='shoulder_' + str(self.leg_id), damping=str(self.config['hip_damping']))
		femur_site = etree.Element('site', name='s'+str(self.leg_id)+'_1', pos=self.femur_attachment.get_rescaled_text())

		tibia = etree.Element('body')
		tibia_geom = etree.Element('geom', type='capsule', fromto=self.tibia_attachment.get_rescaled_text() + ' ' + self.tibia_foot.get_rescaled_text())
		tibia_joint = etree.Element('joint', limited='true', range='-60 0', pos=self.femur_tibia_joint.get_rescaled_text(), damping=str(self.config['knee_damping']))
		tibia_site = etree.Element('site', name='s'+str(self.leg_id)+'_2', pos=self.tibia_attachment.get_rescaled_text())

		foot = etree.Element('body', pos=self.tibia_foot.get_rescaled_text())
		foot_geom = etree.Element('geom', friction='10 0.005 0.0001', type='capsule', fromto=self.tibia_foot.get_rescaled_text() + ' ' + self.tibia_foot2.get_rescaled_text())
		foot_site = etree.Element('site', name='sensor_'+str(self.leg_id), pos=self.tibia_foot.get_rescaled_text())

		foot.extend([foot_geom, foot_site])
		tibia.extend([tibia_geom, tibia_joint, tibia_site, foot])
		leg.extend([femur_geom, femur_joint, femur_site, tibia])

		tendon = etree.Element('tendon')
		spatial = etree.Element('spatial', stiffness=str(self.config['spring_stiffness']))
		site1 = etree.Element('site', site='s'+str(self.leg_id)+'_1')
		site2 = etree.Element('site', site='s'+str(self.leg_id)+'_2')

		spatial.extend([site1, site2])
		tendon.append(spatial)
		tendons.append(tendon)

		actuators.append(etree.Element('position', ctrllimited="false", ctrlrange="0 6.283185308", joint="shoulder_"+str(self.leg_id), gear="1", kp=str(self.config['actuator_kp'])))
		sensors.append(etree.Element('force', site='sensor_'+str(self.leg_id)))

		return leg

	def get_height(self):
		return -self.tibia_foot.z

def generate_xml_defaults():
	default = etree.Element('default')

	geom = etree.Element('geom', rgba=".9 .7 .1 1", size="0.05", density="1")
	site = etree.Element('site', type="sphere", rgba=".9 .9 .9 1", size="0.005")
	joint = etree.Element('joint', type="hinge", axis="1 0 0", limited="true", range="-100 100", solimplimit="0.95 0.95 0.1")
	tendon = etree.Element('tendon', width="0.02", rgba=".95 .3 .3 1", limited="false", range="0.25 1",  stiffness="4000")

	default.extend([geom, site, joint, tendon])

	return default

def generate_xml_assets():
	asset = etree.Element('asset')

	skybox = etree.Element('texture', type="skybox", builtin="gradient", width="128", height="128", rgb1=".4 .6 .8", rgb2="0 0 0")
	texgeom = etree.Element('texture', name="texgeom", type="cube", builtin="flat", mark="cross", width="127", height="1278", rgb1="0.8 0.6 0.4", rgb2="0.8 0.6 0.4", markrgb="1 1 1", random="0.01")
	texplane = etree.Element('texture', name="texplane", type="2d", builtin="checker", rgb1=".2 .3 .4", rgb2=".1 0.15 0.2", width="512", height="512")
	matplane = etree.Element('material', name='MatPlane', reflectance='0', texture="texplane", texrepeat="1 1", texuniform="true")
	geom_material = etree.Element('material', name='geom', texture="texgeom", texuniform="true")

	asset.extend([skybox, texgeom, texplane, matplane, geom_material])

	return asset

def generate_body():
	leg1 = MotorLeg(1, model_config['legs']['FL'])
	leg2 = MotorLeg(2, model_config['legs']['FR'])
	leg3 = MotorLeg(3, model_config['legs']['BL'])
	leg4 = MotorLeg(4, model_config['legs']['BR'])

	width = model_config['body']['width']
	length = model_config['body']['length']
	height = model_config['body']['height']

	leg_height = max(leg1.get_height(),leg2.get_height(),leg3.get_height(),leg4.get_height())

	worldbody = etree.Element('worldbody')
	floor = etree.Element('geom', name='floor', pos='0 0 0', size='50 50 .125', type='plane', material="MatPlane", condim='3')

	torso = etree.Element('body', name='torso')
	torso_geom = etree.Element('geom', type="box", mass="0.667", size="{0:.5f} {1:.5f} {2:.5f}".format(width/2/model_scale, length/2/model_scale, height/2/model_scale),  pos="0 0 {0:.5f}".format((leg_height + height/2) / model_scale))
	torso_joint = etree.Element('joint', type='free', limited='false', name='gravity')
	torso_sensor_site = etree.Element('site', name='sensor_torso', pos="0 0 {0:.5f}".format(leg_height / model_scale))

	torso.extend([torso_geom, torso_joint, torso_sensor_site])

	torso.append(leg1.generate_xml(width / 2, -1 * length/2 + model_config['legs']['FL']['leg_attachment_length_offset'], leg_height))
	torso.append(leg2.generate_xml(width / 2, -1 * length/2 + model_config['legs']['FR']['leg_attachment_length_offset'], leg_height))
	torso.append(leg3.generate_xml(width / 2, length/2 - model_config['legs']['BL']['leg_attachment_length_offset'], leg_height))
	torso.append(leg4.generate_xml(width / 2, length/2 - model_config['legs']['BR']['leg_attachment_length_offset'], leg_height))

	worldbody.extend([floor, torso])

	return worldbody

def generate_actuators():
	actuator = etree.Element('actuator')
	actuator.extend(actuators)
	return actuator

def generate_sensors():
	sensor = etree.Element('sensor')
	sensors.append(etree.Element('accelerometer', site='sensor_torso'))

	sensor.extend(sensors)

	return sensor

def generate_xml_model(output_file, config=None):
	tendons.clear()
	actuators.clear()
	sensors.clear()

	if config is not None:
		# update model configuration
		for key, value in config.items():
			model_config[key] = value

	root = etree.Element('mujoco', model='quadruped')

	compiler_settings = {'inertiafromgeom': 'true', 'angle': 'degree', 'coordinate': "global"}

	compiler = etree.Element('compiler', **compiler_settings)
	option = etree.Element('option', gravity='0 0 -98.1')

	root.append(compiler)
	root.append(option)
	root.append(generate_xml_defaults())
	root.append(generate_xml_assets())
	root.append(generate_body())

	for tendon in tendons:
		root.append(tendon)

	root.append(generate_actuators())

	root.append(generate_sensors())

	# with open(output_file, 'w') as f:
	f = open(output_file, 'w')
	f.write(etree.tostring(root, pretty_print=True).decode('utf-8'))
	f.flush()
	f.close()

def get_model_generator_version():
	return VERSION

if __name__ == '__main__':
	generate_xml_model('model.xml')