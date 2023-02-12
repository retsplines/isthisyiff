/// <reference types="vite/client" />

interface ImportMetaEnv {
    VITE_ITY_BACKEND_URI: string,
    VITE_ITY_ASSET_ROOT_URI: string
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}
