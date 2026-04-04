import router from '@ohos.router';
import { apiGet } from '../common/Api';

interface StatRecord {
  timestamp: string;
  status: string;
  hasDefect: boolean;
  defectType: string;
  presetModel: string;
}

interface DefectItem {
  name: string;
  count: number;
  pct: number;
}

interface ModelRate {
  model: string;
  rate: number;
}

@Entry
@Component
struct Statistics {
  @State total: number = 0;
  @State passCount: number = 0;
  @State failCount: number = 0;
  @State passRate: number = 0;
  @State defectDist: DefectItem[] = [];
  @State modelRates: ModelRate[] = [];
  @State isLoading: boolean = false;

  aboutToAppear() {
    this.fetchStats();
  }

  async fetchStats() {
    this.isLoading = true;
    try {
      let data = await apiGet('/api/statistic') as StatRecord[];
      let arr = data || [];
      this.total = arr.length;
      this.passCount = arr.filter((d: StatRecord) => d.status === 'OK').length;
      this.failCount = this.total - this.passCount;
      this.passRate = this.total > 0 ? Math.round(this.passCount / this.total * 100) : 0;

      // 缺陷分布
      let dc: Record<string, number> = {};
      arr.forEach((item: StatRecord) => {
        let defect = item.defectType;
        if (!defect || defect === '无' || defect === 'none') return;
        defect.split(',').forEach((t: string) => {
          let n = t.trim();
          if (n && n !== '无') dc[n] = (dc[n] || 0) + 1;
        });
      });
      let maxCount = Math.max(...Object.values(dc), 1);
      this.defectDist = Object.keys(dc).map((name: string) => ({
        name: name,
        count: dc[name],
        pct: Math.round(dc[name] / maxCount * 100)
      })).sort((a: DefectItem, b: DefectItem) => b.count - a.count);

      // 型号合格率
      let ms: Record<string, { total: number; ok: number }> = {};
      arr.forEach((item: StatRecord) => {
        let m = item.presetModel || '未知';
        if (!ms[m]) ms[m] = { total: 0, ok: 0 };
        ms[m].total++;
        if (item.status === 'OK') ms[m].ok++;
      });
      this.modelRates = Object.keys(ms).map((model: string) => ({
        model: model,
        rate: ms[model].total > 0 ? Math.round(ms[model].ok / ms[model].total * 100) : 0
      }));
    } catch (e) {}
    this.isLoading = false;
  }

  build() {
    Column() {
      // 顶部栏
      Row() {
        Button('← 返回').fontSize(12).height(28).backgroundColor('#FFFFFF10').fontColor('#AAAAAA')
          .onClick(() => router.back())
        Text('数据统计').fontSize(18).fontWeight(FontWeight.Bold).fontColor('#FFFFFF').margin({ left: 12 })
      }.width('100%').padding({ left: 16, right: 16, top: 12, bottom: 12 }).backgroundColor('#1A1A2E')

      Scroll() {
        Column() {
          // 统计卡片
          Row() {
            Column() {
              Text(this.total.toString()).fontSize(28).fontWeight(FontWeight.Bold).fontColor('#FFFFFF')
              Text('总检测数').fontSize(10).fontColor('#888888').margin({ top: 2 })
            }.layoutWeight(1).alignItems(HorizontalAlign.Center).padding(14).borderRadius(10)
            .backgroundColor('#0F3460').margin({ right: 6 })

            Column() {
              Text(this.passCount.toString()).fontSize(28).fontWeight(FontWeight.Bold).fontColor('#10B981')
              Text('合格数').fontSize(10).fontColor('#888888').margin({ top: 2 })
            }.layoutWeight(1).alignItems(HorizontalAlign.Center).padding(14).borderRadius(10)
            .backgroundColor('#0F3460').margin({ right: 6 })

            Column() {
              Text(this.failCount.toString()).fontSize(28).fontWeight(FontWeight.Bold).fontColor('#EF4444')
              Text('不合格数').fontSize(10).fontColor('#888888').margin({ top: 2 })
            }.layoutWeight(1).alignItems(HorizontalAlign.Center).padding(14).borderRadius(10)
            .backgroundColor('#0F3460').margin({ right: 6 })

            Column() {
              Text(this.passRate + '%').fontSize(28).fontWeight(FontWeight.Bold).fontColor('#818CF8')
              Text('合格率').fontSize(10).fontColor('#888888').margin({ top: 2 })
            }.layoutWeight(1).alignItems(HorizontalAlign.Center).padding(14).borderRadius(10)
            .backgroundColor('#0F3460')
          }.width('100%').margin({ bottom: 12 })

          // 缺陷分布
          Column() {
            Text('🍕 缺陷类型分布').fontSize(14).fontWeight(FontWeight.Medium).fontColor('#FFFFFF').margin({ bottom: 12 })
            if (this.defectDist.length > 0) {
              ForEach(this.defectDist, (item: DefectItem) => {
                Row() {
                  Text(item.name).fontSize(11).fontColor('#AAAAAA').width(60)
                  Stack() {
                    Row().width('100%').height(12).borderRadius(6).backgroundColor('#FFFFFF08')
                    Row().width(item.pct + '%').height(12).borderRadius(6)
                      .linearGradient({ direction: GradientDirection.Right, colors: [['#6366F1', 0], ['#A855F7', 1]] })
                  }.layoutWeight(1).height(12)
                  Text(item.count.toString()).fontSize(11).fontWeight(FontWeight.Bold).fontColor('#818CF8')
                    .width(40).textAlign(TextAlign.End)
                }.width('100%').margin({ bottom: 8 })
              })
            } else {
              Text('暂无数据').fontSize(12).fontColor('#666666').width('100%').textAlign(TextAlign.Center).padding(20)
            }
          }.width('100%').padding(14).borderRadius(12).backgroundColor('#0F3460').margin({ bottom: 12 })

          // 型号合格率
          Column() {
            Text('📊 各型号合格率').fontSize(14).fontWeight(FontWeight.Medium).fontColor('#FFFFFF').margin({ bottom: 12 })
            if (this.modelRates.length > 0) {
              ForEach(this.modelRates, (item: ModelRate) => {
                Row() {
                  Text(item.model).fontSize(11).fontColor('#AAAAAA').width(70)
                  Stack() {
                    Row().width('100%').height(14).borderRadius(7).backgroundColor('#FFFFFF08')
                    Row().width(item.rate + '%').height(14).borderRadius(7)
                      .linearGradient({ direction: GradientDirection.Right, colors: [['#6366F1', 0], ['#A855F7', 1]] })
                  }.layoutWeight(1).height(14)
                  Text(item.rate + '%').fontSize(12).fontWeight(FontWeight.Bold)
                    .fontColor(item.rate >= 90 ? '#10B981' : item.rate >= 70 ? '#F59E0B' : '#EF4444')
                    .width(50).textAlign(TextAlign.End)
                }.width('100%').margin({ bottom: 10 })
              })
            } else {
              Text('暂无数据').fontSize(12).fontColor('#666666').width('100%').textAlign(TextAlign.Center).padding(20)
            }
          }.width('100%').padding(14).borderRadius(12).backgroundColor('#0F3460')
        }.width('100%').padding(12)
      }.width('100%').layoutWeight(1).backgroundColor('#0A0A1A')
    }.width('100%').height('100%').backgroundColor('#0A0A1A')
  }
}