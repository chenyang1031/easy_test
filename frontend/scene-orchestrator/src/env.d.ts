/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module 'vue-draggable-next' {
  import { DefineComponent } from 'vue'
  export const VueDraggableNext: DefineComponent<any, any, any>
}
