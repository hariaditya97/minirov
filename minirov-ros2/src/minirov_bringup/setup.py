from setuptools import find_packages, setup

package_name = 'minirov_bringup'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='hari',
    maintainer_email='hari@todo.todo',
    description='ROS 2 nodes for miniROV',
    license='GPL-3.0-only',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
    'console_scripts': [
        'mavlink_node = minirov_bringup.mavlink_node:main',
        'llm_node = minirov_bringup.llm_node:main',
        'operator_node = minirov_bringup.operator_node:main',
        'logger_node = minirov_bringup.logger_node:main',
    ],
  },
)
