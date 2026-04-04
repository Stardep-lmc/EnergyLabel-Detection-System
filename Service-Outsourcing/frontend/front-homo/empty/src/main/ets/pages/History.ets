import router from '@ohos.router';
import { apiGet } from '../common/Api';

interface HistoryRecord {
  timestamp: string;
  presetModel: string;
  ocrText: string;
  status: string;
  defectType: string;
  positionStatus: string;
  imageUrl: string;
}

interface HistoryResponse {
  total: number;
  records: HistoryRecord[];
}

@Entry
@Component
struct History {
  @State records: HistoryRecord[] = [];
  @State total: number = 0;
  @State page: number = 1;
  @State isLoading: boolean = false;
  @State statusFilter: string = 'ALL';

  private pageSize: number = 20;
  private statusOptions: string[] = ['ALL', 'OK', 'NG'];
  private statusLabels: string[] = ['全部', '合格', '不合格'];
  @State statusIdx: number = 0;

  aboutToAppear() {
    this.fetchHistory();
  }

  async fetchHistory() {
    if (this.isLoading) return;
    this.isLoading = true;
    try {
      let resp = await apiGet(`/api/history?page=${this.page}&pageSize=${this.pageSize}&statusFilter=${this.statusFilter}`) as HistoryResponse;
      this.total = resp.total;
      if (this.page === 1) {
        this.records = resp.records || [];
      } else {
        this.records = this.records.concat(resp.records || []);
      }
    } catch (e) {}
    this.isLoading = false;
  }

  build() {
    Column() {
      // 顶部栏
      Row() {
        Button('← 返回').fontSize(12).height(28).backgroundColor('#FFFFFF10').fontColor('#AAAAAA')
          .onClick(() => router.back())
        Text('历史记录').fontSize(18).fontWeight(FontWeight.Bold).fontColor('#FFFFFF').margin({ left: 12 })
        Blank()
        Text(`共 ${this.total} 条`).fontSize(11).fontColor('#888888')
      }.width('100%').padding({ left: 16, right: 16, top: 12, bottom: 12 }).backgroundColor('#1A1A2E')

      // 筛选栏
      Row() {
        ForEach(this.statusLabels, (label: string, idx: number) => {
          Text(label).fontSize(12).fontColor(this.statusIdx === idx ? '#818CF8' : '#888888')
            .padding({ left: 16, right: 16, top: 6, bottom: 6 }).borderRadius(20)
            .backgroundColor(this.statusIdx === idx ? '#6366F120' : '#FFFFFF06')
            .border({ width: 1, color: this.statusIdx === idx ? '#6366F140' : '#FFFFFF10' })
            .onClick(() => {
              this.statusIdx = idx;
              this.statusFilter = this.statusOptions[idx];
              this.page = 1;
              this.records = [];
              this.fetchHistory();
            })
        })
      }.width('100%').padding({ left: 16, right: 16, top: 8, bottom: 8 }).justifyContent(FlexAlign.Start)
      .backgroundColor('#0A0A1A')

      // 记录列表
      Scroll() {
        Column() {
          if (this.records.length > 0) {
            ForEach(this.records, (item: HistoryRecord) => {
              Column() {
                Row() {
                  Text(item.timestamp).fontSize(10).fontColor('#888888')
                  Blank()
                  Text(item.status === 'OK' ? '合格' : '不合格').fontSize(11).fontWeight(FontWeight.Medium)
                    .fontColor(item.status === 'OK' ? '#10B981' : '#EF4444')
                    .padding({ left: 10, right: 10, top: 2, bottom: 2 }).borderRadius(10)
                    .backgroundColor(item.status === 'OK' ? '#10B98115' : '#EF444415')
                }.width('100%').margin({ bottom: 8 })

                Row() {
                  Text('型号：').fontSize(11).fontColor('#888888')
                  Text(item.presetModel || '--').fontSize(11).fontColor('#FFFFFF')
                }.width('100%').margin({ bottom: 4 })
                Row() {
                  Text('标签：').fontSize(11).fontColor('#888888')
                  Text(item.ocrText || '--').fontSize(11).fontColor('#FFFFFF')
                }.width('100%').margin({ bottom: 4 })
                Row() {
                  Text('缺陷：').fontSize(11).fontColor('#888888')
                  Text(item.defectType || '无').fontSize(11).fontColor('#FFFFFF')
                }.width('100%').margin({ bottom: 4 })
                Row() {
                  Text('位置：').fontSize(11).fontColor('#888888')
                  Text(item.positionStatus).fontSize(11).fontWeight(FontWeight.Medium)
                    .fontColor(item.positionStatus === '正常' ? '#10B981' : '#EF4444')
                }.width('100%')
              }.width('100%').padding(14).borderRadius(12).backgroundColor('#0F3460')
              .margin({ bottom: 10 })
            })

            if (this.records.length < this.total) {
              Button('加载更多').fontSize(12).height(32).width('100%').backgroundColor('#FFFFFF08')
                .fontColor('#818CF8').margin({ top: 4 })
                .onClick(() => { this.page++; this.fetchHistory(); })
            } else {
              Text('已加载全部').fontSize(11).fontColor('#666666').width('100%').textAlign(TextAlign.Center).padding(16)
            }
          } else if (!this.isLoading) {
            Column() {
              Text('📋').fontSize(40)
              Text('暂无记录').fontSize(14).fontColor('#888888').margin({ top: 8 })
            }.width('100%').padding(60).alignItems(HorizontalAlign.Center)
          }

          if (this.isLoading) {
            Text('加载中...').fontSize(12).fontColor('#888888').width('100%').textAlign(TextAlign.Center).padding(20)
          }
        }.width('100%').padding(12)
      }.width('100%').layoutWeight(1).backgroundColor('#0A0A1A')
    }.width('100%').height('100%').backgroundColor('#0A0A1A')
  }
}