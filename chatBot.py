import erniebot
import gradio as gr
from spire.doc import *
from spire.doc.common import *
from spire.presentation import *
from spire.presentation.common import *
import argparse

from marker.convert import convert_single_pdf
from marker.logger import configure_logging
from marker.models import load_all_models
import json

erniebot.api_type = "aistudio"
erniebot.access_token = "4f6d02126358f9f440f27db45da1ff4dabbf9490"

import base64
import hashlib
import hmac
import json
import os
import time

import requests

lfasr_host = "http://raasr.xfyun.cn/api"

# 请求的接口名
api_prepare = "/prepare"
api_upload = "/upload"
api_merge = "/merge"
api_get_progress = "/getProgress"
api_get_result = "/getResult"
# 文件分片大小10M
file_piece_sice = 10485760

# ——————————————————转写可配置参数————————————————
# 参数可在官网界面（https://doc.xfyun.cn/rest_api/%E8%AF%AD%E9%9F%B3%E8%BD%AC%E5%86%99.html）查看，根据需求可自行在gene_params方法里添加修改
# 转写类型
lfasr_type = 0
# 是否开启分词
has_participle = "false"
has_seperate = "true"
# 多候选词个数
max_alternatives = 0
# 子用户标识
suid = ""


class SliceIdGenerator:
    """slice id生成器"""

    def __init__(self):
        self.__ch = "aaaaaaaaa`"

    def getNextSliceId(self):
        ch = self.__ch
        j = len(ch) - 1
        while j >= 0:
            cj = ch[j]
            if cj != "z":
                ch = ch[:j] + chr(ord(cj) + 1) + ch[j + 1 :]
                break
            else:
                ch = ch[:j] + "a" + ch[j + 1 :]
                j = j - 1
        self.__ch = ch
        return self.__ch


class RequestApi(object):
    def __init__(self, appid, secret_key, upload_file_path):
        self.appid = appid
        self.secret_key = secret_key
        self.upload_file_path = upload_file_path

    # 根据不同的apiname生成不同的参数,本示例中未使用全部参数您可在官网(https://doc.xfyun.cn/rest_api/%E8%AF%AD%E9%9F%B3%E8%BD%AC%E5%86%99.html)查看后选择适合业务场景的进行更换
    def gene_params(self, apiname, taskid=None, slice_id=None):
        appid = self.appid
        secret_key = self.secret_key
        upload_file_path = self.upload_file_path
        ts = str(int(time.time()))
        m2 = hashlib.md5()
        m2.update((appid + ts).encode("utf-8"))
        md5 = m2.hexdigest()
        md5 = bytes(md5, encoding="utf-8")
        # 以secret_key为key, 上面的md5为msg， 使用hashlib.sha1加密结果为signa
        signa = hmac.new(secret_key.encode("utf-8"), md5, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, "utf-8")
        file_len = os.path.getsize(upload_file_path)
        file_name = os.path.basename(upload_file_path)
        param_dict = {}

        if apiname == api_prepare:
            # slice_num是指分片数量，如果您使用的音频都是较短音频也可以不分片，直接将slice_num指定为1即可
            slice_num = int(file_len / file_piece_sice) + (
                0 if (file_len % file_piece_sice == 0) else 1
            )
            param_dict["app_id"] = appid
            param_dict["signa"] = signa
            param_dict["ts"] = ts
            param_dict["file_len"] = str(file_len)
            param_dict["file_name"] = file_name
            param_dict["slice_num"] = str(slice_num)
        elif apiname == api_upload:
            param_dict["app_id"] = appid
            param_dict["signa"] = signa
            param_dict["ts"] = ts
            param_dict["task_id"] = taskid
            param_dict["slice_id"] = slice_id
        elif apiname == api_merge:
            param_dict["app_id"] = appid
            param_dict["signa"] = signa
            param_dict["ts"] = ts
            param_dict["task_id"] = taskid
            param_dict["file_name"] = file_name
        elif apiname == api_get_progress or apiname == api_get_result:
            param_dict["app_id"] = appid
            param_dict["signa"] = signa
            param_dict["ts"] = ts
            param_dict["task_id"] = taskid
        return param_dict

    # 请求和结果解析，结果中各个字段的含义可参考：https://doc.xfyun.cn/rest_api/%E8%AF%AD%E9%9F%B3%E8%BD%AC%E5%86%99.html
    def gene_request(self, apiname, data, files=None, headers=None):
        response = requests.post(
            lfasr_host + apiname, data=data, files=files, headers=headers
        )
        result = json.loads(response.text)
        if result["ok"] == 0:
            # print("{} success:".format(apiname) + str(result))
            return result
        else:
            # print("{} error:".format(apiname) + str(result))
            exit(0)
            return result

    # 预处理
    def prepare_request(self):
        return self.gene_request(
            apiname=api_prepare, data=self.gene_params(api_prepare)
        )

    # 上传
    def upload_request(self, taskid, upload_file_path):
        file_object = open(upload_file_path, "rb")
        try:
            index = 1
            sig = SliceIdGenerator()
            while True:
                content = file_object.read(file_piece_sice)
                if not content or len(content) == 0:
                    break
                files = {
                    "filename": self.gene_params(api_upload).get("slice_id"),
                    "content": content,
                }
                response = self.gene_request(
                    api_upload,
                    data=self.gene_params(
                        api_upload, taskid=taskid, slice_id=sig.getNextSliceId()
                    ),
                    files=files,
                )
                if response.get("ok") != 0:
                    # 上传分片失败
                    # print('upload slice fail, response: ' + str(response))
                    return False
                # print('upload slice ' + str(index) + ' success')
                index += 1
        finally:
            "file index:" + str(file_object.tell())
            file_object.close()
        return True

    # 合并
    def merge_request(self, taskid):
        return self.gene_request(
            api_merge, data=self.gene_params(api_merge, taskid=taskid)
        )

    # 获取进度
    def get_progress_request(self, taskid):
        return self.gene_request(
            api_get_progress, data=self.gene_params(api_get_progress, taskid=taskid)
        )

    # 获取结果
    def get_result_request(self, taskid):
        return self.gene_request(
            api_get_result, data=self.gene_params(api_get_result, taskid=taskid)
        )

    def all_api_request(self):
        # 1. 预处理
        pre_result = self.prepare_request()
        taskid = pre_result["data"]
        # 2 . 分片上传
        self.upload_request(taskid=taskid, upload_file_path=self.upload_file_path)
        # 3 . 文件合并
        self.merge_request(taskid=taskid)
        # 4 . 获取任务进度
        while True:
            # 每隔20秒获取一次任务进度
            progress = self.get_progress_request(taskid)
            progress_dic = progress
            if progress_dic["err_no"] != 0 and progress_dic["err_no"] != 26605:
                # print('task error: ' + progress_dic['failed'])
                return
            else:
                data = progress_dic["data"]
                task_status = json.loads(data)
                if task_status["status"] == 9:
                    # print('task ' + taskid + ' finished')
                    break
                # print('The task ' + taskid + ' is in processing, task status: ' + str(data))

            # 每次获取进度间隔20S
            time.sleep(20)

            res = self.get_result_request(taskid=taskid)
            result = ""
            res_data = json.loads(res["data"])
            for i in res_data:
                result = result + i["onebest"]
            # #print('\n',res_data,'\n',res_data[0])
            print(result)
            return result


def audioToText(path):
    api = RequestApi(
        appid="6dfa0f1c",
        secret_key="51b5696302968fa926dce34baf523873",
        upload_file_path=path,
    )
    return api.all_api_request()


def pptToText(path):
    # 创建 Presentation 类的对象
    pres = Presentation()

    # 加载 PowerPoint 演示文稿
    pres.LoadFromFile(path)

    ppt_text = ""
    for slide in pres.Slides:
        # 循环遍历每个形状
        for shape in slide.Shapes:
            # 检查形状是否为 IAutoShape 实例
            if isinstance(shape, IAutoShape):
                # from形状提取文本
                for paragraph in shape.TextFrame.Paragraphs:
                    ppt_text = ppt_text + paragraph.Text
    return ppt_text


def wordToText(path):
    # 创建Document实例
    document = Document()
    # 加载Word文档
    document.LoadFromFile(path)

    # 获取文档的文本内容
    document_text = document.GetText()
    return document_text


def txtToText(path):
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
        print(data)
        return data


def pdfToText(path):
    model_lst = load_all_models()
    full_text, _, _ = convert_single_pdf(
        path, model_lst, max_pages=10, batch_multiplier=2, langs=["Chinese", "English"]
    )
    return full_text


old_filename = None
text = ""


def predict(message, history, filename):
    global text
    global old_filename
    history_ernie_format = []

    if filename != old_filename:
        old_filename = filename
        file_extension = os.path.splitext(filename)[-1]
        if (
            file_extension == ".mp4"
            or file_extension == ".mp3"
            or file_extension == "wave"
        ):
            text = audioToText(filename)

        if file_extension == ".doc" or file_extension == ".docx":
            text = wordToText(filename)
        if file_extension == ".pptx":
            text = pptToText(filename)
            print(text)
        if file_extension == ".txt":
            text = txtToText(filename)
        if file_extension == ".pdf":
            text = pdfToText(filename)

        history_ernie_format = [
            {
                "role": "user",
                "content": "下面是一段{file_format}的内容'{txt}'".format(
                    file_format=file_extension, txt=text
                ),
            },
            {"role": "assistant", "content": "你好"},
        ]

    for human, assistant in history:
        history_ernie_format.append({"role": "user", "content": human})
        history_ernie_format.append({"role": "assistant", "content": assistant})
    history_ernie_format.append({"role": "user", "content": message})

    response = erniebot.ChatCompletion.create(
        model="ernie-4.0",
        messages=history_ernie_format,
    )

    return response.get_result()


demo = gr.ChatInterface(
    predict,
    additional_inputs=[gr.File()],
)
if __name__ == "__main__":
    demo.launch()
