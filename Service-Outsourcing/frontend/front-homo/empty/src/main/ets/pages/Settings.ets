import router from '@ohos.router';
import { apiGet, apiPost } from '../common/Api';

interface PresetModel {
  name: string;
  model: string;
  standardLabel: string;
  enabled: boolean;
}

interface CameraConfig {
  exposure: number;
  resolution: string;
}

interface ConfigData {
  models: PresetModel[];
  positionTolerance: number;
  sensitivity: string;
  lightCompensation: number;
  camera: CameraConfig;
}

@Entry
@Component
struct Settings {
  @State presetModels: PresetModel[] = [{ name: '冰箱', model: 'BCD-520W', standardLabel: 'A++', enabled: true }];
  @State positionTolerance: number = 10;
  @State sensitivity: string = '中';
  @State lightCompensation: number = 0;
  @State exposure: number = 0;
  @State resolution: string = '1280x720';
  @State isSaving: boolean = false;

  private sensitivityLevels: string[] = ['低', '中', '高'];
  private resolutions: string[] = ['640x480', '1280x720', '1920x1080'];

  aboutToAppear() {
    this.fetchConfig();
  }

  async fetchConfig() {
    try {
      let d = await apiGet('/api/config') as ConfigData;
      if (d.models) this.presetModels = d.models;
      this.positionTolerance = d.positionTolerance ?? 10;
      this.sensitivity = d.sensitivity ?? '中';
      this.lightCompensation = d.lightCompensation ?? 0;
      this.exposure = d.camera?.exposure ?? 0;
      this.resolution = d.camera?.resolution ?? '1280x720';
    } catch (e) {}
  }

  async saveConfig() {
    this.isSaving = true;
    let cfg: ConfigData = {
      models: this.presetModels,
      positionTolerance: this.positionTolerance,
      sensitivity: this.sensitivity,
      lightCompensation: this.lightCompensation,
      camera: { exposure: this.exposure, resolution: this.resolution }
    };
    try {
      await apiPost('/api/config', cfg as object);
      try { await apiPost('/api/ml/reload', {} as object); } catch (e) {}
      AlertDialog.show({ message: '配置已保存' });
    } catch (e) {
      AlertDialog.show({ message: '保存失败' });
    }
    this.isSaving = false;
  }

  build() {
    Column() {
      // 顶部栏
      Row() {
        Button('← 返回').fontSize(12).height(28).backgroundColor('#FFFFFF10').fontColor('#AAAAAA')
          .onClick(() => router.back())
        Text('系统配置').fontSize(18).fontWeight(FontWeight.Bold).fontColor('#FFFFFF').margin({ left: 12 })
      }.width('100%').padding({ left: 16, right: 16, top: 12, bottom: 12 }).backgroundColor('#1A1A2E')

      Scroll() {
        Column() {
          // 预设型号
          Column() {
            Text('📋 预设产品型号').fontSize(14).fontWeight(FontWeight.Medium).fontColor('#FFFFFF').margin({ bottom: 12 })
            ForEach(this.presetModels, (item: PresetModel, idx: number) => {
              Row() {
                Column() {
                  Text(item.name).fontSize(12).fontWeight(FontWeight.Medium).fontColor('#FFFFFF')
                  Text(item.model).fontSize(10).fontColor('#888888').margin({ top: 2 })
                }.layoutWeight(1)
                Text(item.standardLabel).fontSize(11).fontColor('#818CF8')
                  .padding({ left: 10, right: 10, top: 4, bottom: 4 }).borderRadius(12).backgroundColor('#6366F115')
                  .margin({ left: 8 })
                Toggle({ type: ToggleType.Switch, isOn: item.enabled })
                  .margin({ left: 8 })
                  .onChange((isOn: boolean) => { this.presetModels[idx].enabled = isOn; })
              }.width('100%').padding(10).borderRadius(8).backgroundColor('#FFFFFF06')
              .border({ width: 1, color: '#FFFFFF10' }).margin({ bottom: 6 })
            })
          }.width('100%').padding(14).borderRadius(12).backgroundColor('#0F3460').margin({ bottom: 12 })

          // 检测参数
          Column() {
            Text('⚙️ 检测参数').fontSize(14).fontWeight(FontWeight.Medium).fontColor('#FFFFFF').margin({ bottom: 12 })

            // 位置容忍度
            Column() {
              Row() {
                Text('📍 位置偏移容忍度').fontSize(12).fontColor('#FFFFFF')
                Blank()
                Text(this.positionTolerance + '%').fontSize(14).fontWeight(FontWeight.Bold).fontColor('#818CF8')
              }.width('100%')
              Text('标签偏离中心多少%算异常').fontSize(10).fontColor('#888888').margin({ top: 2 })
              Slider({ value: this.positionTolerance, min: 0, max: 20, step: 1 })
                .trackColor('#FFFFFF10').selectedColor('#6366F1').margin({ top: 8 })
                .onChange((value: number) => { this.positionTolerance = value; })
            }.width('100%').padding(12).borderRadius(8).backgroundColor('#FFFFFF06').margin({ bottom: 8 })

            // 灵敏度
            Column() {
              Text('🔍 缺陷检测灵敏度').fontSize(12).fontColor('#FFFFFF')
              Text('越高越容易检出微小缺陷').fontSize(10).fontColor('#888888').margin({ top: 2 })
              Row() {
                ForEach(this.sensitivityLevels, (s: string) => {
                  Text(s).fontSize(12).fontColor(this.sensitivity === s ? '#FFFFFF' : '#888888')
                    .padding({ left: 20, right: 20, top: 6, bottom: 6 }).borderRadius(20)
                    .backgroundColor(this.sensitivity === s ? '#6366F1' : '#FFFFFF08')
                    .onClick(() => { this.sensitivity = s; })
                })
              }.margin({ top: 8 }).justifyContent(FlexAlign.Start)
            }.width('100%').padding(12).borderRadius(8).backgroundColor('#FFFFFF06').margin({ bottom: 8 })

            // 光照补偿
            Column() {
              Row() {
                Text('💡 光照补偿').fontSize(12).fontColor('#FFFFFF')
                Blank()
                Text((this.lightCompensation > 0 ? '+' : '') + this.lightCompensation)
                  .fontSize(14).fontWeight(FontWeight.Bold).fontColor('#818CF8')
              }.width('100%')
              Slider({ value: this.lightCompensation, min: -5, max: 5, step: 1 })
                .trackColor('#FFFFFF10').selectedColor('#6366F1').margin({ top: 8 })
                .onChange((value: number) => { this.lightCompensation = value; })
            }.width('100%').padding(12).borderRadius(8).backgroundColor('#FFFFFF06')
          }.width('100%').padding(14).borderRadius(12).backgroundColor('#0F3460').margin({ bottom: 12 })

          // 相机参数
          Column() {
            Text('📷 相机参数').fontSize(14).fontWeight(FontWeight.Medium).fontColor('#FFFFFF').margin({ bottom: 12 })

            Column() {
              Row() {
                Text('🔆 曝光').fontSize(12).fontColor('#FFFFFF')
                Blank()
                Text((this.exposure > 0 ? '+' : '') + this.exposure)
                  .fontSize(14).fontWeight(FontWeight.Bold).fontColor('#818CF8')
              }.width('100%')
              Slider({ value: this.exposure, min: -3, max: 3, step: 1 })
                .trackColor('#FFFFFF10').selectedColor('#6366F1').margin({ top: 8 })
                .onChange((value: number) => { this.exposure = value; })
            }.width('100%').padding(12).borderRadius(8).backgroundColor('#FFFFFF06').margin({ bottom: 8 })

            Column() {
              Text('📱 分辨率').fontSize(12).fontColor('#FFFFFF').margin({ bottom: 8 })
              Row() {
                ForEach(this.resolutions, (r: string) => {
                  Text(r).fontSize(11).fontColor(this.resolution === r ? '#FFFFFF' : '#888888')
                    .padding({ left: 14, right: 14, top: 6, bottom: 6 }).borderRadius(20)
                    .backgroundColor(this.resolution === r ? '#6366F1' : '#FFFFFF08')
                    .onClick(() => { this.resolution = r; })
                })
              }.justifyContent(FlexAlign.Start)
            }.width('100%').padding(12).borderRadius(8).backgroundColor('#FFFFFF06')
          }.width('100%').padding(14).borderRadius(12).backgroundColor('#0F3460').margin({ bottom: 12 })

          // 保存按钮
          Row() {
            Button('💾 保存配置').fontSize(14).height(40).layoutWeight(2)
              .backgroundColor('#6366F1').fontColor('#FFFFFF').borderRadius(12)
              .onClick(() => this.saveConfig())
            Button('↺ 恢复默认').fontSize(14).height(40).layoutWeight(1)
              .backgroundColor('#FFFFFF08').fontColor('#AAAAAA').borderRadius(12).margin({ left: 10 })
              .onClick(() => this.fetchConfig())
          }.width('100%').margin({ top: 4 })
        }.width('100%').padding(12)
      }.width('100%').layoutWeight(1).backgroundColor('#0A0A1A')
    }.width('100%').height('100%').backgroundColor('#0A0A1A')
  }
}