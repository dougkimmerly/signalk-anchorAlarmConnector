const tokenManager = require('./tokenManager')
const axios = require('axios')

// Test simulation module (enable testMode in settings to use)
const testSimulation = require('./testSimulation')

// Plugin state
let serverBaseUrl = null
let clientId = null
let description = null
let testMode = false
let token = null
let rodeDeployed = 0
let anchorDropped = false
let depth = 0
let rodeLength = 0
let bowHeight = 0
let unsubscribes = []
let lastPosition = 0
let lastDepth = 0
let lastCounterConnection = 0
let activeUpdates = 1000
let lastDropCommandTime = 0

// Auto-clear alarm variables
let alarmClearInterval = null
let safeZoneCounter = 0
let alarmAutoClearEnabled = false
let alarmAutoClearTime = 30 // seconds

module.exports = (app) => {
    const plugin = {
        id: 'signalk-anchorAlarmConnector',
        name: 'anchorAlarmConnector',
        start: async (settings, restartPlugin) => {
            // Load configuration from settings
            serverBaseUrl = settings.serverBaseUrl || 'http://localhost:3000'
            clientId = settings.clientId || 'signalk-anchor-alarm-connector'
            description = settings.description || 'SignalK Anchor Alarm Connector Plugin'
            testMode = settings.testMode || false
            alarmAutoClearEnabled = settings.alarmAutoClearEnabled !== undefined ? settings.alarmAutoClearEnabled : true
            alarmAutoClearTime = settings.alarmAutoClearTime || 30

            app.debug('Configuration loaded:', { serverBaseUrl, clientId, description, testMode })

            token = await tokenManager.getToken(
                serverBaseUrl,
                clientId,
                description
            )
            if (!token) {
                console.error('Failed to obtain token.')
                return
            }
            console.log('Token obtained:', token)

            // Start test simulation if enabled
            if (testMode) {
                console.log('Test mode enabled - starting physics simulation')
                testSimulation.runTestSequence(app, sendChange)
            } else {
                console.log('Test mode disabled - running in production mode')
            }

            // Delay 3 seconds so the needed paths can be established at startup
            setTimeout(() => {
                rodeDeployed = app.getSelfPath(
                    'navigation.anchor.rodeDeployed'
                )?.value
                anchorDropped =
                    app.getSelfPath('navigation.anchor.position')?.value != null
                depth = app.getSelfPath('environment.depth.belowSurface')?.value
                rodeLength = app.getSelfPath(
                    'navigation.anchor.rodeLength'
                )?.value
                bowHeight =
                    app.getSelfPath('design.bowAnchorHeight')?.value || 2

            }, 3000)
            sendChange('navigation.anchor.autoReady', false)
            sendChange('navigation.anchor.scope', 0)
            sendChange('navigation.anchor.setAnchor', false)

            app.subscriptionmanager.subscribe(
                {
                    context: 'vessels.self',
                    subscribe: [
                        {
                            path: 'navigation.anchor.rodeDeployed',
                            period: 1000,
                        },
                        {
                            path: 'navigation.anchor.position',
                            period: activeUpdates,
                        },
                        {
                            path: 'navigation.anchor.rodeLength',
                            period: activeUpdates,
                        },
                        {
                            path: 'environment.depth.belowSurface',
                            period: activeUpdates,
                        },
                        { path: 'navigation.position', period: 15000 },
                        { path: 'navigation.anchor.command', period: 15000 },
                        {
                            path: 'navigation.anchor.distanceFromBow',
                            period: activeUpdates,
                        },
                        {
                            path: 'notifications.navigation.anchor',
                            period: 1000,
                        },
                        {
                            path: 'navigation.anchor.maxRadius',
                            period: 1000,
                        },
                    ],
                },
                unsubscribes,
                (err) => {
                    app.error('Subscription error:', err)
                },
                (delta) => {
                    delta.updates.forEach((update) => {
                        update.values?.forEach((v) => {
                            const path = v.path
                            const value = v.value
                            const updateTime = new Date(
                                update.timestamp
                            ).getTime()
                            if (path === 'navigation.anchor.rodeDeployed') {
                                let previousRode = rodeDeployed
                                let newRode = value
                                app.debug(
                                    'newRode',
                                    value,
                                    ' previousRode',
                                    previousRode,
                                    ' depth',
                                    depth,
                                    ' anchorDropped',
                                    anchorDropped
                                )
                                if (
                                    newRode > previousRode &&
                                    newRode > depth + bowHeight &&
                                    !anchorDropped &&
                                    Date.now() - lastDropCommandTime > 5000
                                ) {
                                    sendAnchorCommand('dropAnchor')
                                    lastDropCommandTime = Date.now()
                                }
                                if (
                                    newRode < previousRode &&
                                    anchorDropped &&
                                    newRode < depth + bowHeight
                                ) {
                                    sendAnchorCommand('raiseAnchor')
                                    sendChange('navigation.anchor.scope', 0)
                                }
                                rodeDeployed = newRode

                                // Calculate and publish scope when we have valid anchor position
                                const anchorPos = app.getSelfPath('navigation.anchor.position')
                                if (anchorPos?.value?.altitude !== undefined && rodeDeployed > 0) {
                                    const anchorDepthVal = Math.abs(anchorPos.value.altitude)
                                    // Scope = rode length / (depth + bow height)
                                    // bowHeight accounts for height of bow roller above water
                                    const scope = rodeDeployed / (anchorDepthVal + bowHeight)
                                    if (isValidNumber(scope) && scope > 0) {
                                        sendChange('navigation.anchor.scope', scope)
                                    }
                                }
                            } else if (path === 'navigation.anchor.position') {
                                anchorDropped = value != null

                                // Calculate and publish scope when anchor position changes
                                if (value?.altitude !== undefined && rodeDeployed > 0) {
                                    const anchorDepthVal = Math.abs(value.altitude)
                                    const scope = rodeDeployed / (anchorDepthVal + bowHeight)
                                    if (isValidNumber(scope) && scope > 0) {
                                        sendChange('navigation.anchor.scope', scope)
                                    }
                                } else if (value === null) {
                                    // Anchor raised - clear scope
                                    sendChange('navigation.anchor.scope', 0)
                                }
                            } else if (
                                path === 'navigation.anchor.rodeLength'
                            ) {
                                rodeLength = value
                            } else if (
                                path === 'environment.depth.belowSurface'
                            ) {
                                depth = value
                                lastDepth = updateTime
                            } else if (path === 'navigation.position') {
                                lastPosition = updateTime
                            } else if (path === 'navigation.anchor.command') {
                                lastCounterConnection = updateTime
                            } else if (path === 'notifications.navigation.anchor') {
                                // Handle alarm notification changes
                                handleAlarmNotification(value)
                            } else if (path === 'navigation.anchor.maxRadius') {
                                // Update setAnchor based on maxRadius validity
                                // When maxRadius is a valid number, anchor alarm is set
                                // When maxRadius is null/undefined, anchor alarm is not set
                                const isAnchorSet = value !== null && value !== undefined && !isNaN(value) && value > 0
                                sendChange('navigation.anchor.setAnchor', isAnchorSet)
                                console.log(`[maxRadius] ${value} -> setAnchor: ${isAnchorSet}`)
                            }

                            if (
                                lastPosition > Date.now() - 30000 &&
                                lastDepth > Date.now() - 30000 &&
                                lastCounterConnection > Date.now() - 60000
                            ) {
                                sendChange('navigation.anchor.autoReady', true)
                            } else {
                                sendChange('navigation.anchor.autoReady', false)
                            }
                        })
                    })
                }
            )

            // Register HTTP router if available
            if (app.registerPluginWithRouter) {
                app.registerPluginWithRouter(plugin.id, plugin.registerWithRouter)
            }

            // Register setAnchor PUT handler (production feature)
            registerSetAnchorPutHandler()

            // Register test endpoints only in test mode
            if (testMode) {
                testSimulation.registerMotorPutHandlers(app, plugin.id)
            }
        },
        registerWithRouter: (router) => {
            // Register test endpoints only in test mode
            if (testMode) {
                testSimulation.registerTestRouterEndpoints(router)
            }
            // Note: setanchor functionality moved to PUT handler at navigation.anchor.setAnchor
            // This allows SKipper app and other SignalK clients to use standard PUT API
        },

        stop: () => {
            unsubscribes.forEach((f) => f())
            unsubscribes = []

            // Stop alarm auto-clear monitoring
            stopAlarmClearMonitoring()

            // Stop test simulation if it was running
            if (testMode) {
                console.log('Stopping test simulation')
                testSimulation.stopTestSimulation()
            }

            console.log('Plugin stopped')
        },
        schema: () => {
            return {
                type: 'object',
                required: ['serverBaseUrl', 'clientId'],
                properties: {
                    serverBaseUrl: {
                        type: 'string',
                        title: 'Server Base URL',
                        description: 'The base URL of the SignalK server (e.g., http://localhost:80)',
                        default: 'http://localhost:80',
                    },
                    clientId: {
                        type: 'string',
                        title: 'Client ID',
                        description: 'A unique identifier for this client (UUID or other identifier)',
                        default: 'signalk-anchor-alarm-connector',
                    },
                    description: {
                        type: 'string',
                        title: 'Client Description',
                        description: 'A description of this client for the access request',
                        default: 'SignalK Anchor Alarm Connector Plugin',
                    },
                    testMode: {
                        type: 'boolean',
                        title: 'Enable Test Simulation',
                        description: 'Enable physics-based anchor test simulation for development and testing (disable for production)',
                        default: false,
                    },
                    alarmAutoClearEnabled: {
                        type: 'boolean',
                        title: 'Auto-Clear Alarms',
                        description: 'Automatically clear anchor alarms when boat returns to safe zone for sustained period (prevents false alarms from transient bad data)',
                        default: true,
                    },
                    alarmAutoClearTime: {
                        type: 'number',
                        title: 'Auto-Clear Sustained Time (seconds)',
                        description: 'How long boat must remain in safe zone before alarm auto-clears (default: 30 seconds)',
                        default: 30,
                    },
                },
            }
        },
    }
    async function sendChange(path, value) {
        // Debug logging for position updates
        if (path === 'navigation.position' || path === 'navigation.headingTrue') {
            console.log(`sendChange(${path}):`, JSON.stringify(value))
        }

        app.handleMessage(
            'netmonitor',
            {
                context: 'vessels.self',
                updates: [
                    {
                        timestamp: new Date().toISOString(),
                        values: [
                            {
                                path: path,
                                value: value,
                            },
                        ],
                    },
                ],
            }
        )
    }
    async function sendAnchorCommand(command, params = {}) {
        if (!token) {
            console.error('No token available. Please authenticate first.')
            return
        }

        const url = `${serverBaseUrl}/plugins/anchoralarm/${command}`
        console.log(`Sending "${command}" to ${url}`)
        console.log('Params:', JSON.stringify(params))
        console.log('Token:', token ? 'present' : 'missing')

        try {
            const response = await axios.post(
                url,
                params,
                {
                    headers: {
                        Authorization: 'Bearer ' + token,
                        'Content-Type': 'application/json',
                    },
                }
            )
            console.log(
                `"${command}" command sent successfully:`,
                response.data
            )
        } catch (error) {
            console.error(
                `Error sending "${command}":`,
                error.response?.data || error.message || error
            )
            if (error.response) {
                console.error('Response status:', error.response.status)
                console.error('Response headers:', error.response.headers)
            }
        }
    }
    function isValidNumber(x) {
        return typeof x === 'number' && !isNaN(x) && isFinite(x)
    }

    // Auto-clear alarm functions
    function handleAlarmNotification(notification) {
        if (!alarmAutoClearEnabled) {
            return
        }

        const state = notification?.state
        app.debug(`Alarm notification state: ${state}`)

        if (state === 'warn' || state === 'emergency') {
            // Alarm active - start monitoring if not already running
            app.debug(`Alarm active (${state}), starting auto-clear monitoring`)
            startAlarmClearMonitoring()
        } else {
            // Alarm cleared (normal or null) - stop monitoring
            app.debug('Alarm cleared, stopping auto-clear monitoring')
            stopAlarmClearMonitoring()
        }
    }

    function startAlarmClearMonitoring() {
        // Don't start if already running
        if (alarmClearInterval) {
            return
        }

        safeZoneCounter = 0
        const checkIntervalMs = 5000 // Check every 5 seconds

        app.debug(`Starting alarm auto-clear monitoring (checking every ${checkIntervalMs}ms, threshold: ${alarmAutoClearTime}s)`)

        alarmClearInterval = setInterval(() => {
            checkAndClearAlarm()
        }, checkIntervalMs)
    }

    function stopAlarmClearMonitoring() {
        if (alarmClearInterval) {
            clearInterval(alarmClearInterval)
            alarmClearInterval = null
            safeZoneCounter = 0
            app.debug('Stopped alarm auto-clear monitoring')
        }
    }

    function checkAndClearAlarm() {
        // Get current alarm state and position data
        const notification = app.getSelfPath('notifications.navigation.anchor')?.value
        const distanceFromBow = app.getSelfPath('navigation.anchor.distanceFromBow')?.value
        const anchorMeta = app.getSelfPath('navigation.anchor.meta')?.value

        if (!notification || !distanceFromBow || !anchorMeta?.zones) {
            app.debug('Missing data for alarm check')
            return
        }

        // Find the normal zone upper boundary (where warning starts)
        const normalZone = anchorMeta.zones.find(z => z.state === 'normal')
        if (!normalZone) {
            app.debug('Normal zone not found in metadata')
            return
        }

        const isInSafeZone = distanceFromBow <= normalZone.upper

        if (isInSafeZone) {
            safeZoneCounter += 5 // Add 5 seconds (check interval)
            app.debug(`Boat in safe zone: ${distanceFromBow.toFixed(1)}m <= ${normalZone.upper.toFixed(1)}m (${safeZoneCounter}s/${alarmAutoClearTime}s)`)

            if (safeZoneCounter >= alarmAutoClearTime) {
                // Sustained time in safe zone reached - clear the alarm
                console.log(`Boat has been in safe zone for ${safeZoneCounter}s, auto-clearing alarm`)
                clearAlarmNotification()
                stopAlarmClearMonitoring()
            }
        } else {
            // Not in safe zone - reset counter
            if (safeZoneCounter > 0) {
                app.debug(`Boat left safe zone: ${distanceFromBow.toFixed(1)}m > ${normalZone.upper.toFixed(1)}m, resetting counter`)
                safeZoneCounter = 0
            }
        }
    }

    async function clearAlarmNotification() {
        try {
            console.log('Clearing anchor alarm notification to normal state')

            // Send a delta to set the alarm to normal state
            const delta = {
                context: 'vessels.self',
                updates: [
                    {
                        $source: plugin.id,
                        timestamp: new Date().toISOString(),
                        values: [
                            {
                                path: 'notifications.navigation.anchor',
                                value: {
                                    state: 'normal',
                                    method: [],
                                    message: 'Boat returned to safe zone'
                                }
                            }
                        ]
                    }
                ]
            }

            app.handleMessage(plugin.id, delta)
            console.log('Alarm cleared successfully')
        } catch (error) {
            console.error('Error clearing alarm notification:', error)
        }
    }

    /**
     * Register PUT handler for setAnchor
     * This is a production feature - sets anchor alarm using current position and rode
     */
    function registerSetAnchorPutHandler() {
        // PUT handler for setAnchor - sets anchor alarm using current position and rode
        // This is the SignalK-standard path accessible from SKipper app and other clients
        // PUT to navigation.anchor.setAnchor with value: true to set the anchor alarm
        // The setAnchor value is automatically maintained by watching navigation.anchor.maxRadius:
        //   - When maxRadius becomes a valid number, setAnchor publishes as true
        //   - When maxRadius becomes null, setAnchor publishes as false
        app.registerPutHandler(
            'vessels.self',
            'navigation.anchor.setAnchor',
            (context, path, _value) => {
                console.log(`[PUT] setAnchor request received`)

                try {
                    // Get current anchor depth from position altitude
                    const anchorPosition = app.getSelfPath('navigation.anchor.position')
                    const rodeDeployedValue = app.getSelfPath('navigation.anchor.rodeDeployed')

                    if (!anchorPosition || !anchorPosition.value) {
                        console.log('[PUT] setAnchor failed: Anchor position not set')
                        return { state: 'COMPLETED', statusCode: 400, message: 'Anchor position not set in SignalK' }
                    }

                    if (!rodeDeployedValue || rodeDeployedValue.value === undefined) {
                        console.log('[PUT] setAnchor failed: Rode deployed not available')
                        return { state: 'COMPLETED', statusCode: 400, message: 'Rode deployed not available in SignalK' }
                    }

                    const currentAnchorDepth = Math.abs(anchorPosition.value.altitude)
                    const currentRodeLength = rodeDeployedValue.value

                    console.log(`[PUT] Setting anchor: depth=${currentAnchorDepth.toFixed(2)}m, rode=${currentRodeLength.toFixed(2)}m`)

                    sendAnchorCommand('setManualAnchor', {
                        anchorDepth: currentAnchorDepth,
                        rodeLength: currentRodeLength,
                    })

                    sendAnchorCommand('setRodeLength', {
                        length: currentRodeLength,
                    })

                    console.log(`[PUT] Anchor set successfully`)
                    return { state: 'COMPLETED', statusCode: 200, message: `Anchor set: depth=${currentAnchorDepth.toFixed(2)}m, rode=${currentRodeLength.toFixed(2)}m` }
                } catch (error) {
                    console.error('[PUT] setAnchor error:', error)
                    return { state: 'COMPLETED', statusCode: 500, message: error.message }
                }
            }
        )
        console.log('PUT handler registered: navigation.anchor.setAnchor')
    }

    return plugin
}
