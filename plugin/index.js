const tokenManager = require('./tokenManager')
const axios = require('axios')
const fs = require('fs').promises
const path = require('path')
/* you need to add a config.json file to your plugin
directory holding the config infor for your install similar 
to 
{
  "serverBaseUrl": "http://localhost",
  "clientId": "a UUID or other client identifier",
  "description": "description of this client"
}

*/
const config = require('./config.json')

//global variables go here
const serverBaseUrl = config.serverBaseUrl
const clientId = config.clientId
const description = config.description
let token = null
let rodeDeployed = 0
let anchorDropped = false
let depth = 0
let rodeLength = 0
let bowHeight = 0
let unsubscribes = []
let anchorSet = false
let lastChainMove = 0
let lastPosition = 0
let lastDepth = 0
let lastCounterConnection = 0
let activeUpdates = 1000
let anchorDepth = 0

// testing
let moveEast = true

module.exports = (app) => {
    const plugin = {
        id: 'signalk-anchorAlarmConnector',
        name: 'anchorAlarmConnector',
        start: async (settings, restartPlugin) => {
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

            // Uncomment line below to run test sequence
            runTestSequence()

            /*delaying 3 seconds so the needed paths 
            can be established at startup*/
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
                    app.getSelfPath('design.bowAnchorHeight')?.value || 0

                console.log(rodeDeployed, anchorDropped, depth, rodeLength)
            }, 3000)
            sendChange('navigation.anchor.autoReady', false)

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
                                    !anchorDropped
                                ) {
                                    sendAnchorCommand('dropAnchor')
                                    lastChainMove = Date.now()
                                    anchorDepth = depth
                                    anchorSet = false
                                }
                                if (
                                    newRode < previousRode &&
                                    anchorDropped &&
                                    newRode < depth + bowHeight
                                ) {
                                    sendAnchorCommand('raiseAnchor')
                                    anchorSet = false
                                    lastChainMove = Date.now()
                                    anchorSet = false
                                }
                                if (newRode != rodeDeployed && anchorDropped) {
                                    lastChainMove = Date.now()
                                    anchorSet = false
                                }
                                rodeDeployed = newRode
                            } else if (path === 'navigation.anchor.position') {
                                // app.debug('Anchor position changed:', value)
                                anchorDropped = value != null
                            } else if (
                                path === 'navigation.anchor.rodeLength'
                            ) {
                                // app.debug('Rode length changed:', value)
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
                            }

                            // autoset radius after 20 minutes of no chain movement 1200000 ms
                            // for testing set to 1 minute 60000 ms

                            if (
                                Date.now() - lastChainMove > 60000 &&
                                !anchorSet
                            ) {
                                // sendAnchorCommand('setRadius')
                                sendAnchorCommand('setRodeLength', {
                                    length: rodeDeployed,
                                })
                                activeUpdates = 20000
                                anchorSet = true
                                anchorDepth = Math.abs(
                                    app.getSelfPath(
                                        'navigation.anchor.position'
                                    ).value.altitude
                                )

                                let scope = rodeDeployed / (anchorDepth + 2)
                                sendChange('navigation.anchor.scope', scope)
                            } else {
                                activeUpdates = 1000
                            }

                            if (
                                lastPosition > Date.now() - 120000 &&
                                lastDepth > Date.now() - 120000 &&
                                lastCounterConnection > Date.now() - 120000
                            ) {
                                sendChange('navigation.anchor.autoReady', true)
                            }
                        })
                    })
                }
            )
        },

        stop: () => {
            unsubscribes.forEach((f) => f())
            unsubscribes = []
        },
        schema: () => {
            return {
                type: 'object',
                required: ['some_string', 'some_other_number'],
                properties: {
                    some_string: {
                        type: 'string',
                        title: 'Some string that the plugin needs',
                    },
                    some_number: {
                        type: 'number',
                        title: 'Some number that the plugin needs',
                        default: 60,
                    },
                    some_other_number: {
                        type: 'number',
                        title: 'Some other number that the plugin needs',
                        default: 5,
                    },
                },
            }
        },
    }
    async function sendChange(path, value) {
        app.handleMessage(
            'netmonitor',
            {
                updates: [
                    {
                        values: [
                            {
                                path: path,
                                value: value,
                            },
                        ],
                    },
                ],
            },
            'v1'
        )
    }
    async function sendAnchorCommand(command, params = {}) {
        if (!token) {
            console.error('No token available. Please authenticate first.')
            return
        }
        // console.log(`Sending "${command}" command with params:`, params)
        // console.log(`Using token: ${token}`)
        try {
            const response = await axios.post(
                `${serverBaseUrl}/plugins/anchoralarm/${command}`,
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
                `Error sending "${command}": `,
                error.response ? error.response.data : error.message
            )
        }
    }
    /* Example usage:
            sendAnchorCommand('dropAnchor');
            sendAnchorCommand('raiseAnchor');
            sendAnchorCommand('setRodeLength', { length: 50 });
            */

    function runTestSequence() {
        console.log('Starting test sequence...')
        sendChange('environment.depth.belowSurface', 5)
        sendChange('navigation.position', {
            longitude: -79.5073,
            latitude: 43.59738,
        })

        console.log(
            'tests running',
            rodeDeployed,
            anchorDropped,
            depth,
            rodeLength
        )
        // east west is +- longitude approx 0.0000624 per 5 meters
        // north south is +- latitude approx 0.0000090 per 1 meter

        setTimeout(() => {
            let position = app.getSelfPath('navigation.position').value
            if (moveEast) {
                position.longitude += 0.0000624
            } else {
                position.longitude -= 0.0000624
            }
            moveEast = !moveEast
            app.debug('Moving east to:', position)
            sendChange('navigation.position', position)
            // repeat every 5 seconds
            setInterval(() => {
                let position = app.getSelfPath('navigation.position').value
                if (moveEast) {
                    position.longitude += 0.0000624
                } else {
                    position.longitude -= 0.0000624
                }
                moveEast = !moveEast
                app.debug('Moving east to:', position)
                sendChange('navigation.position', position)
                if (!anchorSet) {
                    app.debug(
                        'Anchor complete ' +
                            anchorSet +
                            ' lastChainMove ' +
                            lastChainMove +
                            ' Date.now ' +
                            Date.now() +
                            ' diff ' +
                            (Date.now() - lastChainMove)
                    )
                }
                sendChange('environment.depth.belowSurface', 5)
            }, 5000)
        }, 15000)

        setTimeout(() => {
            let position = app.getSelfPath('navigation.position').value
            let depth = app.getSelfPath('environment.depth.belowSurface').value
            let rodeDeployed = app.getSelfPath(
                'navigation.anchor.rodeDeployed'
            )?.value
            let distance = app.getSelfPath(
                'navigation.anchor.distanceFromBow'
            )?.value
            let movetodo = rodeDeployed * 0.9 - distance
            if (movetodo > 1) {
                position.latitude -= 0.000009
                sendChange('navigation.position', position)
                console.log('moved south')
            }
            // repeat every 2 seconds
            setInterval(() => {
                let position = app.getSelfPath('navigation.position').value
                let depth = app.getSelfPath(
                    'environment.depth.belowSurface'
                ).value
                let rodeDeployed = app.getSelfPath(
                    'navigation.anchor.rodeDeployed'
                ).value
                let distance = app.getSelfPath(
                    'navigation.anchor.distanceFromBow'
                )?.value
                let movetodo = rodeDeployed * 0.9 - distance
                if (movetodo > 1) {
                    position.latitude -= 0.000009
                    sendChange('navigation.position', position)
                    console.log('moved south again')
                }
            }, 2000)
        }, 22000)

        //uncomment below to run test sequence that drops and raises anchor
        // wait 35 seconds then drop anchor
        // setTimeout(() => {
        //     sendAnchorCommand('dropAnchor')

        //     setTimeout(() => {
        //         sendChange('navigation.position', {
        //             longitude: -79.38,
        //             latitude: 43.649823,
        //         })
        //         sendAnchorCommand('setRodeLength', { length: 50 })
        //         // wait another 5 seconds then raise anchor
        //         setTimeout(() => {
        //             sendAnchorCommand('raiseAnchor')
        //         }, 35000)
        //     }, 5000)
        // }, 3000)
    }

    return plugin
}
