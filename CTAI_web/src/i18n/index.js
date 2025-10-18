import Vue from 'vue'
import VueI18n from 'vue-i18n'
import ElementLocale from 'element-ui/lib/locale'
import zhCN from 'element-ui/lib/locale/lang/zh-CN'
import enUS from 'element-ui/lib/locale/lang/en'

Vue.use(VueI18n)

const STORAGE_KEY = 'lang'

function detectLocale() {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) return saved
    const nav = (navigator.language || 'zh').toLowerCase()
    return nav.startsWith('zh') ? 'zh' : 'en'
}

export const messages = {
    zh: {
        app: { title: '肌少症诊断系统' },
        system: { name: 'iDoctor 医学影像处理系统' },
        nav: {
            upload: '上传与处理',
            results: '结果列表',
            detail: '结果详情'
        },
        login: {
            subtitle: '智能医学影像分析平台',
            loginTab: '登录',
            registerTab: '注册',
            usernamePlaceholder: '请输入用户名或邮箱',
            passwordPlaceholder: '请输入密码',
            usernameRegister: '请输入用户名（3-20字符）',
            emailPlaceholder: '请输入邮箱地址',
            passwordRegister: '请输入密码（至少6位）',
            confirmPassword: '请再次输入密码',
            loginButton: '登 录',
            registerButton: '注 册',
            loggingIn: '登录中...',
            registering: '注册中...',
            loginSuccess: '登录成功',
            loginFailed: '登录失败，请检查用户名和密码',
            registerSuccess: '注册成功，请登录',
            registerFailed: '注册失败，请稍后重试',
            usernameRequired: '请输入用户名',
            passwordRequired: '请输入密码',
            emailRequired: '请输入邮箱',
            emailInvalid: '请输入有效的邮箱地址',
            usernameLength: '用户名长度应为3-20个字符',
            passwordLength: '密码至少需要6个字符',
            confirmPasswordRequired: '请再次输入密码',
            passwordMismatch: '两次输入的密码不一致',
            terms: '登录即表示同意用户协议和隐私政策',
            noAccount: '还没有账号？',
            registerNow: '立即注册'
        },
        user: {
            welcome: '欢迎，{username}',
            quotaDetail: '配额详情',
            subscription: '订阅管理',
            logout: '退出登录',
            quotaBadge: '{used}/{limit}'
        },
        quota: {
            insufficient: '配额不足',
            insufficientMessage: '您的处理配额已用尽，无法继续上传。请升级套餐以获取更多配额。',
            upgradeNow: '立即升级',
            cancel: '取消',
            checkingQuota: '检查配额中...',
            checkFailed: '配额检查失败',
            available: '可用配额：{available}',
            used: '已使用：{used}',
            limit: '总配额：{limit}'
        },
        upload: {
            uploadZipTitle: '上传 CT 扫描压缩包（ZIP）',
            selectedPrefix: '已选：'
        },
        actions: {
            upload: '上传',
            process: '开始处理',
            viewResult: '查看结果',
            viewAll: '查看所有结果',
            back: '返回',
            retry: '重新生成',
            detectL3: '检测 L3',
            manualL3: '手动标注 L3 mask',
            continue: '继续后续流程',
            saveUpload: '保存上传',
            cancel: '取消',
            refresh: '刷新',
            chooseFile: '选择文件',
            prevStep: '返回上一步',
            action: '操作',
            undo: '撤销',
            clear: '清空',
            undoPoint: '撤销点',
            manualMiddleMask: "手动标注 腰大肌、全肌肉",

        },
        form: {
            patientName: '病人姓名',
            studyDate: '检查日期',
            zipFile: 'ZIP 文件',
            patientNamePlaceholder: '例如：张三',
            studyDatePlaceholder: '例如：20250915'
        },
        labels: {
            processData: '处理数据'
        },
        steps: {
            step1: '步骤 1 上传 DICOM ZIP',
            step2: '步骤 2 处理数据',
            step3: '步骤 3 查看结果'
        },
        result: {
            keyMetrics: '关键指标（HU 与面积）',
            keyImages: '关键图片（middle）',
            l3Ops: 'L3 操作',
            l3Preview: 'L3 结果预览',
            emptyMetrics: '未解析到关键指标',
            processedList: '已处理结果',
            noMatch: '暂无匹配结果',
            searchPlaceholder: '搜索病人或日期'
        },
        fields: {
            slice: '切片',
            psoasHu: 'Psoas HU(mean)',
            psoasArea: 'Psoas 面积(mm²)',
            comboHu: 'Combo HU(mean)',
            comboArea: 'Combo 面积(mm²)',
            patient: '病人',
            date: '日期'
        },
        editor: {
            l3MaskTitle: 'L3 Mask 标注',
            noSagittal: '未获取到侧视图',
            tips: '拖动鼠标绘制多个矩形，可撤销/清空，保存会生成白色区域、黑色背景的二值 mask。'
        },
        messages: {
            uploadSuccess: '上传成功',
            uploadFail: '上传失败',
            processSuccess: '处理完成',
            processFail: '处理失败',
            fetchFail: '获取结果失败',
            l3DetectSuccess: 'L3 检测完成',
            l3DetectFail: 'L3 检测失败',
            l3ContinueSuccess: '后续流程已完成',
            l3ContinueFail: '后续流程失败',
            pngOnly: '请上传 PNG 格式的 mask',
            sagittalFail: '生成侧视图失败',
            maskUploadSuccess: 'L3 mask 上传成功',
            maskUploadFail: '上传失败',
            waitUpload: '等待上传完成',
            clickProcessHint: '点击“开始处理”调用后端推理',
            waitProcess: '等待处理完成',
            enterResultHint: '可进入结果详情或结果列表',
            processApiTip: '调用后端 /process 接口处理刚上传的数据',
            noContent: '无内容',
            needOneRect: '请先绘制至少一个矩形'
        },
        footer: {
            copyright: 'Copyright {year} © 肌少症诊断系统 版权所有'
        },
        middleEditor: {
            title: 'Middle Mask 标注',
            editing: '当前图像',
            psoas: 'Psoas 区域',
            combo: 'Combo 区域',
            modePsoas: 'Psoas 模式',
            modeCombo: 'Combo 模式',
            switchTo: '切换到 {mode}',
            tips: '拖动绘制矩形（多次）。可在 Psoas / Combo 两模式间切换；保存将上传两张黑底白区 PNG。',
            emptyWarn: '至少在一个模式下绘制一个矩形',
            polyHint: '单击添加顶点；最后一个点靠近第一个点自动闭合；Backspace 删除上一个点；Esc 取消当前多边形；撤销删除最近一个多边形。'
        },
    },
    en: {
        app: { title: 'Sarcopenia Diagnosis System' },
        system: { name: 'iDoctor Medical Imaging System' },
        nav: {
            upload: 'Upload & Process',
            results: 'Results List',
            detail: 'Result Detail'
        },
        login: {
            subtitle: 'Intelligent Medical Imaging Analysis Platform',
            loginTab: 'Login',
            registerTab: 'Register',
            usernamePlaceholder: 'Username or Email',
            passwordPlaceholder: 'Password',
            usernameRegister: 'Username (3-20 characters)',
            emailPlaceholder: 'Email Address',
            passwordRegister: 'Password (at least 6 characters)',
            confirmPassword: 'Confirm Password',
            loginButton: 'Login',
            registerButton: 'Register',
            loggingIn: 'Logging in...',
            registering: 'Registering...',
            loginSuccess: 'Login successful',
            loginFailed: 'Login failed, please check your credentials',
            registerSuccess: 'Registration successful, please login',
            registerFailed: 'Registration failed, please try again',
            usernameRequired: 'Please enter username',
            passwordRequired: 'Please enter password',
            emailRequired: 'Please enter email',
            emailInvalid: 'Please enter a valid email address',
            usernameLength: 'Username length should be 3-20 characters',
            passwordLength: 'Password must be at least 6 characters',
            confirmPasswordRequired: 'Please confirm password',
            passwordMismatch: 'Passwords do not match',
            terms: 'By logging in, you agree to the Terms of Service and Privacy Policy',
            noAccount: 'Don\'t have an account?',
            registerNow: 'Register Now'
        },
        user: {
            welcome: 'Welcome, {username}',
            quotaDetail: 'Quota Details',
            subscription: 'Subscription',
            logout: 'Logout',
            quotaBadge: '{used}/{limit}'
        },
        quota: {
            insufficient: 'Quota Insufficient',
            insufficientMessage: 'Your processing quota has been exhausted. Please upgrade your plan to get more quota.',
            upgradeNow: 'Upgrade Now',
            cancel: 'Cancel',
            checkingQuota: 'Checking quota...',
            checkFailed: 'Quota check failed',
            available: 'Available: {available}',
            used: 'Used: {used}',
            limit: 'Total: {limit}'
        },
        upload: {
            uploadZipTitle: 'Upload CT Scan Archive (ZIP)',
            selectedPrefix: 'Selected:'
        },
        actions: {
            upload: 'Upload',
            process: 'Start Processing',
            viewResult: 'View This Result',
            viewAll: 'All Results',
            back: 'Back',
            retry: 'Regenerate',
            detectL3: 'Detect L3',
            manualL3: 'Manual L3 Mask',
            continue: 'Continue Pipeline',
            saveUpload: 'Save & Upload',
            cancel: 'Cancel',
            refresh: 'Refresh',
            chooseFile: 'Choose File',
            prevStep: 'Previous Step',
            action: 'Action',
            undo: 'Undo',
            clear: 'Clear',
            undoPoint: 'Undo Point',
            manualMiddleMask: "Manual Middle Mask",

        },
        form: {
            patientName: 'Patient Name',
            studyDate: 'Study Date',
            zipFile: 'ZIP File',
            patientNamePlaceholder: 'e.g. John Doe',
            studyDatePlaceholder: 'e.g. 20250915'
        },
        labels: {
            processData: 'Process Data'
        },
        steps: {
            step1: 'Step 1 Upload DICOM ZIP',
            step2: 'Step 2 Process Data',
            step3: 'Step 3 View Results'
        },
        result: {
            keyMetrics: 'Key Metrics (HU & Area)',
            keyImages: 'Key Images (middle)',
            l3Ops: 'L3 Operations',
            l3Preview: 'L3 Preview',
            emptyMetrics: 'No key metrics parsed',
            processedList: 'Processed Results',
            noMatch: 'No matched records',
            searchPlaceholder: 'Search patient or date'
        },
        fields: {
            slice: 'Slice',
            psoasHu: 'Psoas HU(mean)',
            psoasArea: 'Psoas Area(mm²)',
            comboHu: 'Combo HU(mean)',
            comboArea: 'Combo Area(mm²)',
            patient: 'Patient',
            date: 'Date'
        },
        editor: {
            l3MaskTitle: 'L3 Mask Annotation',
            noSagittal: 'No sagittal view available',
            tips: 'Drag to draw multiple rectangles. Undo/Clear supported. Save to build a binary mask (white ROIs on black background).'
        },
        messages: {
            uploadSuccess: 'Upload succeeded',
            uploadFail: 'Upload failed',
            processSuccess: 'Processing finished',
            processFail: 'Processing failed',
            fetchFail: 'Fetch failed',
            l3DetectSuccess: 'L3 detection finished',
            l3DetectFail: 'L3 detection failed',
            l3ContinueSuccess: 'Pipeline finished',
            l3ContinueFail: 'Pipeline failed',
            pngOnly: 'Please upload a PNG mask',
            sagittalFail: 'Generate sagittal view failed',
            maskUploadSuccess: 'Mask uploaded',
            maskUploadFail: 'Upload failed',
            waitUpload: 'Waiting for upload',
            clickProcessHint: 'Click "Start Processing" to run backend inference',
            waitProcess: 'Waiting for processing',
            enterResultHint: 'Go to detail or results list',
            processApiTip: 'Calls backend /process API for the uploaded data',
            noContent: 'No content',
            needOneRect: 'Draw at least one rectangle first'
        },
        footer: {
            copyright: 'Copyright {year} © Sarcopenia Diagnosis System. All rights reserved.'
        },
        middleEditor: {
            title: 'Middle Mask Annotation',
            editing: 'Current Image',
            psoas: 'Psoas Region',
            combo: 'Combo Region',
            modePsoas: 'Psoas Mode',
            modeCombo: 'Combo Mode',
            switchTo: 'Switch to {mode}',
            tips: 'Drag to draw rectangles (multiple). Switch between Psoas / Combo modes; saving uploads two binary PNG masks.',
            emptyWarn: 'Draw at least one rectangle in either mode',
            polyHint: 'Click to add vertices; bring last point near the first to auto-close; Backspace removes last point; Esc cancels current polygon; Undo removes last finished polygon.'
        }
    }
}


const locale = detectLocale()

export const i18n = new VueI18n({
    locale,
    fallbackLocale: 'zh',
    messages,
    silentFallbackWarn: true
})

ElementLocale.use(locale === 'en' ? enUS : zhCN)

export function setLocale(lang) {
    if (i18n.locale === lang) return
    i18n.locale = lang
    localStorage.setItem(STORAGE_KEY, lang)
    ElementLocale.use(lang === 'en' ? enUS : zhCN)
    document.title = i18n.t('app.title')
}

export function getLocale() {
    return i18n.locale
}

