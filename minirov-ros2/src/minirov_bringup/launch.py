from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='minirov_bringup',
            executable='mavlink_node',
            name='mavlink_node',
            output='screen',
        ),
        Node(
            package='minirov_bringup',
            executable='llm_node',
            name='llm_node',
            output='screen',
        ),
        Node(
            package='minirov_bringup',
            executable='operator_node',
            name='operator_node',
            output='screen',
        ),
        Node(
            package='minirov_bringup',
            executable='logger_node',
            name='logger_node',
            output='screen',
        ),
    ])