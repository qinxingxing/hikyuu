# coding:utf-8
#
# The MIT License (MIT)
#
# Copyright (c) 2010-2017 fasiondog/hikyuu
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import hashlib
import sqlite3
import urllib.request

from hikyuu.data.weight_to_sqlite import qianlong_import_weight

class ImportWeightToSqliteTask:
    def __init__(self, queue, sqlitefile, dest_dir):
        self.queue = queue
        self.sqlitefile = sqlitefile
        self.dest_dir = dest_dir
        self.msg_name = 'IMPORT_WEIGHT'

    def __call__(self):
        total_count = 0
        try:
            connect = sqlite3.connect(self.sqlitefile)
        except Exception as e:
            #self.queue.put([self.msg_name, str(e), -1, 0, total_count])
            self.queue.put([self.msg_name, 'INFO', str(e), 0, 0])
            self.queue.put([self.msg_name, '', 0, None, total_count])
            return

        try:
            download_dir = self.dest_dir + "/downloads"
            if not os.path.lexists(download_dir):
                os.makedirs(download_dir)
            
            self.queue.put([self.msg_name, '正在下载...', 0, 0, 0])
            net_file = urllib.request.urlopen('http://www.qianlong.com.cn/download/history/weight.rar', timeout=60)
            buffer = net_file.read()

            self.queue.put([self.msg_name, '下载完成，正在校验是否存在更新...', 0, 0, 0])
            new_md5 = hashlib.md5(buffer).hexdigest()

            dest_filename = download_dir + '/weight.rar'
            old_md5 = None
            if os.path.exists(dest_filename):
                with open(dest_filename, 'rb') as oldfile:
                    old_md5 = hashlib.md5(oldfile.read()).hexdigest()

            #如果没变化不需要解压导入
            if new_md5 != old_md5:
                with open(dest_filename, 'wb') as file:
                    file.write(buffer)

                self.queue.put([self.msg_name, '下载完成，正在解压...', 0, 0, 0])
                x = os.system('unrar x -o+ -inul {} {}'.format(dest_filename, download_dir))
                if x != 0:
                    raise Exception("无法找到unrar命令！")

                self.queue.put([self.msg_name, '解压完毕，正在导入权息数据...', 0, 0, 0])
                total_count = qianlong_import_weight(connect, download_dir + '/weight', 'SH')
                total_count += qianlong_import_weight(connect, download_dir + '/weight', 'SZ')
                self.queue.put([self.msg_name, '导入完成!', 0, 0, total_count])

            else:
                self.queue.put([self.msg_name, 'INFO', '权息数据无变化', 0, 0])

        except Exception as e:
            #self.queue.put([self.msg_name, str(e), -1, 0, total_count])
            self.queue.put([self.msg_name, 'INFO', str(e), 0, 0])
        finally:
            connect.commit()
            connect.close()

        self.queue.put([self.msg_name, '', 0, None, total_count])
