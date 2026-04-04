import router from '@ohos.router';
import picker from '@ohos.file.picker';
import fs from '@ohos.file.fs';
import http from '@ohos.net.http';
import { apiGet, BASE_URL } from '../common/Api';
import { WebSocketClient } from '../common/WebSocketClient';

interface DetectionResult {
  status: string;
  ocrText: string;
  presetModel: string;
  isMatch: boolean;
  defectType: string;
  positionStatus: string;
  positionX: number;
  positionY: number;
  timestamp: string;
  imageUrl: string;
  confidence: number;
}

interface RecentRecord {
  timestamp: string;
  presetModel: string;
  status: string;
  defectType: string;
  positionStatus: string;
}

@Entry
@Component
struct Index {
  @State currentTab: number = 0;
  @State currentResult: DetectionResult = {
    status: '', ocrText: '', presetModel: '', isMatch: false,
    defectType: '无', positionStatus: '正常', positionX: 50, positionY: 50,
    timestamp: '', imageUrl: '', confidence: 0
  };
  @State recentList: RecentRecord[] = [];
  @State mlAvailable: boolean = false;
  @State isLoading: boolean = false;
  @State wsConnected: boolean = false;
  @State previewUri: string = '';
  @State detecting: boolean = false;

  private wsClient: WebSocketClient = new WebSocketClient();
  private tabs: string[] = ['监控', '历史', '统计', '设置'];
  private tabIcons: string[] = ['📡', '📋', '📊', '⚙️'];
  private defectNames: string[] = ['破损', '污渍', '褶皱', '划痕', '偏移'];
  private defectIcons: string[] = ['💔', '💧', '📄', '🔪', '↔️'];

  aboutToAppear() {
    this.loadData();
    // WebSocket 实时推送
    this.wsClient.setOnMessage((data: object) => {
      let d = data as Record<string, string | number | boolean>;
      if (d['type'] === 'detection_result') {
        // 收到新检测结果，刷新数据
        this.loadData();
      }
    });
    this.wsClient.setOnStatusChange((connected: boolean) => {
      this.wsConnected = connected;
    });
    this.wsClient.connect();
  }

  aboutToDisappear() {
    this.wsClient.disconnect();
  }

  async loadData() {
    this.isLoading = true;
    try {
      let status = await apiGet('/api/ml/status') as Record<string, boolean>;
      this.mlAvailable = status.available === true;
    } catch (e) {}
    try {
      let result = await apiGet('/api/current') as DetectionResult;
      if (result.status) {
        this.currentResult = {
          status: result.status || '',
          ocrText: result.ocrText || '',
          presetModel: result.presetModel || '',
          isMatch: result.isMatch || false,
          defectType: result.defectType || '无',
          positionStatus: result.positionStatus || '正常',
          positionX: result.positionX || 50,
          positionY: result.positionY || 50,
          timestamp: result.timestamp || '',
          imageUrl: result.imageUrl || '',
          confidence: result.confidence || 0
        };
      }
    } catch (e) {}
    try {
      let records = await apiGet('/api/recent?limit=10') as RecentRecord[];
      this.recentList = records.map((item: RecentRecord) => ({
        timestamp: item.timestamp || '',
        presetModel: item.presetModel || '',
        status: item.status || '',
        defectType: item.defectType || '无',
        positionStatus: item.positionStatus || '正常'
      }));
    } catch (e) {}
    this.isLoading = false;
  }

  async pickImage() {
    try {
      let photoPicker = new picker.PhotoViewPicker();
      let result = await photoPicker.select({ MIMEType: picker.PhotoViewMIMETypes.IMAGE_TYPE, maxSelectNumber: 1 });
      if (result.photoUris && result.photoUris.length > 0) {
        this.previewUri = result.photoUris[0];
      }
    } catch (e) { /* user cancelled */ }
  }

  async doDetect() {
    if (this.previewUri === '' || this.detecting) return;
    this.detecting = true;
    try {
      // 读取文件到缓存目录以便上传
      let context = getContext(this);
      let srcFile = await fs.open(this.previewUri, fs.OpenMode.READ_ONLY);
      let cacheDir = context.cacheDir;
      let tmpPath = cacheDir + '/upload_' + Date.now() + '.jpg';
      let dstFile = await fs.open(tmpPath, fs.OpenMode.CREATE | fs.OpenMode.READ_WRITE);
      let buf = new ArrayBuffer(4 * 1024 * 1024); // 4MB buffer
      let readLen = await fs.read(srcFile.fd, buf);
      await fs.write(dstFile.fd, buf, { length: readLen });
      await fs.close(srcFile);
      await fs.close(dstFile);

      // multipart/form-data 上传
      let req = http.createHttp();
      let boundary = '----FormBoundary' + Date.now();
      let fileData = await fs.readText(tmpPath);

      // 使用 request 上传
      let uploadReq = http.createHttp();
      let resp = await new Promise<string>((resolve, reject) => {
        uploadReq.request(BASE_URL + '/api/ml/detect', {
          method: http.RequestMethod.POST,
          header: { 'Content-Type': 'multipart/form-data' },
          multiFormDataList: [{
            name: 'file',
            contentType: 'image/jpeg',
            remoteFileName: 'detect.jpg',
            filePath: tmpPath
          }]
        }, (err, data) => {
          if (!err && data.responseCode === 200) {
            resolve(data.result as string);
          } else {
            reject(new Error(err?.message || `HTTP ${data?.responseCode}`));
          }
          uploadReq.destroy();
        });
      });

      let d = JSON.parse(resp) as Record<string, string | number | boolean>;
      this.currentResult = {
        status: (d['status'] as string) || (d['is_qualified'] ? 'OK' : 'NG'),
        ocrText: (d['ocr_text'] as string) || '',
        presetModel: (d['preset_model'] as string) || '',
        isMatch: (d['is_qualified'] as boolean) || false,
        defectType: (d['defect_type'] as string) || '无',
        positionStatus: (d['position_status'] as string) || '正常',
        positionX: d['position_x'] ? Math.round((d['position_x'] as number) * 100) : 50,
        positionY: d['position_y'] ? Math.round((d['position_y'] as number) * 100) : 50,
        timestamp: (d['timestamp'] as string) || new Date().toLocaleTimeString(),
        imageUrl: (d['image_url'] as string) || '',
        confidence: (d['confidence'] as number) || 0
      };

      // 清理临时文件
      try { await fs.unlink(tmpPath); } catch (e) {}

      // 刷新最近记录
      this.loadData();
      AlertDialog.show({ message: d['is_qualified'] ? '检测合格 ✓' : '检测不合格 ✗' });
    } catch (e) {
      AlertDialog.show({ message: '检测失败: ' + (e as Error).message });
    }
    this.detecting = false;
  }

  onTabChange(idx: number) {
    if (idx === 0) {
      this.loadData();
      return;
    }
    let pages: string[] = ['', 'pages/History', 'pages/Statistics', 'pages/Settings'];
    if (pages[idx]) {
      router.pushUrl({ url: pages[idx] });
    }
  }

  build() {
    Column() {
      // 顶部栏
      Row() {
        Column() {
          Text('实时监控').fontSize(20).fontWeight(FontWeight.Bold).fontColor('#FFFFFF')
          Text('上传图片检测能效标签').fontSize(11).fontColor('#888888').margin({ top: 2 })
        }.alignItems(HorizontalAlign.Start)
        Blank()
        Row() {
          Circle({ width: 8, height: 8 }).fill(this.mlAvailable ? '#10B981' : '#EF4444')
          Text(this.mlAvailable ? 'ML就绪' : 'ML离线')
            .fontSize(11).fontColor(this.mlAvailable ? '#10B981' : '#EF4444').margin({ left: 6 })
        }.padding({ left: 10, right: 10, top: 4, bottom: 4 }).borderRadius(16)
        .backgroundColor(this.mlAvailable ? '#10B98115' : '#EF444415')
        // WS 状态
        Row() {
          Circle({ width: 6, height: 6 }).fill(this.wsConnected ? '#06B6D4' : '#666666')
          Text('WS').fontSize(9).fontColor(this.wsConnected ? '#06B6D4' : '#666666').margin({ left: 4 })
        }.padding({ left: 6, right: 6, top: 2, bottom: 2 }).borderRadius(10).backgroundColor('#FFFFFF08').margin({ left: 6 })

        Button('刷新').fontSize(11).height(28).margin({ left: 8 }).onClick(() => this.loadData())
      }.width('100%').padding({ left: 16, right: 16, top: 12, bottom: 12 }).backgroundColor('#1A1A2E')

      // 图片上传检测区域
      Column() {
        Text('📤 图片检测').fontSize(14).fontWeight(FontWeight.Medium).fontColor('#FFFFFF').margin({ bottom: 10 })
        if (this.detecting) {
          Row() {
            Text('⏳ 正在检测...').fontSize(13).fontColor('#818CF8')
          }.width('100%').height(100).justifyContent(FlexAlign.Center).borderRadius(10)
          .border({ width: 2, color: '#6366F140', style: BorderStyle.Dashed })
        } else if (this.previewUri !== '') {
          Image(this.previewUri).width('100%').height(160).objectFit(ImageFit.Contain).borderRadius(10)
        } else {
          Row() {
            Column() {
              Text('📁').fontSize(28)
              Text('点击选择图片').fontSize(12).fontColor('#888888').margin({ top: 4 })
            }.alignItems(HorizontalAlign.Center)
          }.width('100%').height(100).justifyContent(FlexAlign.Center).borderRadius(10)
          .border({ width: 2, color: '#FFFFFF15', style: BorderStyle.Dashed }).backgroundColor('#FFFFFF06')
          .onClick(() => this.pickImage())
        }
        Row() {
          Button('📁 选择图片').fontSize(12).height(32).layoutWeight(1).backgroundColor('#FFFFFF08').fontColor('#AAAAAA')
            .borderRadius(10).onClick(() => this.pickImage())
          Button('🔍 开始检测').fontSize(12).height(32).layoutWeight(2).backgroundColor('#6366F1').fontColor('#FFFFFF')
            .borderRadius(10).margin({ left: 8 }).enabled(this.previewUri !== '' && !this.detecting)
            .opacity(this.previewUri !== '' && !this.detecting ? 1.0 : 0.4)
            .onClick(() => this.doDetect())
          Button('清除').fontSize(12).height(32).layoutWeight(1).backgroundColor('#FFFFFF08').fontColor('#AAAAAA')
            .borderRadius(10).margin({ left: 8 }).onClick(() => { this.previewUri = ''; })
        }.width('100%').margin({ top: 10 })
      }.width('100%').padding(14).borderRadius(12).backgroundColor('#0F3460').margin({ left: 12, right: 12, top: 12, bottom: 6 })

      // 主内容
      Scroll() {
        Column() {
          // 状态条
          if (this.currentResult.status !== '') {
            Row() {
              Text(this.currentResult.status === 'OK' ? '✓' : '✗').fontSize(24)
                .fontColor(this.currentResult.status === 'OK' ? '#10B981' : '#EF4444')
              Column() {
                Text(this.currentResult.status === 'OK' ? '检测合格' : '检测不合格')
                  .fontSize(16).fontWeight(FontWeight.Bold)
                  .fontColor(this.currentResult.status === 'OK' ? '#10B981' : '#EF4444')
                Text(this.currentResult.timestamp).fontSize(10).fontColor('#888888').margin({ top: 2 })
              }.margin({ left: 12 })
              Blank()
              if (this.currentResult.ocrText !== '') {
                Text(this.currentResult.ocrText).fontSize(18).fontWeight(FontWeight.Bold).fontColor('#818CF8')
                  .padding({ left: 12, right: 12, top: 4, bottom: 4 }).borderRadius(8).backgroundColor('#FFFFFF08')
              }
            }.width('100%').padding(14).borderRadius(12)
            .backgroundColor(this.currentResult.status === 'OK' ? '#10B98112' : '#EF444412')
            .margin({ bottom: 12 })

            // 标签识别
            Column() {
              Text('📋 标签识别').fontSize(14).fontWeight(FontWeight.Medium).fontColor('#FFFFFF').margin({ bottom: 10 })
              Row() {
                Text('识别标签：').fontSize(12).fontColor('#AAAAAA')
                Text(this.currentResult.ocrText || '--').fontSize(16).fontWeight(FontWeight.Bold).fontColor('#818CF8')
              }.width('100%').margin({ bottom: 6 })
              Row() {
                Text('预设型号：').fontSize(12).fontColor('#AAAAAA')
                Text(this.currentResult.presetModel || '--').fontSize(12).fontColor('#FFFFFF')
              }.width('100%').margin({ bottom: 6 })
              Row() {
                Text('置信度：').fontSize(12).fontColor('#AAAAAA')
                Text(this.currentResult.confidence > 0 ? (this.currentResult.confidence * 100).toFixed(1) + '%' : '--')
                  .fontSize(12).fontColor('#FFFFFF')
              }.width('100%').margin({ bottom: 6 })
              Row() {
                Text('比对结果：').fontSize(12).fontColor('#AAAAAA')
                Text(this.currentResult.isMatch ? '✓ 匹配' : '✗ 不匹配')
                  .fontSize(12).fontWeight(FontWeight.Bold)
                  .fontColor(this.currentResult.isMatch ? '#10B981' : '#EF4444')
              }.width('100%')
            }.width('100%').padding(14).borderRadius(10).backgroundColor('#0F3460').margin({ bottom: 10 })

            // 缺陷检测
            Column() {
              Text('⚠️ 缺陷检测').fontSize(14).fontWeight(FontWeight.Medium).fontColor('#FFFFFF').margin({ bottom: 10 })
              Row() {
                ForEach(this.defectNames, (name: string, idx: number) => {
                  let active = this.currentResult.defectType.includes(name);
                  Column() {
                    Text(this.defectIcons[idx]).fontSize(18)
                    Text(name).fontSize(10).fontWeight(FontWeight.Medium).fontColor('#FFFFFF').margin({ top: 2 })
                    Text(active ? '检出' : '正常').fontSize(9)
                      .fontColor(active ? '#EF4444' : '#888888').margin({ top: 2 })
                  }.width('18%').padding(6).borderRadius(8).alignItems(HorizontalAlign.Center)
                  .backgroundColor(active ? '#EF444412' : '#FFFFFF06')
                  .border({ width: 1, color: active ? '#EF444440' : '#FFFFFF10' })
                })
              }.width('100%').justifyContent(FlexAlign.SpaceBetween)
            }.width('100%').padding(14).borderRadius(10).backgroundColor('#0F3460').margin({ bottom: 10 })

            // 位置检测
            Column() {
              Text('📍 位置检测').fontSize(14).fontWeight(FontWeight.Medium).fontColor('#FFFFFF').margin({ bottom: 10 })
              Row() {
                // 3x3 宫格
                Grid() {
                  ForEach([0, 1, 2, 3, 4, 5, 6, 7, 8], (i: number) => {
                    GridItem() {
                      Column() {
                        if (Math.floor((this.currentResult.positionY) / 34) === Math.floor(i / 3) &&
                            Math.floor((this.currentResult.positionX) / 34) === i % 3) {
                          Circle({ width: 10, height: 10 }).fill('#6366F1')
                        }
                      }.width('100%').height('100%').justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
                      .backgroundColor(
                        Math.floor((this.currentResult.positionY) / 34) === Math.floor(i / 3) &&
                        Math.floor((this.currentResult.positionX) / 34) === i % 3
                          ? '#6366F130' : '#FFFFFF06'
                      ).borderRadius(4).border({ width: 1, color: '#FFFFFF10' })
                    }
                  })
                }.columnsTemplate('1fr 1fr 1fr').rowsTemplate('1fr 1fr 1fr').width(80).height(80).columnsGap(3).rowsGap(3)

                Column() {
                  Text('粘贴位置').fontSize(11).fontColor('#888888')
                  Text(this.currentResult.positionStatus).fontSize(16).fontWeight(FontWeight.Bold)
                    .fontColor(this.currentResult.positionStatus === '正常' ? '#10B981' : '#EF4444').margin({ top: 4 })
                }.margin({ left: 20 })
              }.width('100%')
            }.width('100%').padding(14).borderRadius(10).backgroundColor('#0F3460').margin({ bottom: 10 })
          } else {
            Column() {
              Text('📷').fontSize(40)
              Text('暂无检测结果').fontSize(14).fontColor('#888888').margin({ top: 8 })
              Text('请通过Web端或移动端上传图片检测').fontSize(11).fontColor('#666666').margin({ top: 4 })
            }.width('100%').padding(40).borderRadius(12).backgroundColor('#0F3460')
            .alignItems(HorizontalAlign.Center).margin({ bottom: 12 })
          }

          // 最近记录
          Column() {
            Row() {
              Text('📝 最近记录').fontSize(14).fontWeight(FontWeight.Medium).fontColor('#FFFFFF')
              Blank()
              Text(this.recentList.length + ' 条').fontSize(11).fontColor('#888888')
            }.width('100%').margin({ bottom: 10 })

            Row() {
              Text('时间').fontSize(9).fontColor('#666666').width('25%')
              Text('型号').fontSize(9).fontColor('#666666').width('20%')
              Text('结果').fontSize(9).fontColor('#666666').width('15%').textAlign(TextAlign.Center)
              Text('缺陷').fontSize(9).fontColor('#666666').width('20%').textAlign(TextAlign.Center)
              Text('位置').fontSize(9).fontColor('#666666').width('20%').textAlign(TextAlign.Center)
            }.width('100%').padding({ bottom: 6 })

            if (this.recentList.length > 0) {
              ForEach(this.recentList, (item: RecentRecord) => {
                Row() {
                  Text(item.timestamp.slice(-8)).fontSize(10).fontColor('#AAAAAA').width('25%')
                  Text(item.presetModel).fontSize(10).fontColor('#FFFFFF').width('20%')
                  Text(item.status).fontSize(10).fontWeight(FontWeight.Bold)
                    .fontColor(item.status === 'OK' ? '#10B981' : '#EF4444').width('15%').textAlign(TextAlign.Center)
                  Text(item.defectType || '无').fontSize(10).fontColor('#AAAAAA').width('20%').textAlign(TextAlign.Center)
                  Text(item.positionStatus).fontSize(10)
                    .fontColor(item.positionStatus === '正常' ? '#10B981' : '#EF4444').width('20%').textAlign(TextAlign.Center)
                }.width('100%').padding({ top: 6, bottom: 6 }).borderWidth({ bottom: 1 }).borderColor('#1A1A2E')
              })
            } else {
              Text('暂无记录').fontSize(12).fontColor('#666666').width('100%').textAlign(TextAlign.Center).padding(20)
            }
          }.width('100%').padding(14).borderRadius(12).backgroundColor('#0F3460')
        }.width('100%').padding(12)
      }.width('100%').layoutWeight(1).backgroundColor('#0A0A1A')

      // 底部 TabBar
      Row() {
        ForEach(this.tabs, (tab: string, idx: number) => {
          Column() {
            Text(this.tabIcons[idx]).fontSize(20)
            Text(tab).fontSize(10).fontColor(this.currentTab === idx ? '#818CF8' : '#888888').margin({ top: 2 })
          }.layoutWeight(1).alignItems(HorizontalAlign.Center).padding({ top: 8, bottom: 8 })
          .onClick(() => { this.currentTab = idx; this.onTabChange(idx); })
        })
      }.width('100%').backgroundColor('#0F0F1E').border({ width: { top: 1 }, color: '#1A1A2E' })
    }.width('100%').height('100%').backgroundColor('#0A0A1A')
  }
}