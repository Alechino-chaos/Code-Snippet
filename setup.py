from setuptools import setup

setup(
    name='Code-Snippet',         # 你的开源项目名称
    version='1.0.0',         # 版本号
    py_modules=['main'],     # 你的核心代码文件名 (不带 .py)
    entry_points={
        'console_scripts': [
            # 这里的格式是：'你想缩短的命令名 = 文件名:函数名'
            'snip = main:main', 
        ],
    },
)