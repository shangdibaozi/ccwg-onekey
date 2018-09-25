import shutil
import os
import time
import json
import sys
import tinify
import os.path
import paramiko
import re

def renameMainJs(cwd):
	path = "./wechatgame"
	for item in os.listdir(path):
		if 'main' in item:
			fullPath = os.path.join(cwd, path, item)
			os.rename(fullPath, os.path.join(cwd, path, 'main.js'))

def buildSettingJson(cwd):
	jsonStr = None
	path = "./wechatgame/src"
	fullPath = None
	for item in os.listdir(path):
		fullPath = os.path.join(cwd, path, item)
		if "settings" in item and os.path.isfile(fullPath):
			break
	with open(fullPath, 'r', encoding='utf-8') as rFile:
		lines = rFile.readlines()
		newLines = []
		for line in lines:
			if '\n' in line:
				line = line.strip('\n')
			line = line.strip()
			newLines.append(line)

		pattern = re.compile("[0-9a-zA-Z]")
		result = []
		for line in newLines:
			if len(line) > 0 and line[0] != '"' and ':' in line and pattern.match(line[0]):
				line = '"' + line 
				index = line.index(':')
				line = line[:index] + '"' + line[index:]
			result.append(line)

		jsonStr = ''.join(result)
		jsonStr = jsonStr.strip('window._CCSettings = ').strip(';')

	os.remove(fullPath)

	with open(os.path.join(cwd, path, 'settings.json'), 'w', encoding='utf-8') as wFile:
		wFile.write(jsonStr)

			
	

def copyFolder(folderName):
	src = "./wechatgame/res"
	# dst = "./wechatgameres/%s/res" % time.strftime("%Y_%m_%d", time.localtime())
	dst = "./wechatgameres/%s/res" % folderName

	# 判断文件夹是否存在
	if os.path.exists(dst):
		# 删除文件夹
		shutil.rmtree(dst)

	if os.path.exists(src):
		# 剪切文件夹
		# 如果在使用命令的过程中，微信开发者工具没有关闭，会引发“src目录不是空的”的异常
		shutil.move(src, dst)

	# 移动settings.json
	path = os.path.join(os.getcwd(), "./wechatgame/src/settings.json")
	shutil.move(path, dst)

	# 拷贝shader1.png和startBtn.png
	# shutil.copy(os.path.join("./wechatgameres", 'share1.png'),  dst)
	# shutil.copy(os.path.join("./wechatgameres", 'startBtn.png'), dst)

def rebuildConfig(resUrl):
	# resUrl = 'https://h5.qiqugame.cn:30013'

	lines = []
	# 读取game.js
	with open('wechatgame/game.js', "r", encoding="utf-8") as file:
		while True:
			line = file.readline()
			if not line:
				break
			lines.append(line)

	# 填写远程ftp服务器地址
	for i in range(len(lines)):
		if 'wxDownloader.REMOTE_SERVER_ROOT' in lines[i]:
			lines[i] = 'wxDownloader.REMOTE_SERVER_ROOT = "%s";\n' % resUrl
			break

	# 写入XMLHttpRequest
	newLines = []
	isNeedT = False
	for line in lines:
		if "src/settings" in line:
			isNeedT = True
			newLines.append("var xhr = new XMLHttpRequest();\n")
			newLines.append("xhr.onreadystatechange = function () {\n")
			newLines.append("\tif (xhr.readyState == 4 && (xhr.status >= 200 && xhr.status < 400)) {\n")
			newLines.append("\t\tvar response = xhr.responseText;\n")
			newLines.append("\t\twindow._CCSettings = JSON.parse(response);\n")
		else:
			if 'main.' in line:
				line = "require('main');\n"
			if isNeedT:
				newLines.append("\t\t" + line)
			else:
				newLines.append(line)
	newLines.append("\n\t}\n")
	newLines.append("};\n")
	newLines.append("xhr.open(\"GET\", '%s/res/settings.json', true);\n" % resUrl)
	newLines.append("xhr.send();\n")

	# 重新覆写game.js
	with open('wechatgame/game.js', "w", encoding = 'utf-8') as file:
		file.writelines(newLines)


	lines.clear()
	with open('wechatgame/project.config.json', 'r', encoding='utf-8') as file:
		allLines = file.readlines()
		ss = ''.join(allLines)
		jsonObj = json.loads(ss, encoding='utf-8')
		jsonObj['description'] = '项目配置文件。'
		setting = jsonObj['setting']
		setting['urlCheck'] = False
		setting['es6'] = False
		setting['postcss'] = True
		setting['minified'] = False
		setting['newFeature'] = False 
			
		# json.dumps在默认情况下，对于非ascii字符生成的是相对应的字符编码，而非原始字符，只需要ensure_ascii = False
		# sort_keys：是否按照字典排序（a-z）输出，True代表是，False代表否。 
		# indent=4：设置缩进格数，一般由于Linux的习惯，这里会设置为4。 
		# separators：设置分隔符，在dic = {'a': 1, 'b': 2, 'c': 3}这行代码里可以看到冒号和逗号后面都带了个空格，这也是因为Python的默认格式也是如此，
		# 如果不想后面带有空格输出，那就可以设置成separators=(',', ':')，如果想保持原样，可以写成separators=(', ', ': ')。 
		rebuildContent = json.dumps(jsonObj, ensure_ascii = False, sort_keys = False, indent = 4, separators = (',', ' : '))
		lines.append(rebuildContent)
		
	with open('wechatgame/project.config.json', 'w', encoding='utf-8') as file:
		file.writelines(lines)

def tinypng(src, dst):
	"""
	将初步打包的项目下的图片资源上传到tinypng上进行压缩
	src和dst要穿完整路径
	"""
	tinify.key = "去tinypng官网申请的key"

	fromFilePath = src
	toFilePath = dst

	def compress_core(inputFile, outputFile):
		source = tinify.from_file(inputFile)
		source.to_file(outputFile)

	for root, dirs, files in os.walk(fromFilePath):
		for name in files:
			fileName, fileSuffix = os.path.splitext(name) # 解析文件名和文件类型后缀
			if fileSuffix == '.png' or fileSuffix == '.jpg':
				toFullPath = toFilePath + root[len(fromFilePath):]
				toFullName = os.path.join(toFullPath, name)
				print(toFullName)
				if os.path.isdir(toFullPath):
					pass
				else:
					os.mkdir(toFullPath)

				compress_core(toFullName, toFullName)

def upload(folderName):
	ip = '服务端ip'
	port = 端口
	username = '帐号'
	password = '密码'

	cwd = os.getcwd()

	def sftp(src, dest):
		"""
		上传压缩包到服务端
		"""
		transport = paramiko.Transport((ip, port))
		transport.connect(username = username, password = password)
		sftp = paramiko.SFTPClient.from_transport(transport)
		sftp.put(src, dest)
		sftp.close()
		return True

	def ssh_exec_command(commands):
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh.connect(hostname = ip, port = port, username = username, password = password)

		for command in commands:
			stdin, stdout, stderr = ssh.exec_command(command)
			print(stdout.read().decode())
			print(stderr.read().decode())
		ssh.close()
	# 先上传文件到服务端
	# 然后解压缩文件
	resPath = os.path.join(cwd, "wechatgameres/res.zip")
	if sftp(resPath, '/home/fish/fishres/res.zip'):
		cmds = []
		cmds.append('cd /home/fish/fishres;')
		cmds.append('rm -rf %s;' % folderName)
		cmds.append('sh unzip.sh')
		ssh_exec_command([''.join(cmds)])
		print('success')

def zipFolder(folderName):
	"""
	调用7z对文件进行压缩操作
	"""
	if os.path.isfile("./wechatgameres/res.zip"):
		os.remove("./wechatgameres/res.zip")
	# src = "./wechatgameres/%s" % time.strftime("%Y_%m_%d", time.localtime())
	src = "./wechatgameres/%s" % folderName
	os.system('"D:\\Program Files\\7-Zip\\7z.exe" a ./wechatgameres/res.zip %s' % src)

if __name__ == '__main__':
	folderName = time.strftime("%Y_%m_%d_%H_%M", time.localtime())
	print('-----------------------开始重构微信小游戏配置文件--------')
	rebuildConfig('https://h5.qiqugame.cn:40013/%s' % folderName)
	cwd = os.getcwd()
	fromFilePath = os.path.join(cwd, "wechatgame/res")
	toFilePath = os.path.join(cwd, "wechatgame/res")
	print('-----------------------开始压缩图片资源------------------')
	tinypng(fromFilePath, toFilePath)
	print('-----------------------重命名main.js--------------------')
	renameMainJs(cwd)
	print('-----------------------创建settings.json文件------------')
	buildSettingJson(cwd)
	print('-----------------------开始拷贝资源文件------------------')
	copyFolder(folderName)
	print('-----------------------开始压缩文件----------------------')
	zipFolder(folderName)
	print('-----------------------开始上传文件----------------------')
	upload(folderName)
