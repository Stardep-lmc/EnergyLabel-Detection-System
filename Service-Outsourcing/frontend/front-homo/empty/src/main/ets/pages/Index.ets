import http from '@ohos.net.http';

// 检测结果数据结构
interface DetectionResult {
  status: string;
  ocrText: string;
  presetModel: string;
  isMatch: boolean;
  defectType: string;
  positionStatus: string;
  timestamp: string;
  imageUrl: string;
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
  @State currentResult: DetectionResult = {
    status: '',
    ocrText: '',
    presetModel: '',
    isMatch: false,
    defectType: '无',
    positionStatus: '正常',
    timestamp: '',
    imageUrl: ''
  };
  @State recentList: RecentRecord[] = [];
  @State isLoading: boolean = false;
  @State mlAvailable: boolean = false;
  @State errorMsg: string = '';

  // 后端API地址（实际部署时修改）
  private baseUrl: string = 'http://192.168.1.100:8000';

  aboutToAppear() {
    this.checkMLStatus();
    this.fetchCurrentResult();
    this.fetchRecentRecords();
  }

  // 检查ML服务状态
  checkMLStatus() {
    let httpRequest = http.createHttp();
    httpRequest.request(
      this.baseUrl + '/api/ml/status',
      { method: http.RequestMethod.GET },
      (err, data) => {
        if (!err && data.responseCode === 200) {
          let result = JSON.parse(data.result as string);
          this.mlAvailable = result.available === true;
        }
        httpRequest.destroy();
      }
    );
  }

  // 获取当前检测结果
  fetchCurrentResult() {
    let httpRequest = http.createHttp();
    httpRequest.request(
      this.baseUrl + '/api/current',
      { method: http.RequestMethod.GET },
      (err, data) => {
        if (!err && data.responseCode === 200) {
          let result = JSON.parse(data.result as string);
          this.currentResult = {
            status: result.status || '',
            ocrText: result.ocrText || '',
            presetModel: result.presetModel || '',
            isMatch: result.isMatch || false,
            defectType: result.defectType || '无',
            positionStatus: result.positionStatus || '正常',
            timestamp: result.timestamp || '',
            imageUrl: result.imageUrl || ''
          };
        }
        httpRequest.destroy();
      }
    );
  }

  // 获取最近记录
  fetchRecentRecords() {
    let httpRequest = http.createHttp();
    httpRequest.request(
      this.baseUrl + '/api/recent?limit=10',
      { method: http.RequestMethod.GET },
      (err, data) => {
        if (!err && data.responseCode === 200) {
          let records: RecentRecord[] = JSON.parse(data.result as string);
          this.recentList = records.map((item: RecentRecord) => ({
            timestamp: item.timestamp || '',
            presetModel: item.presetModel || '',
            status: item.status || '',
            defectType: item.defectType || '无',
            positionStatus: item.positionStatus || '正常'
          }));
        }
        httpRequest.destroy();
      }
    );
  }

  // 刷新数据
  refreshData() {
    this.isLoading = true;
    this.fetchCurrentResult();
    this.fetchRecentRecords();
    this.checkMLStatus();
    setTimeout(() => { this.isLoading = false; }, 1000);
  }

  build() {
    Column() {
      // 顶部标题栏
      Row() {
        Column() {
          Text('能效标签检测')
            .fontSize(22)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FFFFFF')
          Text('OpenHarmony 设备端')
            .fontSize(12)
            .fontColor('#AAAAAA')
            .margin({ top: 2 })
        }
        .alignItems(HorizontalAlign.Start)

        Blank()

        // ML状态指示
        Row() {
          Circle({ width: 8, height: 8 })
            .fill(this.mlAvailable ? '#10B981' : '#EF4444')
          Text(this.mlAvailable ? 'ML就绪' : 'ML离线')
            .fontSize(11)
            .fontColor(this.mlAvailable ? '#10B981' : '#EF4444')
            .margin({ left: 6 })
        }
        .padding({ left: 10, right: 10, top: 4, bottom: 4 })
        .borderRadius(16)
        .backgroundColor(this.mlAvailable ? '#10B98115' : '#EF444415')

        // 刷新按钮
        Button('刷新')
          .fontSize(12)
          .height(32)
          .margin({ left: 8 })
          .onClick(() => this.refreshData())
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 12, bottom: 12 })
      .backgroundColor('#1A1A2E')

      // 主内容区域
      Scroll() {
        Column() {
          // 检测状态卡片
          if (this.currentResult.status !== '') {
            Column() {
              Row() {
                Text(this.currentResult.status === 'OK' ? '✓ 检测合格' : '✗ 检测不合格')
                  .fontSize(18)
                  .fontWeight(FontWeight.Bold)
                  .fontColor(this.currentResult.status === 'OK' ? '#10B981' : '#EF4444')
                Blank()
                Text(this.currentResult.timestamp)
                  .fontSize(11)
                  .fontColor('#888888')
              }
              .width('100%')
              .margin({ bottom: 12 })

              // 标签识别
              Column() {
                Text('📋 标签识别')
                  .fontSize(14)
                  .fontWeight(FontWeight.Medium)
                  .fontColor('#FFFFFF')
                  .margin({ bottom: 8 })

                Row() {
                  Text('识别标签：')
                    .fontSize(13)
                    .fontColor('#AAAAAA')
                  Text(this.currentResult.ocrText || '--')
                    .fontSize(15)
                    .fontWeight(FontWeight.Bold)
                    .fontColor('#818CF8')
                }
                .width('100%')
                .margin({ bottom: 4 })

                Row() {
                  Text('预设型号：')
                    .fontSize(13)
                    .fontColor('#AAAAAA')
                  Text(this.currentResult.presetModel || '--')
                    .fontSize(13)
                    .fontColor('#FFFFFF')
                }
                .width('100%')
                .margin({ bottom: 4 })

                Row() {
                  Text('比对结果：')
                    .fontSize(13)
                    .fontColor('#AAAAAA')
                  Text(this.currentResult.isMatch ? '✓ 匹配' : '✗ 不匹配')
                    .fontSize(13)
                    .fontColor(this.currentResult.isMatch ? '#10B981' : '#EF4444')
                }
                .width('100%')
              }
              .width('100%')
              .padding(12)
              .borderRadius(8)
              .backgroundColor('#16213E')
              .margin({ bottom: 10 })

              // 缺陷检测
              Column() {
                Text('⚠️ 缺陷检测')
                  .fontSize(14)
                  .fontWeight(FontWeight.Medium)
                  .fontColor('#FFFFFF')
                  .margin({ bottom: 8 })

                Row() {
                  ForEach(['破损', '污渍', '褶皱', '划痕', '偏移'], (item: string) => {
                    Column() {
                      Text(item)
                        .fontSize(11)
                        .fontColor('#AAAAAA')
                      Text(this.currentResult.defectType.includes(item) ? '检出' : '正常')
                        .fontSize(10)
                        .fontColor(this.currentResult.defectType.includes(item) ? '#EF4444' : '#10B981')
                        .margin({ top: 2 })
                    }
                    .width('18%')
                    .padding(6)
                    .borderRadius(6)
                    .backgroundColor(this.currentResult.defectType.includes(item) ? '#EF444410' : '#10B98110')
                    .alignItems(HorizontalAlign.Center)
                  })
                }
                .width('100%')
                .justifyContent(FlexAlign.SpaceBetween)
              }
              .width('100%')
              .padding(12)
              .borderRadius(8)
              .backgroundColor('#16213E')
              .margin({ bottom: 10 })

              // 位置检测
              Column() {
                Text('📍 位置检测')
                  .fontSize(14)
                  .fontWeight(FontWeight.Medium)
                  .fontColor('#FFFFFF')
                  .margin({ bottom: 8 })

                Row() {
                  Text('粘贴位置：')
                    .fontSize(13)
                    .fontColor('#AAAAAA')
                  Text(this.currentResult.positionStatus)
                    .fontSize(13)
                    .fontWeight(FontWeight.Bold)
                    .fontColor(this.currentResult.positionStatus === '正常' ? '#10B981' : '#EF4444')
                }
                .width('100%')
              }
              .width('100%')
              .padding(12)
              .borderRadius(8)
              .backgroundColor('#16213E')
            }
            .width('100%')
            .padding(16)
            .borderRadius(12)
            .backgroundColor('#0F3460')
            .margin({ bottom: 12 })
          } else {
            // 空状态
            Column() {
              Text('📷')
                .fontSize(40)
              Text('暂无检测结果')
                .fontSize(14)
                .fontColor('#888888')
                .margin({ top: 8 })
              Text('请通过Web端或移动端上传图片进行检测')
                .fontSize(11)
                .fontColor('#666666')
                .margin({ top: 4 })
            }
            .width('100%')
            .padding(40)
            .borderRadius(12)
            .backgroundColor('#0F3460')
            .alignItems(HorizontalAlign.Center)
            .margin({ bottom: 12 })
          }

          // 最近记录
          Column() {
            Row() {
              Text('📝 最近检测记录')
                .fontSize(14)
                .fontWeight(FontWeight.Medium)
                .fontColor('#FFFFFF')
              Blank()
              Text(this.recentList.length + ' 条')
                .fontSize(11)
                .fontColor('#888888')
            }
            .width('100%')
            .margin({ bottom: 10 })

            // 表头
            Row() {
              Text('时间').fontSize(10).fontColor('#666666').width('25%')
              Text('型号').fontSize(10).fontColor('#666666').width('20%')
              Text('结果').fontSize(10).fontColor('#666666').width('15%').textAlign(TextAlign.Center)
              Text('缺陷').fontSize(10).fontColor('#666666').width('20%').textAlign(TextAlign.Center)
              Text('位置').fontSize(10).fontColor('#666666').width('20%').textAlign(TextAlign.Center)
            }
            .width('100%')
            .padding({ bottom: 6 })

            // 记录列表
            if (this.recentList.length > 0) {
              ForEach(this.recentList, (item: RecentRecord, index: number) => {
                Row() {
                  Text(item.timestamp.slice(-8))
                    .fontSize(11)
                    .fontColor('#AAAAAA')
                    .width('25%')
                  Text(item.presetModel)
                    .fontSize(11)
                    .fontColor('#FFFFFF')
                    .width('20%')
                  Text(item.status)
                    .fontSize(11)
                    .fontColor(item.status === 'OK' ? '#10B981' : '#EF4444')
                    .fontWeight(FontWeight.Bold)
                    .width('15%')
                    .textAlign(TextAlign.Center)
                  Text(item.defectType || '无')
                    .fontSize(11)
                    .fontColor('#AAAAAA')
                    .width('20%')
                    .textAlign(TextAlign.Center)
                  Text(item.positionStatus)
                    .fontSize(11)
                    .fontColor(item.positionStatus === '正常' ? '#10B981' : '#EF4444')
                    .width('20%')
                    .textAlign(TextAlign.Center)
                }
                .width('100%')
                .padding({ top: 8, bottom: 8 })
                .borderWidth({ bottom: 1 })
                .borderColor('#1A1A2E')
              })
            } else {
              Text('暂无记录')
                .fontSize(12)
                .fontColor('#666666')
                .width('100%')
                .textAlign(TextAlign.Center)
                .padding(20)
            }
          }
          .width('100%')
          .padding(16)
          .borderRadius(12)
          .backgroundColor('#0F3460')
        }
        .width('100%')
        .padding(12)
      }
      .width('100%')
      .layoutWeight(1)
      .backgroundColor('#0A0A1A')
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#0A0A1A')
  }
}