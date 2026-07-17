import { createI18n } from 'vue-i18n'
import dataFactoryZhCn from '../locales/lang/zh-cn/data-factory.js'

const messages = {
  'zh-CN': {
    dataFactory: dataFactoryZhCn
  }
}

const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages,
  silentTranslationWarn: true,
  missingWarn: false,
  fallbackWarn: false,
})

export default i18n
